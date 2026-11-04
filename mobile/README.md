# 大肥魚手機版（Android / Termux）

讓大肥魚在**手機上**發文、回覆留言，電腦不用開著。手機端沒有桌寵，只有本體。

> 如果你只是「不想開電腦」、但也不介意手機不跑，**GitHub Actions 雲端版**更省事：
> 電腦手機都不用開。做法看 `docs/GitHub-Actions-雲端版.md`。

---

## 先講清楚：為什麼不是 .apk

要做成 .apk 需要：Android SDK + Java + 把 Python 塞進 App + 自己做一個前端 + 串接模型。
這台筆電沒有那些工具，而且光是打包就會多出好幾 GB，還要處理簽章、權限、上架問題。

**Termux 是同樣效果的免費做法**：它在 Android 裡開一個小型 Linux 環境，直接跑同一份 Python 程式。
你看到的會是「一個黑色終端機視窗」，但設定好之後**可以整個關掉**，大肥魚會在背景繼續跑。

---

## 需要準備什麼

| 項目 | 說明 |
|---|---|
| 手機 | Android 7 以上，建議 4 GB RAM 以上 |
| Termux | **一定要從 F-Droid 安裝**（Google Play 那版已停止更新，會裝不起來） |
| Threads token | 跟電腦版同一組，`docs/設定步驟.md` 產生 |
| Gemini API key | **手機必備**（Android 跑不動 Ollama），免費申請：https://aistudio.google.com/apikey |
| 網路 | 發文時要連網，平常待機不太耗流量 |

> Gemini 免費層：每分鐘約 15 次、每天約 1,000–1,500 次。一天 3 篇 + 幾十則回覆，非常夠。

---

## 安裝步驟

### 1. 安裝 Termux

1. 手機瀏覽器開 https://f-droid.org/packages/com.termux/
2. 下載 APK → 安裝（Android 會問「允許安裝不明來源」，允許）
3. 開 Termux，等它跑完初始化

### 2. 把「大肥魚」資料夾放進手機

最簡單：用 USB 線接電腦，把整個 `大肥魚` 資料夾複製到手機的 `Download` 資料夾。

（用 OneDrive 同步也可以，但資料夾裡的 `.venv` 不用帶，帶了也用不到。）

### 3. 讓 Termux 看得到手機檔案

在 Termux 輸入：

```bash
termux-setup-storage
```

跳出權限視窗 → 允許。

### 4. 複製到家目錄並安裝

```bash
cp -r ~/storage/downloads/大肥魚 ~/大肥魚
cd ~/大肥魚
bash mobile/install-termux.sh
```

這會裝 Python 和 4 個套件（requests、filelock、opencc、tzdata），大約 1–2 分鐘。

### 5. 填入 token 與 Gemini key

```bash
python -m app.cli setup
```

- 貼上 Threads token → Enter
- 貼上 Gemini API key → Enter
- 確認帳號正確 → 輸入 `y`

### 6. 切換成 Gemini 大腦

```bash
python scripts/switch_brain.py
```

（電腦版是 Ollama 為主；手機沒有 Ollama，所以要切換。之後回電腦想用本機模型，再跑 `python scripts/switch_brain.py ollama`。）

### 7. 健康檢查

```bash
python -m app.cli doctor
```

預期看到：Threads 帳號 OK、Gemini OK。
`Ollama` 那行會是紅字，**手機上是正常的**，不用理它。

### 8. 先預覽，再真的發

```bash
python -m app.cli post --dry-run
python -m app.cli post
```

確認 Threads 上真的有出現，再進下一步。

### 9. 開始常駐

```bash
bash mobile/start.sh
```

看到「已啟動（PID …）」就完成了。這時可以直接把 Termux 滑掉，它會在背景繼續跑。

---

## 開關與查看

| 動作 | 指令 |
|---|---|
| 啟動 | `cd ~/大肥魚 && bash mobile/start.sh` |
| 停止 | `cd ~/大肥魚 && bash mobile/stop.sh` |
| 看日誌 | `tail -f ~/大肥魚/logs/mobile.log` |
| 今天進度 | `python -m app.cli status` |

排程內容（跟電腦版一樣）：

- 09:30 / 14:30 / 21:30 各發一篇
- 09:00–23:00 每 30 分鐘檢查並回覆留言
- 每週日 03:00 自動更新 token

---

## 一定要做的事（不然會被 Android 殺掉）

1. **關閉電池最佳化**
   設定 → 應用程式 → Termux → 電池 → 選「不受限制」／「不要最佳化」。
   各家手機名稱不同（小米：省電策略 → 無限制；三星：電池 → 未受監控的應用程式）。

2. **Termux 裡執行一次**
   ```bash
   termux-wake-lock
   ```
   `start.sh` 已經會自動做，但重開機後要再進 Termux 跑一次 `start.sh`。

3. **（選用）開機自動啟動**
   安裝 `Termux:Boot`（同樣在 F-Droid），開啟一次後建立：
   ```bash
   mkdir -p ~/.termux/boot
   cat > ~/.termux/boot/dafeiyu.sh <<'EOF'
   #!/data/data/com.termux/files/usr/bin/bash
   termux-wake-lock
   bash ~/大肥魚/mobile/start.sh
   EOF
   chmod +x ~/.termux/boot/dafeiyu.sh
   ```

---

## 常見問題

**Q：手機和電腦可以同時跑嗎？**
不要。兩邊都會發文、都會回覆同一批留言，會重複。
要換裝置前，先在舊的那台停掉（電腦：`scripts\pause_tasks.ps1`；手機：`bash mobile/stop.sh`）。

**Q：`state/` 要不要一起複製？**
要。`state/secrets.json` 是 token，`state/memory.json` 是發文紀錄（避免同一天重複發）。
第一次從電腦搬到手機時，建議**兩邊的 `state` 都先備份**，再以其中一邊為主。

**Q：很耗電嗎？**
待機時每 20 秒醒一次看時間，幾乎不吃電；真正耗電的是發文那幾十秒的網路與 Gemini 呼叫。
實測一小時約 1–2% 電量（螢幕關閉、有開 wake lock）。

**Q：Termux 被系統清掉怎麼辦？**
再開 Termux → `cd ~/大肥魚 && bash mobile/start.sh`。
如果常常被清掉，去電池設定把它設為「不受限制」，並確認 `termux-wake-lock` 有生效（Termux 通知列會顯示）。

**Q：可以只用 Wi-Fi 嗎？**
可以。沒有網路時發文會失敗並寫進日誌，下一輪再試。

**Q：token 過期？**
排程每週日會自動續期。如果真的過期，重新產生 token，再跑一次 `python -m app.cli setup`。

---

## 跟電腦版的差異

| 項目 | 電腦版 | 手機版 |
|---|---|---|
| 大腦 | Ollama（Qwen2.5 7B，離線） | Gemini（免費雲端） |
| 桌寵 | 有 | 沒有 |
| 排程 | Windows 工作排程 | Termux 背景迴圈 |
| 需要開著 | 筆電要開機 | 手機要開機（本來就開著） |
| 費用 | 0 元 | 0 元 |
