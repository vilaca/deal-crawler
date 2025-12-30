"""Stock availability checker for products."""

import re
from bs4 import BeautifulSoup, Tag
from typing import Optional

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

OUT_OF_STOCK_CLASS_PATTERN = re.compile(
    r"out.?of.?stock|sold.?out|unavailable", re.IGNORECASE
)


def _check_meta_tags_for_stock(soup: BeautifulSoup) -> Optional[bool]:
    """Check meta tags for availability (Strategy 1).

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
            if any(
                status in content
                for status in ["outofstock", "out of stock", "soldout"]
            ):
                return True
            if "instock" in content or "in stock" in content:
                return False

    return None


def _check_text_patterns_for_stock(soup: BeautifulSoup) -> Optional[bool]:
    """Check page text for out-of-stock patterns (Strategy 2).

    Returns:
        True if out of stock, None if not found
    """
    page_text = soup.get_text().lower()
    for pattern in OUT_OF_STOCK_PATTERNS:
        if pattern.search(page_text):
            return True

    return None


def _check_class_names_for_stock(soup: BeautifulSoup) -> Optional[bool]:
    """Check CSS classes for out-of-stock indicators (Strategy 3).

    Returns:
        True if out of stock, None if not found
    """
    element = soup.find(attrs={"class": OUT_OF_STOCK_CLASS_PATTERN})
    if element:
        return True

    return None


def is_out_of_stock(soup: BeautifulSoup) -> bool:
    """Check if product is out of stock using multiple strategies.

    Tries strategies in order of reliability:
    1. Meta tags (most reliable)
    2. Text patterns (language-specific)
    3. CSS class names (fallback)

    Args:
        soup: BeautifulSoup object of the page

    Returns:
        True if product is out of stock, False otherwise
    """
    if not soup:
        return False

    # Try each strategy in order
    strategies = [
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
