# discord-calendar-bot

Discord から決まったコマンドで Google カレンダーに予定を追加する**独立bot**。
Claude / Anthropic API には依存しない（純Pythonパース）。サービスアカウント認証で、どのサーバーでも常駐できる。

```
!cal 9/5 18:00 歯医者
!cal 明日 15:00 散歩
!cal 来週火曜 10:00 面談
!cal 9/10 終日 帰省
```

---

## セットアップ

### 1. Discord bot を作る
1. https://discord.com/developers/applications → **New Application**
2. 左メニュー **Bot** → **Reset Token** でトークンを取得（後で `.env` に入れる）
3. 同ページの **Privileged Gateway Intents** で **MESSAGE CONTENT INTENT** を **ON**
4. 左メニュー **OAuth2 > URL Generator** → scope `bot` を選び、権限 `Send Messages` / `Read Message History` にチェック → 生成URLで自分のサーバーに招待

### 2. Google 側（サービスアカウント）
1. https://console.cloud.google.com/ でプロジェクトを作成（既存でも可）
2. **APIとサービス > ライブラリ** で **Google Calendar API** を有効化
3. **APIとサービス > 認証情報 > 認証情報を作成 > サービスアカウント** を作成
4. 作成したサービスアカウントを開く → **キー > 鍵を追加 > 新しい鍵 > JSON** をダウンロード
   → このファイルを `service_account.json` としてこのフォルダに置く
5. サービスアカウントのメールアドレス（`xxxx@yyyy.iam.gserviceaccount.com`）をコピー

### 3. カレンダーをサービスアカウントに共有（重要）
サービスアカウントは他人。あなたのカレンダーに書かせるには共有が必要。

1. PCの Google カレンダーを開く
2. 書き込み先カレンダーの **設定と共有**
3. **特定のユーザーやグループと共有** → 手順2-5でコピーしたサービスアカウントのメールを追加
4. 権限を **「予定の変更権限」** にする
5. 同じ設定画面の **「カレンダーの統合」** にある **カレンダー ID** をコピー（`.env` の `CALENDAR_ID` に入れる。個人の主カレンダーなら通常あなたのGmailアドレス）

> メモ: サービスアカウントは Google カレンダーの `primary`（主カレンダー）エイリアスには書けない。
> 上記のように**実際のカレンダーIDを指定して共有**すれば、あなたの普段のカレンダーにそのまま予定が入る。

### 4. 環境変数
`.env.example` をコピーして `.env` を作り、値を埋める:

```
DISCORD_BOT_TOKEN=（手順1のトークン）
CALENDAR_ID=（手順3のカレンダーID）
SERVICE_ACCOUNT_FILE=service_account.json
ALLOWED_CHANNEL_IDS=（任意。反応させるチャンネルを限定するなら）
```

---

## 起動

### ローカル / VPS（直接）
```bash
pip install -r requirements.txt
python bot.py
```

### Docker（VPS推奨・常駐）
`.env` と `service_account.json` をこのフォルダに置いた状態で:
```bash
docker compose up -d --build
docker compose logs -f      # ログ確認
```

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

## パーサ単体テスト
Discord/Google 無しで日時解釈だけ確認できる:
```bash
python dateparse.py
```
