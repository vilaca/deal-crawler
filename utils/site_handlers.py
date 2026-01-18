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

from .config import Config


class SiteHandler(ABC):
    """Abstract base class for site-specific handling.

    Each site can define custom behavior for:
    - Request delays (rate limiting)
    - HTTP headers (anti-bot detection)
    - Price extraction (site-specific HTML structure)
    """

    def __init__(self, config: Config) -> None:
        """Initialize handler with configuration.

        Args:
            config: Configuration instance (required)
        """
        self.config = config

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
                '"Google Chrome";v="131.0.6778.109", ' '"Chromium";v="131.0.6778.109", ' '"Not_A Brand";v="24.0.0.0"'
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
                    price_matches = re.findall(r'"price"\s*:\s*([0-9]+\.?[0-9]*)', script.string)

                    for price_str in price_matches:
                        price = float(price_str)
                        # Validate price is in acceptable range
                        if self.config.min_price < price < self.config.max_price:
                            return price

                except ValueError:
                    continue

        return None


class FarmacentralHandler(SiteHandler):
    """Handler for farmacentral.pt which uses Nuxt.js.

    Farmacentral.pt stores product data in window.__NUXT__ JavaScript state.
    This handler extracts prices from the serialized JavaScript object.
    """

    def get_domain_pattern(self) -> str:
        """Return domain pattern for Farmacentral."""
        return "farmacentral.pt"

    def get_delay_range(self) -> tuple[float, float]:
        """Return default delay range (1-2 seconds)."""
        return (1.0, 2.0)

    def get_custom_headers(self, domain: str) -> Dict[str, str]:
        """Return empty dict - no custom headers needed."""
        return {}

    def _is_valid_price(self, price: float) -> bool:
        """Check if price is within acceptable range.

        Args:
            price: Price value to validate

        Returns:
            True if price is valid, False otherwise
        """
        return self.config.min_price < price < self.config.max_price

    def _extract_from_nuxt_script(self, script_content: str) -> Optional[float]:
        """Extract price from Nuxt.js script content.

        Args:
            script_content: JavaScript content containing __NUXT__ state

        Returns:
            Extracted price if found, None otherwise
        """
        # Patterns for various formats found in Nuxt state
        price_patterns = [
            r"price:([0-9]+\.?[0-9]*)",  # price:7.32 (any context)
            r"\.price[=:]([0-9]+\.?[0-9]*)",  # gl.price=7.32
            r'"price"[:\s]*([0-9]+\.?[0-9]*)',  # "price":7.32
            r"'price'[:\s]*([0-9]+\.?[0-9]*)",  # 'price':7.32
        ]

        # Try specific price patterns first
        for pattern in price_patterns:
            price_matches = re.findall(pattern, script_content)
            for price_str in price_matches:
                try:
                    price = float(price_str)
                    if self._is_valid_price(price):
                        return price
                except ValueError:
                    continue

        # Fallback: find all decimal numbers and return first valid one
        all_numbers = re.findall(r"\b([0-9]+\.[0-9]{2})\b", script_content)
        for num_str in all_numbers:
            try:
                price = float(num_str)
                if self._is_valid_price(price):
                    return price
            except ValueError:
                continue

        return None

    def extract_price(self, soup: BeautifulSoup) -> Optional[float]:
        """Extract price from Nuxt.js state in <script> tags."""
        for script in soup.find_all("script"):
            if not script.string:
                continue

            # Look for window.__NUXT__ state
            if "window.__NUXT__" in script.string or "__NUXT__" in script.string:
                price = self._extract_from_nuxt_script(script.string)
                if price:
                    return price

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
    """Registry for managing site handler classes.

    Handler classes are registered, and instances are created on demand
    with the provided configuration.
    """

    def __init__(self) -> None:
        """Initialize registry with empty handler class list."""
        self._handler_classes: list[type[SiteHandler]] = []
        self._default_handler_class: type[SiteHandler] = DefaultSiteHandler

    def register(self, handler_class: type[SiteHandler]) -> None:
        """Register a site handler class.

        Args:
            handler_class: SiteHandler class to register
        """
        self._handler_classes.append(handler_class)

    def get_handler(self, url: str, config: Config) -> SiteHandler:
        """Get appropriate handler instance for the given URL.

        Args:
            url: URL to get handler for
            config: Configuration instance (required)

        Returns:
            Matching SiteHandler instance, or DefaultSiteHandler if no match
        """
        # Check registered handlers for match
        for handler_class in self._handler_classes:
            # Create temporary instance to check pattern
            temp_handler = handler_class(config)
            pattern = temp_handler.get_domain_pattern()
            if pattern != "*" and pattern in url:
                return temp_handler

        # Return default handler
        return self._default_handler_class(config)


# Global registry - register all site handler classes here
_registry = SiteHandlerRegistry()
_registry.register(NotinoHandler)
_registry.register(FarmacentralHandler)

# Add more site handlers here as needed:
# _registry.register(AmazonHandler)
# _registry.register(EbayHandler)


def get_site_handler(url: str, config: Config) -> SiteHandler:
    """Get handler instance for the given URL.

    Args:
        url: URL to get handler for
        config: Configuration instance (required)

    Returns:
        Appropriate SiteHandler instance
    """
    return _registry.get_handler(url, config)
