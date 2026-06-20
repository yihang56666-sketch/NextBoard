"""Simple file-based cache for hardware butler."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Callable, TypeVar, cast

T = TypeVar("T")


class SimpleCache:
    """Simple JSON file-based cache."""

    def __init__(self, cache_dir: Path, default_ttl: int = 86400):
        """Initialize cache.

        Args:
            cache_dir: Directory for cache files
            default_ttl: Default TTL in seconds (default: 24h)
        """
        self.cache_dir = cache_dir
        self.default_ttl = default_ttl
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _key_path(self, key: str) -> Path:
        """Get cache file path for key."""
        key_hash = hashlib.sha256(key.encode()).hexdigest()[:16]
        return self.cache_dir / f"{key_hash}.json"

    def get(self, key: str) -> Any | None:
        """Get value from cache.

        Returns:
            Cached value or None if not found or expired
        """
        path = self._key_path(key)
        if not path.exists():
            return None

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if time.time() > data["expires_at"]:
                path.unlink()
                return None
            return data["value"]
        except (json.JSONDecodeError, KeyError, OSError):
            return None

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Set value in cache.

        Args:
            key: Cache key
            value: Value to cache (must be JSON-serializable)
            ttl: TTL in seconds (default: cache default_ttl)
        """
        path = self._key_path(key)
        ttl = ttl if ttl is not None else self.default_ttl
        expires_at = time.time() + ttl

        data = {"key": key, "value": value, "expires_at": expires_at}
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def delete(self, key: str) -> None:
        """Delete key from cache."""
        path = self._key_path(key)
        if path.exists():
            path.unlink()

    def clear(self) -> None:
        """Clear all cache entries."""
        for path in self.cache_dir.glob("*.json"):
            path.unlink()

    def memoize(self, ttl: int | None = None) -> Callable[[Callable[..., T]], Callable[..., T]]:
        """Decorator to memoize function results.

        Args:
            ttl: TTL in seconds

        Example:
            cache = SimpleCache(Path("~/.cache"))

            @cache.memoize(ttl=3600)
            def expensive_function(arg):
                return compute(arg)
        """

        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            def wrapper(*args: Any, **kwargs: Any) -> T:
                # Create cache key from function name and arguments
                key_parts = [func.__module__, func.__name__]
                if args:
                    key_parts.append(str(args))
                if kwargs:
                    key_parts.append(str(sorted(kwargs.items())))
                cache_key = "|".join(key_parts)

                # Try to get from cache
                cached = self.get(cache_key)
                if cached is not None:
                    return cast(T, cached)

                # Compute and cache
                result = func(*args, **kwargs)
                self.set(cache_key, result, ttl=ttl)
                return result

            return wrapper

        return decorator


def get_default_cache(name: str = "hardware-butler") -> SimpleCache:
    """Get default cache instance.

    Args:
        name: Cache subdirectory name

    Returns:
        SimpleCache instance in user's home directory
    """
    cache_dir = Path.home() / ".cache" / name
    return SimpleCache(cache_dir)
