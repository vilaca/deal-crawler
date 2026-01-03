"""CLI entry point for Deal Crawler price scraper."""

import argparse
import sys
from typing import Dict, List

from utils.config import config
from utils.data_loader import load_products
from utils.filters import filter_by_sites, filter_by_products
from utils.finder import (
    SearchResults,
    find_cheapest_prices,
    filter_best_value_sizes,
    find_all_prices,
    filter_all_prices_by_best_value,
)
from utils.http_client import HttpClient
from utils.markdown_formatter import print_results_markdown
from utils.optimizer import optimize_shopping_plan
from utils.plan_formatter import print_plan_markdown, print_plan_text
from utils.shipping import load_shipping_config
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
        "--plan",
        type=str,
        nargs="?",
        const="",
        help="Optimize purchase plan to minimize total cost including shipping. "
        "Optionally specify comma-separated products, or use without value to optimize all products",
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

    # Apply filters (--sites and --products)
    products = _apply_filters(products, args)

    # Handle --plan mode: optimize purchases across stores
    if args.plan is not None:
        # If --plan has a value (comma-separated products), filter to those
        if args.plan:  # Non-empty string
            plan_products = [p.strip() for p in args.plan.split(",")]
            products = filter_by_products(products, plan_products)
            if not products:
                print(f"\nNo products matching: {', '.join(plan_products)}", file=sys.stderr)
                sys.exit(1)
        # If --plan is empty, use all (already filtered) products

        # Find ALL prices (not just cheapest) for optimization
        with HttpClient(use_cache=not args.no_cache) as http_client:
            all_prices = find_all_prices(products, http_client)

        # Load shipping configuration (needed for value filtering)
        try:
            shipping_config = load_shipping_config("shipping.yaml")
        except FileNotFoundError:
            print("\nError: shipping.yaml not found", file=sys.stderr)
            print("Please ensure shipping.yaml exists in the project directory", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"\nError loading shipping configuration: {e}", file=sys.stderr)
            sys.exit(1)

        # For plan mode, let optimizer see all sizes to find optimal solution
        # The optimizer will select best size+store+shipping combination
        # Note: --all-sizes flag doesn't apply to plan mode (optimizer decides)

        # Optimize shopping plan (exhaustive search across all sizes and stores)
        optimized_plan = optimize_shopping_plan(all_prices, shipping_config)

        # Display optimized plan
        if args.markdown:
            print_plan_markdown(optimized_plan)
        else:
            print_plan_text(optimized_plan)

    # Normal mode: find cheapest prices
    else:
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
