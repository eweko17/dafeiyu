from __future__ import annotations

import sys


def setup_console() -> None:
    """讓 Windows 主控台正確顯示中文（搭配 大肥魚.bat 的 chcp 65001）。"""
    for stream in (sys.stdout, sys.stderr):
        if stream is None:
            continue
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass
