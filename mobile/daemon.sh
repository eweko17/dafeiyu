#!/data/data/com.termux/files/usr/bin/bash
# 大肥魚手機常駐排程
#   09:30 / 14:30 / 21:30 各發一篇
#   09:00–23:00 每 30 分鐘檢查一次留言並回覆
#   每週日 03:00 自動更新 Threads token
# 由 mobile/start.sh 在背景啟動，不要直接雙擊執行。
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT" || exit 1

PY="${PREFIX:-/data/data/com.termux/files/usr}/bin/python"
LOG="$ROOT/logs/mobile.log"
mkdir -p "$ROOT/logs" "$ROOT/state"

# 讓 Android 不要在螢幕關閉時把 Termux 凍結
command -v termux-wake-lock >/dev/null 2>&1 && termux-wake-lock

echo "[$(date '+%F %T')] 大肥魚手機排程啟動" >> "$LOG"

LAST_POST=""
LAST_REPLY=""
LAST_REFRESH=""

while true; do
  now_hm="$(date '+%H:%M')"
  today="$(date '+%F')"
  hour="$(date '+%-H')"
  minute="$(date '+%-M')"

  # ── 發文 ─────────────────────────────────────────────
  case "$now_hm" in
    09:30|14:30|21:30)
      key="$today $now_hm"
      if [ "$LAST_POST" != "$key" ]; then
        LAST_POST="$key"
        slot=1
        case "$now_hm" in
          14:30) slot=2 ;;
          21:30) slot=3 ;;
        esac
        echo "[$(date '+%F %T')] 發文 slot=$slot" >> "$LOG"
        "$PY" -m app.cli post --slot "$slot" >> "$LOG" 2>&1
      fi
      ;;
  esac

  # ── 回覆留言 ─────────────────────────────────────────
  if [ "$hour" -ge 9 ] && [ "$hour" -le 22 ] && [ $((minute % 30)) -eq 0 ]; then
    key="$today $now_hm"
    if [ "$LAST_REPLY" != "$key" ]; then
      LAST_REPLY="$key"
      echo "[$(date '+%F %T')] 檢查留言" >> "$LOG"
      "$PY" -m app.cli replies >> "$LOG" 2>&1
    fi
  fi

  # ── Token 續期（每週日 03:00）────────────────────────
  if [ "$(date '+%u')" = "7" ] && [ "$now_hm" = "03:00" ]; then
    key="$today refresh"
    if [ "$LAST_REFRESH" != "$key" ]; then
      LAST_REFRESH="$key"
      echo "[$(date '+%F %T')] 更新 token" >> "$LOG"
      "$PY" -m app.cli refresh-token >> "$LOG" 2>&1
    fi
  fi

  sleep 20
done
