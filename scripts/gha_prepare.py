"""GitHub Actions 用：從環境變數產生 state/secrets.json。

需要的環境變數：
    THREADS_TOKEN     （必填）
    GEMINI_API_KEY    （雲端版必填，大腦是 Gemini）
    THREADS_USER_ID   （選填，沒給就用 /me 自動抓）
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from threads_api import ThreadsClient  # noqa: E402

SECRETS = ROOT / "state" / "secrets.json"


def main() -> int:
    token = os.environ.get("THREADS_TOKEN", "").strip()
    if not token:
        print("缺少 THREADS_TOKEN，請到 repo → Settings → Secrets and variables → Actions 設定。")
        return 1

    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
    user_id = os.environ.get("THREADS_USER_ID", "").strip()
    username = ""

    if not user_id:
        try:
            me = ThreadsClient(token, "me").me()
        except Exception as exc:  # noqa: BLE001
            print(f"Token 驗證失敗：{exc}")
            return 1
        user_id = str(me.get("id", "")).strip()
        username = str(me.get("username", "")).strip()

    if not user_id:
        print("抓不到 user id，請手動設定 THREADS_USER_ID。")
        return 1

    data = {
        "threads_token": token,
        "threads_user_id": user_id,
        "gemini_api_key": gemini_key,
    }
    if username:
        data["threads_username"] = username

    SECRETS.parent.mkdir(parents=True, exist_ok=True)
    SECRETS.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    # 讓 state/memory.json 一定存在，後面「存回紀錄」才不會出錯。
    memory = ROOT / "state" / "memory.json"
    if not memory.exists():
        memory.write_text("{}\n", encoding="utf-8")

    print(f"已寫入 {SECRETS.relative_to(ROOT)}（id={user_id}）")
    if not gemini_key:
        print("提醒：沒有 GEMINI_API_KEY，雲端版會沒有大腦可用。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
