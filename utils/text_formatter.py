"""Text output formatting utilities for Deal Crawler."""

from typing import Dict, List, Optional

from utils.finder import PriceResult, SearchResults


def _format_product_line(
    product_name: str,
    result: Optional[PriceResult],
    max_name_len: int,
    max_price_width: int,
) -> str:
    """Format a single product line for text output.

    Args:
        product_name: Name of the product
        result: PriceResult object or None if no price found
        max_name_len: Width to pad product name to
        max_price_width: Width to pad price to

    Returns:
        Formatted line string
    """
    if result:
        price_str = f"€{result.price:.2f}"
        # Add price per 100ml if available
        if result.price_per_100ml:
            price_str = f"{price_str} (€{result.price_per_100ml:.2f}/100ml)"
        return f"{product_name:<{max_name_len}} {price_str:>{max_price_width}}  {result.url}"
    return f"{product_name:<{max_name_len}} {'⚠️  No prices found':>{max_price_width}}"


def _sort_and_group_items(
    prices: Dict[str, Optional[PriceResult]],
) -> List[tuple[str, Optional[PriceResult]]]:
    """Sort items by price and group priced items before unpriced items.

    Args:
        prices: Dictionary of product names to PriceResult objects or None

    Returns:
        List of (name, result) tuples sorted by price, with unpriced items last
    """
    items_with_prices: List[tuple[str, Optional[PriceResult]]] = [
        (name, result) for name, result in prices.items() if result
    ]
    items_without_prices: List[tuple[str, Optional[PriceResult]]] = [
        (name, result) for name, result in prices.items() if not result
    ]

    # Sort items with prices by price (ascending)
    # mypy needs the conditional even though we filtered for non-None values
    items_with_prices.sort(key=lambda x: x[1].price if x[1] else 0)

    # Combine: priced items first, then non-priced items
    return items_with_prices + items_without_prices


def _calculate_price_width(items_with_prices: List[tuple[str, PriceResult]]) -> int:
    """Calculate width needed for price column.

    Args:
        items_with_prices: List of items that have prices

    Returns:
        Width required for price display
    """
    # Single pass to extract max price and max price_per_100ml
    max_price = 0.0
    max_per_100ml = 0.0

    for _, result in items_with_prices:
        max_price = max(max_price, result.price)
        if result.price_per_100ml:
            max_per_100ml = max(max_per_100ml, result.price_per_100ml)

    # Calculate base price width
    price_width = len(f"€{max_price:.2f}")

    # Add per-100ml width if any item has it
    if max_per_100ml > 0:
        price_width += len(f" (€{max_per_100ml:.2f}/100ml)")

    return price_width


def _calculate_column_widths(
    sorted_items: List[tuple[str, Optional[PriceResult]]],
) -> tuple[int, int]:
    """Calculate dynamic column widths for product names and prices.

    Args:
        sorted_items: List of (name, result) tuples

    Returns:
        Tuple of (max_name_len, max_price_width)
    """
    if not sorted_items:
        return 0, 0

    # Calculate max product name length
    max_name_len = max(len(name) for name, _ in sorted_items)

    # Separate items with and without prices
    items_with_prices = [(name, result) for name, result in sorted_items if result]

    if not items_with_prices:
        # No prices found - use warning message width
        return max_name_len, len("⚠️  No prices found")

    # Calculate price column width
    price_width = _calculate_price_width(items_with_prices)

    # If mixed scenario, ensure column fits both prices and warning
    has_items_without_prices = len(items_with_prices) < len(sorted_items)
    if has_items_without_prices:
        price_width = max(price_width, len("⚠️  No prices found"))

    return max_name_len, price_width


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
