from __future__ import annotations

import json

from threads_api import ThreadsClient

from . import config as config_mod
from .paths import CONFIG_PATH, EXAMPLE_CONFIG_PATH, SECRETS_PATH

GUIDE = """
============================================================
 大肥魚設定精靈
============================================================
你需要先準備：
  1. 一個新的 Threads 帳號（建議設為公開）
  2. 一個 Meta 開發者 App（選「Access the Threads API」）
  3. 把你的 Threads 帳號加為 Threads Tester，並接受邀請
  4. 在 App 後台產生 User Token

完整圖文步驟在：docs/設定步驟.md

提醒：token 等於帳號的發文權限，不要貼給任何人。
============================================================
"""


def _ask(prompt: str, default: str = "") -> str:
    suffix = f"（預設 {default}）" if default else ""
    value = input(f"{prompt}{suffix}: ").strip()
    return value or default


def run() -> int:
    print(GUIDE)

    token = _ask("貼上 Threads access token").strip()
    if not token:
        print("沒有 token，先到 docs/設定步驟.md 取得後再回來。")
        return 1

    client = ThreadsClient(token, "me")
    try:
        me = client.me()
    except Exception as exc:  # noqa: BLE001
        print(f"\nToken 驗證失敗：{exc}")
        print("常見原因：token 過期、複製不完整、或帳號還沒被加進 Threads Tester。")
        return 1

    username = me.get("username")
    user_id = str(me.get("id"))
    print(f"\n驗證成功：@{username}（id={user_id}）")
    if _ask("確定要讓大肥魚用這個帳號發文嗎？(y/n)", "y").lower() not in ("y", "yes", "是"):
        print("已取消。")
        return 1

    gemini_key = _ask("Gemini API key（可留空，之後再補）").strip()
    if gemini_key:
        print("已收到 Gemini key（只會存在本機 state/secrets.json）。")

    secrets = config_mod.load_secrets()
    secrets.update(
        {
            "threads_token": token,
            "threads_user_id": user_id,
            "threads_username": username,
        }
    )
    # 留空就保留原本的 key，避免重新設定 Threads token 時把 Gemini 清掉。
    if gemini_key:
        secrets["gemini_api_key"] = gemini_key
    else:
        secrets.setdefault("gemini_api_key", "")
    config_mod.save_secrets(secrets)

    if not CONFIG_PATH.exists() and EXAMPLE_CONFIG_PATH.exists():
        CONFIG_PATH.write_text(
            EXAMPLE_CONFIG_PATH.read_text(encoding="utf-8"), encoding="utf-8"
        )

    print("\n設定已寫入：")
    print(f"  {SECRETS_PATH}")
    print(f"  {CONFIG_PATH}")
    print("\n下一步：")
    print("  py -m app.cli doctor")
    print("  py -m app.cli post --dry-run")
    print("  py -m app.cli post")
    return 0
