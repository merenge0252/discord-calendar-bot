# セットアップ手順シート（常駐PCの担当者向け）

このPCで **Discord → Google カレンダー登録bot** を常駐させるための手順です。
このPCの**共有Googleアカウントにブラウザでログインした状態**で、上から順にやればOK。
所要時間およそ20〜30分。専門知識は不要です。

> 秘密情報（トークン・鍵ファイル）はこのPCの中で作ってこの中に置くだけ。**どこにも貼らない・送らない**でください。

---

## 手順① Discord bot を作る

1. https://discord.com/developers/applications を開く → **New Application**（名前は何でもOK、例: `cal-bot`）
2. 左メニュー **Bot** → **Reset Token** を押して表示された**トークンをコピー**
   → 一旦メモ帳に貼っておく（あとで `.env` に入れます）
3. （このbotは**スラッシュコマンド（`/cal`）方式**なので、**MESSAGE CONTENT INTENT は不要**です。ここは触らなくてOK）
4. 左メニュー **OAuth2 → URL Generator**
   - SCOPES: `bot` と **`applications.commands`** の両方にチェック（★`applications.commands` を忘れると `/cal` が出ません）
   - BOT PERMISSIONS: `Send Messages` にチェック
   - 一番下に出るURLをコピー
5. そのURLをブラウザで開き、**botを使いたいDiscordサーバー**を選んで招待

   > ★ **依頼者に確認**: どのDiscordサーバーに入れるか／どのチャンネルで使うか。
   > 招待URLは「サーバーの管理」権限を持つ人（＝依頼者の可能性大）に開いてもらってもOK。

---

## 手順② Google Cloud でサービスアカウントを作る

このPCの共有Googleアカウントでログインしたまま行います。

1. https://console.cloud.google.com/ を開く → 上部でプロジェクトを**新規作成**（名前は何でも、例: `cal-bot`）
2. 上の検索窓で **「Google Calendar API」** を検索 → 開いて **「有効にする」**
3. 左メニュー **APIとサービス → 認証情報** → 上部 **「＋認証情報を作成」→「サービスアカウント」**
   - 名前を入力（例: `cal-bot-sa`）→ 作成して続行 → そのまま「完了」
4. 作成されたサービスアカウントをクリック → 上部タブ **「キー」** → **「鍵を追加」→「新しい鍵を作成」→「JSON」** → 作成
   → JSONファイルが自動ダウンロードされる
5. そのJSONファイルを、このリポジトリのフォルダに **`service_account.json`** という名前で置く
   （手順④でフォルダを用意します。ダウンロードフォルダに置いておいて後で移動でもOK）
6. サービスアカウントのメールアドレス（`〜@〜.iam.gserviceaccount.com` の形）を**コピー**しておく

---

## 手順③ カレンダーをサービスアカウントに共有する

同じ共有Googleアカウントの Google カレンダーで行います。

1. https://calendar.google.com/ を開く
2. 左の「マイカレンダー」で予定を入れたいカレンダーにマウスを乗せ、︙→ **「設定と共有」**
   （主カレンダーでOK。名前は共有アカウントのメアドになっているはず）
3. **「特定のユーザーやグループと共有する」→「ユーザーやグループを追加」**
   → 手順②-6でコピーした**サービスアカウントのメール**を追加
4. 権限を **「予定の変更権限」** にする（★「閲覧」だと登録できません）
5. 同じ設定画面を下にスクロール → **「カレンダーの統合」** の中の **「カレンダー ID」** をコピー
   （主カレンダーなら、この共有アカウントのメアドがそのままIDです）
   → メモ帳に貼っておく（`.env` に入れます）

   > ★ コピーするのは必ず**この「カレンダー ID」の文字列**（主カレンダーならメアドそのもの）。
   > `primary` という語をそのまま `.env` に入れてもサービスアカウントでは書き込めません。

---

## 手順④ プロジェクトを用意して設定を書く

1. このPCに **Git** と **Docker Desktop** を入れる
   - Git: https://git-scm.com/download/win
   - Docker Desktop: https://www.docker.com/products/docker-desktop/
2. 適当な場所でコマンドプロンプト（またはPowerShell）を開いて:
   ```
   git clone https://github.com/merenge0252/discord-calendar-bot.git
   cd discord-calendar-bot
   ```
3. 手順②でDLした **`service_account.json`** を、この `discord-calendar-bot` フォルダの直下に置く
4. 同じフォルダの **`.env.example`** をコピーして **`.env`** を作り、メモ帳で開いて記入:
   ```
   DISCORD_BOT_TOKEN=（手順①-2でコピーしたトークン）
   CALENDAR_ID=（手順③-5でコピーしたカレンダーID）
   SERVICE_ACCOUNT_FILE=service_account.json
   GUILD_ID=（botを使うDiscordサーバーのID。下記参照）
   ALLOWED_CHANNEL_IDS=
   ```
   - `GUILD_ID` を入れると、そのサーバーで**起動直後に `/cal` が使える**ようになります（おすすめ）。
     サーバーIDは、Discordの設定→詳細設定→「開発者モード」をONにし、サーバー名を右クリック →「サーバーIDをコピー」で取得。
     空のままだと全サーバー共通の登録になり、**反映に最大1時間**かかります。
   - `ALLOWED_CHANNEL_IDS` は空でOK（全チャンネルで反応）。特定チャンネルだけにしたい場合のみIDを入れる。

---

## 手順⑤ 起動する（常駐）

`discord-calendar-bot` フォルダで:
```
docker compose up -d --build
```
- これで起動。`restart: unless-stopped` 設定済みなので、**PCを再起動してもDockerが動いていれば自動で立ち上がります**。
- ★ **PC起動時に自動で動かす**には、Docker Desktop の設定 → **General → 「Start Docker Desktop when you sign in to your computer」を ON** にしておく。

ログを見る:
```
docker compose logs -f
```
`サービスアカウント認証OK` → `スラッシュコマンド同期 ...` → `Bot起動: ...` が出れば成功。
（`スラッシュコマンド同期(guild=...)` なら即時反映、`(global)` なら反映に最大1時間）

> **Dockerを使いたくない場合**（Python直実行）:
> ```
> pip install -r requirements.txt
> python bot.py
> ```
> ただしこの方法だとPC再起動で止まるので、常駐にはタスクスケジューラ登録が必要。Docker推奨。

---

## 動作確認

botを入れたDiscordチャンネルで、メッセージ欄に **`/`** を打つとコマンド候補が出ます。
（出てこない場合は下の「うまくいかないとき」を参照）

- **`/ping`** → `pong 🏓` が返ればDiscord接続OK。
- **`/cal`** → `日付` と `タイトル` を入れる（`開始`・`終了` は任意）。
  - 各欄は入力すると**候補（サジェスト）が出る**ので、書式を覚えなくても選べます。
  - `開始` と `終了` の両方を入れると **時間枠**（例: 18:00〜20:00）になります。
  - `開始` だけなら開始から1時間、`開始` を空にする／`終日` を ON にすると終日予定。
  - 実行して `✅ 予定を追加しました` が返り、共有アカウントのGoogleカレンダーに予定が入っていれば**完成**。

---

## うまくいかないとき

| 症状 | 原因と対処 |
|---|---|
| `/` を打っても `/cal` `/ping` が出ない | ①招待URLに **`applications.commands` スコープ**が付いていない（手順①-4）→ 付けて招待し直す。②`.env` の `GUILD_ID` が空だとグローバル登録で**最大1時間**かかる → すぐ使うなら `GUILD_ID` を入れて `docker compose restart`。③反映後、Discordアプリを再読み込み（Ctrl+R）すると出ることがある |
| 登録時に「登録に失敗」`403` | 手順③のカレンダー共有ができていない／権限が「閲覧」になっている。**「予定の変更権限」**で共有し直す |
| 登録時に「登録に失敗」`404` | `.env` の `CALENDAR_ID` が違う。手順③-5のIDを再確認 |
| 起動時に「鍵が見つかりません」 | `service_account.json` がフォルダ直下に無い。名前とパスを確認 |
| 起動時に「DISCORD_BOT_TOKEN が…」 | `.env` が作れていない／記入ミス |

設定を直したら再起動: `docker compose restart`（Python直実行なら `python bot.py` を止めて再実行）

---

困ったら、この手順の何番で詰まったかを依頼者に伝えてください。
