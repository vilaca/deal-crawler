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
    out_of_stock_items: Dict[str, List[str]] = field(default_factory=dict)  # product -> URLs
    failed_urls: List[str] = field(default_factory=list)  # URLs that failed (fetch or extraction errors)

    def _pluralize(self, count: int, singular: str, plural: str) -> str:
        """Return singular or plural form based on count."""
        return singular if count == 1 else plural

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL with fallback for malformed URLs.

        Args:
            url: URL to extract domain from

        Returns:
            Domain without 'www.' prefix, or full URL if parsing fails
        """
        parsed = urlparse(url)
        domain = parsed.netloc.replace("www.", "")

        # If netloc is empty (malformed URL), return the full URL as fallback
        if not domain:
            return url

        return domain

    def _get_success_emoji(self, success_rate: float) -> str:
        """Get emoji based on success rate."""
        if success_rate >= 80:
            return "✅"
        if success_rate >= 50:
            return "⚠️"
        return "❌"

    def _format_success_line(self, markdown: bool = False) -> str:
        """Format the success rate summary line.

        Args:
            markdown: If True, format for markdown; otherwise format for terminal
        """
        products_text = self._pluralize(self.total_products, "product", "products")

        if self.total_urls_checked == 0:
            if markdown:
                return f"**{self.total_products} {products_text}** · No URLs checked"
            return f"{self.total_products} {products_text} · No URLs checked"

        success_rate = (self.prices_found / self.total_urls_checked) * 100
        emoji = self._get_success_emoji(success_rate)
        urls_text = self._pluralize(self.total_urls_checked, "URL", "URLs")

        if markdown:
            return (
                f"**{emoji} {self.prices_found}/{self.total_urls_checked} {urls_text}** "
                f"({success_rate:.0f}% success) · "
                f"**{self.total_products} {products_text}**"
            )

        return (
            f"{emoji} {self.prices_found}/{self.total_urls_checked} {urls_text} "
            f"({success_rate:.0f}% success) · {self.total_products} {products_text}"
        )

    def _format_issues_line(self, markdown: bool = False) -> Optional[str]:
        """Format the issues summary line.

        Args:
            markdown: If True, format for markdown; otherwise format for terminal
        """
        issues = []
        if self.out_of_stock > 0:
            issues.append(f"📦 {self.out_of_stock} out of stock")
        if self.fetch_errors > 0:
            error_text = self._pluralize(self.fetch_errors, "fetch error", "fetch errors")
            issues.append(f"🌐 {self.fetch_errors} {error_text}")
        if self.extraction_errors > 0:
            error_text = self._pluralize(self.extraction_errors, "extraction error", "extraction errors")
            issues.append(f"🔍 {self.extraction_errors} {error_text}")

        if not issues:
            return None

        joined = " · ".join(issues)
        return f"_{joined}_" if markdown else f"Issues: {joined}"

    def _print_out_of_stock_items(self, markdown: bool = False) -> None:
        """Print out of stock items grouped by product.

        Args:
            markdown: If True, format for markdown; otherwise format for terminal
        """
        if not self.out_of_stock_items:
            return

        if markdown:
            print("\n**Out of Stock:**")
            for product, urls in self.out_of_stock_items.items():
                domains = [self._extract_domain(url) for url in urls]
                print(f"- **{product}**: {', '.join(domains)}")
        else:
            print("\nOut of Stock:")
            for product, urls in self.out_of_stock_items.items():
                domains = [self._extract_domain(url) for url in urls]
                print(f"  • {product}: {', '.join(domains)}")

    def _print_failed_urls(self, markdown: bool = False) -> None:
        """Print failed URLs (showing first 3).

        Args:
            markdown: If True, format for markdown; otherwise format for terminal
        """
        if not self.failed_urls:
            return

        if markdown:
            print(f"\n**Failed URLs** ({len(self.failed_urls)}):")
            for url in self.failed_urls[:3]:
                print(f"- `{url}`")
            if len(self.failed_urls) > 3:
                print(f"- _{len(self.failed_urls) - 3} more..._")
        else:
            print(f"\nFailed URLs ({len(self.failed_urls)}):")
            for url in self.failed_urls[:3]:
                print(f"  • {url}")
            if len(self.failed_urls) > 3:
                print(f"  • {len(self.failed_urls) - 3} more...")

    def print_summary(self, markdown: bool = False) -> None:
        """Print a concise summary of the search results.

        Args:
            markdown: If True, format for markdown; otherwise format for terminal
        """
        if markdown:
            print("\n## 📊 Search Summary\n")
        else:
            print("\n📊 Search Summary")
            print("=" * 70)

        print(self._format_success_line(markdown=markdown))

        issues_line = self._format_issues_line(markdown=markdown)
        if issues_line:
            print(f"\n{issues_line}")

        self._print_out_of_stock_items(markdown=markdown)
        self._print_failed_urls(markdown=markdown)
        print()  # Empty line at end


def find_cheapest_prices(products: Dict[str, List[str]], http_client: HttpClient) -> SearchResults:
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
                results.out_of_stock_items.setdefault(product_name, []).append(url)
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
                # Remove from cache so we can retry later
                http_client.remove_from_cache(url)

        if prices:
            cheapest = min(prices, key=lambda x: x[0])
            results.prices[product_name] = cheapest
        else:
            results.prices[product_name] = None

    return results
