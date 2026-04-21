"""Generate markdown report from collected price data.

Reads the latest all-prices CSV file and generates a markdown report
showing cheapest prices per product, with links to all available stores.

Usage:
    python generate_report.py [--input-dir DIR] [--output FILE]
"""

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional
from urllib.parse import urlparse


class PriceRow(NamedTuple):
    """A single price entry from the CSV."""

    product: str
    site: str
    price: float
    price_per_100ml: Optional[float]
    url: str


def _find_latest_csv(input_dir: Path) -> Path:
    """Find the most recent CSV file by filename.

    Args:
        input_dir: Directory containing CSV files.

    Returns:
        Path to the latest CSV file.
    """
    csv_files = sorted(input_dir.glob("*.csv"))
    if not csv_files:
        print(f"No CSV files found in {input_dir}", file=sys.stderr)
        sys.exit(1)
    return csv_files[-1]


def _read_csv(csv_path: Path) -> List[PriceRow]:
    """Read all price rows from a CSV file.

    Args:
        csv_path: Path to the CSV file.

    Returns:
        List of PriceRow entries.
    """
    rows: List[PriceRow] = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            price_per_100ml = float(row["Price per 100ml"]) if row["Price per 100ml"] else None
            rows.append(
                PriceRow(
                    product=row["Product"],
                    site=row["Site"],
                    price=float(row["Price"]),
                    price_per_100ml=price_per_100ml,
                    url=row["URL"],
                )
            )
    return rows


def _generate_markdown(rows: List[PriceRow], csv_path: Path) -> str:
    """Generate markdown report from price rows.

    Picks the cheapest price per product and formats as a markdown table
    matching the existing latest_results.md format.

    Args:
        rows: All price rows from CSV.
        csv_path: Path to source CSV (for the header).

    Returns:
        Markdown string.
    """
    by_product: Dict[str, List[PriceRow]] = defaultdict(list)
    for row in rows:
        by_product[row.product].append(row)

    lines = []
    lines.append("")
    lines.append("# Best Prices")
    lines.append("")
    lines.append("| Product | Price | Link |")
    lines.append("|---------|-------|------|")

    for product_name in sorted(by_product):
        cheapest = min(by_product[product_name], key=lambda r: r.price)
        domain = urlparse(cheapest.url).netloc.replace("www.", "")

        if cheapest.price_per_100ml:
            price_display = f"€{cheapest.price:.2f}<br>_(€{cheapest.price_per_100ml:.2f}/100ml)_"
        else:
            price_display = f"€{cheapest.price:.2f}"

        lines.append(f"| **{product_name}** | {price_display} | [{domain}]({cheapest.url}) |")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(f"_Generated from {csv_path.name} — {len(rows)} prices across {len(by_product)} products_")
    lines.append("")

    return "\n".join(lines)


def main() -> None:
    """Parse arguments and generate report."""
    parser = argparse.ArgumentParser(description="Generate markdown report from price CSV")
    parser.add_argument("--input-dir", default="history/all", help="Directory with CSV files")
    parser.add_argument("--output", default="latest_results.md", help="Output markdown file")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    csv_path = _find_latest_csv(input_dir)
    rows = _read_csv(csv_path)

    if not rows:
        print(f"No price data in {csv_path}", file=sys.stderr)
        sys.exit(1)

    markdown = _generate_markdown(rows, csv_path)

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(markdown)

    print(f"Report written to {args.output} ({len(rows)} prices)", file=sys.stderr)


if __name__ == "__main__":
    main()
