"""
Google カレンダー登録 Discord bot（スラッシュコマンド版・サービスアカウント認証）。

スラッシュコマンド:
    /cal 日付:<...> タイトル:<...> [開始:<...>] [終了:<...>] [終日:true/false]
    /ping   疎通確認

日付・開始・終了は入力途中に候補（サジェスト）が出るので、書式を覚えなくても選べる。
開始と終了を両方入れれば時間枠（例 18:00〜20:00）になる。
Claude / Anthropic API には一切依存しない。
"""

import os
import logging
from datetime import datetime, timedelta, time
from typing import Optional

import discord
from discord import app_commands
from dotenv import load_dotenv

from dateparse import _parse_date_token, _parse_clock, ParseError, TZ, DEFAULT_DURATION
from calendar_client import build_service, insert_event

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("cal-bot")

TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
CALENDAR_ID = os.environ.get("CALENDAR_ID")
KEY_PATH = os.environ.get("SERVICE_ACCOUNT_FILE", "service_account.json")
GUILD_ID = os.environ.get("GUILD_ID", "").strip()
ALLOWED_CHANNEL_IDS = {
    int(c) for c in os.environ.get("ALLOWED_CHANNEL_IDS", "").replace(" ", "").split(",") if c
}

# サービスアカウント接続は起動時に1度だけ構築（main で代入）
service = None

_WD = "月火水木金土日"
# 08:00〜23:30 → 00:00〜07:30 の順（サジェスト先頭を日中に）
_TIME_SLOTS = [
    f"{h:02d}:{m:02d}"
    for h in list(range(8, 24)) + list(range(0, 8))
    for m in (0, 30)
]


def format_confirmation(parsed):
    wd = _WD[parsed["start"].weekday()]
    d = parsed["start"].strftime(f"%Y-%m-%d({wd})")
    if parsed["all_day"]:
        when = f"{d} 終日"
    else:
        st = parsed["start"].strftime("%H:%M")
        en = parsed["end"].strftime("%H:%M")
        when = f"{d} {st}〜{en}"
    return f"✅ 予定を追加しました\n📌 {parsed['title']}\n🗓 {when}"


# ---- サジェスト（autocomplete）候補 ----

def _date_choices(current):
    now = datetime.now(TZ)
    today = now.date()
    out = []  # (label, value)
    for word, off in (("今日", 0), ("明日", 1), ("明後日", 2)):
        d = today + timedelta(days=off)
        out.append((f"{word}（{d.month}/{d.day} {_WD[d.weekday()]}）", word))
    for off in range(3, 21):
        d = today + timedelta(days=off)
        out.append((f"{d.month}/{d.day}（{_WD[d.weekday()]}）", f"{d.year}/{d.month}/{d.day}"))
    cur = current.strip()
    if cur:
        out = [(lbl, val) for lbl, val in out if cur in lbl or cur in val]
    return out[:25]


def _time_choices(current):
    cur = current.strip()
    slots = [t for t in _TIME_SLOTS if t.startswith(cur)] if cur else _TIME_SLOTS
    return slots[:25]


async def date_autocomplete(interaction: discord.Interaction, current: str):
    return [app_commands.Choice(name=lbl, value=val) for lbl, val in _date_choices(current)]


async def time_autocomplete(interaction: discord.Interaction, current: str):
    return [app_commands.Choice(name=t, value=t) for t in _time_choices(current)]


class CalBot(discord.Client):
    def __init__(self):
        # スラッシュコマンドのみ使用するので message_content 等の特権intentは不要
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        # コマンド登録（同期）。GUILD_ID があればそのサーバーへ即時反映、無ければグローバル。
        try:
            if GUILD_ID:
                guild = discord.Object(id=int(GUILD_ID))
                self.tree.copy_global_to(guild=guild)
                synced = await self.tree.sync(guild=guild)
                log.info("スラッシュコマンド同期(guild=%s): %d件", GUILD_ID, len(synced))
            else:
                synced = await self.tree.sync()
                log.info("スラッシュコマンド同期(global): %d件 ※全サーバー反映に最大1時間", len(synced))
        except Exception:
            log.exception("コマンド同期に失敗しました")


client = CalBot()
tree = client.tree


@client.event
async def on_ready():
    log.info("Bot起動: %s", client.user)
    log.info("カレンダーID: %s", CALENDAR_ID)
    if ALLOWED_CHANNEL_IDS:
        log.info("許可チャンネル: %s", sorted(ALLOWED_CHANNEL_IDS))
    else:
        log.info("許可チャンネル: 未設定（全チャンネルで反応）")


@tree.command(name="ping", description="botの疎通確認")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("pong 🏓", ephemeral=True)


@tree.command(name="cal", description="Google カレンダーに予定を追加します")
@app_commands.rename(date="日付", title="タイトル", start="開始", end="終了", allday="終日")
@app_commands.describe(
    date="日付（例: 今日 / 明日 / 9/5 / 来週火曜）※入力すると候補が出ます",
    title="予定のタイトル（例: 歯医者）",
    start="開始時刻（例: 18:00）。省略すると終日予定になります",
    end="終了時刻（例: 20:00）。省略すると開始から1時間",
    allday="終日予定にする（ON なら時刻は無視）",
)
@app_commands.autocomplete(date=date_autocomplete, start=time_autocomplete, end=time_autocomplete)
async def add_event(
    interaction: discord.Interaction,
    date: str,
    title: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
    allday: bool = False,
):
    if ALLOWED_CHANNEL_IDS and interaction.channel_id not in ALLOWED_CHANNEL_IDS:
        await interaction.response.send_message(
            "このチャンネルでは使えません。", ephemeral=True
        )
        return

    title = title.strip()
    if not title:
        await interaction.response.send_message(
            "⚠ タイトルを入力してください。", ephemeral=True
        )
        return

    now = datetime.now(TZ)
    try:
        the_date = _parse_date_token(date.strip(), now)
    except ParseError as e:
        await interaction.response.send_message(f"⚠ {e}", ephemeral=True)
        return
    if the_date is None:
        await interaction.response.send_message(
            f"⚠ 日付を認識できませんでした: 「{date}」\n"
            "例: `今日` `明日` `9/5` `来週火曜` `2026年9月5日`",
            ephemeral=True,
        )
        return

    try:
        if allday or not start:
            start_dt = datetime.combine(the_date, time(0, 0), TZ)
            parsed = {
                "all_day": True,
                "start": start_dt,
                "end": start_dt + timedelta(days=1),
                "title": title,
            }
        else:
            st = _parse_clock(start.strip())
            if st is None:
                raise ParseError(f"開始時刻を認識できませんでした: 「{start}」（例: 18:00）")
            start_dt = datetime.combine(the_date, st, TZ)
            if end and end.strip():
                en = _parse_clock(end.strip())
                if en is None:
                    raise ParseError(f"終了時刻を認識できませんでした: 「{end}」（例: 20:00）")
                end_dt = datetime.combine(the_date, en, TZ)
                if end_dt <= start_dt:  # 日跨ぎ（22:00-2:00 等）は翌日終了とみなす
                    end_dt += timedelta(days=1)
            else:
                end_dt = start_dt + DEFAULT_DURATION
            parsed = {
                "all_day": False,
                "start": start_dt,
                "end": end_dt,
                "title": title,
            }
    except ParseError as e:
        await interaction.response.send_message(f"⚠ {e}", ephemeral=True)
        return

    # Calendar API が数秒かかることがあるので先に defer（3秒制限対策）
    await interaction.response.defer()
    try:
        insert_event(service, CALENDAR_ID, parsed)
    except Exception as e:
        log.exception("insert error")
        await interaction.followup.send(
            f"⚠ カレンダー登録に失敗しました。\n`{e}`\n"
            "サービスアカウントへのカレンダー共有設定を確認してください。"
        )
        return

    await interaction.followup.send(format_confirmation(parsed))


def main():
    global service
    if not TOKEN:
        raise SystemExit("環境変数 DISCORD_BOT_TOKEN が設定されていません。")
    if not CALENDAR_ID:
        raise SystemExit("環境変数 CALENDAR_ID が設定されていません。")
    if not os.path.exists(KEY_PATH):
        raise SystemExit(f"サービスアカウント鍵が見つかりません: {KEY_PATH}")
    # 鍵の妥当性をここで確認（失敗なら即終了して原因を明示）
    service = build_service(KEY_PATH)
    log.info("サービスアカウント認証OK")
    client.run(TOKEN)


if __name__ == "__main__":
    main()
