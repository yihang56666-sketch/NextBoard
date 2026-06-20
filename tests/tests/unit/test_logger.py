"""Unit tests for logger module."""

import logging
import sys

sys.path.insert(0, 'tools')

from logger import get_logger


def test_get_logger_returns_logger():
    """get_logger should return a logging.Logger instance."""
    logger = get_logger("test_basic")
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
