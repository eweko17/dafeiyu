"""GitHub Actions 用：依排程時間（UTC）決定要跑哪個指令。

GitHub 的 cron 一律是 UTC，台灣是 UTC+8：
    01:30 UTC = 09:30 台灣
    06:30 UTC = 14:30 台灣
    13:30 UTC = 21:30 台灣
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# 排程（UTC）→ 指令
# 台灣時間 = UTC+8；:04/:14/:24… 是刻意避開整點與半點，GitHub 在整點最容易延遲或掉單。
SCHEDULE_TASKS: dict[str, list[str]] = {
    "4,14,24,34,44,54 0-15 * * *": ["auto"],
    "0 19 * * 6": ["refresh-token"],
}

# 手動觸發（workflow_dispatch）→ 指令
MANUAL_TASKS: dict[str, list[str]] = {
    "auto": ["auto"],
    "post-1": ["post", "--slot", "1"],
    "post-2": ["post", "--slot", "2"],
    "post-3": ["post", "--slot", "3"],
    "replies": ["replies"],
    "refresh": ["refresh-token"],
    "doctor": ["doctor"],
    "dry-run": ["post", "--dry-run"],
}


def main() -> int:
    schedule = (os.environ.get("SCHEDULE") or "").strip()
    args = SCHEDULE_TASKS.get(schedule)

    if args is None and schedule:
        # 排程字串對不上（例如 cron 剛改、GitHub 還留著舊的），
        # 寧可照常跑 auto，也不要直接失敗。
        print(f"沒對應到排程「{schedule}」，改用 auto。", flush=True)
        args = ["auto"]

    if args is None:
        task = (os.environ.get("TASK") or "doctor").strip()
        args = MANUAL_TASKS.get(task)
        if args is None:
            print(f"不認識的任務：{task}")
            return 1

    print("執行：python -m app.cli " + " ".join(args), flush=True)
    return subprocess.call([sys.executable, "-m", "app.cli", *args], cwd=str(ROOT))


if __name__ == "__main__":
    raise SystemExit(main())
