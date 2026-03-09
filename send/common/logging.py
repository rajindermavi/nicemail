from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

_LOGGER_NAME = "send"


def setup_logging(
    log_file: Path,
    level: int = logging.INFO,
    console: bool = True,
) -> logging.Logger:
    """
    Configure the send logger.

    Parameters
    ----------
    log_file : Path
        Path to the shared log file.
    level : int
        Logging level (default: INFO).
    console : bool
        Whether to also log to stdout.
    """
    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(level)

    if logger.handlers:
        # Logger already configured
        return logger

    log_file.parent.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # File handler (rotating to avoid runaway logs)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)
    logger.addHandler(file_handler)

    if console:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(level)
        logger.addHandler(console_handler)

    logger.propagate = False
    logger.info("Logging initialized")

    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get a child logger.

    Example:
        logger = get_logger(__name__)
    """
    base = logging.getLogger(_LOGGER_NAME)
    return base if name is None else base.getChild(name)
