#!/data/data/com.termux/files/usr/bin/bash
# 大肥魚手機版（Termux）安裝腳本
# 用法：把整個「大肥魚」資料夾放到手機後，在 Termux 裡執行：
#   cd ~/大肥魚 && bash mobile/install-termux.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
echo "資料夾：$ROOT"
echo ""

if [ ! -f "$ROOT/requirements.txt" ]; then
  echo "找不到 requirements.txt，請確認你是在「大肥魚」資料夾裡執行。"
  exit 1
fi

echo "[1/3] 更新套件庫…"
pkg update -y >/dev/null

echo "[2/3] 安裝 Python…"
pkg install -y python

echo "[3/3] 安裝 Python 套件…"
"${PREFIX}/bin/python" -m pip install --upgrade pip >/dev/null
"${PREFIX}/bin/python" -m pip install -r "$ROOT/requirements.txt"

echo ""
echo "安裝完成。接下來照順序執行："
echo "  1. python -m app.cli setup        （貼 Threads token 與 Gemini key）"
echo "  2. python scripts/switch_brain.py    （手機沒有 Ollama，改用 Gemini）"
echo "  3. python -m app.cli doctor       （健康檢查）"
echo "  4. bash mobile/start.sh           （開始常駐排程）"
