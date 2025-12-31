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

IN_STOCK_CLASS_PATTERN = re.compile(
    r"(?<!back)in.?stock|em.?stock|(?<!in)disponível|(?<!in)disponivel|\bavailable\b",
    re.IGNORECASE,
)


def _check_for_in_stock_indicators(soup: BeautifulSoup) -> Optional[bool]:
    """Check for positive in-stock indicators (Strategy 1 - highest priority).

    Returns:
        False if clear in-stock indicators found, None if unclear
    """
    # Check for in-stock classes with meaningful text content
    # (e.g., <span class="in_stock">Em Stock</span>)
    # Ignore empty icons or elements without text
    in_stock_elements = soup.find_all(attrs={"class": IN_STOCK_CLASS_PATTERN})
    for element in in_stock_elements:
        text = element.get_text(strip=True)
        # Only consider elements with actual text content (not just icons)
        # and exclude "icon" or "svg" elements which are likely just visual indicators
        if text and len(text) > 2:  # At least 3 characters of actual text
            # Additional check: element name should not be just an icon
            if "icon" not in " ".join(element.get("class", [])).lower():
                return False

    # Check JSON-LD structured data for InStock availability
    scripts = soup.find_all("script", type="application/ld+json")
    for script in scripts:
        if script.string and "InStock" in script.string:
            return False

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
            if any(
                status in content
                for status in ["outofstock", "out of stock", "soldout"]
            ):
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


def is_out_of_stock(soup: Optional[BeautifulSoup]) -> bool:
    """Check if product is out of stock using multiple strategies.

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
