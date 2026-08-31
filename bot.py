"""
Google カレンダー登録 Discord bot（独立版・サービスアカウント認証・純Pythonパース）。

コマンド:
    !cal <日付> [<時刻|時刻範囲|終日>] <タイトル...>
    !cal            使い方を表示
    !calhelp        使い方を表示
    !ping           疎通確認

Claude / Anthropic API には一切依存しない。
"""

import os
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import discord
from dotenv import load_dotenv

from dateparse import parse_event, ParseError, TZ
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
ALLOWED_CHANNEL_IDS = {
    int(c) for c in os.environ.get("ALLOWED_CHANNEL_IDS", "").replace(" ", "").split(",") if c
}

HELP_TEXT = (
    "**🗓 カレンダー登録bot の使い方**\n"
    "```\n"
    "!cal <日付> [<時刻|時刻範囲|終日>] <タイトル>\n"
    "```\n"
    "**例**\n"
    "・`!cal 9/5 18:00 歯医者`\n"
    "・`!cal 9/5 18:00-20:00 ゼミ飲み会`\n"
    "・`!cal 明日 15:00 散歩`\n"
    "・`!cal 来週火曜 10:00 面談`\n"
    "・`!cal 9/10 終日 帰省`\n"
    "・`!cal 9/5 歯医者`（時刻なし → 終日）\n\n"
    "**日付**: `9/5` `2026/9/5` `9月5日` `今日` `明日` `明後日` `今週/来週/再来週+曜日`\n"
    "**時刻**: `18:00` `18時` `18時半` `午後6時` `18:00-20:00` `18時から20時まで`\n"
    "終了時刻を省くと1時間の予定になります。"
)


def format_confirmation(parsed):
    wd = "月火水木金土日"[parsed["start"].weekday()]
    d = parsed["start"].strftime(f"%Y-%m-%d({wd})")
    if parsed["all_day"]:
        when = f"{d} 終日"
    else:
        st = parsed["start"].strftime("%H:%M")
        en = parsed["end"].strftime("%H:%M")
        when = f"{d} {st}〜{en}"
    return f"✅ 予定を追加しました\n📌 {parsed['title']}\n🗓 {when}"


intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# サービスアカウントの接続は起動時に1度だけ構築
service = None


@client.event
async def on_ready():
    log.info("Bot起動: %s", client.user)
    log.info("カレンダーID: %s", CALENDAR_ID)
    if ALLOWED_CHANNEL_IDS:
        log.info("許可チャンネル: %s", sorted(ALLOWED_CHANNEL_IDS))
    else:
        log.info("許可チャンネル: 未設定（全チャンネルで反応）")


@client.event
async def on_message(message):
    if message.author == client.user:
        return
    if ALLOWED_CHANNEL_IDS and message.channel.id not in ALLOWED_CHANNEL_IDS:
        return

    content = message.content.strip()

    if content == "!ping":
        await message.channel.send("pong 🏓")
        return

    if content in ("!calhelp", "!help"):
        await message.channel.send(HELP_TEXT)
        return

    if content == "!cal" or content.startswith("!cal "):
        body = content[len("!cal"):].strip()
        if not body:
            await message.channel.send(HELP_TEXT)
            return
        try:
            parsed = parse_event(body, now=datetime.now(TZ))
        except ParseError as e:
            await message.channel.send(f"⚠ {e}")
            return
        except Exception as e:  # 想定外のパース失敗
            log.exception("parse error")
            await message.channel.send(f"⚠ 解釈に失敗しました: {e}")
            return

        try:
            insert_event(service, CALENDAR_ID, parsed)
        except Exception as e:
            log.exception("insert error")
            await message.channel.send(
                f"⚠ カレンダー登録に失敗しました。\n`{e}`\n"
                "サービスアカウントへのカレンダー共有設定を確認してください。"
            )
            return

        await message.channel.send(format_confirmation(parsed))
        return


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
