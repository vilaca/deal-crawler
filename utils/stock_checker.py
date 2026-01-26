"""Stock availability checker for products."""

import re
from bs4 import BeautifulSoup, Tag
from typing import Optional

from .config import Config
from .site_handlers import get_site_handler

# Compile regex patterns at module level for better performance
OUT_OF_STOCK_PATTERNS = [
    re.compile(r"out\s+of\s+stock", re.IGNORECASE),
    re.compile(r"esgotado", re.IGNORECASE),
    re.compile(r"sin\s+stock", re.IGNORECASE),
    re.compile(r"não\s+disponível", re.IGNORECASE),
    re.compile(r"indisponível", re.IGNORECASE),
    re.compile(r"sem\s+stock", re.IGNORECASE),
    re.compile(r"sold\s+out", re.IGNORECASE),
    re.compile(r"rupture\s+de\s+stock", re.IGNORECASE),
    re.compile(r"agotado", re.IGNORECASE),
    re.compile(r"não\s+disponivel", re.IGNORECASE),
]

OUT_OF_STOCK_CLASS_PATTERN = re.compile(r"out.?of.?stock|sold.?out|unavailable|indispon[ií]vel", re.IGNORECASE)

IN_STOCK_CLASS_PATTERN = re.compile(
    r"in[-_\s]?stock|em[-_\s]?stock|(?<!in)disponível|(?<!in)disponivel|\bavailable\b",
    re.IGNORECASE,
)


def _check_for_in_stock_indicators(soup: BeautifulSoup) -> Optional[bool]:
    """Check for positive in-stock indicators (Strategy 1 - highest priority).

    Returns:
        False if clear in-stock indicators found, True if out-of-stock indicators found, None if unclear
    """
    # Check for in-stock classes with meaningful text content
    # (e.g., <span class="in_stock">Em Stock</span>)
    # Ignore empty icons or elements without text
    in_stock_elements = soup.find_all(attrs={"class": IN_STOCK_CLASS_PATTERN})
    for element in in_stock_elements:
        # Skip pure icon elements (i, svg, img tags typically have no meaningful text)
        if element.name in ["i", "svg", "img"]:
            continue

        # Skip "back in stock" notification elements (false positive)
        classes = " ".join(element.get("class", []))
        if re.search(r"back[-_\s]?in[-_\s]?stock", classes, re.IGNORECASE):
            continue

        text = element.get_text(strip=True)
        # Only consider elements with actual text content (not just icons)
        if text and len(text) > 2:  # At least 3 characters of actual text
            return False

    # Check JSON-LD structured data for availability
    # For products with multiple variants, prioritize in-stock over out-of-stock
    scripts = soup.find_all("script", type="application/ld+json")
    has_in_stock = False
    has_out_of_stock = False

    for script in scripts:
        if script.string:
            if "InStock" in script.string:
                has_in_stock = True
            if "OutOfStock" in script.string:
                has_out_of_stock = True

    # If any variant is in stock, consider product available
    if has_in_stock:
        return False

    # If only out of stock variants found (no in-stock), product is unavailable
    if has_out_of_stock:
        return True

    return None


def _check_meta_tags_for_stock(soup: BeautifulSoup) -> Optional[bool]:
    """Check meta tags for availability (Strategy 2).

    Returns:
        True if out of stock, False if in stock, None if unclear
    """
    meta_tags = [
        ("meta", {"property": "product:availability"}),
        ("meta", {"property": "og:availability"}),
        ("meta", {"itemprop": "availability"}),
    ]

    for tag, attrs in meta_tags:
        element = soup.find(tag, attrs)
        if isinstance(element, Tag):
            content_val = element.get("content", "")
            content = str(content_val).lower() if content_val else ""
            if any(status in content for status in ["outofstock", "out of stock", "soldout"]):
                return True
            if "instock" in content or "in stock" in content:
                return False

    return None


def _check_text_patterns_for_stock(soup: BeautifulSoup) -> Optional[bool]:
    """Check page text for out-of-stock patterns (Strategy 3).

    Returns:
        True if out of stock, None if not found
    """
    page_text = soup.get_text().lower()
    for pattern in OUT_OF_STOCK_PATTERNS:
        if pattern.search(page_text):
            return True

    return None


def _check_class_names_for_stock(soup: BeautifulSoup) -> Optional[bool]:
    """Check CSS classes for out-of-stock indicators (Strategy 4).

    Returns:
        True if out of stock, None if not found
    """
    element = soup.find(attrs={"class": OUT_OF_STOCK_CLASS_PATTERN})
    if element:
        return True

    return None


def is_out_of_stock_with_url(soup: Optional[BeautifulSoup], url: str, config: Config) -> bool:
    """Check if product is out of stock using site-specific and generic strategies.

    Tries strategies in order of reliability:
    0. Site-specific handler (if available)
    1. In-stock indicators (highest priority - classes, JSON-LD)
    2. Meta tags (structured data)
    3. Text patterns (language-specific)
    4. CSS class names (fallback)

    Args:
        soup: BeautifulSoup object of the page (or None)
        url: URL of the page (for site-specific handling)
        config: Configuration instance (required)

    Returns:
        True if product is out of stock, False otherwise (returns False if soup is None)
    """
    if not soup:
        return False

    # Try site-specific stock checking first
    handler = get_site_handler(url, config)
    site_result = handler.check_stock(soup, url)
    if site_result is not None:
        return site_result

    # Fallback to generic strategies
    strategies = [
        _check_for_in_stock_indicators,
        _check_meta_tags_for_stock,
        _check_text_patterns_for_stock,
        _check_class_names_for_stock,
    ]

    for strategy in strategies:
        result = strategy(soup)
        if result is not None:
            return result

    # If no clear indicators, assume in stock
    return False


def is_out_of_stock(soup: Optional[BeautifulSoup]) -> bool:
    """Check if product is out of stock using generic strategies only.

    This function is for backward compatibility and tests.
    For production use, prefer is_out_of_stock_with_url() which includes site-specific handlers.

    Tries strategies in order of reliability:
    1. In-stock indicators (highest priority - classes, JSON-LD)
    2. Meta tags (structured data)
    3. Text patterns (language-specific)
    4. CSS class names (fallback)

    Args:
        soup: BeautifulSoup object of the page (or None)

    Returns:
        True if product is out of stock, False otherwise (returns False if soup is None)
    """
    if not soup:
        return False

    # Try each strategy in order
    strategies = [
        _check_for_in_stock_indicators,
        _check_meta_tags_for_stock,
        _check_text_patterns_for_stock,
        _check_class_names_for_stock,
    ]

    for strategy in strategies:
        result = strategy(soup)
        if result is not None:
            return result

    # If no clear indicators, assume in stock
    return False
