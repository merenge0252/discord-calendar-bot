# discord-calendar-bot

Discord から決まったコマンドで Google カレンダーに予定を追加する**独立bot**。
Claude / Anthropic API には依存しない（純Pythonパース）。サービスアカウント認証で、どのサーバーでも常駐できる。

```
!cal 9/5 18:00 歯医者
!cal 明日 15:00 散歩
!cal 来週火曜 10:00 面談
!cal 9/10 終日 帰省
```

> 🛠 **セットアップする方へ**: Discord bot 作成・サービスアカウント発行・カレンダー共有・`.env` 設定・Docker常駐まで、上から順にやるだけの手順シート **[SETUP.md](SETUP.md)** にまとめています。まずそちらを参照してください。

---

## コマンド

| コマンド | 動作 |
|---|---|
| `!cal <日付> [時刻] <タイトル>` | 予定を追加 |
| `!cal` / `!calhelp` | 使い方を表示 |
| `!ping` | 疎通確認 |

**日付**: `9/5` `2026/9/5` `9月5日` `今日` `明日` `明後日` `今週/来週/再来週+曜日`
**時刻**: `18:00` `18時` `18時半` `午後6時` `18:00-20:00` `18時から20時まで`
時刻を省くと**終日**、終了だけ省くと**1時間**の予定になる。

---

## 開発者向け

Discord bot 作成・サービスアカウント・カレンダー共有・`.env` 記入の詳細手順は **[SETUP.md](SETUP.md)** を参照。
`.env` と `service_account.json` を用意したうえで:

### 直接実行
```bash
pip install -r requirements.txt
python bot.py
```

Docker での常駐起動は **[SETUP.md 手順⑤](SETUP.md)** を参照。

### パーサ単体テスト
Discord / Google 無しで日時解釈だけ確認できる:
```bash
python dateparse.py
```

### 構成
| ファイル | 役割 |
|---|---|
| `bot.py` | Discord クライアント・コマンド処理 |
| `dateparse.py` | 日本語の日付・時刻パース（純Python） |
| `calendar_client.py` | Google Calendar への予定登録 |
