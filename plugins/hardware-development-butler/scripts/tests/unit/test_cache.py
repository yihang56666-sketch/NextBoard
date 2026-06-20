"""Unit tests for cache module."""

import sys

sys.path.insert(0, 'tools')
import time
from pathlib import Path

from cache import SimpleCache


def test_cache_set_and_get(tmp_path: Path):
    """Cache should store and retrieve values."""
    cache = SimpleCache(tmp_path)

    cache.set("key1", {"data": "value"})
    result = cache.get("key1")

    assert result == {"data": "value"}


def test_cache_expiration(tmp_path: Path):
    """Cache should expire after TTL."""
    cache = SimpleCache(tmp_path, default_ttl=1)

    cache.set("key1", "value")
    assert cache.get("key1") == "value"

    time.sleep(1.1)
    assert cache.get("key1") is None


def test_cache_delete(tmp_path: Path):
    """Cache should delete keys."""
    cache = SimpleCache(tmp_path)

    cache.set("key1", "value")
    cache.delete("key1")

    assert cache.get("key1") is None


def test_cache_clear(tmp_path: Path):
    """Cache should clear all entries."""
    cache = SimpleCache(tmp_path)

    cache.set("key1", "value1")
    cache.set("key2", "value2")
    cache.clear()

    assert cache.get("key1") is None
    assert cache.get("key2") is None


def test_cache_memoize(tmp_path: Path):
    """Memoize decorator should cache function results."""
    cache = SimpleCache(tmp_path)
    call_count = 0

    @cache.memoize(ttl=60)
    def expensive_func(x: int) -> int:
        nonlocal call_count
        call_count += 1
        return x * 2

    result1 = expensive_func(5)
    result2 = expensive_func(5)

    assert result1 == 10
    assert result2 == 10
    assert call_count == 1  # Only called once
