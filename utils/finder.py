"""Main price comparison logic."""

import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

from .http_client import HttpClient
from .stock_checker import is_out_of_stock
from .extractors import extract_price


@dataclass
class SearchResults:
    """Results from price search with summary statistics."""

    # Product name -> (price, url) or None
    prices: Dict[str, Optional[Tuple[float, str]]] = field(default_factory=dict)

    # Summary statistics
    total_products: int = 0
    total_urls_checked: int = 0
    prices_found: int = 0
    out_of_stock: int = 0
    fetch_errors: int = 0
    extraction_errors: int = 0

    # Detailed tracking
    out_of_stock_items: Dict[str, List[str]] = field(
        default_factory=dict
    )  # product -> URLs
    failed_urls: List[str] = field(default_factory=list)

    def print_summary(self) -> None:
        """Print a concise markdown summary of the search results."""
        print("\n## 📊 Search Summary\n", file=sys.stderr)

        # Success rate with emoji
        if self.total_urls_checked > 0:
            success_rate = (self.prices_found / self.total_urls_checked) * 100
            emoji = "✅" if success_rate >= 80 else "⚠️" if success_rate >= 50 else "❌"
            print(
                f"**{emoji} {self.prices_found}/{self.total_urls_checked} URLs** "
                f"({success_rate:.0f}% success) · "
                f"**{self.total_products} products**",
                file=sys.stderr,
            )
        else:
            print(
                f"**{self.total_products} products** · No URLs checked", file=sys.stderr
            )

        # Issues section (only if there are any)
        issues = []
        if self.out_of_stock > 0:
            issues.append(f"📦 {self.out_of_stock} out of stock")
        if self.fetch_errors > 0:
            issues.append(f"🌐 {self.fetch_errors} fetch errors")
        if self.extraction_errors > 0:
            issues.append(f"🔍 {self.extraction_errors} extraction errors")

        if issues:
            print(f"\n_{' · '.join(issues)}_", file=sys.stderr)

        # Show out of stock items grouped by product
        if self.out_of_stock_items:
            print("\n**Out of Stock:**", file=sys.stderr)
            for product, urls in self.out_of_stock_items.items():
                # Get domains from URLs
                domains = [urlparse(url).netloc.replace("www.", "") for url in urls]
                domains_str = ", ".join(domains)
                print(f"- **{product}**: {domains_str}", file=sys.stderr)

        # Show failed URLs if any (compact list)
        if self.failed_urls:
            print(f"\n**Failed URLs** ({len(self.failed_urls)}):", file=sys.stderr)
            for url in self.failed_urls[:3]:  # Show first 3 only
                print(f"- `{url}`", file=sys.stderr)
            if len(self.failed_urls) > 3:
                print(f"- _{len(self.failed_urls) - 3} more..._", file=sys.stderr)

        print("", file=sys.stderr)  # Empty line at end


def find_cheapest_prices(
    products: Dict[str, List[str]], http_client: HttpClient
) -> SearchResults:
    """Find the cheapest price for each product, excluding out-of-stock items.

    Args:
        products: Dictionary mapping product names to lists of URLs
        http_client: HttpClient instance for fetching pages

    Returns:
        SearchResults object with prices and summary statistics
    """
    results = SearchResults()
    results.total_products = len(products)

    for product_name, urls in products.items():
        print(f"\nChecking prices for {product_name}...", file=sys.stderr)
        prices = []

        for url in urls:
            results.total_urls_checked += 1
            print(f"  Fetching: {url}", file=sys.stderr)
            soup = http_client.fetch_page(url)

            if not soup:
                print("    Could not fetch page", file=sys.stderr)
                results.fetch_errors += 1
                results.failed_urls.append(url)
                continue

            # Check stock status first
            if is_out_of_stock(soup):
                print("    Out of stock - skipping", file=sys.stderr)
                results.out_of_stock += 1
                # Track which product is out of stock at which URL
                if product_name not in results.out_of_stock_items:
                    results.out_of_stock_items[product_name] = []
                results.out_of_stock_items[product_name].append(url)
                continue

            price = extract_price(soup, url)

            if price:
                print(f"    Found price: €{price:.2f}", file=sys.stderr)
                prices.append((price, url))
                results.prices_found += 1
            else:
                print("    Could not find price", file=sys.stderr)
                results.extraction_errors += 1
                results.failed_urls.append(url)

        if prices:
            cheapest = min(prices, key=lambda x: x[0])
            results.prices[product_name] = cheapest
        else:
            results.prices[product_name] = None

    return results
