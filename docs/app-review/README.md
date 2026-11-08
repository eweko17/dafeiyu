# App Review 送審懶人包

要申請的權限只有一個：**`threads_keyword_search`**（搜尋公開貼文）。
它的用途是讓大肥魚能主動去回覆陌生人的公開貼文。

> **先說實話**
> - Meta 對「主動回覆陌生人」審得比較嚴，因為很容易變成洗版。
> - 純個人興趣的小帳號，通過率不高，也可能被要求做商業驗證。
> - **不要為此付錢給任何代辦。** 沒過也不影響現在的功能（自己發文＋回自己貼文留言照常）。
> - 就算通過，也建議一天最多 3–5 則，只回跟「白飯、摸魚、上班、工程師、桌面寵物、AI」有關的貼文。

---

## 一、送審前要準備的 4 樣

| # | 項目 | 狀態 |
|---|---|---|
| 1 | App 是 **Live**（不是 Development） | 到 Meta 後台右上角切換 |
| 2 | 公開的**隱私權政策**網址 | ✅ <https://eweko17.github.io/dafeiyu/app-review/privacy-policy.html> |
| 3 | 公開的**服務條款**網址 | ✅ <https://eweko17.github.io/dafeiyu/app-review/terms.html> |
| 4 | **App 圖示 1024×1024 PNG** | ⬜ 目前只有 512，需要另外做一張（或把 512 放大） |
| 5 | **螢幕錄影** 2–3 分鐘 | ⬜ 照 `screencast-script.md` 拍 |

兩個網址都確認過回 200，內容也和程式實際行為一致（GitHub Actions、公開 repo、私密 Gist、Groq／Gemini、保存期限）。

---

## 二、送審步驟（照順序點）

1. 打開 <https://developers.facebook.com/apps/> → 選你的 App。
2. 右上角確認 App 狀態是 **Live**。
3. 左側 **App Review → Permissions and features**。
4. 找到 **`threads_keyword_search`** → 按 **Request advanced access**。
5. 表單三個欄位：

   | 欄位 | 填什麼 |
   |---|---|
   | **Tell us how you'll use this permission** | 貼 `permission-justification.md` 的英文段落 |
   | **Privacy policy URL** | <https://eweko17.github.io/dafeiyu/app-review/privacy-policy.html> |
   | **Screencast / video URL** | YouTube 設「不公開」的連結，或直接上傳 |

6. 按 **Submit for review**，等 Meta 回覆（通常幾天到幾週）。
7. 審核期間**不要**改 App 名稱、網址或權限設定，會被退回重審。

---

## 三、錄影要注意的事

- 權限還沒開，所以 keyword search **只會搜到你自己的貼文**，這是 Meta 的規定，不是壞掉。
- 錄影時照實拍：輸入關鍵字 → 看到結果（可能只有自己的）→ 生成一則回覆 → 送出。
- 口述補一句：「權限通過後，才會搜尋到其他使用者的公開貼文；目前受平台限制只會回傳自己的內容。」
- 全程要讓審核員看到「**使用者本人在操作**」：有人按按鈕、有人輸入關鍵字、有畫面變化。
- 不要只拍終端機跑指令，Meta 會認為「這不是給人用的 App」。

---

## 四、通過之後（4 步開啟）

1. 重新產生 Threads token（授權時勾選新出現的 `threads_keyword_search`）。
2. 更新 GitHub Secrets 的 `THREADS_TOKEN`（跑 `上傳Token.bat`）。
3. `config.json` → `"discover": { "enabled": true }`。
4. 先試跑，不會發出去：

   ```powershell
   .\大肥魚.bat discover --dry-run --limit 1
   ```

   看到 `[dry-run] @某人：… → …` 就代表通了；接著 `.\大肥魚.bat discover --limit 1` 真的回一則。

之後雲端的 `auto` 每次跑就會順便主動回 1 則（一天最多 3 則）。細節見 [`docs/主動回覆陌生人.md`](../主動回覆陌生人.md)。

---

## 五、如果被拒

| 理由 | 處理 |
|---|---|
| 使用情境不明確 | 說明裡寫清楚「只回特定關鍵字、一天上限 3 則、同一人 7 天內不回」 |
| 沒有隱私政策／條款 | 換成上面兩個網址 |
| 影片看不出實際流程 | 重拍：關鍵字 → 結果 → 回覆 → 成功畫面，全程不剪接 |
| 平台不需要這個權限 | 老實承認是個人興趣專案，接受結果 |

被拒**不會**影響現有功能。A 計畫（自己發文＋回自己留言）照常運作。

---

## 六、其他資料

| 檔案 | 用途 |
|---|---|
| `permission-justification.md` | 送審時「用途說明」直接貼這個 |
| `screencast-script.md` | 錄影旁白與流程 |
| `privacy-policy.html` / `.md` | 隱私權政策（Meta 會點進去看） |
| `terms.html` | 服務條款 |
| `申請-主動回覆陌生人.md` | 中文版完整說明與注意事項 |
