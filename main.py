"""CLI entry point for Deal Crawler price scraper."""

import argparse
import sys
from typing import Dict, List
from urllib.parse import urlparse

from utils.data_loader import load_products
from utils.finder import find_cheapest_prices, SearchResults
from utils.http_client import HttpClient


def filter_by_sites(
    products: Dict[str, List[str]], sites: List[str]
) -> Dict[str, List[str]]:
    """Filter products to only include URLs from specified sites.

    Args:
        products: Dictionary of product names to URL lists
        sites: List of site domains to include (e.g., ["notino.pt", "wells.pt"])

    Returns:
        Filtered products dictionary
    """
    filtered = {}
    for product_name, urls in products.items():
        filtered_urls = [
            url
            for url in urls
            if any(site.lower() in urlparse(url).netloc.lower() for site in sites)
        ]
        if filtered_urls:
            filtered[product_name] = filtered_urls
    return filtered


def filter_by_products(
    products: Dict[str, List[str]], substrings: List[str]
) -> Dict[str, List[str]]:
    """Filter products to only include those matching substring(s).

    Args:
        products: Dictionary of product names to URL lists
        substrings: List of substrings to match (case-insensitive)

    Returns:
        Filtered products dictionary
    """
    filtered = {}
    for product_name, urls in products.items():
        if any(substring.lower() in product_name.lower() for substring in substrings):
            filtered[product_name] = urls
    return filtered


def print_results_text(search_results: SearchResults) -> None:
    """Print results in text format optimized for terminal."""
    print("\n🛒 Best Prices")

    # Sort by price: items with prices first (by price), then items without prices
    items_with_prices = [(name, result) for name, result in search_results.prices.items() if result]
    items_without_prices = [(name, result) for name, result in search_results.prices.items() if not result]

    # Sort items with prices by price (ascending)
    items_with_prices.sort(key=lambda x: x[1][0])

    # Combine: priced items first, then non-priced items
    sorted_items = items_with_prices + items_without_prices

    # Calculate max product name length for dynamic column width
    max_name_len = max(len(name) for name, _ in sorted_items) if sorted_items else 0

    # Calculate max price width for decimal point alignment
    max_price_width = 0
    if items_with_prices:
        max_price = max(price for _, (price, _) in items_with_prices)
        max_price_width = len(f"€{max_price:.2f}")

    # Calculate maximum line length for dynamic separator
    max_line_len = 0
    for product_name, result in sorted_items:
        if result:
            price, url = result
            # name + space + price + "  " + url
            line_len = max_name_len + 1 + max_price_width + 2 + len(url)
        else:
            # name + space + message
            line_len = max_name_len + 1 + len("⚠️  No prices found")
        max_line_len = max(max_line_len, line_len)

    # Print separator with dynamic width
    print("=" * max_line_len)

    for product_name, result in sorted_items:
        if result:
            price, url = result
            # Columnar format: product name (dynamic width) | price (decimal-aligned) | URL
            price_str = f"€{price:.2f}"
            print(f"{product_name:<{max_name_len}} {price_str:>{max_price_width}}  {url}")
        else:
            # No prices found
            print(f"{product_name:<{max_name_len}} {'⚠️  No prices found':>{max_price_width}}")

    print("=" * max_line_len)


def print_results_markdown(search_results: SearchResults) -> None:
    """Print results in markdown format."""
    print("\n# 🛒 Best Prices\n")
    print("| Product | Price | Link |")
    print("|---------|-------|------|")

    for product_name, result in search_results.prices.items():
        if result:
            price, url = result
            domain = urlparse(url).netloc.replace("www.", "")
            print(f"| **{product_name}** | €{price:.2f} | [🔗 {domain}]({url}) |")
        else:
            print(f"| **{product_name}** | _No prices found_ | - |")

    print("\n---\n")


def main() -> None:
    """Main function to run the price scraper."""
    parser = argparse.ArgumentParser(
        description="Find cheapest prices for products across multiple stores"
    )
    parser.add_argument(
        "--markdown",
        action="store_true",
        help="Output in markdown format (default: text format for terminal)",
    )
    parser.add_argument(
        "--sites",
        type=str,
        help="Filter by site domains (comma-separated, e.g., 'notino.pt,wells.pt')",
    )
    parser.add_argument(
        "--products",
        type=str,
        help="Filter by product name substrings (comma-separated, case-insensitive)",
    )
    args = parser.parse_args()

    # Load products from YAML
    products = load_products("data.yml")

    if not products:
        print("\nNo products to compare. Exiting.", file=sys.stderr)
        sys.exit(1)

    # Apply filters if specified
    if args.sites:
        sites = [s.strip() for s in args.sites.split(",")]
        products = filter_by_sites(products, sites)
        if not products:
            print(f"\nNo products found for sites: {', '.join(sites)}", file=sys.stderr)
            sys.exit(1)

    if args.products:
        substrings = [s.strip() for s in args.products.split(",")]
        products = filter_by_products(products, substrings)
        if not products:
            print(f"\nNo products matching: {', '.join(substrings)}", file=sys.stderr)
            sys.exit(1)

    # Find cheapest prices using HttpClient context manager
    with HttpClient() as http_client:
        search_results = find_cheapest_prices(products, http_client)

    # Display results based on format
    if args.markdown:
        print_results_markdown(search_results)
    else:
        print_results_text(search_results)

    # Print summary
    search_results.print_summary(markdown=args.markdown)


if __name__ == "__main__":
    main()
