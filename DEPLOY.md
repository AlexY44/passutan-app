# パス単 準1級 — Streamlit Community Cloud デプロイ手順

## 全体の流れ（所要時間：約15分）

```
Supabase でDBを作る → GitHub にpush → Streamlit Cloud でデプロイ → Secrets を設定
```

---

## STEP 1: Supabase でデータベースを作る（無料）

1. https://supabase.com にアクセス → **Start your project** でアカウント作成

2. **New project** をクリック
   - Project name: `passutan`（なんでも可）
   - Database Password: 任意（メモしておく）
   - Region: `Northeast Asia (Tokyo)` を選択
   - → **Create new project**（1〜2分かかります）

3. 左メニュー **SQL Editor** を開き、以下を貼り付けて **Run**

```sql
CREATE TABLE progress (
  word_no   INTEGER PRIMARY KEY,
  status    TEXT NOT NULL DEFAULT 'new',
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 匿名アクセスを許可（RLSは無効化）
ALTER TABLE progress DISABLE ROW LEVEL SECURITY;
```

4. 左メニュー **Project Settings → API** を開き、以下をメモ

   - **Project URL** → `https://xxxxxxxxxx.supabase.co`
   - **anon public** キー → `eyJhbGci...` （長い文字列）

---

## STEP 2: GitHub にリポジトリを作る

1. https://github.com でログイン → **New repository**
   - Repository name: `passutan-app`
   - Public / Private どちらでも可
   - → **Create repository**

2. このフォルダをアップロード
   ```bash
   # zipを解凍したフォルダで実行
   git init
   git add .
   git commit -m "initial commit"
   git branch -M main
   git remote add origin https://github.com/あなたのID/passutan-app.git
   git push -u origin main
   ```

   **または** GitHub の「Upload files」でフォルダをドラッグ＆ドロップでもOK

   > ⚠️ `.streamlit/secrets.toml` は `.gitignore` で除外済みなので安全です

---

## STEP 3: Streamlit Community Cloud でデプロイ

1. https://share.streamlit.io にアクセス → GitHubアカウントでログイン

2. **Create app** → **Deploy a public app from GitHub**

3. 以下を設定
   | 項目 | 値 |
   |---|---|
   | Repository | `あなたのID/passutan-app` |
   | Branch | `main` |
   | Main file path | `app.py` |
   | App URL | お好みで（例: `passutan-app`） |

4. → **Deploy!** をクリック（最初は2〜3分かかります）

---

## STEP 4: Secrets を設定する（重要）

デプロイ後、アプリを開いてもエラーが出ます。Secretsを設定する必要があります。

1. Streamlit Cloud のダッシュボードで、作ったアプリの **⋮ → Settings → Secrets**

2. 以下を貼り付けて **Save**

```toml
SUPABASE_URL = "https://xxxxxxxxxx.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

> `xxxxxxxxxx` と `eyJhbGci...` は STEP 1-4 でメモした値に置き換えてください

3. アプリが自動で再起動し、正常に動作します ✅

---

## ローカルで動かす場合

```bash
pip install streamlit supabase
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# secrets.toml を編集して URL と KEY を入力
streamlit run app.py
```

---

## よくある質問

**Q: 複数人で使えますか？**
A: 現在の設計では全員が同じ進捗を共有します。個人管理したい場合はユーザー認証の追加が必要です。

**Q: Supabase の無料枠は？**
A: 月50万リクエスト、500MB ストレージまで無料。個人利用なら十分です。

**Q: 単語データを変えたい場合は？**
A: `words.json` を差し替えてGitHubにpushすると自動で反映されます。
