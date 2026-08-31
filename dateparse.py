"""
!cal コマンドの日本語日時パーサ（純Python・外部API不使用）。

書式:
    <日付> [<時刻|時刻範囲|終日>] <タイトル...>

日付トークン:
    9/5, 2026/9/5, 9-5, 9月5日, 2026年9月5日
    今日 / 明日 / 明後日 / 明々後日 / 昨日
    月曜〜日曜（曜日）, 今週火曜 / 来週火曜 / 再来週火曜

時刻トークン（省略時は終日扱い）:
    18:00, 18時, 18時30分, 18時半, 午後6時
    18:00-20:00, 18:00〜20:00, 18時から20時まで
    終日 / 全日 / 1日
"""

import re
from datetime import date, datetime, timedelta, time
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Tokyo")
DEFAULT_DURATION = timedelta(hours=1)  # 終了未指定の予定の長さ

_WD = {"月": 0, "火": 1, "水": 2, "木": 3, "金": 4, "土": 5, "日": 6}
_WEEK_OFFSET = {"今週": 0, "来週": 1, "再来週": 2}
_ALLDAY = {"終日", "全日", "1日", "一日", "終日予定"}
_RANGE_SEP = re.compile(r"\s*(?:から|〜|~|-|–|—|−|to)\s*")


class ParseError(Exception):
    pass


def _today(now):
    return now.date()


def _parse_date_token(tok, now):
    """日付トークンを date に。解釈できなければ None。"""
    today = _today(now)

    # 相対語
    rel = {"今日": 0, "本日": 0, "明日": 1, "あした": 1, "みょうにち": 1,
           "明後日": 2, "あさって": 2, "明々後日": 3, "明明後日": 3, "しあさって": 3,
           "昨日": -1}
    if tok in rel:
        return today + timedelta(days=rel[tok])

    # 曜日（[今週|来週|再来週]?<曜>曜(日)?）
    m = re.fullmatch(r"(今週|来週|再来週)?([月火水木金土日])曜(?:日)?", tok)
    if m:
        offset_word, wd_kanji = m.group(1), m.group(2)
        target_wd = _WD[wd_kanji]
        monday = today - timedelta(days=today.weekday())  # 今週の月曜
        if offset_word:
            monday += timedelta(weeks=_WEEK_OFFSET[offset_word])
            return monday + timedelta(days=target_wd)
        # 接頭辞なし: 今日以降で最も近いその曜日（今日が該当なら今日）
        delta = (target_wd - today.weekday()) % 7
        return today + timedelta(days=delta)

    # YYYY年M月D日 / M月D日
    m = re.fullmatch(r"(?:(\d{4})年)?(\d{1,2})月(\d{1,2})日?", tok)
    if m:
        return _ymd(m.group(1), m.group(2), m.group(3), today)

    # YYYY/M/D | M/D | YYYY-M-D | M-D
    m = re.fullmatch(r"(?:(\d{4})[/-])?(\d{1,2})[/-](\d{1,2})", tok)
    if m:
        return _ymd(m.group(1), m.group(2), m.group(3), today)

    return None


def _ymd(y, mo, d, today):
    mo, d = int(mo), int(d)
    if y:
        year = int(y)
    else:
        # 年省略: 今年で作り、既に過ぎていれば翌年に送る（予定は未来という前提）
        year = today.year
        try:
            cand = date(year, mo, d)
        except ValueError:
            raise ParseError(f"存在しない日付です: {mo}/{d}")
        if cand < today:
            year += 1
    try:
        return date(year, mo, d)
    except ValueError:
        raise ParseError(f"存在しない日付です: {mo}/{d}")


def _parse_clock(s):
    """単一の時刻表現を time に。解釈できなければ None。"""
    s = s.strip()
    if not s:
        return None
    pm = None
    if s.startswith("午前") or s.upper().startswith("AM"):
        pm = False
        s = re.sub(r"^(午前|AM)", "", s, flags=re.IGNORECASE).strip()
    elif s.startswith("午後") or s.upper().startswith("PM"):
        pm = True
        s = re.sub(r"^(午後|PM)", "", s, flags=re.IGNORECASE).strip()

    hour = minute = None
    # HH:MM
    m = re.fullmatch(r"(\d{1,2}):(\d{2})", s)
    if m:
        hour, minute = int(m.group(1)), int(m.group(2))
    else:
        # H時(M分)? / H時半
        m = re.fullmatch(r"(\d{1,2})時(半|(\d{1,2})分?)?", s)
        if m:
            hour = int(m.group(1))
            if m.group(2) == "半":
                minute = 30
            elif m.group(3):
                minute = int(m.group(3))
            else:
                minute = 0
        elif re.fullmatch(r"\d{1,2}", s) and pm is not None:
            # 「午後6」のような裸の数字（午前/午後付きのときだけ許可）
            hour, minute = int(s), 0

    if hour is None:
        return None
    if pm is True and hour < 12:
        hour += 12
    if pm is False and hour == 12:
        hour = 0
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ParseError(f"時刻が不正です: {s}")
    return time(hour, minute)


def _parse_time_token(tok):
    """
    時刻トークンを解釈。戻り値:
        ("allday", None, None)                終日
        ("timed", start_time, end_time|None)  時刻あり
        None                                  時刻トークンではない
    """
    if tok in _ALLDAY:
        return ("allday", None, None)
    parts = _RANGE_SEP.split(tok)
    parts = [p for p in parts if p not in ("", "まで")]
    if len(parts) == 1:
        st = _parse_clock(parts[0])
        return ("timed", st, None) if st else None
    if len(parts) == 2:
        st = _parse_clock(parts[0])
        en = _parse_clock(parts[1])
        if st and en:
            return ("timed", st, en)
        return None
    return None


def parse_event(content, now=None):
    """
    !cal の本文を解釈して予定 dict を返す。
        {"all_day": bool, "start": datetime, "end": datetime, "title": str}
    解釈できない場合は ParseError。now は Asia/Tokyo の aware datetime（テスト用）。
    """
    if now is None:
        now = datetime.now(TZ)

    tokens = content.split()
    if not tokens:
        raise ParseError("内容が空です。")

    the_date = _parse_date_token(tokens[0], now)
    if the_date is None:
        raise ParseError(
            f"日付を認識できませんでした: 「{tokens[0]}」\n"
            "例: `9/5`, `明日`, `来週火曜`, `2026年9月5日`"
        )
    rest = tokens[1:]

    time_info = None
    if rest:
        time_info = _parse_time_token(rest[0])
        if time_info is not None:
            rest = rest[1:]

    title = " ".join(rest).strip()
    if not title:
        raise ParseError("予定のタイトルがありません。例: `!cal 明日 15:00 歯医者`")

    # 時刻トークンが無い、または終日指定 → 終日予定
    if time_info is None or time_info[0] == "allday":
        start = datetime.combine(the_date, time(0, 0), TZ)
        end = start + timedelta(days=1)
        return {"all_day": True, "start": start, "end": end, "title": title}

    _, st, en = time_info
    start = datetime.combine(the_date, st, TZ)
    if en is None:
        end = start + DEFAULT_DURATION
    else:
        end = datetime.combine(the_date, en, TZ)
        if end <= start:  # 日跨ぎ（22:00-2:00 等）は翌日終了とみなす
            end += timedelta(days=1)
    return {"all_day": False, "start": start, "end": end, "title": title}


if __name__ == "__main__":
    # 単体テスト（Discord/Google 不要）
    now = datetime(2026, 8, 31, 12, 0, tzinfo=TZ)  # 2026-08-31 は月曜
    cases = [
        "9/5 18:00 歯医者",
        "9/5 18:00-20:00 ゼミ飲み会",
        "明日 15:00 散歩",
        "9/10 終日 帰省",
        "9/5 歯医者",
        "来週火曜 10:00 面談",
        "今日 18時半 ジム",
        "2026年12月31日 23:00 年越し",
        "9/5 午後6時 通院",
        "9/1 22:00-2:00 夜勤",
    ]
    for c in cases:
        try:
            r = parse_event(c, now=now)
            s = r["start"].strftime("%Y-%m-%d(%a) %H:%M")
            e = r["end"].strftime("%H:%M")
            kind = "終日" if r["all_day"] else f"{s}〜{e}"
            print(f"OK  | {c:28} -> [{r['title']}] {kind}")
        except ParseError as ex:
            print(f"ERR | {c:28} -> {ex}")
