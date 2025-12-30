"""HTTP client for fetching web pages."""

import random
import sys
import time
from typing import Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from .config import config

# Transient errors that should trigger retries
RETRYABLE_EXCEPTIONS = (
    requests.exceptions.ConnectionError,
    requests.exceptions.Timeout,
    requests.exceptions.ChunkedEncodingError,
)


class HttpClient:
    """HTTP client for fetching web pages with session management."""

    def __init__(
        self, timeout: Optional[int] = None, max_retries: Optional[int] = None
    ):
        """Initialize HTTP client with configuration.

        Args:
            timeout: Request timeout in seconds (uses config default if None)
            max_retries: Maximum number of retry attempts (uses config default if None)
        """
        self.timeout = timeout if timeout is not None else config.request_timeout
        self.max_retries = (
            max_retries if max_retries is not None else config.max_retries
        )
        self.session = requests.Session()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, _exc_type, _exc_val, _exc_tb):
        """Context manager exit - ensures session is closed."""
        self.close()
        return False

    def close(self):
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
        if "notino.pt" in url:
            return random.uniform(config.notino_delay_min, config.notino_delay_max)
        return random.uniform(config.default_delay_min, config.default_delay_max)

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
                "text/html,application/xhtml+xml,application/xml;q=0.9,"
                "image/avif,image/webp,image/apng,*/*;q=0.8"
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
            "sec-ch-ua": (
                '"Google Chrome";v="131", "Chromium";v="131", ' '"Not_A Brand";v="24"'
            ),
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"macOS"',
        }

        # Enhanced headers for notino.pt (aggressive bot detection)
        if "notino.pt" in domain:
            # Vary referer to look more natural
            referers = [
                "https://www.google.com/",
                "https://www.google.pt/",
                f"https://{domain}/",
            ]
            base_headers.update(
                {
                    "Referer": random.choice(referers),
                    "Origin": f"https://{domain}",
                    "Sec-Fetch-Site": "same-origin",
                    "DNT": "1",
                    "sec-ch-ua-arch": '"arm"',
                    "sec-ch-ua-bitness": '"64"',
                    "sec-ch-ua-full-version-list": (
                        '"Google Chrome";v="131.0.6778.109", '
                        '"Chromium";v="131.0.6778.109", '
                        '"Not_A Brand";v="24.0.0.0"'
                    ),
                    "Viewport-Width": "1920",
                }
            )

        return base_headers

    def fetch_page(
        self, url: str, retry_count: Optional[int] = None
    ) -> Optional[BeautifulSoup]:
        """Fetch and parse a webpage with retry logic.

        Retries on transient errors (connection errors, timeouts, 403 status).

        Args:
            url: The URL to fetch
            retry_count: Number of retries (uses self.max_retries if None)

        Returns:
            BeautifulSoup object if successful, None otherwise
        """
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
                return BeautifulSoup(response.content, "lxml")

            except requests.exceptions.HTTPError as e:
                # Retry on 403 (bot detection)
                if attempt < retry_count and e.response.status_code == 403:
                    wait_time = random.uniform(
                        config.retry_delay_min, config.retry_delay_max
                    )
                    print(
                        f"    Got 403, waiting {wait_time:.1f}s "
                        f"before retry {attempt + 1}/{retry_count}...",
                        file=sys.stderr,
                    )
                    time.sleep(wait_time)
                    continue
                print(f"Error fetching {url}: {e}", file=sys.stderr)
                return None

            except RETRYABLE_EXCEPTIONS as e:
                # Retry on transient network errors
                if attempt < retry_count:
                    wait_time = random.uniform(
                        config.retry_delay_min, config.retry_delay_max
                    )
                    error_type = type(e).__name__
                    print(
                        f"    {error_type}, waiting {wait_time:.1f}s "
                        f"before retry {attempt + 1}/{retry_count}...",
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
