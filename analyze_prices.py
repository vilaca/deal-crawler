#!/usr/bin/env python3
"""Analyze historical price data to help determine when to buy products.

This script reads CSV files from the history folder and provides insights like:
- Current price
- Average price over different time periods
- Lowest/highest prices and when they occurred
- Price trends
- Out of stock frequency
"""

import argparse
import csv
import shutil
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from statistics import mean
from typing import Dict, List, Optional
from urllib.parse import urlparse


# Configuration constants
DAYS_FOR_AVERAGE = 30
DEAL_THRESHOLD_GREAT = -10.0  # Below this percentage = great deal (🔥)
DEAL_THRESHOLD_GOOD = 0.0     # Below this percentage = good deal (✅)
TABLE_FIXED_COLUMNS_WIDTH = 71
MIN_PRODUCT_COLUMN_WIDTH = 30
MAX_PRODUCT_COLUMN_WIDTH = 80


@dataclass
class PriceRecord:
    """Single price observation for a product."""

    date: datetime
    price: Optional[float]
    price_per_100ml: Optional[float]
    url: str


@dataclass
class PriceStats:
    """Statistical analysis of product prices for summary display."""

    product_name: str
    current_price: Optional[float]
    current_price_per_100ml: Optional[float]
    current_url: str
    current_date: Optional[datetime]
    avg_price_30d: Optional[float]
    avg_price_per_100ml_30d: Optional[float]
    lowest_price_ever: Optional[float]
    lowest_price_per_100ml_ever: Optional[float]
    last_time_this_cheap_ever: Optional[datetime]
    last_time_this_cheap_per_100ml_ever: Optional[datetime]


def parse_csv_files(history_dir: Path) -> Dict[str, List[PriceRecord]]:
    """Parse all CSV files from history directory.

    Args:
        history_dir: Path to directory containing historical CSV files

    Returns:
        Dictionary mapping product names to list of price records
    """
    products: Dict[str, List[PriceRecord]] = defaultdict(list)

    csv_files = sorted(history_dir.glob("*.csv"))
    if not csv_files:
        print(f"No CSV files found in {history_dir}", file=sys.stderr)
        return products

    for csv_file in csv_files:
        # Extract date from filename (format: YYYY-MM-DD.csv)
        try:
            date_str = csv_file.stem  # Remove .csv extension
            date = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            print(f"Skipping file with invalid date format: {csv_file}", file=sys.stderr)
            continue

        try:
            with open(csv_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    product_name = row.get("Product", "").strip()
                    if not product_name:
                        continue

                    # Parse price (empty means out of stock)
                    price_str = row.get("Price", "").strip()
                    price = float(price_str) if price_str else None

                    # Parse price per 100ml (optional)
                    price_per_100ml_str = row.get("Price per 100ml", "").strip()
                    price_per_100ml = float(price_per_100ml_str) if price_per_100ml_str else None

                    url = row.get("URL", "").strip()

                    products[product_name].append(
                        PriceRecord(
                            date=date,
                            price=price,
                            price_per_100ml=price_per_100ml,
                            url=url,
                        )
                    )
        except (csv.Error, ValueError, KeyError) as e:
            print(f"Error reading {csv_file}: {e}", file=sys.stderr)
            continue

    # Sort all records by date (newest first) for consistent processing
    for product_name in products:
        products[product_name].sort(key=lambda r: r.date, reverse=True)

    return products


def calculate_stats(product_name: str, records: List[PriceRecord]) -> PriceStats:
    """Calculate statistics for a product's price history.

    Args:
        product_name: Name of the product
        records: List of price records sorted by date (newest first)

    Returns:
        PriceStats object with calculated statistics
    """

    # Current values (most recent)
    current_price = records[0].price if records else None
    current_price_per_100ml = records[0].price_per_100ml if records else None
    current_url = records[0].url if records else ""
    current_date = records[0].date if records else None

    # Time windows
    now = datetime.now()
    cutoff_30d = now - timedelta(days=DAYS_FOR_AVERAGE)

    # Filter records
    records_30d = [r for r in records if r.date >= cutoff_30d and r.price is not None]
    records_all = [r for r in records if r.price is not None]

    # Calculate 30-day averages
    avg_price_30d = mean(r.price for r in records_30d) if records_30d else None

    records_30d_with_per_ml = [r for r in records_30d if r.price_per_100ml is not None]
    avg_price_per_100ml_30d = mean(r.price_per_100ml for r in records_30d_with_per_ml) if records_30d_with_per_ml else None

    # Find lowest prices ever
    lowest_ever = min(records_all, key=lambda r: r.price) if records_all else None

    records_all_with_per_ml = [r for r in records_all if r.price_per_100ml is not None]
    lowest_per_100ml_ever = (
        min(records_all_with_per_ml, key=lambda r: r.price_per_100ml)
        if records_all_with_per_ml else None
    )

    # Find when product was last cheaper (absolute price)
    last_cheaper_ever_record = None
    if current_price is not None:
        cheaper_records = [r for r in records if r.price is not None and r.price < current_price]
        if cheaper_records:
            last_cheaper_ever_record = max(cheaper_records, key=lambda r: r.date)

    # Find when product price per 100ml was last cheaper
    last_cheaper_per_100ml_ever_record = None
    if current_price_per_100ml is not None:
        cheaper_per_100ml_records = [
            r for r in records
            if r.price_per_100ml is not None and r.price_per_100ml < current_price_per_100ml
        ]
        if cheaper_per_100ml_records:
            last_cheaper_per_100ml_ever_record = max(cheaper_per_100ml_records, key=lambda r: r.date)

    return PriceStats(
        product_name=product_name,
        current_price=current_price,
        current_price_per_100ml=current_price_per_100ml,
        current_url=current_url,
        current_date=current_date,
        avg_price_30d=avg_price_30d,
        avg_price_per_100ml_30d=avg_price_per_100ml_30d,
        lowest_price_ever=lowest_ever.price if lowest_ever else None,
        lowest_price_per_100ml_ever=lowest_per_100ml_ever.price_per_100ml if lowest_per_100ml_ever else None,
        last_time_this_cheap_ever=last_cheaper_ever_record.date if last_cheaper_ever_record else None,
        last_time_this_cheap_per_100ml_ever=last_cheaper_per_100ml_ever_record.date if last_cheaper_per_100ml_ever_record else None,
    )


def format_price(price: Optional[float]) -> str:
    """Format price for display."""
    return f"€{price:.2f}" if price is not None else "N/A"


def extract_site_name(url: str) -> str:
    """Extract site name from URL.

    Args:
        url: URL to extract site name from

    Returns:
        Site name (e.g., "atida.com", "wells.pt")
    """
    if not url:
        return "-"

    try:
        parsed = urlparse(url)
        domain = parsed.netloc

        # Remove www. prefix
        if domain.startswith("www."):
            domain = domain[4:]

        return domain if domain else "-"
    except Exception:
        return "-"


def get_comparison_values(stats: PriceStats) -> Optional[tuple[float, float, float, Optional[datetime]]]:
    """Extract comparison values, preferring per-100ml pricing.

    Returns:
        Tuple of (current, avg_30d, lowest, last_cheaper_date) or None
    """
    if stats.current_price_per_100ml and stats.avg_price_per_100ml_30d and stats.lowest_price_per_100ml_ever:
        return (
            stats.current_price_per_100ml,
            stats.avg_price_per_100ml_30d,
            stats.lowest_price_per_100ml_ever,
            stats.last_time_this_cheap_per_100ml_ever,
        )
    if stats.current_price and stats.avg_price_30d and stats.lowest_price_ever:
        return (
            stats.current_price,
            stats.avg_price_30d,
            stats.lowest_price_ever,
            stats.last_time_this_cheap_ever,
        )
    return None


def calculate_deal_score(stats: PriceStats) -> Optional[float]:
    """Calculate deal score as percentage difference from 30-day average (negative = good deal)."""
    values = get_comparison_values(stats)
    if not values:
        return None

    current, avg, _lowest, _last_cheaper = values
    return ((current - avg) / avg) * 100


def get_deal_indicator(score: float) -> str:
    """Return emoji indicator for deal quality."""
    if score < DEAL_THRESHOLD_GREAT:
        return "🔥"
    elif score < DEAL_THRESHOLD_GOOD:
        return "✅"
    else:
        return "⚠️"


def format_days_since(last_cheaper_date: Optional[datetime]) -> str:
    """Format 'days since cheaper' display."""
    if not last_cheaper_date:
        return "never"
    days = (datetime.now().date() - last_cheaper_date.date()).days
    return str(days)


def filter_current_products(all_stats: List[PriceStats]) -> List[PriceStats]:
    """Return only products from the most recent date."""
    in_stock = [s for s in all_stats if s.current_price is not None]
    if not in_stock:
        return []

    most_recent_date = max(s.current_date for s in in_stock if s.current_date)
    return [s for s in in_stock if s.current_date == most_recent_date]


def print_summary_table(all_stats: List[PriceStats]) -> None:
    """Print a summary table of all products."""
    current_products = filter_current_products(all_stats)
    if not current_products:
        print("No products available")
        return

    # Calculate scores and sort by best deals
    deals = []
    for stats in current_products:
        score = calculate_deal_score(stats)
        if score is not None:
            deals.append((stats, score))
    deals.sort(key=lambda x: x[1])

    # Calculate product column width
    terminal_width = shutil.get_terminal_size().columns
    longest_name = max(len(stats.product_name) for stats, _ in deals) if deals else MIN_PRODUCT_COLUMN_WIDTH
    available_width = terminal_width - TABLE_FIXED_COLUMNS_WIDTH
    ideal_width = min(longest_name + 2, MAX_PRODUCT_COLUMN_WIDTH)
    product_width = max(MIN_PRODUCT_COLUMN_WIDTH, min(ideal_width, available_width))

    # Print header
    print("\n" + "=" * terminal_width)
    print("SUMMARY - Best Deals Right Now")
    print("=" * terminal_width)
    header = (
        f"{'Product':<{product_width}} "
        f"{'Current':>9} "
        f"{'€/100ml':>8} "
        f"{'Avg 30d':>9} "
        f"{'Lowest':>9} "
        f"{'Deal':^10} "
        f"{'Last':>5} "
        f"  {'Site':<17}"
    )
    print(header)
    print("-" * terminal_width)

    # Print rows
    for stats, score in deals:
        values = get_comparison_values(stats)
        if values:
            _current, avg, lowest, last_cheaper = values
            avg_display = format_price(avg)
            lowest_display = format_price(lowest)
            days_str = format_days_since(last_cheaper)
        else:
            avg_display = "N/A"
            lowest_display = "N/A"
            days_str = "-"

        indicator = get_deal_indicator(score)
        price_per_100ml_str = format_price(stats.current_price_per_100ml) if stats.current_price_per_100ml else "   -"
        site_name = extract_site_name(stats.current_url)
        product_display = stats.product_name[:product_width] if len(stats.product_name) > product_width else stats.product_name

        print(
            f"{product_display:<{product_width}} "
            f"{format_price(stats.current_price):>9} "
            f"{price_per_100ml_str:>8} "
            f"{avg_display:>9} "
            f"{lowest_display:>9} "
            f" {indicator} {f'{score:>5.1f}%'} "
            f"{days_str:>6} "
            f" {site_name:<15}"
        )


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Analyze historical price data")
    parser.add_argument(
        "--history-dir",
        type=Path,
        default=Path("history"),
        help="Directory containing historical CSV files (default: history)",
    )

    args = parser.parse_args()

    # Parse historical data
    products = parse_csv_files(args.history_dir)

    if not products:
        print("No product data found", file=sys.stderr)
        return 1

    # Calculate statistics for all products
    all_stats = []
    for product_name, records in products.items():
        stats = calculate_stats(product_name, records)
        all_stats.append(stats)

    # Sort by product name
    all_stats.sort(key=lambda s: s.product_name)

    # Show summary
    print_summary_table(all_stats)

    return 0


if __name__ == "__main__":
    sys.exit(main())
