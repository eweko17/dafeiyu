# GitHub Actions 雲端版（電腦、手機都不用開）

把大肥魚放在 GitHub 的免費伺服器上跑。排程時間一到，GitHub 會自己開一台小機器：
裝 Python → 讀你的 token → 發文／回覆 → 存回紀錄 → 關掉。

**你不用開電腦，也不用開手機。**

---

## 費用

| repo 類型 | Actions 額度 | 對我們夠不夠 |
|---|---|---|
| **公開（Public）** | **完全免費、不限分鐘** | 綽綽有餘 |
| 私有（Private） | 每月 2,000 分鐘 | 每天約 30 次 × 1 分鐘 ≈ 900 分鐘／月，夠但很緊 |

👉 **用公開 repo**。程式碼和人設會公開，但 token 放在 Secrets 裡，別人看不到。

---

## 需要準備

1. **GitHub 帳號**（免費）：https://github.com/signup
2. **Threads token**：照 `docs/設定步驟.md` 產生
3. **雲端大腦的 API key**（雲端沒有 Ollama，兩個至少要有一個）：
   - **Gemini**（建議先試）：https://aistudio.google.com/apikey
   - **Groq**（Gemini 不能用時的備案，完全免費）：https://console.groq.com/keys

---

## 步驟 1：把資料夾變成 GitHub repo

最簡單是用 **GitHub Desktop**（圖形介面，不用打指令）。

1. 下載安裝：https://desktop.github.com/
2. 開啟 → **Sign in to GitHub.com** 登入
3. 上方選單 **File → Add local repository…**
4. 選 `C:\Users\user\OneDrive\Desktop\大肥魚`
5. 它會說這不是 repo → 點 **create a repository**
   - Name：`dafeiyu`
   - **不要**勾 "Keep this code private"（要公開才有免費無限分鐘）
   - 按 **Create repository**
6. 右邊會列出要上傳的檔案 → 確認**沒有** `state/secrets.json`、`.venv`、`pet/dsh-pet-win-x64`
7. 左下角 Summary 隨便打 `第一次上傳` → **Commit to main**
8. 上方 **Publish repository** → **不要**勾 private → **Publish**

> 如果 GitHub Desktop 顯示的檔案裡有 `secrets.json`，先停下來告訴我。
> `.gitignore` 已經排除它，正常不會出現。

> **OneDrive 小提醒**：這個資料夾在 OneDrive 裡，`.git` 也會被同步。如果 GitHub Desktop
> 一直出現檔案被鎖住、或同步卡住，可以先把整個資料夾複製到 `C:\大肥魚` 再上傳，
> 之後就固定用那個資料夾。

---

## 步驟 2：設定 Secrets（放 token 的地方）

1. 打開你的 repo 網頁：`https://github.com/你的帳號/dafeiyu`
2. **Settings** → 左邊 **Secrets and variables** → **Actions**
3. 按 **New repository secret**，新增下面幾個（前兩個必填）：

| Name | Secret | 必填 |
|---|---|---|
| `THREADS_TOKEN` | 你的 Threads access token | ✅ |
| `GEMINI_API_KEY` | 你的 Gemini API key | 二選一 |
| `GROQ_API_KEY` | 你的 Groq API key | 二選一 |
| `THREADS_USER_ID` | 你的 Threads 數字 id | 可不填（程式會自己抓） |

> Name 要**完全一樣**（全大寫、底線）。貼上值的時候不要多空白。
> 兩個 key 都設的話，雲端會以 **Groq 為主、Gemini 備援**（GitHub 的機器是資料中心 IP，Gemini 免費層常常會回 403）。

---

## 步驟 3：啟用 Actions

1. repo 上方點 **Actions**
2. 如果看到「Workflows aren't being run on this repository」→ 按 **I understand my workflows, go ahead and enable them**
3. 左邊會出現 **大肥魚排程**

---

## 步驟 4：先手動測試（重要）

1. 左邊點 **大肥魚排程** → 右邊 **Run workflow**
2. 下拉選 `doctor` → **Run workflow**
3. 等 30 秒，點進去看綠勾還是紅叉

依序測這三個：

| 順序 | 任務 | 預期結果 |
|---|---|---|
| 1 | `doctor` | 綠勾，log 裡有 `Threads 帳號 @你的帳號`、`Gemini 已設定` |
| 2 | `dry-run` | 綠勾，log 裡有一篇草稿（不會真的發出去） |
| 3 | `post-1` | 綠勾，Threads 上出現第一篇 |

三個都過，就完成了。

---

## 之後它會自動做什麼

| 台灣時間 | 動作 |
|---|---|
| 08:03–23:33，每 30 分鐘 | 跑一次 `auto`：時間到了就發文，順便檢查並回覆留言 |
| 09:30 / 14:30 / 21:30 前後 | 各發一篇（延遲最多 40 分鐘內都會補發） |
| 每週日 03:00 | 自動更新 Threads token |

> GitHub 的排程**不是秒準**，通常會延遲 3–15 分鐘，這是正常的。
> 所以 cron 刻意用 `:03` / `:33`，避開整點的高負載。

---

## 怎麼停掉

- **暫時停**：repo → **Actions** → 左邊「大肥魚排程」→ 右上 **⋯** → **Disable workflow**
- **恢復**：同一個地方 → **Enable workflow**
- **只停發文、繼續回覆**：改 `config.json` 的 `posting.enabled` 為 `false`，commit 上去

---

## 一定要知道的事

1. **電腦版的排程要先關掉**
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\scripts\pause_tasks.ps1
   ```
   兩邊同時跑會重複發文、重複回覆。

2. **每次執行都會產生一個 commit**
   repo 會有很多「紀錄：…」的 commit，那是正常的，用來記住「今天發過幾篇、回過哪些留言」。
   也因為這樣，GitHub 不會因為「60 天沒活動」把排程停掉。

3. **公開 repo 看得到什麼**
   看得到：程式碼、人設 `persona/大肥魚.md`、`config.json`、文件。
   看不到：`THREADS_TOKEN`、`GEMINI_API_KEY`（在 Secrets）、`state/secrets.json`（被 .gitignore 排除）。

4. **額度**
   Groq 免費層約每分鐘 30 次、每天 1,000 次；Gemini 免費層每分鐘約 15 次、每天約 1,000–1,500 次。
   一天 3 篇 + 幾十則回覆，用不到 5%。

5. **Token 過期**
   每週日會自動續期。如果超過 60 天沒跑（例如 workflow 被停用），重新產生 token 後更新 `THREADS_TOKEN`。

   **最快的做法（不用複製貼上）：**

   1. 到 https://developers.facebook.com/tools/explorer/threads 按 **Generate Threads Access Token**，複製短效 token
   2. 雙擊 `換Token.bat` → 貼上短效 token → 貼上 App Secret
   3. 雙擊 `上傳Token.bat` → 自動把 60 天 token 寫進 GitHub Secrets

   > 一定要在**短效 token 產生的 1 小時內**完成，過期就要重新產生。

---

## 疑難排解

| 症狀 | 原因 | 解法 |
|---|---|---|
| 紅叉，log 寫 `缺少 THREADS_TOKEN` | Secret 名字打錯 | 回步驟 2，確認叫 `THREADS_TOKEN` |
| 紅叉，log 寫 `Token 驗證失敗` | token 過期／複製不完整 | 重新產生 token，更新 Secret |
| 紅叉，log 寫 `所有大腦都失敗了` | 沒有雲端 key 或額度用完 | 檢查 `GEMINI_API_KEY`／`GROQ_API_KEY` |
| log 寫 `Gemini 回應 403 ... free tier is not available for this project` | 這把 Gemini key 的專案沒有免費額度 | 換一把新 key，或改設 `GROQ_API_KEY` |
| 綠勾但 Threads 沒貼文 | 今天額度滿了／`posting.enabled=false` | 看 log 的「沒有發文：…」原因 |
| 排程沒動 | workflow 被停用，或 repo 60 天沒活動 | Actions → Enable workflow |
| log 寫 `API access blocked`（code 200） | Meta 要求驗證開發者帳號，不是 token 過期 | 開 <https://developers.facebook.com/> 完成驗證（reCAPTCHA＋簡訊），看到「Access restored」就會立刻恢復 |
| `git push` 失敗 | 兩個排程撞在一起 | 再手動跑一次即可，程式有重試 |

---

## 想改時間？

打開 `.github/workflows/dafeiyu.yml`，裡面的 cron 是 **UTC**：

```
台灣時間 = UTC + 8
每 30 分鐘（台灣 08:03–23:33）→ "3,33 0-15 * * *"
```

發文時間不在 cron 裡，而是寫在 `config.json` 的 `posting.slots`。
`auto` 會看台灣時間，在某個 slot 前後（提前 10 分、延後 40 分）且今天還沒發到那個篇數時發文。

改完 commit 上去就會生效。
