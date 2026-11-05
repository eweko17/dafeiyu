"""把「短效 token」換成 60 天長效 token，並存進 state/secrets.json。

什麼時候會用到？
- 你用「圖形 API 瀏覽器（Graph API Explorer）」產生的 token → 只有 1 小時
- 你想換成 60 天的長效 token，之後才能自動續期

用法（在「大肥魚」資料夾）：
    .\\.venv\\Scripts\\python.exe scripts\\token_helper.py

需要準備：
    1. 短效 token（瀏覽器產生的那串）
    2. App Secret（Meta 後台 → 應用程式設定 → 基本資料 → 應用程式密鑰）

App Secret 只會在你的電腦上用，不會上傳、不會寫進 repo。
"""

from __future__ import annotations

import getpass
import json
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
SECRETS = ROOT / "state" / "secrets.json"
EXCHANGE_URL = "https://graph.threads.net/access_token"
ME_URL = "https://graph.threads.net/v1.0/me"


def _ask(label: str, secret: bool = False) -> str:
    value = (getpass.getpass(f"{label}（貼上後按 Enter，不會顯示）: ") if secret else input(f"{label}: ")).strip()
    return value.strip('"').strip("'").replace("\n", "").replace("\r", "")


def _me(token: str) -> dict:
    response = requests.get(
        ME_URL, params={"fields": "id,username", "access_token": token}, timeout=30
    )
    body = response.json() if response.content else {}
    if not response.ok or "error" in body:
        raise RuntimeError(body.get("error", {}).get("message", response.text[:200]))
    return body


def main() -> int:
    print("=" * 56)
    print(" 大肥魚：短效 token → 60 天長效 token")
    print("=" * 56)
    print("App Secret 在：Meta 後台 → 應用程式設定 → 基本資料 → 應用程式密鑰")
    print("（只在這台電腦使用，不會上傳）")
    print()

    short_token = _ask("短效 token")
    if not short_token:
        print("沒有 token，結束。")
        return 1

    print("\n先確認這串 token 本身有效…")
    try:
        me = _me(short_token)
    except Exception as exc:  # noqa: BLE001
        print(f"token 無效：{exc}")
        print("請重新產生一次，確認複製完整。")
        return 1
    print(f"token 有效：@{me.get('username')}（id={me.get('id')}）")

    app_secret = _ask("App Secret", secret=True)
    if not app_secret:
        print("沒有 App Secret，無法換成長效 token。")
        return 1

    print("\n換成長效 token…")
    try:
        response = requests.get(
            EXCHANGE_URL,
            params={
                "grant_type": "th_exchange_token",
                "client_secret": app_secret,
                "access_token": short_token,
            },
            timeout=30,
        )
        body = response.json() if response.content else {}
    except Exception as exc:  # noqa: BLE001
        print(f"連線失敗：{exc}")
        return 1

    if not response.ok or "access_token" not in body:
        message = body.get("error", {}).get("message", response.text[:300])
        print(f"轉換失敗：{message}")
        print("常見原因：App Secret 貼錯、或這串已經是長效 token。")
        return 1

    long_token = body["access_token"]
    days = int(body.get("expires_in", 0)) / 86400
    print(f"成功！有效期限約 {days:.0f} 天。")

    # 存進 state/secrets.json（保留原本的 Gemini key）
    data: dict = {}
    if SECRETS.exists():
        try:
            data = json.loads(SECRETS.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {}
    data["threads_token"] = long_token
    data["threads_user_id"] = str(me.get("id", ""))
    data["threads_username"] = str(me.get("username", ""))
    SECRETS.parent.mkdir(parents=True, exist_ok=True)
    SECRETS.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"已存到 {SECRETS.relative_to(ROOT)}（本機，不會上傳）")

    print()
    print("=" * 56)
    print("接下來：把下面這串貼到 GitHub Secrets 的 THREADS_TOKEN")
    print("https://github.com/eweko17/dafeiyu/settings/secrets/actions")
    print("=" * 56)
    print()
    print(long_token)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
