from __future__ import annotations

import logging
import sys
from datetime import datetime

from .paths import LOGS_DIR


def setup(verbose: bool = False) -> logging.Logger:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    logfile = LOGS_DIR / f"{datetime.now():%Y-%m-%d}.log"

    handlers: list[logging.Handler] = [
        logging.FileHandler(logfile, encoding="utf-8"),
    ]
    # pythonw.exe 沒有 stdout，避免 StreamHandler 炸掉。
    if sys.stdout is not None:
        handlers.append(logging.StreamHandler(sys.stdout))

    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        handlers=handlers,
    )
    return logging.getLogger("dafeiyu")
