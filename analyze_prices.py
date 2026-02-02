#!/usr/bin/env python3
"""Analyze historical price data to help determine when to buy products.

This script reads CSV files from the history folder and provides insights like:
- Current price
- Average price over different time periods
- Lowest/highest prices and when they occurred
- Price trends
- Out of stock frequency
"""

import csv
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class PriceRecord:
    """Single price observation for a product."""

    date: datetime
    price: Optional[float]
    price_per_100ml: Optional[float]
    url: str


@dataclass
class PriceStats:
    """Statistical analysis of product prices."""

    product_name: str
    current_price: Optional[float]
    current_price_per_100ml: Optional[float]
    current_url: str
    avg_price_30d: Optional[float]
    avg_price_90d: Optional[float]
    avg_price_all: Optional[float]
    avg_price_per_100ml_30d: Optional[float]
    avg_price_per_100ml_all: Optional[float]
    lowest_price_30d: Optional[float]
    lowest_price_30d_date: Optional[datetime]
    lowest_price_90d: Optional[float]
    lowest_price_90d_date: Optional[datetime]
    lowest_price_ever: Optional[float]
    lowest_price_ever_date: Optional[datetime]
    lowest_price_per_100ml_ever: Optional[float]
    lowest_price_per_100ml_ever_date: Optional[datetime]
    highest_price_90d: Optional[float]
    highest_price_90d_date: Optional[datetime]
    last_time_this_cheap_7d: Optional[datetime]
    last_time_this_cheap_7d_price: Optional[float]
    last_time_this_cheap_30d: Optional[datetime]
    last_time_this_cheap_30d_price: Optional[float]
    last_time_this_cheap_90d: Optional[datetime]
    last_time_this_cheap_90d_price: Optional[float]
    last_time_this_cheap_ever: Optional[datetime]
    last_time_this_cheap_ever_price: Optional[float]
    out_of_stock_count: int
    total_observations: int
    days_tracked: int


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
        except Exception as e:
            print(f"Error reading {csv_file}: {e}", file=sys.stderr)
            continue

    return products


def calculate_stats(product_name: str, records: List[PriceRecord]) -> PriceStats:
    """Calculate statistics for a product's price history.

    Args:
        product_name: Name of the product
        records: List of price records sorted by date

    Returns:
        PriceStats object with calculated statistics
    """
    # Sort by date (newest first)
    records = sorted(records, key=lambda r: r.date, reverse=True)

    # Current values (most recent)
    current_price = records[0].price if records else None
    current_price_per_100ml = records[0].price_per_100ml if records else None
    current_url = records[0].url if records else ""

    # Time windows
    now = datetime.now()
    cutoff_30d = now - timedelta(days=30)
    cutoff_90d = now - timedelta(days=90)

    # Filter records by time window
    records_30d = [r for r in records if r.date >= cutoff_30d and r.price is not None]
    records_90d = [r for r in records if r.date >= cutoff_90d and r.price is not None]
    records_all = [r for r in records if r.price is not None]

    # Calculate averages
    avg_price_30d = sum(r.price for r in records_30d) / len(records_30d) if records_30d else None
    avg_price_90d = sum(r.price for r in records_90d) / len(records_90d) if records_90d else None
    avg_price_all = sum(r.price for r in records_all) / len(records_all) if records_all else None

    # Calculate price per 100ml averages (only for records that have this data)
    records_30d_with_per_ml = [r for r in records_30d if r.price_per_100ml is not None]
    records_all_with_per_ml = [r for r in records_all if r.price_per_100ml is not None]

    avg_price_per_100ml_30d = (
        sum(r.price_per_100ml for r in records_30d_with_per_ml) / len(records_30d_with_per_ml)
        if records_30d_with_per_ml else None
    )
    avg_price_per_100ml_all = (
        sum(r.price_per_100ml for r in records_all_with_per_ml) / len(records_all_with_per_ml)
        if records_all_with_per_ml else None
    )

    # Find lowest prices
    lowest_30d = min(records_30d, key=lambda r: r.price) if records_30d else None
    lowest_90d = min(records_90d, key=lambda r: r.price) if records_90d else None
    lowest_ever = min(records_all, key=lambda r: r.price) if records_all else None

    # Find lowest price per 100ml ever
    lowest_per_100ml_ever = (
        min(records_all_with_per_ml, key=lambda r: r.price_per_100ml)
        if records_all_with_per_ml else None
    )

    # Find highest price in 90 days
    highest_90d = max(records_90d, key=lambda r: r.price) if records_90d else None

    # Find when product was last cheaper than current price
    cutoff_7d = now - timedelta(days=7)
    last_cheaper_7d_record = None
    last_cheaper_30d_record = None
    last_cheaper_90d_record = None
    last_cheaper_ever_record = None

    if current_price is not None:
        # Search for records cheaper than current price (excluding today)
        cheaper_records = [r for r in records if r.price is not None and r.price < current_price]

        if cheaper_records:
            # Find most recent cheaper price in each time window
            cheaper_7d = [r for r in cheaper_records if r.date >= cutoff_7d]
            cheaper_30d = [r for r in cheaper_records if r.date >= cutoff_30d]
            cheaper_90d = [r for r in cheaper_records if r.date >= cutoff_90d]

            last_cheaper_7d_record = max(cheaper_7d, key=lambda r: r.date) if cheaper_7d else None
            last_cheaper_30d_record = max(cheaper_30d, key=lambda r: r.date) if cheaper_30d else None
            last_cheaper_90d_record = max(cheaper_90d, key=lambda r: r.date) if cheaper_90d else None
            last_cheaper_ever_record = max(cheaper_records, key=lambda r: r.date) if cheaper_records else None

    # Count out of stock occurrences
    out_of_stock_count = sum(1 for r in records if r.price is None)

    # Days tracked
    if len(records) >= 2:
        days_tracked = (records[0].date - records[-1].date).days + 1
    else:
        days_tracked = 1 if records else 0

    return PriceStats(
        product_name=product_name,
        current_price=current_price,
        current_price_per_100ml=current_price_per_100ml,
        current_url=current_url,
        avg_price_30d=avg_price_30d,
        avg_price_90d=avg_price_90d,
        avg_price_all=avg_price_all,
        avg_price_per_100ml_30d=avg_price_per_100ml_30d,
        avg_price_per_100ml_all=avg_price_per_100ml_all,
        lowest_price_30d=lowest_30d.price if lowest_30d else None,
        lowest_price_30d_date=lowest_30d.date if lowest_30d else None,
        lowest_price_90d=lowest_90d.price if lowest_90d else None,
        lowest_price_90d_date=lowest_90d.date if lowest_90d else None,
        lowest_price_ever=lowest_ever.price if lowest_ever else None,
        lowest_price_ever_date=lowest_ever.date if lowest_ever else None,
        lowest_price_per_100ml_ever=lowest_per_100ml_ever.price_per_100ml if lowest_per_100ml_ever else None,
        lowest_price_per_100ml_ever_date=lowest_per_100ml_ever.date if lowest_per_100ml_ever else None,
        highest_price_90d=highest_90d.price if highest_90d else None,
        highest_price_90d_date=highest_90d.date if highest_90d else None,
        last_time_this_cheap_7d=last_cheaper_7d_record.date if last_cheaper_7d_record else None,
        last_time_this_cheap_7d_price=last_cheaper_7d_record.price if last_cheaper_7d_record else None,
        last_time_this_cheap_30d=last_cheaper_30d_record.date if last_cheaper_30d_record else None,
        last_time_this_cheap_30d_price=last_cheaper_30d_record.price if last_cheaper_30d_record else None,
        last_time_this_cheap_90d=last_cheaper_90d_record.date if last_cheaper_90d_record else None,
        last_time_this_cheap_90d_price=last_cheaper_90d_record.price if last_cheaper_90d_record else None,
        last_time_this_cheap_ever=last_cheaper_ever_record.date if last_cheaper_ever_record else None,
        last_time_this_cheap_ever_price=last_cheaper_ever_record.price if last_cheaper_ever_record else None,
        out_of_stock_count=out_of_stock_count,
        total_observations=len(records),
        days_tracked=days_tracked,
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
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc

        # Remove www. prefix
        if domain.startswith("www."):
            domain = domain[4:]

        return domain if domain else "-"
    except Exception:
        return "-"


def format_date(date: Optional[datetime], show_today: bool = False) -> str:
    """Format date for display.

    Args:
        date: Date to format
        show_today: If True, append "(today)" when date is today

    Returns:
        Formatted date string
    """
    if not date:
        return "N/A"

    formatted = date.strftime("%Y-%m-%d")

    if show_today:
        today = datetime.now().date()
        if date.date() == today:
            formatted += " (today)"

    return formatted


def print_product_stats(stats: PriceStats) -> None:
    """Print statistics for a single product in a readable format."""
    print(f"\n{'=' * 80}")
    print(f"Product: {stats.product_name}")
    print(f"{'=' * 80}")

    # Current status
    if stats.current_price is None:
        print("⚠️  CURRENTLY OUT OF STOCK")
    else:
        print(f"Current Price: {format_price(stats.current_price)}")
        if stats.current_price_per_100ml:
            print(f"Price per 100ml: {format_price(stats.current_price_per_100ml)}")

        # Price comparison indicators
        if stats.lowest_price_ever and stats.current_price:
            diff_from_lowest = ((stats.current_price - stats.lowest_price_ever) / stats.lowest_price_ever) * 100
            if diff_from_lowest <= 5:
                print("🔥 NEAR LOWEST PRICE EVER!")
            elif diff_from_lowest <= 10:
                print("✅ Good price (within 10% of lowest)")

        if stats.avg_price_30d and stats.current_price:
            if stats.current_price < stats.avg_price_30d * 0.95:
                print("📉 Below recent average (good deal!)")
            elif stats.current_price > stats.avg_price_30d * 1.05:
                print("📈 Above recent average")

    print(f"URL: {stats.current_url}")
    print()

    # Price statistics
    print("Price Statistics:")
    print(f"  Average (30 days):  {format_price(stats.avg_price_30d)}")
    print(f"  Average (90 days):  {format_price(stats.avg_price_90d)}")
    print(f"  Average (all time): {format_price(stats.avg_price_all)}")
    if stats.avg_price_per_100ml_30d or stats.avg_price_per_100ml_all:
        print()
        print("Price per 100ml:")
        print(f"  Average (30 days):  {format_price(stats.avg_price_per_100ml_30d)}")
        print(f"  Average (all time): {format_price(stats.avg_price_per_100ml_all)}")
    print()

    # Lowest prices
    print("Lowest Prices:")
    if stats.lowest_price_30d:
        print(f"  Last 30 days: {format_price(stats.lowest_price_30d)} on {format_date(stats.lowest_price_30d_date)}")
    if stats.lowest_price_90d:
        print(f"  Last 90 days: {format_price(stats.lowest_price_90d)} on {format_date(stats.lowest_price_90d_date)}")
    if stats.lowest_price_ever:
        print(f"  All time:     {format_price(stats.lowest_price_ever)} on {format_date(stats.lowest_price_ever_date)}")
    if stats.lowest_price_per_100ml_ever:
        print()
        print("Lowest Price per 100ml:")
        print(f"  All time:     {format_price(stats.lowest_price_per_100ml_ever)} on {format_date(stats.lowest_price_per_100ml_ever_date)}")
    print()

    # Highest price in 90 days
    if stats.highest_price_90d:
        print(f"Highest Price (90 days): {format_price(stats.highest_price_90d)} on {format_date(stats.highest_price_90d_date, show_today=True)}")
        if stats.lowest_price_90d:
            price_range = stats.highest_price_90d - stats.lowest_price_90d
            print(f"  Price range: €{price_range:.2f}")
        print()

    # When was it last cheaper than today?
    if stats.current_price is not None:
        print("Last Time Cheaper Than Today:")
        if stats.last_time_this_cheap_7d:
            print(f"  Last 7 days:  {format_date(stats.last_time_this_cheap_7d)} ({format_price(stats.last_time_this_cheap_7d_price)})")
        elif stats.last_time_this_cheap_30d or stats.last_time_this_cheap_90d or stats.last_time_this_cheap_ever:
            print(f"  Last 7 days:  Never")

        if stats.last_time_this_cheap_30d:
            print(f"  Last 30 days: {format_date(stats.last_time_this_cheap_30d)} ({format_price(stats.last_time_this_cheap_30d_price)})")
        elif stats.last_time_this_cheap_90d or stats.last_time_this_cheap_ever:
            print(f"  Last 30 days: Never")

        if stats.last_time_this_cheap_90d:
            print(f"  Last 90 days: {format_date(stats.last_time_this_cheap_90d)} ({format_price(stats.last_time_this_cheap_90d_price)})")
        elif stats.last_time_this_cheap_ever:
            print(f"  Last 90 days: Never")

        if stats.last_time_this_cheap_ever:
            print(f"  Ever:         {format_date(stats.last_time_this_cheap_ever)} ({format_price(stats.last_time_this_cheap_ever_price)})")
        else:
            print(f"  Ever:         Never (lowest price ever!)")
        print()

    # Tracking info
    print(f"Tracking: {stats.days_tracked} days with {stats.total_observations} observations")
    if stats.out_of_stock_count > 0:
        out_of_stock_pct = (stats.out_of_stock_count / stats.total_observations) * 100
        print(f"Out of stock: {stats.out_of_stock_count} times ({out_of_stock_pct:.1f}%)")


def extract_base_product_name(product_name: str) -> str:
    """Extract base product name by removing size/quantity suffixes.

    Examples:
        "Cerave Hydrating Cleanser (1000ml)" -> "Cerave Hydrating Cleanser"
        "Cerave Hydrating Cleanser (2x1000ml)" -> "Cerave Hydrating Cleanser"
        "Paradontax pasta gums (2x75ml)" -> "Paradontax pasta gums"
    """
    import re
    # Remove patterns like (1000ml), (2x295ml), (200ml), etc.
    base_name = re.sub(r'\s*\(\d+x?\d*ml\)$', '', product_name)
    return base_name.strip()


def select_best_value_per_product(all_stats: List[PriceStats]) -> List[PriceStats]:
    """Group products by base name and select the best value (lowest price per 100ml) for each.

    For products without price per 100ml data, keep them as-is.
    """
    from collections import defaultdict

    # Group by base product name
    product_groups: Dict[str, List[PriceStats]] = defaultdict(list)

    for stats in all_stats:
        base_name = extract_base_product_name(stats.product_name)
        product_groups[base_name].append(stats)

    # For each group, select the best value
    best_products = []
    for base_name, products in product_groups.items():
        # If only one product in group, keep it
        if len(products) == 1:
            best_products.append(products[0])
            continue

        # If multiple products, prefer the one with lowest price per 100ml
        products_with_per_ml = [p for p in products if p.current_price_per_100ml is not None]

        if products_with_per_ml:
            # Select product with lowest price per 100ml
            best = min(products_with_per_ml, key=lambda p: p.current_price_per_100ml)
            best_products.append(best)
        else:
            # No price per 100ml data, keep the first one
            best_products.append(products[0])

    return best_products


def print_summary_table(all_stats: List[PriceStats]) -> None:
    """Print a summary table of all products."""
    import shutil
    terminal_width = shutil.get_terminal_size().columns

    print("\n" + "=" * terminal_width)
    print("SUMMARY - Best Deals Right Now")
    print("=" * terminal_width)

    # Filter products that are in stock
    in_stock = [s for s in all_stats if s.current_price is not None]

    # Select best value for each product (by price per 100ml)
    best_value_products = select_best_value_per_product(in_stock)

    # Calculate deal score (how far below average and lowest ever)
    deals = []
    for stats in best_value_products:
        if stats.avg_price_30d and stats.lowest_price_ever:
            # Score: negative % difference from avg (lower is better) + bonus if near lowest
            avg_diff = ((stats.current_price - stats.avg_price_30d) / stats.avg_price_30d) * 100
            lowest_diff = ((stats.current_price - stats.lowest_price_ever) / stats.lowest_price_ever) * 100
            score = avg_diff + (lowest_diff * 0.5)  # Weight lowest ever less
            deals.append((stats, score))

    # Sort by score (best deals first)
    deals.sort(key=lambda x: x[1])

    # Calculate dynamic product column width
    # Fixed columns: Current(9) + €/100ml(8) + Avg 30d(9) + Lowest(9) + Deal(8) + Days(6) + Site(15) + spaces(7) = 71
    fixed_width = 71
    min_product_width = 30
    max_product_width = 80

    # Find longest product name in current results
    if deals:
        longest_name = max(len(stats.product_name) for stats, _ in deals[:15])
        # Product width: ensure total line doesn't exceed terminal width
        available_width = terminal_width - fixed_width
        # Use longest name if it fits, otherwise use available width, respecting min/max bounds
        ideal_width = min(longest_name + 2, max_product_width)
        product_width = max(min_product_width, min(ideal_width, available_width))
    else:
        product_width = min_product_width

    # Print header
    header = (
        f"{'Product':<{product_width}} "
        f"{'Current':>9} "
        f"{'€/100ml':>8} "
        f"{'Avg 30d':>9} "
        f"{'Lowest':>9} "
        f"{'Deal':>8} "
        f"{'Days':>6} "
        f" {'Site':<15}"
    )
    print(header)
    print("-" * terminal_width)

    for stats, score in deals[:15]:  # Top 15 deals
        indicator = "🔥" if score < -10 else "✅" if score < 0 else "⚠️"
        price_per_100ml_str = format_price(stats.current_price_per_100ml) if stats.current_price_per_100ml else "   -"

        # Calculate days since last cheaper
        if stats.last_time_this_cheap_ever:
            days_since = (datetime.now().date() - stats.last_time_this_cheap_ever.date()).days
            if days_since == 0:
                days_str = "today"
            else:
                days_str = str(days_since)
        else:
            # Never been cheaper (lowest price ever)
            # If deal is 0.0% (at lowest price), show "-" instead of "never"
            if abs(score) < 0.05:  # Within 0.05% is effectively 0.0%
                days_str = "-"
            else:
                days_str = "never"

        # Extract site name from URL
        site_name = extract_site_name(stats.current_url)

        # Truncate product name if needed
        product_display = stats.product_name[:product_width] if len(stats.product_name) > product_width else stats.product_name

        # Format deal with emoji - emoji takes 2 visual spaces but counts as 1 char
        # Format percentage without emoji first, then add emoji with spacing
        percent_str = f"{score:>5.1f}%"

        print(
            f"{product_display:<{product_width}} "
            f"{format_price(stats.current_price):>9} "
            f"{price_per_100ml_str:>8} "
            f"{format_price(stats.avg_price_30d):>9} "
            f"{format_price(stats.lowest_price_ever):>9} "
            f" {indicator} {percent_str} "
            f"{days_str:>6} "
            f" {site_name:<15}"
        )


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Analyze historical price data")
    parser.add_argument(
        "--history-dir",
        type=Path,
        default=Path("history"),
        help="Directory containing historical CSV files (default: history)",
    )
    parser.add_argument(
        "--product",
        type=str,
        help="Show detailed stats for specific product (partial name match)",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Show summary table of best deals",
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

    # Filter by product name if specified
    if args.product:
        pattern = args.product.lower()
        all_stats = [s for s in all_stats if pattern in s.product_name.lower()]

        if not all_stats:
            print(f"No products matching '{args.product}' found", file=sys.stderr)
            return 1

    # Show results
    if args.summary:
        print_summary_table(all_stats)
    else:
        for stats in all_stats:
            print_product_stats(stats)

    return 0


if __name__ == "__main__":
    sys.exit(main())
