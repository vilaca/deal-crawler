"""Price extraction logic for various websites."""

import re
from bs4 import BeautifulSoup, Tag
from typing import Any, Dict, List, Optional

from src.config import config

# Compile regex patterns at module level for better performance
PRIORITY_PRICE_CLASS_PATTERN = re.compile(
    r"(price-product|price.*actual|actual.*price|price.*current|current.*price|"
    r"price.*final|final.*price|price.*sale|sale.*price)",
    re.IGNORECASE,
)

GENERIC_PRICE_CLASS_PATTERN = re.compile(r"price", re.IGNORECASE)


def parse_price_string(price_str: str) -> Optional[float]:
    """Parse a price string and return float value."""
    if not price_str:
        return None

    try:
        # First, extract price pattern (digits with comma or dot as decimal)
        # This prevents multiple prices from merging when spaces are removed
        match = re.search(r"(\d+[,.]?\d{0,2})", str(price_str))
        if match:
            price_text = match.group(1)
            # Remove currency symbols and spaces from extracted price
            cleaned = re.sub(r"[€$£\s]", "", price_text)
            # Replace comma with dot for decimal
            cleaned = cleaned.replace(",", ".")
            return float(cleaned)
    except (ValueError, AttributeError):
        pass

    return None


def extract_price_notino(soup: BeautifulSoup) -> Optional[float]:
    """Extract price from notino.pt JSON data."""
    if not soup:
        return None

    # Look for JSON data with price information
    all_scripts = soup.find_all("script")

    for script in all_scripts:
        if not script.string:
            continue

        script_content = str(script.string)

        # Look for price in JSON format
        if '"price"' in script_content:
            try:
                # Try to extract price value from JSON-like structures
                # Look for "price":NUMBER pattern
                price_matches = re.findall(
                    r'"price"\s*:\s*([0-9]+\.?[0-9]*)', script_content
                )
                for price_str in price_matches:
                    price = float(price_str)
                    # Sanity check: price should be reasonable
                    if config.min_price < price < config.max_price:
                        return price
            except ValueError:
                continue

    return None


def _extract_price_from_meta_tags(soup: BeautifulSoup) -> Optional[float]:
    """Extract price from meta tags (Strategy 1)."""
    meta_tags = [
        ("meta", {"property": "product:price:amount"}),
        ("meta", {"property": "og:price:amount"}),
        ("meta", {"name": "price"}),
    ]

    for tag, attrs in meta_tags:
        element = soup.find(tag, attrs)
        if isinstance(element, Tag):
            content = element.get("content")
            if content and isinstance(content, str):
                price = parse_price_string(content)
                if price:
                    return price
    return None


def _extract_price_from_data_attribute(soup: BeautifulSoup) -> Optional[float]:
    """Extract price from data-price attribute (Strategy 2)."""
    data_price_elements = soup.find_all(attrs={"data-price": True})
    for element in data_price_elements:
        if isinstance(element, Tag):
            data_price = element.get("data-price")
            if data_price and isinstance(data_price, str):
                price = parse_price_string(data_price)
                if price:
                    return price
    return None


def _extract_price_from_priority_classes(soup: BeautifulSoup) -> Optional[float]:
    """Extract price from priority CSS classes (Strategy 3).

    Prioritizes actual/discounted prices over original prices.
    Priority order: actual > current > final > sale over original > old > was
    """
    priority_price_classes: List[Dict[str, Any]] = [
        {"class": PRIORITY_PRICE_CLASS_PATTERN},
        {"itemprop": "price"},
    ]

    for selector in priority_price_classes:
        elements = soup.find_all(attrs=selector)
        for element in elements:
            if not isinstance(element, Tag):
                continue

            # Skip hidden elements (e.g., alternative variants)
            class_attr = element.get("class", [])
            if isinstance(class_attr, list):
                classes = " ".join(class_attr).lower()
            else:
                classes = str(class_attr).lower()

            if any(
                keyword in classes for keyword in ["display-none", "hidden", "d-none"]
            ):
                continue

            # Skip elements with display:none or visibility:hidden in style
            style = element.get("style", "")
            style_str = str(style) if style else ""
            if "display:none" in style_str.replace(
                " ", ""
            ) or "visibility:hidden" in style_str.replace(" ", ""):
                continue

            # Check content attribute first
            content = element.get("content")
            if content and isinstance(content, str):
                price = parse_price_string(content)
                if price:
                    return price

            # Check text content
            text = element.get_text(strip=True)
            price = parse_price_string(text)
            if price:
                return price
    return None


def _extract_price_from_generic_classes(soup: BeautifulSoup) -> Optional[float]:
    """Extract price from generic price classes (Strategy 4).

    Excludes classes that indicate old/original prices.
    """
    generic_price_elements = soup.find_all(class_=GENERIC_PRICE_CLASS_PATTERN)
    for element in generic_price_elements:
        if not isinstance(element, Tag):
            continue
        # Skip elements with classes indicating old/original prices
        class_attr = element.get("class", [])
        if isinstance(class_attr, list):
            classes = " ".join(class_attr).lower()
        else:
            classes = str(class_attr).lower()

        if any(
            keyword in classes
            for keyword in [
                "old",
                "original",
                "was",
                "before",
                "regular",
                "display-none",
                "hidden",
                "d-none",
            ]
        ):
            continue

        # Skip elements with display:none or visibility:hidden in style
        style = element.get("style", "")
        style_str = str(style) if style else ""
        if "display:none" in style_str.replace(
            " ", ""
        ) or "visibility:hidden" in style_str.replace(" ", ""):
            continue

        # Check content attribute first
        content = element.get("content")
        if content and isinstance(content, str):
            price = parse_price_string(content)
            if price:
                return price

        # Check text content
        text = element.get_text(strip=True)
        price = parse_price_string(text)
        if price:
            return price
    return None


def _extract_price_from_text_patterns(soup: BeautifulSoup) -> Optional[float]:
    """Extract price from text patterns in page content (Strategy 5)."""
    all_text = soup.get_text()
    price_patterns = [
        r"€\s*(\d+[.,]\d{2})",  # €29.99 or € 29,99
        r"(\d+[.,]\d{2})\s*€",  # 29.99€ or 29,99 €
        r"EUR\s*(\d+[.,]\d{2})",  # EUR 29.99
    ]

    for pattern in price_patterns:
        matches = re.findall(pattern, all_text)
        if matches:
            # Get the first reasonable price found
            for match in matches:
                price = parse_price_string(match)
                if price and config.min_price < price < config.max_price:
                    return price
    return None


def extract_price(soup: BeautifulSoup, url: str) -> Optional[float]:
    """Extract price from HTML using multiple strategies.

    Tries strategies in order of reliability:
    1. Site-specific extraction (notino.pt)
    2. Meta tags
    3. Data attributes
    4. Priority CSS classes
    5. Generic price classes
    6. Text patterns
    """
    if not soup:
        return None

    # Special handling for notino.pt
    if "notino.pt" in url:
        price = extract_price_notino(soup)
        if price:
            return price

    # Try each extraction strategy in order
    strategies = [
        _extract_price_from_meta_tags,
        _extract_price_from_data_attribute,
        _extract_price_from_priority_classes,
        _extract_price_from_generic_classes,
        _extract_price_from_text_patterns,
    ]

    for strategy in strategies:
        price = strategy(soup)
        if price:
            return price

    return None
