from __future__ import annotations

import json
import os
import shutil
from typing import Any

from .paths import CONFIG_PATH, EXAMPLE_CONFIG_PATH, SECRETS_PATH, STATE_DIR


class ConfigError(RuntimeError):
    pass


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        if EXAMPLE_CONFIG_PATH.exists():
            shutil.copyfile(EXAMPLE_CONFIG_PATH, CONFIG_PATH)
        else:
            raise ConfigError("找不到 config.json 或 config.example.json")

    try:
        config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"config.json 格式錯誤：{exc}") from exc

    config.setdefault("timezone", "Asia/Taipei")
    config.setdefault("brain", {})
    config.setdefault("threads", {})
    config.setdefault("posting", {})
    config.setdefault("replies", {})
    config.setdefault("safety", {})
    return config


def load_secrets() -> dict[str, Any]:
    if not SECRETS_PATH.exists():
        return {}
    try:
        return json.loads(SECRETS_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def save_secrets(data: dict[str, Any]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = STATE_DIR / "secrets.json.tmp"
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, SECRETS_PATH)
