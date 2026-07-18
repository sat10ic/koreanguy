"""Shared, bounded file logging for unattended Manas OS operations."""
from __future__ import annotations

import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent / "data" / "logs"


def rotating_file_handler(log_name: str, *, log_dir: Path = LOG_DIR) -> TimedRotatingFileHandler:
    """Return a midnight-rotating UTF-8 handler with 14 dated backups."""
    log_dir.mkdir(parents=True, exist_ok=True)
    handler = TimedRotatingFileHandler(
        log_dir / f"{log_name}.log",
        when="midnight",
        backupCount=14,
        encoding="utf-8",
        delay=True,
    )
    handler.suffix = "%Y-%m-%d"
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    return handler


def configure_ops_logger(log_name: str) -> logging.Logger:
    """Configure one idempotent console + rotating-file logger per operation."""
    logger = logging.getLogger(f"manas_os.ops.{log_name}")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    target = str((LOG_DIR / f"{log_name}.log").resolve())
    if not any(
        isinstance(handler, TimedRotatingFileHandler)
        and handler.baseFilename == target
        for handler in logger.handlers
    ):
        logger.addHandler(rotating_file_handler(log_name))
    if not any(type(handler) is logging.StreamHandler for handler in logger.handlers):
        logger.addHandler(logging.StreamHandler())
    return logger
