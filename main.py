"""CLI entry point for Deal Crawler price scraper."""

import argparse
import sys
from urllib.parse import urlparse

from utils.data_loader import load_products
from utils.finder import find_cheapest_prices
from utils.http_client import HttpClient


def print_results_text(search_results):
    """Print results in text format optimized for terminal."""
    print("\n🛒 Cheapest Prices")
    print("=" * 70)

    for product_name, result in search_results.prices.items():
        if result:
            price, url = result
            domain = urlparse(url).netloc.replace("www.", "")
            print(f"\n{product_name}")
            print(f"  Price: €{price:.2f}")
            print(f"  Store: {domain}")
            print(f"  Link:  {url}")
        else:
            print(f"\n{product_name}")
            print("  ⚠️  No prices found")

    print("\n" + "=" * 70)


def print_results_markdown(search_results):
    """Print results in markdown format."""
    print("\n# 🛒 Cheapest Prices\n")
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


def main():
    """Main function to run the price scraper."""
    parser = argparse.ArgumentParser(
        description="Find cheapest prices for products across multiple stores"
    )
    parser.add_argument(
        "--markdown",
        action="store_true",
        help="Output in markdown format (default: text format for terminal)",
    )
    args = parser.parse_args()

    # Load products from YAML
    products = load_products("data.yml")

    if not products:
        print("\nNo products to compare. Exiting.", file=sys.stderr)
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
