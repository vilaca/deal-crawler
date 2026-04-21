#!/usr/bin/env python3
"""Collect all prices from all sites and save to daily CSV.

Scrapes ALL price results (not just cheapest) for every product
across all monitored e-commerce sites, and saves them to a CSV file
or prints to stdout.

Usage:
    python collect_all_prices.py [--output-dir DIR] [--stdout] [--verbose] [--no-progress]
"""

import argparse
import csv
import io
import os
import sys
from datetime import datetime, timezone
from typing import Dict, List, Optional

from utils.config import Config
from utils.data_loader import load_products
from utils.filters import filter_by_products, filter_by_sites
from utils.finder import find_all_prices
from utils.http_client import HttpClient
from utils.price_models import PriceResult
from utils.url_utils import extract_domain


def _write_csv(output: io.TextIOBase, all_prices: Dict[str, List[PriceResult]]) -> int:
    """Write all prices as CSV to a file or stream.

    Args:
        output: Writable text stream (file or stdout).
        all_prices: Dictionary mapping product names to lists of PriceResult.

    Returns:
        Number of data rows written.
    """
    header = ["Product", "Site", "Price", "Price per 100ml", "URL"]
    row_count = 0

    writer = csv.writer(output)
    writer.writerow(header)

    for product_name in sorted(all_prices):
        for result in sorted(all_prices[product_name], key=lambda r: r.price):
            site = extract_domain(result.url)
            price_per_100ml = f"{result.price_per_100ml:.2f}" if result.price_per_100ml else ""
            writer.writerow([product_name, site, f"{result.price:.2f}", price_per_100ml, result.url])
            row_count += 1

    return row_count


def _collect(
    verbose: bool, show_progress: bool, products_filter: Optional[str], sites_filter: Optional[str]
) -> Dict[str, List[PriceResult]]:
    """Load products, apply filters, and scrape all prices.

    Args:
        verbose: If True, print detailed progress.
        show_progress: If True, display progress bar.
        products_filter: Comma-separated product name substrings, or None.
        sites_filter: Comma-separated site domains, or None.

    Returns:
        Dictionary mapping product names to lists of PriceResult.
    """
    config = Config()
    products = load_products(config.products_file)

    if not products:
        print("No products found.", file=sys.stderr)
        sys.exit(1)

    if products_filter:
        products = filter_by_products(products, [p.strip() for p in products_filter.split(",")])
    if sites_filter:
        products = filter_by_sites(products, [s.strip() for s in sites_filter.split(",")])

    if not products:
        print("No products match the given filters.", file=sys.stderr)
        sys.exit(1)

    with HttpClient(config=config, use_cache=False, verbose=verbose) as http_client:
        return find_all_prices(products, http_client, verbose=verbose, show_progress=show_progress)


def main() -> None:
    """Parse arguments and run collection."""
    parser = argparse.ArgumentParser(description="Collect all prices from all sites")
    parser.add_argument("--output-dir", default="history/all", help="Output directory for CSV files")
    parser.add_argument("--stdout", action="store_true", help="Print CSV to stdout instead of writing a file")
    parser.add_argument("--products", help="Filter by product names (comma-separated substrings)")
    parser.add_argument("--sites", help="Filter by site domains (comma-separated)")
    parser.add_argument("--verbose", action="store_true", help="Print detailed progress")
    parser.add_argument("--no-progress", action="store_true", help="Disable progress bar")
    args = parser.parse_args()

    all_prices = _collect(
        args.verbose,
        show_progress=not (args.no_progress or args.verbose),
        products_filter=args.products,
        sites_filter=args.sites,
    )

    if args.stdout:
        row_count = _write_csv(sys.stdout, all_prices)
        print(f"Wrote {row_count} prices", file=sys.stderr)
    else:
        os.makedirs(args.output_dir, exist_ok=True)
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        filepath = os.path.join(args.output_dir, f"{today}.csv")

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            row_count = _write_csv(f, all_prices)

        print(f"Saved {row_count} prices to {filepath}", file=sys.stderr)


if __name__ == "__main__":
    main()
