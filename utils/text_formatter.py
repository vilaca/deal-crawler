"""Text output formatting utilities for Deal Crawler."""

from typing import Dict, List, Optional, Tuple

from utils.finder import SearchResults


def _format_product_line(
    product_name: str,
    result: Optional[Tuple[float, str]],
    max_name_len: int,
    max_price_width: int,
) -> str:
    """Format a single product line for text output.

    Args:
        product_name: Name of the product
        result: Tuple of (price, url) or None if no price found
        max_name_len: Width to pad product name to
        max_price_width: Width to pad price to

    Returns:
        Formatted line string
    """
    if result:
        price, url = result
        price_str = f"€{price:.2f}"
        return f"{product_name:<{max_name_len}} {price_str:>{max_price_width}}  {url}"
    return f"{product_name:<{max_name_len}} {'⚠️  No prices found':>{max_price_width}}"


def _sort_and_group_items(
    prices: Dict[str, Optional[Tuple[float, str]]],
) -> List[Tuple[str, Optional[Tuple[float, str]]]]:
    """Sort items by price and group priced items before unpriced items.

    Args:
        prices: Dictionary of product names to (price, url) tuples or None

    Returns:
        List of (name, result) tuples sorted by price, with unpriced items last
    """
    items_with_prices: List[Tuple[str, Optional[Tuple[float, str]]]] = [
        (name, result) for name, result in prices.items() if result
    ]
    items_without_prices: List[Tuple[str, Optional[Tuple[float, str]]]] = [
        (name, result) for name, result in prices.items() if not result
    ]

    # Sort items with prices by price (ascending)
    # mypy needs the conditional even though we filtered for non-None values
    items_with_prices.sort(key=lambda x: x[1][0] if x[1] else 0)

    # Combine: priced items first, then non-priced items
    return items_with_prices + items_without_prices


def _calculate_column_widths(
    sorted_items: List[Tuple[str, Optional[Tuple[float, str]]]],
) -> Tuple[int, int]:
    """Calculate dynamic column widths for product names and prices.

    Args:
        sorted_items: List of (name, result) tuples

    Returns:
        Tuple of (max_name_len, max_price_width)
    """
    if not sorted_items:
        return 0, 0

    # Calculate max product name length for dynamic column width
    max_name_len = max(len(name) for name, _ in sorted_items)

    # Calculate max price width for decimal point alignment
    items_with_prices = [(name, result) for name, result in sorted_items if result]
    warning_msg_width = len("⚠️  No prices found")

    if items_with_prices:
        max_price = max(price for _, (price, _) in items_with_prices)
        price_width = len(f"€{max_price:.2f}")

        # Check if there are items without prices (mixed scenario)
        has_items_without_prices = len(items_with_prices) < len(sorted_items)

        if has_items_without_prices:
            # In mixed scenarios, ensure the column is wide enough for both
            # prices AND the warning message to maintain alignment
            max_price_width = max(price_width, warning_msg_width)
        else:
            # All items have prices, no need to account for warning message
            max_price_width = price_width
    else:
        # If no items have prices, use the width of the "No prices found" message
        max_price_width = warning_msg_width

    return max_name_len, max_price_width


def print_results_text(search_results: SearchResults) -> None:
    """Print results in text format optimized for terminal."""
    # Minimum separator width for visual consistency
    min_separator_width = 50

    print("\n🛒 Best Prices")

    # Sort and group items
    sorted_items = _sort_and_group_items(search_results.prices)

    # Handle empty results explicitly
    if not sorted_items:
        print("=" * min_separator_width)
        print("No products to display")
        print("=" * min_separator_width)
        return

    # Calculate column widths
    max_name_len, max_price_width = _calculate_column_widths(sorted_items)

    # Format all lines (avoids code duplication and repeated iterations)
    formatted_lines = [
        _format_product_line(name, result, max_name_len, max_price_width) for name, result in sorted_items
    ]

    # Calculate separator width based on longest formatted line (with minimum width)
    max_line_len = max(len(line) for line in formatted_lines) if formatted_lines else 0
    separator_width = max(max_line_len, min_separator_width)

    # Print separator, content lines, and closing separator
    print("=" * separator_width)
    for line in formatted_lines:
        print(line)
    print("=" * separator_width)
