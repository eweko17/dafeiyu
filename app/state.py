from __future__ import annotations

import copy
import json
import os
import time
from contextlib import contextmanager
from datetime import date
from typing import Any, Iterator

from filelock import FileLock

from .paths import MEMORY_PATH, STATE_DIR

DEFAULT_STATE: dict[str, Any] = {
    "version": 1,
    "created_at": None,
    "posts": [],
    "replied": {},
    "skipped": {},
    "daily": {"date": None, "posts": 0, "replies": 0},
    "last_post_at": None,
    "last_reply_at": None,
}


def _read() -> dict[str, Any]:
    data: dict[str, Any] = {}
    if MEMORY_PATH.exists():
        try:
            data = json.loads(MEMORY_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {}

    merged = copy.deepcopy(DEFAULT_STATE)
    merged.update(data)
    merged["daily"] = dict(DEFAULT_STATE["daily"], **(data.get("daily") or {}))
    merged.setdefault("posts", [])
    merged.setdefault("replied", {})
    merged.setdefault("skipped", {})

    today = date.today().isoformat()
    if merged["daily"].get("date") != today:
        merged["daily"] = {"date": today, "posts": 0, "replies": 0}

    if not merged.get("created_at"):
        merged["created_at"] = time.time()
    return merged


def _write(data: dict[str, Any]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = STATE_DIR / "memory.json.tmp"
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, MEMORY_PATH)


def load() -> dict[str, Any]:
    return _read()


def save(data: dict[str, Any]) -> None:
    _write(data)


@contextmanager
def transaction() -> Iterator[dict[str, Any]]:
    """讀取 → 修改 → 原子寫回，並用檔案鎖避免排程重疊。"""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with FileLock(str(MEMORY_PATH) + ".lock", timeout=45):
        data = _read()
        yield data
        prune(data)
        _write(data)


def prune(data: dict[str, Any], days: int = 60) -> None:
    cutoff = time.time() - days * 86400
    data["posts"] = [p for p in data.get("posts", []) if p.get("ts", 0) >= cutoff]
    for key in ("replied", "skipped"):
        bucket = data.get(key, {})
        data[key] = {k: v for k, v in bucket.items() if v.get("ts", 0) >= cutoff}
