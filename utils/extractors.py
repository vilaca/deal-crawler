"""Price extraction logic for various websites."""

import re
from bs4 import BeautifulSoup, Tag
from typing import Any, Dict, List, Optional

from .config import config
from .site_handlers import get_site_handler

# Compile regex patterns at module level for better performance
PRIORITY_PRICE_CLASS_PATTERN = re.compile(
    r"(price-product|price.*actual|actual.*price|price.*current|current.*price|"
    r"price.*final|final.*price|price.*sale|sale.*price)",
    re.IGNORECASE,
)

GENERIC_PRICE_CLASS_PATTERN = re.compile(r"price", re.IGNORECASE)


def parse_price_string(price_str: Optional[str]) -> Optional[float]:
    """Parse a price string and return float value.

    Args:
        price_str: String containing a price, or None

    Returns:
        Parsed price as float, or None if invalid/empty
    """
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


def _is_element_hidden(
    element: Tag, additional_keywords: Optional[List[str]] = None
) -> bool:
    """Check if element is hidden via classes or inline styles.

    Args:
        element: BeautifulSoup Tag element to check
        additional_keywords: Additional class keywords to check (beyond default hidden ones)

    Returns:
        True if element is hidden, False otherwise
    """
    # Check for hidden classes
    class_attr = element.get("class", [])
    if isinstance(class_attr, list):
        classes = " ".join(class_attr).lower()
    else:
        classes = str(class_attr).lower()

    # Default hidden keywords
    hidden_keywords = ["display-none", "hidden", "d-none"]
    if additional_keywords:
        hidden_keywords.extend(additional_keywords)

    if any(keyword in classes for keyword in hidden_keywords):
        return True

    # Check inline styles
    style = element.get("style", "")
    style_str = str(style) if style else ""
    if "display:none" in style_str.replace(
        " ", ""
    ) or "visibility:hidden" in style_str.replace(" ", ""):
        return True

    return False


def _is_inside_delivery_container(element: Tag) -> bool:
    """Check if element is inside a delivery/shipping-related container.

    Args:
        element: BeautifulSoup Tag element to check

    Returns:
        True if element is inside delivery container, False otherwise
    """
    # Check element and all ancestors up to 5 levels up
    current: Optional[Tag] = element
    for _ in range(6):  # Check element + 5 ancestors
        if not current or not hasattr(current, "get"):
            break

        # Check classes
        class_attr = current.get("class", [])
        if isinstance(class_attr, list):
            classes = " ".join(class_attr).lower()
        else:
            classes = str(class_attr).lower()

        # Check ID
        elem_id = current.get("id", "")
        if elem_id:
            elem_id = str(elem_id).lower()

        # Keywords that indicate delivery/shipping containers
        delivery_keywords = [
            "delivery",
            "shipping",
            "ship",
            "freight",
            "postage",
        ]

        if any(
            keyword in classes or keyword in elem_id for keyword in delivery_keywords
        ):
            return True

        current = current.parent

    return False


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
            if _is_element_hidden(element):
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

    Excludes classes that indicate old/original prices and delivery-related prices.
    """
    generic_price_elements = soup.find_all(class_=GENERIC_PRICE_CLASS_PATTERN)
    for element in generic_price_elements:
        if not isinstance(element, Tag):
            continue

        # Skip elements with classes indicating old/original prices or hidden elements
        if _is_element_hidden(element, ["old", "original", "was", "before", "regular"]):
            continue

        # Skip elements inside delivery/shipping containers
        if _is_inside_delivery_container(element):
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


def extract_price(soup: Optional[BeautifulSoup], url: str) -> Optional[float]:
    """Extract price from HTML using multiple strategies.

    Tries strategies in order of reliability:
    1. Site-specific extraction (if handler provides it)
    2. Meta tags
    3. Data attributes
    4. Priority CSS classes
    5. Generic price classes
    6. Text patterns

    Args:
        soup: BeautifulSoup object to extract price from (or None)
        url: URL of the page (for site-specific handling)

    Returns:
        Extracted price as float, or None if not found
    """
    if not soup:
        return None

    # Try site-specific extraction first
    handler = get_site_handler(url)
    price = handler.extract_price(soup)
    if price:
        return price

    # Fallback to generic extraction strategies
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
