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
        self,
        *,
        timeout: Optional[int] = None,
        max_retries: Optional[int] = None,
        use_cache: bool = True,
        cache_duration: Optional[int] = None,
        cache_file: Optional[str] = None,
    ) -> None:
        """Initialize HTTP client with configuration.

        Args:
            timeout: Request timeout in seconds (uses config default if None)
            max_retries: Maximum number of retry attempts (uses config default if None)
            use_cache: Whether to use HTTP response cache (default: True)
            cache_duration: Cache lifetime in seconds (uses config default if None)
            cache_file: Cache file path (uses config default if None)
        """
        self.timeout = timeout if timeout is not None else config.request_timeout
        self.max_retries = max_retries if max_retries is not None else config.max_retries
        self.use_cache = use_cache
        self.session = requests.Session()

        # Use provided cache settings or fall back to config defaults
        _cache_duration = cache_duration if cache_duration is not None else config.cache_duration
        _cache_file = cache_file if cache_file is not None else config.cache_file
        self.cache = HttpCache(_cache_file, _cache_duration) if use_cache else None

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

    def remove_from_cache(self, url: str) -> None:
        """Remove URL from cache (used when extraction fails).

        Args:
            url: The URL to remove from cache
        """
        if self.cache:
            self.cache.remove(url)

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

    def _check_cache(self, url: str) -> Optional[BeautifulSoup]:
        """Check cache for URL and return parsed response if found.

        Args:
            url: The URL to check in cache

        Returns:
            BeautifulSoup object if cached, None otherwise
        """
        if not self.cache:
            return None

        cached_html = self.cache.get(url)
        if cached_html:
            print("  📦 Using cached response", file=sys.stderr)
            return BeautifulSoup(cached_html, "lxml")

        return None

    def _cache_response(self, url: str, response: requests.Response) -> None:
        """Cache successful HTTP response.

        Args:
            url: The URL to cache
            response: The HTTP response object
        """
        if self.cache and response.status_code == 200:
            self.cache.set(url, response.text)

    def _make_request(self, url: str) -> requests.Response:
        """Make a single HTTP request with rate limiting.

        Args:
            url: The URL to fetch

        Returns:
            HTTP response object

        Raises:
            Any requests exception on failure
        """
        headers = self.get_headers_for_site(url)

        # Add rate limiting delay
        delay = self._get_delay_for_url(url)
        time.sleep(delay)

        response = self.session.get(url, headers=headers, timeout=self.timeout)
        response.raise_for_status()

        return response

    def _should_retry_http_error(self, error: requests.exceptions.HTTPError, attempt: int, max_attempts: int) -> bool:
        """Check if HTTP error should trigger a retry.

        Args:
            error: The HTTP error
            attempt: Current attempt number (0-indexed)
            max_attempts: Maximum number of attempts

        Returns:
            True if should retry, False otherwise
        """
        return attempt < max_attempts and error.response is not None and error.response.status_code == 403

    def _wait_for_retry(self, error_message: str, attempt: int, max_attempts: int) -> None:
        """Wait before retry with logging.

        Args:
            error_message: Error description to log
            attempt: Current attempt number (0-indexed)
            max_attempts: Maximum number of attempts
        """
        wait_time = random.uniform(config.retry_delay_min, config.retry_delay_max)
        print(
            f"    {error_message}, waiting {wait_time:.1f}s before retry {attempt + 1}/{max_attempts}...",
            file=sys.stderr,
        )
        time.sleep(wait_time)

    def fetch_page(self, url: str, retry_count: Optional[int] = None) -> Optional[BeautifulSoup]:
        """Fetch and parse a webpage with retry logic.

        Retries on transient errors (connection errors, timeouts, 403 status).

        Args:
            url: The URL to fetch
            retry_count: Number of retries (uses self.max_retries if None)

        Returns:
            BeautifulSoup object if successful, None otherwise
        """
        # Check cache first
        cached_result = self._check_cache(url)
        if cached_result:
            return cached_result

        max_retries = retry_count if retry_count is not None else self.max_retries

        for attempt in range(max_retries + 1):
            try:
                response = self._make_request(url)
                self._cache_response(url, response)
                return BeautifulSoup(response.text, "lxml")

            except requests.exceptions.HTTPError as e:
                if self._should_retry_http_error(e, attempt, max_retries):
                    self._wait_for_retry("Got 403", attempt, max_retries)
                    continue
                print(f"Error fetching {url}: {e}", file=sys.stderr)
                return None

            except RETRYABLE_EXCEPTIONS as e:
                if attempt < max_retries:
                    error_type = type(e).__name__
                    self._wait_for_retry(error_type, attempt, max_retries)
                    continue
                print(f"Error fetching {url}: {e}", file=sys.stderr)
                return None

            except Exception as e:
                print(f"Error fetching {url}: {e}", file=sys.stderr)
                return None

        return None  # Unreachable, but required for mypy type checking
