#!/data/data/com.termux/files/usr/bin/bash
# 停止大肥魚手機常駐排程
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PIDFILE="$ROOT/state/mobile.pid"

if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
  kill "$(cat "$PIDFILE")" 2>/dev/null
  echo "已停止（PID $(cat "$PIDFILE")）"
else
  echo "大肥魚沒有在跑。"
fi

rm -f "$PIDFILE"
