"""Centralised logging and decision-trace utilities for Ainstein."""

import json
import logging
import logging.handlers
from pathlib import Path

_LOGS_DIR = Path(__file__).parent / "logs"


def get_logger(name: str) -> logging.Logger:
    _LOGS_DIR.mkdir(exist_ok=True)
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    fmt = logging.Formatter("%(asctime)s [%(name)s] %(levelname)s %(message)s")
    fh = logging.handlers.TimedRotatingFileHandler(
        _LOGS_DIR / "ainstein.log", when="midnight", backupCount=30, encoding="utf-8"
    )
    fh.setFormatter(fmt)
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.addHandler(fh)
    logger.addHandler(sh)
    logger.setLevel(logging.DEBUG)
    return logger


def append_decision_trace(trace: dict) -> None:
    """Append one JSON line to logs/decisions.jsonl. Rotates at 10 MB."""
    _LOGS_DIR.mkdir(exist_ok=True)
    path = _LOGS_DIR / "decisions.jsonl"
    _MAX_BYTES = 10 * 1024 * 1024  # 10 MB
    if path.exists() and path.stat().st_size >= _MAX_BYTES:
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
        path.rename(_LOGS_DIR / f"decisions_{timestamp}.jsonl")
    line = json.dumps(trace, ensure_ascii=False, default=str)
    with path.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
