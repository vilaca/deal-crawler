"""HTTP response caching with file-based persistent storage."""

import json
import time
from typing import Any, Dict, Optional, Union


class HttpCache:
    """File-based cache for HTTP responses with automatic expiration."""

    def __init__(self, cache_file: str, cache_duration: Union[int, float]) -> None:
        """Initialize cache manager.

        Args:
            cache_file: Path to the cache file
            cache_duration: Cache lifetime in seconds
        """
        self.cache_file = cache_file
        self.cache_duration = cache_duration
        self._cache: Optional[Dict[str, Dict[str, Any]]] = None

    def get(self, url: str) -> Optional[str]:
        """Get cached HTML if valid, None otherwise.

        Args:
            url: The URL to lookup in cache

        Returns:
            Cached HTML string if valid and not expired, None otherwise
        """
        cache = self._load_cache()

        if url not in cache:
            return None

        entry = cache[url]
        if self._is_expired(entry["timestamp"]):
            return None

        return entry["html"]

    def set(self, url: str, html: str) -> None:
        """Cache HTML for successful responses only.

        Args:
            url: The URL to cache
            html: The HTML content to cache
        """
        cache = self._load_cache()

        cache[url] = {"html": html, "timestamp": time.time()}

        self._save_cache()

    def _is_expired(self, timestamp: float) -> bool:
        """Check if cache entry is expired.

        Args:
            timestamp: Unix timestamp when the entry was cached

        Returns:
            True if expired, False otherwise
        """
        return time.time() - timestamp > self.cache_duration

    def _load_cache(self) -> Dict[str, Dict[str, Any]]:
        """Load cache from disk.

        Returns:
            Dictionary containing cached entries
        """
        if self._cache is not None:
            return self._cache

        try:
            with open(self.cache_file, "r", encoding="utf-8") as f:
                self._cache = json.load(f)
        except FileNotFoundError:
            self._cache = {}
        except (json.JSONDecodeError, ValueError):
            # Corrupted cache file, start fresh
            self._cache = {}

        return self._cache

    def _save_cache(self) -> None:
        """Save cache to disk."""
        if self._cache is None:
            return

        # Clear expired entries before saving
        self.clear_expired()

        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, indent=2)
        except (OSError, IOError):
            # Fail gracefully if we can't write (e.g., disk full, permissions)
            pass

    def clear_expired(self) -> int:
        """Remove expired entries, return count removed.

        Returns:
            Number of expired entries removed
        """
        if self._cache is None:
            return 0

        expired_urls = [url for url, entry in self._cache.items() if self._is_expired(entry["timestamp"])]

        for url in expired_urls:
            del self._cache[url]

        return len(expired_urls)
