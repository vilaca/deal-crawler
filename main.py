"""CLI entry point for Deal Crawler price scraper."""

import argparse
import os
import sys
from typing import Dict, List

import yaml

from utils.config import config
from utils.data_loader import load_products
from utils.filters import filter_by_sites, filter_by_products
from utils.finder import SearchResults, find_cheapest_prices, filter_best_value_sizes, find_all_prices
from utils.http_client import HttpClient
from utils.markdown_formatter import print_results_markdown
from utils.text_formatter import print_results_text
from utils.optimizer import optimize_shopping_plan
from utils.plan_formatter import print_plan_text, print_plan_markdown
from utils.shipping import ShippingConfig


def _get_env_bool(key: str, default: bool = False) -> bool:
    """Get boolean value from environment variable.

    Args:
        key: Environment variable name
        default: Default value if not set

    Returns:
        Boolean value from environment variable or default
    """
    value = os.getenv(key)
    if value is None:
        return default
    return value.lower() in ("true", "1", "yes")


def _create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser.

    Returns:
        Configured ArgumentParser instance
    """
    parser = argparse.ArgumentParser(description="Find cheapest prices for products across multiple stores")
    parser.add_argument(
        "--markdown",
        action="store_true",
        default=_get_env_bool("DEAL_CRAWLER_MARKDOWN"),
        help="Output in markdown format (env: DEAL_CRAWLER_MARKDOWN)",
    )
    parser.add_argument(
        "--sites",
        type=str,
        default=os.getenv("DEAL_CRAWLER_SITES"),
        help="Filter by site domains, comma-separated (env: DEAL_CRAWLER_SITES)",
    )
    parser.add_argument(
        "--products",
        type=str,
        default=os.getenv("DEAL_CRAWLER_PRODUCTS"),
        help="Filter by product name substrings, comma-separated (env: DEAL_CRAWLER_PRODUCTS)",
    )
    parser.add_argument(
        "--plan",
        type=str,
        default=os.getenv("DEAL_CRAWLER_PLAN"),
        help="Optimize shopping plan for comma-separated products (env: DEAL_CRAWLER_PLAN)",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        default=_get_env_bool("DEAL_CRAWLER_NO_CACHE"),
        help="Bypass HTTP cache (env: DEAL_CRAWLER_NO_CACHE)",
    )
    parser.add_argument(
        "--products-file",
        type=str,
        default=config.products_file,
        help=f"Path to products data file (env: DEAL_CRAWLER_PRODUCTS_FILE, default: {config.products_file})",
    )
    parser.add_argument(
        "--shipping-file",
        type=str,
        default=config.shipping_file,
        help=f"Path to shipping config file (env: DEAL_CRAWLER_SHIPPING_FILE, default: {config.shipping_file})",
    )
    parser.add_argument(
        "--all-sizes",
        action="store_true",
        default=_get_env_bool("DEAL_CRAWLER_ALL_SIZES"),
        help="Show all product sizes (env: DEAL_CRAWLER_ALL_SIZES)",
    )
    parser.add_argument(
        "--optimize-for-value",
        action="store_true",
        default=_get_env_bool("DEAL_CRAWLER_OPTIMIZE_FOR_VALUE"),
        help="Optimize for best price per ml instead of lowest total cost (env: DEAL_CRAWLER_OPTIMIZE_FOR_VALUE)",
    )
    parser.add_argument(
        "--cache-duration",
        type=int,
        default=int(os.getenv("DEAL_CRAWLER_CACHE_DURATION", "3600")),
        help="HTTP cache lifetime in seconds (env: DEAL_CRAWLER_CACHE_DURATION, default: 3600)",
    )
    parser.add_argument(
        "--request-timeout",
        type=int,
        default=int(os.getenv("DEAL_CRAWLER_REQUEST_TIMEOUT", "15")),
        help="HTTP request timeout in seconds (env: DEAL_CRAWLER_REQUEST_TIMEOUT, default: 15)",
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


def _run_optimization_mode(products: Dict[str, List[str]], args: argparse.Namespace) -> None:
    """Run optimization mode to find optimal shopping plan.

    Args:
        products: Filtered products dictionary
        args: Parsed command line arguments
    """
    with HttpClient(
        use_cache=not args.no_cache,
        timeout=args.request_timeout,
        cache_duration=args.cache_duration,
    ) as http_client:
        all_prices = find_all_prices(products, http_client)

    # Load shipping configuration
    try:
        shipping_config = ShippingConfig.load_from_file(args.shipping_file)
    except FileNotFoundError:
        print(f"Error: {args.shipping_file} not found", file=sys.stderr)
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"Error: {args.shipping_file} is not valid YAML: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyError as e:
        print(f"Error: {args.shipping_file} is missing required field: {e}", file=sys.stderr)
        sys.exit(1)

    # Optimize and display
    optimized_plan = optimize_shopping_plan(all_prices, shipping_config, args.optimize_for_value)

    if args.markdown:
        print_plan_markdown(optimized_plan, shipping_config)
    else:
        print_plan_text(optimized_plan, shipping_config)


def _run_standard_mode(products: Dict[str, List[str]], args: argparse.Namespace) -> None:
    """Run standard mode to find cheapest prices.

    Args:
        products: Filtered products dictionary
        args: Parsed command line arguments
    """
    with HttpClient(
        use_cache=not args.no_cache,
        timeout=args.request_timeout,
        cache_duration=args.cache_duration,
    ) as http_client:
        search_results = find_cheapest_prices(products, http_client)

    # Filter by best value if requested
    if not args.all_sizes:
        search_results = filter_best_value_sizes(search_results)

    # Display results
    _display_results(search_results, args.markdown)


def main() -> None:
    """Main function to run the price scraper."""
    # Parse arguments
    parser = _create_argument_parser()
    args = parser.parse_args()

    # Validate mutually exclusive arguments
    if args.plan and args.products:
        print("Error: --plan and --products cannot be used together", file=sys.stderr)
        sys.exit(1)

    # Load and filter products
    products = load_products(args.products_file)
    if not products:
        print("\nNo products to compare. Exiting.", file=sys.stderr)
        sys.exit(1)

    products = _apply_filters(products, args)

    # Additional filtering for plan mode
    if args.plan:
        plan_products = [p.strip() for p in args.plan.split(",")]
        products = filter_by_products(products, plan_products)
        if not products:
            print(f"\nNo products matching: {', '.join(plan_products)}", file=sys.stderr)
            sys.exit(1)

    # Run appropriate mode
    if args.plan:
        _run_optimization_mode(products, args)
    else:
        _run_standard_mode(products, args)


if __name__ == "__main__":
    main()
