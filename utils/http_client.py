"""HTTP client for fetching web pages."""

import random
import sys
import time
from typing import Literal, Optional, Self
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from .config import config
from .http_cache import HttpCache
from .site_handlers import get_site_handler

# Transient errors that should trigger retries
RETRYABLE_EXCEPTIONS = (
    requests.exceptions.ConnectionError,
    requests.exceptions.Timeout,
    requests.exceptions.ChunkedEncodingError,
)


class HttpClient:
    """HTTP client for fetching web pages with session management."""

    def __init__(
        self, timeout: Optional[int] = None, max_retries: Optional[int] = None, use_cache: bool = True
    ) -> None:
        """Initialize HTTP client with configuration.

        Args:
            timeout: Request timeout in seconds (uses config default if None)
            max_retries: Maximum number of retry attempts (uses config default if None)
            use_cache: Whether to use HTTP response cache (default: True)
        """
        self.timeout = timeout if timeout is not None else config.request_timeout
        self.max_retries = max_retries if max_retries is not None else config.max_retries
        self.use_cache = use_cache
        self.session = requests.Session()
        self.cache = HttpCache(config.cache_file, config.cache_duration) if use_cache else None

    def __enter__(self) -> Self:
        """Context manager entry."""
        return self

    def __exit__(self, _exc_type: object, _exc_val: object, _exc_tb: object) -> Literal[False]:
        """Context manager exit - ensures session is closed.

        Returns:
            False to propagate any exceptions (never suppresses exceptions)
        """
        self.close()
        return False

    def close(self) -> None:
        """Close the HTTP session and release resources."""
        if self.session:
            self.session.close()

    def _get_delay_for_url(self, url: str) -> float:
        """Calculate appropriate delay for the given URL.

        Args:
            url: The URL to calculate delay for

        Returns:
            Delay time in seconds
        """
        handler = get_site_handler(url)
        min_delay, max_delay = handler.get_delay_range()
        return random.uniform(min_delay, max_delay)

    def get_headers_for_site(self, url: str) -> dict:
        """Get appropriate headers for the given site.

        Args:
            url: The URL to get headers for

        Returns:
            Dictionary of HTTP headers
        """
        domain = urlparse(url).netloc

        base_headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9," "image/avif,image/webp,image/apng,*/*;q=0.8"
            ),
            "Accept-Language": "pt-PT,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
            "sec-ch-ua": ('"Google Chrome";v="131", "Chromium";v="131", ' '"Not_A Brand";v="24"'),
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"macOS"',
        }

        # Get site-specific headers and merge
        handler = get_site_handler(url)
        custom_headers = handler.get_custom_headers(domain)
        base_headers.update(custom_headers)

        return base_headers

    def fetch_page(self, url: str, retry_count: Optional[int] = None) -> Optional[BeautifulSoup]:
        """Fetch and parse a webpage with retry logic.

        Retries on transient errors (connection errors, timeouts, 403 status).

        Args:
            url: The URL to fetch
            retry_count: Number of retries (uses self.max_retries if None)

        Returns:
            BeautifulSoup object if successful, None otherwise
        """
        # Check cache first (if caching is enabled)
        if self.cache:
            cached_html = self.cache.get(url)
            if cached_html:
                print("  📦 Using cached response", file=sys.stderr)
                return BeautifulSoup(cached_html, "lxml")

        if retry_count is None:
            retry_count = self.max_retries

        for attempt in range(retry_count + 1):
            try:
                headers = self.get_headers_for_site(url)

                # Add a delay with some randomization to appear more human-like
                delay = self._get_delay_for_url(url)
                time.sleep(delay)

                response = self.session.get(url, headers=headers, timeout=self.timeout)
                response.raise_for_status()

                # Cache successful responses (if caching is enabled)
                if self.cache and response.status_code == 200:
                    html = response.content.decode("utf-8")
                    self.cache.set(url, html)

                return BeautifulSoup(response.content, "lxml")

            except requests.exceptions.HTTPError as e:
                # Retry on 403 (bot detection)
                if attempt < retry_count and e.response.status_code == 403:
                    wait_time = random.uniform(config.retry_delay_min, config.retry_delay_max)
                    print(
                        f"    Got 403, waiting {wait_time:.1f}s " f"before retry {attempt + 1}/{retry_count}...",
                        file=sys.stderr,
                    )
                    time.sleep(wait_time)
                    continue
                print(f"Error fetching {url}: {e}", file=sys.stderr)
                return None

            except RETRYABLE_EXCEPTIONS as e:
                # Retry on transient network errors
                if attempt < retry_count:
                    wait_time = random.uniform(config.retry_delay_min, config.retry_delay_max)
                    error_type = type(e).__name__
                    print(
                        f"    {error_type}, waiting {wait_time:.1f}s " f"before retry {attempt + 1}/{retry_count}...",
                        file=sys.stderr,
                    )
                    time.sleep(wait_time)
                    continue
                print(f"Error fetching {url}: {e}", file=sys.stderr)
                return None

            except Exception as e:
                # Non-retryable errors
                print(f"Error fetching {url}: {e}", file=sys.stderr)
                return None

        return None  # Unreachable, but required for mypy type checking
