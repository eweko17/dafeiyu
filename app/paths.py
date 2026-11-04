from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PERSONA_DIR = ROOT / "persona"
STATE_DIR = ROOT / "state"
LOGS_DIR = ROOT / "logs"
DOCS_DIR = ROOT / "docs"

CONFIG_PATH = ROOT / "config.json"
EXAMPLE_CONFIG_PATH = ROOT / "config.example.json"
SECRETS_PATH = STATE_DIR / "secrets.json"
MEMORY_PATH = STATE_DIR / "memory.json"


def ensure_dirs() -> None:
    for directory in (PERSONA_DIR, STATE_DIR, LOGS_DIR):
        directory.mkdir(parents=True, exist_ok=True)
