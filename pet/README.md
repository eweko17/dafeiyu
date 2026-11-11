# 桌寵（dsh-pet）

這是社群版 `dsh-pet` **v0.4.7** Windows x64 獨立版，解壓即用，**不需要 DSH、不需要 Node、不需要管理員權限**。

本機這一份：
- 程式是上游 **v0.4.7**（2026-11-08 發布），已加**本機安全補丁**（見下方）。
- 上游 v0.4.7 介面預設是簡體，本機已**整套轉成繁體（台灣用語）**：
  39 個文字檔（選單、系統匣、設定頁、對話面板、提示訊息）＋ 118 個素材檔名
  （表情包、動畫、字型）都已轉換，詞彙也改成台灣說法
  （拖曳、帳號、權限、重新載入、資料夾…）。
- 人設、工作狀態台詞、睡覺台詞另外在
  `C:\Users\user\.dsh\dsh-pet\main-config.jsonc` 蓋回原本那隻大肥魚的繁體版。
- 唯一保留的簡體字是 `lib\app.js`／`lib\standalone.js` 裡配圖標記的正則
  `[图圖]`，那是刻意同時接受繁簡兩種寫法，不影響顯示。

### 字型（2026-11-11 換過）

上游內建的「上首軟糖體」只有 **7568 個簡體字**，沒有「魚、軟、體、資、訊、網、
電、腦、點、擊…」這些繁體字。介面轉成繁體後，這些字會逐字退回微軟雅黑，
看起來就會「一半粉圓、一半黑體」。而且 `document.fonts.check()` 還會回報正常，
很難查。

本機已換成 **jf open 粉圓 2.1**（justfont，SIL OFL 1.1，可自由使用／再散布，
12,260 字，繁體完整）：

| 項目 | 位置 |
|---|---|
| 新字型 | `assets\fonts\jf-openhuninn-2.1.ttf`（4.68 MB） |
| 舊字型備份 | `%APPDATA%\dafeiyu-backup\fonts\上首軟糖體.ttf` |
| 引用處 | `lib\client.js`（網頁／設定頁）、`runtime\electron-helper\renderer.js`（桌面寵物） |

CSS 裡的 `font-family: "ShangshouSoftCandy"` 名稱**刻意沒有改**，只換 `src` 指到
新檔，這樣所有既有的字型堆疊與設定頁選項都不用動。

> 想換回原本的糖果體：把備份的 `上首軟糖體.ttf` 丟回 `assets\fonts\`，再把兩處
> `jf-openhuninn-2.1.ttf` 改回 `上首軟糖體.ttf`（記得重新啟動桌寵）。

## 啟動／關閉

| 動作 | 方法 |
|---|---|
| 啟動 | 雙擊 `啟動桌寵.bat`（會同時啟動背景記憶同步） |
| 關閉 | 雙擊 `關閉桌寵.bat`，或系統匣圖示按右鍵 →「結束」 |
| 直接跑 | `dsh-pet-win-x64\dsh-pet-0.4.7-win-x64\dsh-pet.exe` |

- 重複執行 `dsh-pet.exe` 不會開第二隻（單一實例），只會把原本那隻叫出來。
- 工作列右下角（系統匣）會有她的圖示，圖示右鍵就是主要的控制選單。
- 位置記在 `%USERPROFILE%\.dsh\dsh-pet\main-config.jsonc`：右下角、離右邊 300px、離下面 250px。
  想換位置直接把她拖走，或改那份設定。

## 安全補丁（重要）

上游 0.4.7 **仍然沒有**擋「把檔案拖到桌寵身上」的預設行為：

- 拖 `.cpp`／`.txt` → 桌寵視窗會**導覽到那個檔案**，變成文字檢視器。
- 拖 `.exe` → 會跳出**另存新檔**（等於把檔案下載下來）。

本機已補兩層（都在 `resources\app\` 內，重裝新版會被覆蓋）：

1. `runtime\electron-helper\main\windows.js`
   - `will-navigate` 一律取消（不讓視窗被導覽走）
   - `will-download` 一律取消（不跳另存新檔）
   - `setWindowOpenHandler` 一律拒絕（不開新視窗）
2. `runtime\electron-helper\renderer.js`
   - 視窗層攔掉 `dragover` / `drop` 的預設行為

實測結果：

| 測試 | 結果 |
|---|---|
| 合成 `drop` / `dragover` 事件 | 都被 `preventDefault` |
| 把 `location.href` 改成 `file:///...` | 沒反應，仍停在桌寵頁面 |
| `window.open('https://...')` | 回傳 `null`（被拒） |
| 用 CDP 模擬檔案拖放到寵物身上 | 沒有導覽，仍停在桌寵頁面 |

> 註：拖**圖片**到寵物身上在獨立版仍然沒有作用（獨立版沒有 DSH 的附件服務，
> 而且 Groq 的 `openai/gpt-oss-120b` 是純文字模型，不吃圖）。
> 但至少不會再把視窗弄成檔案檢視器或跳出下載。

## 繁體化做了什麼

- 人設（碎碎念／對話）沿用 v0.4.1 的繁體版「圓滾滾的藍色大肥魚」，並加上
  「一律用繁體中文（台灣用語）、不要簡體字、不要輸出 Markdown／網址／圖片連結」。
- 工作狀態氣泡、睡覺／醒來／被叫醒的台詞也都蓋成繁體。
- 對話回覆另外追加指令：直接回答、不要自言自語、繁體中文、口語、30 字以內。
- `lib\app.js`／`lib\standalone.js` 的配圖標記同時接受「圖」與「图」，且不再限定只能放句尾。

## 她的大腦

桌寵已接上 **Groq**（免費方案），設定檔在 `C:\Users\user\.dsh\dsh-pet\standalone-ai.json`：

| 欄位 | 值 |
|---|---|
| 服務商 | OpenAI 相容 |
| 網址 | `https://api.groq.com/openai/v1` |
| 模型 | `openai/gpt-oss-120b` |
| 金鑰 | 使用者自己的 Groq API key（不寫在這裡） |
| 自動碎碎念 | 開啟（約每 5 分鐘一次） |

- 不需要開 Ollama；電腦不用特別做什麼，有網路就能用。
- 也可以在系統匣圖示 →「開啟 AI 設定」裡改，兩邊寫的是同一個檔案。

## 記憶體

- 待機時大約 **300–500 MB**（Electron 主程序＋算圖程序），關掉就是 0。
- 聊天記憶在 `C:\Users\user\.dsh\dsh-pet\memory.json`，雲端同步用 `sync-memory.bat`。

## 備份與還原

| 項目 | 位置 |
|---|---|
| 舊版 v0.4.1（完整可執行） | `C:\Users\user\AppData\Roaming\dafeiyu-backup\dsh-pet-0.4.1\dsh-pet-0.4.1-win-x64\` |
| v0.4.7 原始 `app.asar` | `pet\dsh-pet-win-x64\dsh-pet-0.4.7-win-x64\resources\app.asar.bak` |
| 舊的使用者設定 | `C:\Users\user\.dsh\dsh-pet\main-config.jsonc.bak-before-0.4.7` |

要退回 v0.4.1：

1. 關閉桌寵。
2. 把 `pet\dsh-pet-win-x64\dsh-pet-0.4.7-win-x64` 改名或移走。
3. 把上面的舊版資料夾搬回 `pet\dsh-pet-win-x64\`。
4. 重新啟動。

## 不要她每次開機都出現

她沒有註冊成開機啟動項目，只有你雙擊才會出現。若曾放進「啟動」資料夾，到
`shell:startup`（Win+R 輸入）把捷徑刪掉即可。

## 授權（重要）

| 項目 | 授權 |
|---|---|
| 程式碼 | MIT |
| 動畫素材 | 僅限**非商業**使用 |
| 角色形象 | CC BY-NC-SA 4.0 |

所以：**自己玩、親友間分享可以；拿去做商品、業配、收費服務不行。**
原專案：<https://github.com/PC2005-cloud/dsh-pet>

## 移除

先關閉桌寵，再刪掉整個 `pet\dsh-pet-win-x64` 資料夾與 `%APPDATA%\dsh-pet\`、`%USERPROFILE%\.dsh\dsh-pet\`，不會殘留系統設定。
