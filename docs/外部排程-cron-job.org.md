# 外部排程（cron-job.org）— 讓「每 10 分鐘」真的會跑

GitHub 自己的 `schedule` 常常延遲，甚至直接不掉單。這個 repo 的紀錄就看得出來：
cron 寫的是每 30 分鐘，實際上有時候隔了好幾個小時才跑一次。

如果你要「留言 10 分鐘內一定被回到」，就讓外面的免費服務每 10 分鐘叫 GitHub 跑一次。
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

## 六、順便讓 token 自動續期（選用）

Threads 的長效 token 是 60 天。原本靠 GitHub 每週日的排程續期，但那個排程一樣不一定會跑。

可以再建一個 cron-job.org job：

- 排程：`0 19 * * 6`（台灣時間週日 03:00）
- URL、method、headers 都跟上面一樣
- Request body 改成：`{"ref":"main","inputs":{"task":"refresh"}}`

