"""Collect all prices from all sites and save to daily CSV.

Scrapes ALL price results (not just cheapest) for every product
across all monitored e-commerce sites, and saves them to a CSV file
in the history/all/ directory.

Usage:
    python collect_all_prices.py [--output-dir DIR] [--verbose] [--no-progress]
"""

import argparse
import csv
import os
import sys
from datetime import datetime, timezone
from typing import Dict, List

from utils.config import Config
from utils.data_loader import load_products
from utils.finder import find_all_prices
from utils.http_client import HttpClient
from utils.price_models import PriceResult
from utils.url_utils import extract_domain


def _write_csv(filepath: str, all_prices: Dict[str, List[PriceResult]]) -> int:
    """Write all prices to a CSV file.

    Args:
        filepath: Output CSV file path.
        all_prices: Dictionary mapping product names to lists of PriceResult.

    Returns:
        Number of data rows written.
    """
    header = ["Product", "Site", "Price", "Price per 100ml", "URL"]
    row_count = 0

    with open(filepath, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(header)

        for product_name in sorted(all_prices):
            for result in sorted(all_prices[product_name], key=lambda r: r.price):
                site = extract_domain(result.url)
                price_per_100ml = f"{result.price_per_100ml:.2f}" if result.price_per_100ml else ""
                writer.writerow([product_name, site, f"{result.price:.2f}", price_per_100ml, result.url])
                row_count += 1

    return row_count


def _collect_and_save(output_dir: str, verbose: bool, show_progress: bool) -> str:
    """Load products, scrape all prices, and save to CSV.

    Args:
        output_dir: Directory to write the CSV file.
        verbose: If True, print detailed progress.
        show_progress: If True, display progress bar.

    Returns:
        Path to the output CSV file.
    """
    config = Config()
    products = load_products(config.products_file)

    if not products:
        print("No products found.", file=sys.stderr)
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    filepath = os.path.join(output_dir, f"{today}.csv")

    with HttpClient(config=config, use_cache=False, verbose=verbose) as http_client:
        all_prices = find_all_prices(products, http_client, verbose=verbose, show_progress=show_progress)

    row_count = _write_csv(filepath, all_prices)

    print(f"Saved {row_count} prices to {filepath}", file=sys.stderr)
    return filepath


def main() -> None:
    """Parse arguments and run collection."""
    parser = argparse.ArgumentParser(description="Collect all prices from all sites")
    parser.add_argument("--output-dir", default="history/all", help="Output directory for CSV files")
    parser.add_argument("--verbose", action="store_true", help="Print detailed progress")
    parser.add_argument("--no-progress", action="store_true", help="Disable progress bar")
    args = parser.parse_args()

    _collect_and_save(args.output_dir, args.verbose, show_progress=not (args.no_progress or args.verbose))


if __name__ == "__main__":
    main()
