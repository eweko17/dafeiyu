#!/data/data/com.termux/files/usr/bin/bash
# 啟動大肥魚手機常駐排程（背景執行，關掉 Termux 視窗也不會停）
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PIDFILE="$ROOT/state/mobile.pid"
mkdir -p "$ROOT/state" "$ROOT/logs"

if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
  echo "大肥魚已經在跑了（PID $(cat "$PIDFILE")）"
  exit 0
fi

nohup bash "$ROOT/mobile/daemon.sh" >/dev/null 2>&1 &
echo $! > "$PIDFILE"
echo "已啟動（PID $!）"
echo "日誌：logs/mobile.log"
echo "停止：bash mobile/stop.sh"
