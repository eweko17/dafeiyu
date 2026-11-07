# 大肥魚 🐋🍚

一隻住在 Threads 上的 AI 鯨魚女僕。**完全免費**、資料留在自己的筆電、不用付任何 API 費用。

- 大腦：本機 Ollama 或 Groq（免費），可互換
- 發文：一天最多 3 篇，繁體中文、台灣用語
- 回覆：會回覆自己貼文底下的每一則新留言
- 桌寵：附贈 `dsh-pet` 獨立版，100+ 段透明動畫，解壓就能跑
- 平台：Windows 10/11，Python 3.10+
- 手機：PWA（加到主畫面）或 APK，聊天／語音／記憶，見 `docs/手機版-App.md`（網址 <https://eweko17.github.io/dafeiyu/app/>）
- 記憶同步：手機 ↔ 電腦共用同一份記憶（私密 GitHub Gist）
- 雲端：也可以放 GitHub Actions，電腦手機都不用開，見 `docs/GitHub-Actions-雲端版.md`

---

## 目前的功能範圍（重要）

| 功能 | 狀態 | 說明 |
|---|---|---|
| 自己發文 | ✅ 現在就能用 | 免 Meta App Review |
| 回覆自己貼文底下的留言 | ✅ 現在就能用 | 免 App Review；留言串裡的下層回覆也會回 |
| 記住來留言的人 | ✅ 現在就能用 | 記得見過幾次、說過什麼、上次回什麼 |
| 主動回覆陌生人的公開貼文 | ⏳ 需審核 | 需要 `threads_keyword_search`，Meta 規定未通過前只能搜到自己的貼文 |
| 桌寵 | ✅ 現在就能用 | 獨立版，不需 DSH / Node |

「主動回覆陌生人」的申請資料與步驟放在 `docs/app-review/申請-主動回覆陌生人.md`。這是免費但需要等待的流程，通過與否由 Meta 決定。

---

## 花費

| 項目 | 費用 |
|---|---|
| Ollama | 0 元 |
| Qwen2.5 7B / 3B 模型 | 0 元 |
| Python 套件 | 0 元 |
| Threads API | 0 元（Meta 沒有收費制度） |
| Gemini 備援 | 0 元（免費額度，需自己申請 key） |
| 桌寵 dsh-pet | 0 元（非商業使用） |
| **總計** | **0 元**（只有電費） |

---

## 快速開始

### 1. 安裝

在資料夾上按右鍵 →「在終端機中開啟」，執行：

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

這會建立 `.venv`、安裝套件、複製 `config.json`、下載 `qwen2.5:7b-instruct`（約 4.7 GB）。

### 2. 取得 Threads token

照著 `docs/設定步驟.md` 做，大約 10 分鐘。完成後：

```powershell
.\大肥魚.bat setup
```

貼上 token，它會自動驗證帳號並存到 `state/secrets.json`。

### 3. 健康檢查

```powershell
.\大肥魚.bat doctor
```

會檢查 token、Ollama、模型、額度、硬碟。

### 4. 先預覽，再真的發

```powershell
.\大肥魚.bat post --dry-run
.\大肥魚.bat post
```

### 5. 建立排程

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install_tasks.ps1
```

- 每天 09:30 / 14:30 / 21:30 各發一篇
- 09:00–23:00 每 10 分鐘檢查一次留言並回覆
- 每週日 03:00 自動更新 token

---

## 資料夾結構

```
大肥魚/
├── app/                 主程式（發文、回覆、健康檢查、設定精靈）
├── brain/               大腦：Ollama / Gemini / 自動切換
├── threads_api/         Threads API 用戶端
├── persona/大肥魚.md    人設（改這裡就會改變牠的個性）
├── state/               memory.json、secrets.json（token）
├── logs/                每天一份執行紀錄
├── docs/                設定步驟、App Review 申請資料
├── pet/                 桌寵
├── scripts/             安裝／移除排程、記憶同步
├── install.ps1          一鍵安裝
├── 同步記憶.bat          手機 ↔ 電腦記憶同步
└── 大肥魚.bat           日常指令入口
```

---

## 常用指令

```powershell
.\大肥魚.bat doctor              # 健康檢查
.\大肥魚.bat status              # 今天發了幾篇、回了幾則
.\大肥魚.bat people              # 看牠記得哪些人、聊過什麼
.\大肥魚.bat auto                # 時間到了就發文，順便回覆（雲端排程用）
.\大肥魚.bat post --dry-run      # 預覽一篇
.\大肥魚.bat post                # 發一篇
.\大肥魚.bat replies --dry-run   # 預覽回覆
.\大肥魚.bat replies             # 回覆新留言
.\大肥魚.bat test-brain          # 測試模型
.\大肥魚.bat quota               # 查今日 API 額度
.\大肥魚.bat refresh-token       # 手動更新 token
```

想暫時停掉自動發文／回覆（例如出門幾天、或想專心用電腦）：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\pause_tasks.ps1    # 暫停全部排程
powershell -ExecutionPolicy Bypass -File .\scripts\resume_tasks.ps1   # 恢復
```

---

## 桌寵

`pet/dsh-pet-win-x64/` 是社群的 `dsh-pet` 獨立版，這一台已經把介面**全部改成繁體中文**：

- 角色就是內建的「吃白飯的藍色大肥魚」，名字已設為「大肥魚」
- 109 段透明動畫（待機、打瞌睡、玩魔方、吃火鍋、被拖曳…）、27 張表情包，檔名與參照都已同步轉繁
- 點擊有反應、可拖曳；右鍵選單：查看餘額、待辦事項、碎碎念、對話、配圖、睡覺／起來、動作、顯示位置、重新載入設定
- 不需要 DSH、不需要 Node，完全離線
- 代碼 MIT；動畫素材允許非商業使用；形象為 CC BY-NC-SA 4.0

**開關方式（你完全可以自己控制）**

| 動作 | 方法 |
|---|---|
| 開啟 | 雙擊 `pet/啟動桌寵.bat` |
| 關閉 | 雙擊 `pet/關閉桌寵.bat`，或系統匣圖示右鍵 →「結束」 |
| 不要她佔桌面 | 關掉就好，她沒有設成開機自動啟動 |

**記憶體**：待機約 300–400 MB（實測 355 MB）；關掉就是 0。她講話時才會用到模型，而且本機模型閒置 2 分鐘會自動卸載（`config.json` 的 `brain.ollama.keep_alive = "2m"`）。這台筆電實測平常還有 5 GB 以上可用。

詳細說明（位置怎麼調、怎麼還原成簡體、怎麼接本機 AI）看 `pet/README.md`。

---

## 手機版（Android）

手機是**聊天 App**，不是發文機器人：可以聊天、語音輸入、語音朗讀、有記憶、會主動找你。

- 網址：<https://eweko17.github.io/dafeiyu/app/>
- 用 Chrome 打開 →「加到主畫面」就是 PWA；想更像 App 可以裝 APK（放自己的 OneDrive）
- 大腦用 Groq（免費），跟雲端版可以共用同一把 key
- 記憶存在手機瀏覽器；開啟「記憶同步」後會跟電腦桌寵共用同一份記憶

完整步驟在 `docs/手機版-App.md`。

---

## 雲端版（GitHub Actions）

連手機都不用開。把專案放上 GitHub，排程時間到 GitHub 會自己開機器跑一次，跑完就關。

- 公開 repo 的 Actions **完全免費、不限分鐘**
- token 放在 GitHub Secrets，不會出現在程式碼裡
- 排程每 10 分鐘跑一次 `auto`（台灣 08:04–23:54，刻意避開整點）：時間到了就發文，順便回覆留言
- 缺點：GitHub 的排程會延遲 3–15 分鐘；repo 會多出一些「紀錄：…」的 commit

完整步驟在 `docs/GitHub-Actions-雲端版.md`。

> ⚠️ 電腦、手機、雲端**只能挑一個地方跑**，不然會重複發文、重複回覆同一則留言。

---

## 安全與倫理

- **不洗版**：一天最多 3 篇、回覆上限 30 則，遠低於平台上限。
- **不主動私訊**：程式沒有私訊功能。
- **標示 AI**：每篇貼文都帶 `is_made_with_ai=true`，Threads 會顯示 AI 標籤。
- **敏感話題閃避**：政治、宗教、災難、醫療、投資、色情、廣告，一律跳過。
- **不透露隱私**：人設明確禁止洩漏 token、路徑、帳號、主人資訊。
- **Token 只存本機**：`state/secrets.json`，不上傳任何伺服器。
- **Gemini 是可選的**：只有在 Ollama 失敗時才會把文字送到 Google；不想用就不要填 key。

### 注意

- `state/secrets.json` 在 OneDrive 資料夾裡，會同步到你的雲端。如果不放心，可以把 `state/` 移到 OneDrive 之外，或把 token 當作「60 天後就換一次」的消耗品。
- 這是個人興趣專案，不是 DeepSeek 官方產品。大肥魚形象是社群二創，非官方角色。

---

## 常見問題

**Q：筆電很慢，跑得動嗎？**
7B 模型在 i5-1235U + 16GB RAM 上實測一篇貼文約 30–50 秒（第一次要載入模型會多 30 秒）。一天三次，不影響日常使用，但跑的時候風扇會轉大聲一點。

如果覺得太慢，把 `config.json` 的 `brain.ollama.model` 改成 `qwen2.5:3b-instruct`（已裝好），速度約快一倍，內容會比較跳一點。

**Q：可以關掉筆電嗎？**
可以。把排程搬到 **GitHub Actions**（`docs/GitHub-Actions-雲端版.md`）就完全不用開機。
只關筆電、什麼都不做的話，那幾天就不會發文；開機後 `StartWhenAvailable` 會補跑一次。
不管選哪個，記得先關掉電腦排程，不然會重複發文。

**Q：手機可以跑嗎？一定要 .apk 嗎？**
可以，但不一定要 .apk。用 Chrome 打開 <https://eweko17.github.io/dafeiyu/app/>，「加到主畫面」就能當 App 用。
想更像一般 App 再裝 APK（`apk\dafeiyu.apk`，放自己的 OneDrive）。詳見 `docs/手機版-App.md`。

**Q：Token 過期怎麼辦？**
每週日會自動更新。如果超過 60 天沒開機，重新跑一次 `docs/設定步驟.md` 的產生 token 流程，再 `.\大肥魚.bat setup`。

**Q：可以改個性嗎？**
改 `persona/大肥魚.md`，下次發文就會生效。

**Q：可以改成一天一篇嗎？**
改 `config.json` 的 `posting.slots` 與 `max_per_day`，再重跑 `install_tasks.ps1`。

**Q：桌寵會不會很吃記憶體？**
待機約 300–400 MB（實測 355 MB），關掉就是 0；只有在碎碎念／對話時才會叫模型，而且模型閒置 2 分鐘自動卸載。詳見上面「桌寵」段。

**Q：會被 Meta 鎖嗎？**
正常使用（一天 1–3 篇、不洗版、不主動騷擾）風險很低。主動回陌生人的功能要等審核，就是因為平台不喜歡大量主動回覆。
