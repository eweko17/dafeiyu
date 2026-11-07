# App Review 申請資料（B 計畫）

這份資料是為了申請 `threads_keyword_search`，讓大肥魚可以**主動回覆陌生人的公開貼文**。

## 先說實話

- Meta 對「主動回覆陌生人」的權限審得比較嚴，因為這很容易變成洗版。
- 純個人興趣的小帳號，通過率不高。**不要為此付錢給任何代辦。**
- 即使通過，也建議一天最多回 5–10 則，並且只回跟「AI、白飯、摸魚、工程師」有關的公開貼文。

## 申請前要準備

1. App 已經是 **Live** 狀態（Meta 後台右上角切換）。
2. 有**公開的隱私權政策與服務條款網址**（不能是 Google Docs，要是網頁）。
   - 已經放在 GitHub Pages：
     - 隱私權政策：<https://eweko17.github.io/dafeiyu/app-review/privacy-policy.html>
     - 服務條款：<https://eweko17.github.io/dafeiyu/app-review/terms.html>
3. 一段 **2–3 分鐘的螢幕錄影**，照 `screencast-script.md` 拍。
4. 確認 App 的「資料刪除」說明可以運作（測試者可以要求刪除資料）。

## 申請步驟

1. Meta App 後台 → **App Review** → **Permissions and features**
2. 找到 `threads_keyword_search` → **Request advanced access**
3. 填寫：
   - **Tell us how you'll use this permission**：貼上 `permission-justification.md` 的內容
   - **Privacy policy URL**：你的公開網址
   - **Screencast**：上傳影片（或 YouTube 未公開連結）
4. 送出，等 3–14 個工作天（可能更久）。

## 如果被拒

常見理由與處理：

| 理由 | 處理 |
|---|---|
| 使用情境不明確 | 在說明裡寫清楚「只回特定關鍵字、一天上限 10 則」 |
| 沒有隱私政策 | 補上公開網址 |
| 影片看不出實際流程 | 重拍，從關鍵字搜尋到回覆完整錄一次 |
| 平台不需要這個權限 | 老實承認是個人興趣專案，接受結果 |

被拒不會影響現有功能。A 計畫（自己發文 + 回自己留言）照常運作。

## 檔案

- `privacy-policy.md` / `privacy-policy.html`：隱私政策
- `permission-justification.md`：申請表要貼的說明
- `screencast-script.md`：錄影腳本
