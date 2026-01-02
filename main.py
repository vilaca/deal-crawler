"""CLI entry point for Deal Crawler price scraper."""

import argparse
import sys
from typing import Dict, List

from utils.config import config
from utils.data_loader import load_products
from utils.filters import filter_by_sites, filter_by_products
from utils.finder import SearchResults, find_cheapest_prices, filter_best_value_sizes
from utils.http_client import HttpClient
from utils.markdown_formatter import print_results_markdown
from utils.text_formatter import print_results_text


def _create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser.

    Returns:
        Configured ArgumentParser instance
    """
    parser = argparse.ArgumentParser(description="Find cheapest prices for products across multiple stores")
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
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Bypass HTTP cache (force fresh requests)",
    )
    parser.add_argument(
        "--products-file",
        type=str,
        default=config.products_file,
        help=f"Path to products data file (default: {config.products_file})",
    )
    parser.add_argument(
        "--all-sizes",
        action="store_true",
        help="Show all product sizes (default: only show best value per 100ml)",
    )
    return parser


def _apply_filters(products: Dict[str, List[str]], args: argparse.Namespace) -> Dict[str, List[str]]:
    """Apply site and product filters if specified.

    Args:
        products: Dictionary of products to filter
        args: Parsed command line arguments

    Returns:
        Filtered products dictionary

    Raises:
        SystemExit: If filtering results in no products
    """
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

    return products


def _display_results(search_results: SearchResults, markdown: bool) -> None:
    """Display search results in the specified format.

    Args:
        search_results: Search results to display
        markdown: If True, use markdown format; otherwise use text format
    """
    if markdown:
        print_results_markdown(search_results)
    else:
        print_results_text(search_results)

    search_results.print_summary(markdown=markdown)


def main() -> None:
    """Main function to run the price scraper."""
    # Parse arguments
    parser = _create_argument_parser()
    args = parser.parse_args()

    # Load products
    products = load_products(args.products_file)
    if not products:
        print("\nNo products to compare. Exiting.", file=sys.stderr)
        sys.exit(1)

    # Apply filters
    products = _apply_filters(products, args)

    # Find cheapest prices
    with HttpClient(use_cache=not args.no_cache) as http_client:
        search_results = find_cheapest_prices(products, http_client)

    # Filter by best value if requested
    show_all_sizes = args.all_sizes or config.show_all_sizes
    if not show_all_sizes:
        search_results = filter_best_value_sizes(search_results)

    # Display results
    _display_results(search_results, args.markdown)


if __name__ == "__main__":
    main()
