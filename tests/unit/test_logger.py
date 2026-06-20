"""Unit tests for logger module."""

import logging

from logger import configure_logging, get_logger


def test_get_logger_returns_logger():
    """get_logger should return a logging.Logger instance."""
    logger = get_logger("test")
    assert isinstance(logger, logging.Logger)


def test_get_logger_caches_instances():
    """get_logger should cache and reuse logger instances."""
    logger1 = get_logger("test_cache")
    logger2 = get_logger("test_cache")
    assert logger1 is logger2


def test_logger_has_handler():
    """Logger should have at least one handler."""
    logger = get_logger("test_handler")
    assert len(logger.handlers) > 0


def test_logger_respects_level():
    """Logger should respect specified level."""
    logger = get_logger("test_level", level="WARNING")
    assert logger.level == logging.WARNING


def test_configure_logging_sets_level():
    """configure_logging should set console level."""
    configure_logging(console_level="ERROR")
    root = logging.getLogger()
    console_handlers = [h for h in root.handlers if isinstance(h, logging.StreamHandler)]
    assert len(console_handlers) > 0
    assert console_handlers[0].level == logging.ERROR
