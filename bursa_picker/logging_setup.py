from __future__ import annotations

import logging
import logging.handlers
import os
from pathlib import Path
from threading import Lock

_configured = False
_lock = Lock()

_METRICS: dict[str, int] = {
    "yfinance_calls": 0,
    "yfinance_failures": 0,
    "cache_hits": 0,
    "cache_misses": 0,
}


def configure_logging(level: str = "INFO", logs_dir: Path | None = None) -> None:
    """Idempotent; safe to call from tests and from CLI startup."""
    global _configured
    with _lock:
        if _configured:
            logging.getLogger().setLevel(level.upper())
            return

        root = logging.getLogger()
        root.setLevel(level.upper())

        fmt = logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )

        console = logging.StreamHandler()
        console.setFormatter(fmt)
        root.addHandler(console)

        if logs_dir is not None:
            logs_dir.mkdir(parents=True, exist_ok=True)
            fh = logging.handlers.RotatingFileHandler(
                logs_dir / "bursa-picker.log",
                maxBytes=5_000_000,
                backupCount=3,
            )
            fh.setFormatter(fmt)
            root.addHandler(fh)

        _configured = True


def get_logger(name: str) -> logging.Logger:
    if not _configured:
        configure_logging(os.environ.get("BURSA_PICKER_LOG", "INFO"))
    return logging.getLogger(name)


def incr(metric: str, n: int = 1) -> None:
    _METRICS[metric] = _METRICS.get(metric, 0) + n


def snapshot_metrics() -> dict[str, int]:
    return dict(_METRICS)


def reset_metrics() -> None:
    for k in list(_METRICS.keys()):
        _METRICS[k] = 0
