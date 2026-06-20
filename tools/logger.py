"""Centralized logging configuration for hardware butler."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

_loggers: dict[str, logging.Logger] = {}


def get_logger(name: str, *, level: str | None = None) -> logging.Logger:
    """Get or create a logger with the given name.

    Args:
        name: Logger name (typically __name__)
        level: Log level (DEBUG/INFO/WARNING/ERROR/CRITICAL)

    Returns:
        Configured logger instance
    """
    if name in _loggers:
        return _loggers[name]

    logger = logging.getLogger(name)

    # Set level from parameter or environment
    if level:
        logger.setLevel(getattr(logging, level.upper()))
    else:
        import os
        env_level = os.getenv("HW_BUTLER_LOG_LEVEL", "INFO").upper()
        logger.setLevel(getattr(logging, env_level, logging.INFO))

    # Only add handler if none exist (avoid duplicates)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    _loggers[name] = logger
    return logger


def setup_file_logging(log_file: Path, *, level: str = "DEBUG") -> None:
    """Add file handler to root logger.

    Args:
        log_file: Path to log file
        level: Minimum log level for file output
    """
    log_file.parent.mkdir(parents=True, exist_ok=True)

    handler = logging.FileHandler(log_file, encoding="utf-8")
    handler.setLevel(getattr(logging, level.upper()))
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
    )
    handler.setFormatter(formatter)

    logging.getLogger().addHandler(handler)


def configure_logging(*, console_level: str = "INFO", file_path: Path | None = None) -> None:
    """Configure global logging for the entire application.

    Args:
        console_level: Console log level
        file_path: Optional file for detailed logs
    """
    # Set root logger level
    logging.getLogger().setLevel(logging.DEBUG)

    root = logging.getLogger()

    # Console handler. Keep it first so callers and tests do not depend on
    # unrelated handlers installed by pytest plugins or embedding tools.
    console = next(
        (
            handler
            for handler in root.handlers
            if isinstance(handler, logging.StreamHandler) and getattr(handler, "_hw_butler_console", False)
        ),
        None,
    )
    if console is None:
        console = logging.StreamHandler(sys.stderr)
        setattr(console, "_hw_butler_console", True)
        root.addHandler(console)
        root.handlers.remove(console)
        root.handlers.insert(0, console)
    console.setLevel(getattr(logging, console_level.upper()))
    console_fmt = logging.Formatter("%(levelname)s: %(message)s")
    console.setFormatter(console_fmt)

    # Optional file handler
    if file_path:
        setup_file_logging(file_path)
