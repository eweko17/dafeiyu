# 外部排程（cron-job.org）— 讓「每 10 分鐘」真的會跑

GitHub 自己的 `schedule` 非常不穩。這個 repo 的實際紀錄：
11/04 到 11/07 只跑了 **7 次**（cron 寫的是每 10 分鐘），
11/07 更是一整天 **0 次**，結果當天一篇貼文都沒發。

所以要「一天 3 篇、留言 10 分鐘內被回到」，就讓外面的免費服務每 10 分鐘叫 GitHub 跑一次。
電腦不用開著，也不用付錢。

> 這個做法只是「叫 GitHub 起來做事」，真正執行的還是 GitHub Actions。

---

## 一、先做一把只給這個 repo 用的鑰匙

不要拿原本的登入 token，改用 **Fine-grained token**，權限縮到最小。

1. 開 <https://github.com/settings/personal-access-tokens/new>
2. **Token name**：`大肥魚排程`
3. **Expiration**：90 天（到期再建一把就好）
4. **Resource owner**：選 `eweko17`
5. **Repository access** → **Only select repositories** → 勾 `dafeiyu`
6. **Permissions** → 展開 **Repository permissions** → 找到 **Actions** → 設成 **Read and write**
7. 其他全部不用給（Contents、Metadata 保持預設就好）
8. 按 **Generate token**，複製 `github_pat_...`（只會顯示一次）

這把鑰匙只能「觸發這個 repo 的 workflow」，不能改程式、不能看其他 repo，外流風險很低。

---

## 二、到 cron-job.org 建一個每 10 分鐘的 job

1. 開 <https://console.cron-job.org/signup> 註冊（免費，不用信用卡）
2. 登入後按 **Create cronjob**
3. 填這些：

**Common**

| 欄位 | 值 |
|---|---|
| Title | `大肥魚 auto` |
| URL | `https://api.github.com/repos/eweko17/dafeiyu/actions/workflows/dafeiyu.yml/dispatches` |
| Enable job | ✅ 打勾 |
| Save responses in job history | ✅ 打勾（出錯才看得到原因） |

**Schedule**

- 選 **User-defined schedule**（或 Expert mode），貼上：

```
*/10 0-15 * * *
```

這是 UTC，等於台灣時間 **08:00–23:59 每 10 分鐘**。
（半夜不會跑，避免大肥魚凌晨回留言。）

**Advanced → Request method / Headers / Body**

| 欄位 | 值 |
|---|---|
| Request method | `POST` |
| Headers | 見下面三行 |
| Request body | `{"ref":"main","inputs":{"task":"auto"}}` |

Headers 一行一個：

```
Authorization: Bearer github_pat_貼上你的那把鑰匙
Accept: application/vnd.github+json
Content-Type: application/json
```

4. 按 **Test run**
   - 看到 **HTTP 204** = 成功（GitHub 成功觸發時就是回 204，沒有內容）
   - 看到 **401** = 鑰匙貼錯或過期
   - 看到 **403** = 這把鑰匙沒有 Actions: write
   - 看到 **404** = repo 名稱或 workflow 檔名打錯
5. 回 <https://github.com/eweko17/dafeiyu/actions> 看有沒有出現一筆 `workflow_dispatch` 的執行

---

## 三、兩邊一起跑會不會重複？

不會。

- workflow 有設 `concurrency`，同一時間只會有一個在跑
- 發文看 `state/memory.json` 的「今天第幾篇」，不會重複發
- 回覆看留言 ID，回過的就記住了，不會回第二次

所以 GitHub 原本的排程偶爾醒來，也只是多跑一次空轉，不影響。

---

## 四、怎麼停掉

- cron-job.org → 該 job → **Disable**
- 或 GitHub → Actions → 大肥魚排程 → Disable workflow（兩邊都會停）

---

## 五、如果 cron-job.org 也不穩

替代品（都免費、都支援自訂 header＋POST）：

- **Cloudflare Workers**：Cron Triggers，免費方案每天 10 萬次請求
- **Google Apps Script**：時間觸發器每 5 分鐘，用 `UrlFetchApp.fetch`
- **EasyCron**：免費方案間隔較長

換服務時只要改「URL／method／headers／body」四樣，內容都跟上面一樣。

---

## 六、設定完要確認的事

1. cron-job.org 的 job 狀態是 **Enabled**。
2. 隔 20 分鐘去 <https://github.com/eweko17/dafeiyu/actions> 看，應該每 10 分鐘都有一筆
   `workflow_dispatch` 的執行（不再只有零星的 `schedule`）。
3. job 的 **Save responses in job history** 有開，失敗時才看得到 401／403。
4. cron-job.org 可以設「失敗時寄 email 通知」，建議打開。

> **這把 PAT 只放在 cron-job.org，不要貼進 repo。**
> 如果外流：GitHub → Settings → Developer settings → 撤銷那把 token，再建一把新的貼回 cron-job.org。
> PAT 到期（90 天）後 cron-job.org 會開始收到 401，那時再建新的一把就好。

---

## 七、Token 還是要手動更新

Threads 的長效 token 是 60 天，**雲端沒有辦法自動續期**（GitHub Actions 不能把新 token 寫回 Secrets）。
到期前重新產生一次，再跑 `上傳Token.bat` 更新 `THREADS_TOKEN`。大約 **2027-01-05** 到期。

本機的每週日自動續期只會更新電腦上的 `state/secrets.json`，不會動到雲端。

