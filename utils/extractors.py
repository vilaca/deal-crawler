"""Price extraction logic for various websites."""

import re
from bs4 import BeautifulSoup, Tag
from typing import Any, Dict, List, Optional

from .config import Config
from .site_handlers import get_site_handler

# Compile regex patterns at module level for better performance
PRIORITY_PRICE_CLASS_PATTERN = re.compile(
    r"(price-product|price.*actual|actual.*price|price.*current|current.*price|"
    r"price.*final|final.*price|price.*sale|sale.*price)",
    re.IGNORECASE,
)

GENERIC_PRICE_CLASS_PATTERN = re.compile(r"price", re.IGNORECASE)

# Keywords that indicate delivery/shipping containers
DELIVERY_KEYWORDS = [
    "delivery",
    "shipping",
    "ship",
    "freight",
    "postage",
]


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


def _is_element_hidden(element: Tag, additional_keywords: Optional[List[str]] = None) -> bool:
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
    if "display:none" in style_str.replace(" ", "") or "visibility:hidden" in style_str.replace(" ", ""):
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

        # Check if any delivery keyword is present
        if any(keyword in classes or keyword in elem_id for keyword in DELIVERY_KEYWORDS):
            return True

        current = current.parent

    return False


def _extract_price_from_element(
    element: Tag,
    *,
    check_content: bool = True,
    check_text: bool = True,
    attribute_name: Optional[str] = None,
) -> Optional[float]:
    """Extract price from a single element using various strategies.

    Args:
        element: BeautifulSoup Tag element to extract price from
        check_content: Whether to check 'content' attribute
        check_text: Whether to check text content
        attribute_name: Optional specific attribute to check (e.g., 'data-price')

    Returns:
        Extracted price or None if not found
    """
    # Check specific attribute if provided
    if attribute_name:
        attr_value = element.get(attribute_name)
        if attr_value and isinstance(attr_value, str):
            price = parse_price_string(attr_value)
            if price:
                return price

    # Check content attribute
    if check_content:
        content = element.get("content")
        if content and isinstance(content, str):
            price = parse_price_string(content)
            if price:
                return price

    # Check text content
    if check_text:
        text = element.get_text(strip=True)
        price = parse_price_string(text)
        if price:
            return price

    return None


def _extract_price_from_elements(
    elements: List[Tag],
    *,
    skip_hidden: bool = False,
    skip_delivery: bool = False,
    exclude_keywords: Optional[List[str]] = None,
    check_content: bool = True,
    check_text: bool = True,
    attribute_name: Optional[str] = None,
) -> Optional[float]:
    """Extract price from a list of elements with filtering options.

    Args:
        elements: List of BeautifulSoup Tag elements to check
        skip_hidden: Whether to skip hidden elements
        skip_delivery: Whether to skip elements in delivery containers
        exclude_keywords: Additional keywords to check when skipping hidden elements
        check_content: Whether to check 'content' attribute
        check_text: Whether to check text content
        attribute_name: Optional specific attribute to check (e.g., 'data-price')

    Returns:
        First successfully extracted price or None
    """
    for element in elements:
        if not isinstance(element, Tag):
            continue

        # Skip hidden elements if requested
        if skip_hidden and _is_element_hidden(element, exclude_keywords):
            continue

        # Skip delivery container elements if requested
        if skip_delivery and _is_inside_delivery_container(element):
            continue

        # Try to extract price from this element
        price = _extract_price_from_element(
            element,
            check_content=check_content,
            check_text=check_text,
            attribute_name=attribute_name,
        )
        if price:
            return price

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
            price = _extract_price_from_element(element, check_text=False)
            if price:
                return price
    return None


def _extract_price_from_data_attribute(soup: BeautifulSoup) -> Optional[float]:
    """Extract price from data-price attribute (Strategy 2)."""
    data_price_elements = soup.find_all(attrs={"data-price": True})
    return _extract_price_from_elements(
        data_price_elements,
        check_content=False,
        check_text=False,
        attribute_name="data-price",
    )


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
        price = _extract_price_from_elements(elements, skip_hidden=True)
        if price:
            return price
    return None


def _extract_price_from_generic_classes(soup: BeautifulSoup) -> Optional[float]:
    """Extract price from generic price classes (Strategy 4).

    Excludes classes that indicate old/original prices and delivery-related prices.
    """
    generic_price_elements = soup.find_all(class_=GENERIC_PRICE_CLASS_PATTERN)
    return _extract_price_from_elements(
        generic_price_elements,
        skip_hidden=True,
        skip_delivery=True,
        exclude_keywords=["old", "original", "was", "before", "regular"],
    )


def _extract_price_from_text_patterns(soup: BeautifulSoup, config: Config) -> Optional[float]:
    """Extract price from text patterns in page content (Strategy 5).

    Args:
        soup: BeautifulSoup object to extract from
        config: Configuration instance for price validation

    Returns:
        Extracted price or None
    """
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


def _get_extraction_strategies(config: Config) -> List[Any]:
    """Factory function returning price extraction strategies in priority order.

    This factory makes strategy selection explicit and allows for easy
    modification of the extraction pipeline. Strategies are tried in order
    from most reliable to least reliable.

    Args:
        config: Configuration instance for price validation

    Returns:
        List of extraction strategy functions in priority order:
        1. Meta tags (structured data)
        2. Data attributes (explicit pricing data)
        3. Priority CSS classes (likely price elements)
        4. Generic price classes (broad search)
        5. Text patterns (last resort fallback)
    """
    return [
        _extract_price_from_meta_tags,
        _extract_price_from_data_attribute,
        _extract_price_from_priority_classes,
        _extract_price_from_generic_classes,
        lambda soup: _extract_price_from_text_patterns(soup, config),
    ]


def extract_price(soup: Optional[BeautifulSoup], url: str, config: Config) -> Optional[float]:
    """Extract price from HTML using multiple strategies.

    Tries site-specific extraction first, then falls back to generic strategies
    returned by the extraction factory.

    Args:
        soup: BeautifulSoup object to extract price from (or None)
        url: URL of the page (for site-specific handling)
        config: Configuration instance (required)

    Returns:
        Extracted price as float, or None if not found
    """
    if not soup:
        return None

    # Try site-specific extraction first
    handler = get_site_handler(url, config)
    price = handler.extract_price(soup)
    if price:
        return price

    # Fallback to generic extraction strategies from factory
    strategies = _get_extraction_strategies(config)
    for strategy in strategies:
        price = strategy(soup)
        if price:
            return price

    return None
