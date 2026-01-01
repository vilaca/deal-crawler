"""CLI entry point for Deal Crawler price scraper."""

import argparse
import sys

from utils.data_loader import load_products
from utils.filters import filter_by_sites, filter_by_products
from utils.finder import find_cheapest_prices
from utils.http_client import HttpClient
from utils.markdown_formatter import print_results_markdown
from utils.text_formatter import print_results_text


def main() -> None:
    """Main function to run the price scraper."""
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
