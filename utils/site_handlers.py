"""Site-specific handlers for different e-commerce websites.

This module implements the Strategy Pattern to handle site-specific behavior
such as custom headers, delays, and price extraction logic.

Adding a new site:
1. Create a new class inheriting from SiteHandler
2. Implement the 4 required methods
3. Register it in the global registry at the bottom
"""

import random
import re
from abc import ABC, abstractmethod
from typing import Dict, Optional

from bs4 import BeautifulSoup

from .config import config


class SiteHandler(ABC):
    """Abstract base class for site-specific handling.

    Each site can define custom behavior for:
    - Request delays (rate limiting)
    - HTTP headers (anti-bot detection)
    - Price extraction (site-specific HTML structure)
    """

    @abstractmethod
    def get_domain_pattern(self) -> str:
        """Return domain pattern to match (e.g., 'notino.pt').

        Returns:
            Domain string to search for in URLs
        """

    @abstractmethod
    def get_delay_range(self) -> tuple[float, float]:
        """Return delay range for rate limiting.

        Returns:
            Tuple of (min_delay, max_delay) in seconds
        """

    @abstractmethod
    def get_custom_headers(self, domain: str) -> Dict[str, str]:
        """Return site-specific HTTP headers.

        Args:
            domain: The domain being accessed

        Returns:
            Dictionary of custom headers (empty dict if none needed)
        """

    @abstractmethod
    def extract_price(self, soup: BeautifulSoup) -> Optional[float]:
        """Extract price using site-specific logic.

        Args:
            soup: BeautifulSoup parsed HTML

        Returns:
            Extracted price as float, or None if not found or to use default extraction
        """


class NotinoHandler(SiteHandler):
    """Handler for notino.pt with aggressive bot detection.

    Notino.pt requires:
    - Longer delays (4-7 seconds)
    - Enhanced headers with referer, origin, and security flags
    - JSON-based price extraction from <script> tags
    """

    def get_domain_pattern(self) -> str:
        """Return domain pattern for Notino."""
        return "notino.pt"

    def get_delay_range(self) -> tuple[float, float]:
        """Return delay range for Notino (4-7 seconds)."""
        return (4.0, 7.0)

    def get_custom_headers(self, domain: str) -> Dict[str, str]:
        """Return Notino-specific headers to avoid bot detection."""
        referers = [
            "https://www.google.com/",
            "https://www.google.pt/",
            f"https://{domain}/",
        ]

        return {
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

    def extract_price(self, soup: BeautifulSoup) -> Optional[float]:
        """Extract price from Notino's JSON data in <script> tags."""
        for script in soup.find_all("script"):
            if not script.string:
                continue

            if '"price"' in script.string:
                try:
                    # Find price values in JSON
                    price_matches = re.findall(
                        r'"price"\s*:\s*([0-9]+\.?[0-9]*)', script.string
                    )

                    for price_str in price_matches:
                        price = float(price_str)
                        # Validate price is in acceptable range
                        if config.min_price < price < config.max_price:
                            return price

                except ValueError:
                    continue

        return None


class DefaultSiteHandler(SiteHandler):
    """Default handler for generic e-commerce sites.

    Used when no specific handler matches the URL.
    Uses standard delays and headers, relies on generic extraction strategies.
    """

    def get_domain_pattern(self) -> str:
        """Return wildcard pattern that matches everything."""
        return "*"

    def get_delay_range(self) -> tuple[float, float]:
        """Return default delay range (1-2 seconds)."""
        return (1.0, 2.0)

    def get_custom_headers(self, domain: str) -> Dict[str, str]:
        """Return empty dict - no custom headers for default handler."""
        return {}

    def extract_price(self, soup: BeautifulSoup) -> Optional[float]:
        """Return None to use default extraction strategies."""
        return None


class SiteHandlerRegistry:
    """Registry for managing site handlers.

    Handlers are checked in order of registration. The first handler
    whose domain pattern matches the URL is used.
    """

    def __init__(self) -> None:
        """Initialize registry with empty handler list."""
        self._handlers: list[SiteHandler] = []
        self._default_handler: SiteHandler = DefaultSiteHandler()

    def register(self, handler: SiteHandler) -> None:
        """Register a site handler.

        Args:
            handler: SiteHandler instance to register
        """
        self._handlers.append(handler)

    def get_handler(self, url: str) -> SiteHandler:
        """Get appropriate handler for the given URL.

        Args:
            url: URL to get handler for

        Returns:
            Matching SiteHandler, or DefaultSiteHandler if no match
        """
        for handler in self._handlers:
            pattern = handler.get_domain_pattern()
            if pattern != "*" and pattern in url:
                return handler

        return self._default_handler


# Global registry - register all site handlers here
_registry = SiteHandlerRegistry()
_registry.register(NotinoHandler())

# Add more site handlers here as needed:
# _registry.register(AmazonHandler())
# _registry.register(EbayHandler())


def get_site_handler(url: str) -> SiteHandler:
    """Get handler for the given URL.

    Args:
        url: URL to get handler for

    Returns:
        Appropriate SiteHandler instance

    Example:
        >>> handler = get_site_handler("https://www.notino.pt/product")
        >>> isinstance(handler, NotinoHandler)
        True
    """
    return _registry.get_handler(url)
