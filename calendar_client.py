"""
Google Calendar への予定登録（サービスアカウント認証）。

前提:
  - Google Cloud で Calendar API を有効化したサービスアカウントのJSON鍵。
  - 対象カレンダーをそのサービスアカウントのメールに「予定の変更」権限で共有済み。
"""

from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]


def build_service(key_path):
    creds = service_account.Credentials.from_service_account_file(
        key_path, scopes=SCOPES
    )
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def build_event_body(parsed, tz="Asia/Tokyo"):
    """dateparse.parse_event() の戻り値を events.insert のbodyに変換。"""
    if parsed["all_day"]:
        return {
            "summary": parsed["title"],
            "start": {"date": parsed["start"].date().isoformat()},
            "end": {"date": parsed["end"].date().isoformat()},
        }
    return {
        "summary": parsed["title"],
        "start": {"dateTime": parsed["start"].isoformat(), "timeZone": tz},
        "end": {"dateTime": parsed["end"].isoformat(), "timeZone": tz},
    }


def insert_event(service, calendar_id, parsed, tz="Asia/Tokyo"):
    body = build_event_body(parsed, tz)
    return service.events().insert(calendarId=calendar_id, body=body).execute()
