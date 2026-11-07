from __future__ import annotations

import platform
import shutil
from typing import Any

from brain import router
from threads_api import ThreadsError, make_client

from . import config as config_mod
from . import persona, state
from .paths import CONFIG_PATH, ROOT, SECRETS_PATH


def _line(ok: bool | None, label: str, detail: str) -> str:
    mark = "OK  " if ok is True else ("!!  " if ok is False else "--  ")
    return f"[{mark}] {label:<18} {detail}"


def run() -> int:
    rows: list[str] = []
    critical = False

    rows.append(_line(True, "Python", platform.python_version()))
    rows.append(_line(True, "系統", platform.platform()))

    try:
        cfg = config_mod.load_config()
        rows.append(_line(True, "config.json", str(CONFIG_PATH)))
    except Exception as exc:  # noqa: BLE001
        rows.append(_line(False, "config.json", str(exc)))
        print("\n".join(rows))
        return 1

    rows.append(
        _line(
            persona.PERSONA_FILE.exists(),
            "人設檔",
            str(persona.PERSONA_FILE),
        )
    )

    secrets = config_mod.load_secrets()
    has_token = bool(str(secrets.get("threads_token", "")).strip())
    has_user = bool(str(secrets.get("threads_user_id", "")).strip())
    rows.append(
        _line(
            has_token and has_user,
            "Threads 憑證",
            "已設定" if has_token and has_user else f"未設定（{SECRETS_PATH}）",
        )
    )
    if not (has_token and has_user):
        critical = True

    if has_token and has_user:
        try:
            client = make_client(cfg, secrets)
            me = client.me()
            rows.append(
                _line(True, "Threads 帳號", f"@{me.get('username')} (id={me.get('id')})")
            )
            try:
                limit = client.publishing_limit()
                rows.append(
                    _line(
                        True,
                        "今日額度",
                        f"發文 {limit.get('quota_usage', '?')}/{limit.get('config', {}).get('quota_total', '?')}"
                        f"，回覆 {limit.get('reply_quota_usage', '?')}/{limit.get('reply_config', {}).get('quota_total', '?')}",
                    )
                )
            except ThreadsError as exc:
                rows.append(_line(None, "今日額度", f"查不到：{exc}"))
        except Exception as exc:  # noqa: BLE001
            detail = str(exc)
            if "API access blocked" in detail:
                detail += "（請到 developers.facebook.com 完成帳號驗證）"
            rows.append(_line(False, "Threads 帳號", detail))
            critical = True

    primary = str(cfg.get("brain", {}).get("primary", "ollama")).strip()

    for name, ok, message in router.health(cfg, secrets):
        rows.append(_line(ok, name, message))
        if ok:
            continue
        # 只有「目前實際在用」的大腦掛掉才算嚴重。
        # 例：雲端版用 Gemini，就別因為沒有 Ollama 而亮紅字。
        if name.startswith("Ollama") and primary != "ollama":
            continue
        if name.startswith("Gemini") and primary != "gemini":
            continue
        if name.startswith("Groq") and primary != "groq":
            continue
        critical = True

    free_gb = shutil.disk_usage(ROOT).free / (1024**3)
    rows.append(_line(free_gb > 2, "硬碟空間", f"{free_gb:.1f} GB 可用"))

    data = state.load()
    rows.append(
        _line(
            True,
            "今日進度",
            f"發文 {data['daily'].get('posts', 0)} 篇，回覆 {data['daily'].get('replies', 0)} 則",
        )
    )

    print("\n大肥魚健康檢查\n" + "=" * 52)
    print("\n".join(rows))
    print("=" * 52)

    if critical:
        print("\n有項目需要處理。先看 docs/設定步驟.md。")
        return 1

    print("\n看起來沒問題，可以開始餵 Token 了。")
    return 0
