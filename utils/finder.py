"""Main price comparison logic."""

import re
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from urllib.parse import urlparse

from .http_client import HttpClient
from .stock_checker import is_out_of_stock
from .extractors import extract_price
from .product_info import calculate_price_per_100ml, parse_product_name
from .string_utils import pluralize


@dataclass
class PriceResult:
    """Single price result with value calculation."""

    price: float
    url: str
    price_per_100ml: Optional[float] = None  # Price per 100ml (for value comparison)


@dataclass
class SearchResults:
    """Results from price search with summary statistics."""

    # Product name -> PriceResult or None
    prices: Dict[str, Optional[PriceResult]] = field(default_factory=dict)

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
        products_text = pluralize(self.total_products, "product", "products")

        if self.total_urls_checked == 0:
            if markdown:
                return f"**{self.total_products} {products_text}** · No URLs checked"
            return f"{self.total_products} {products_text} · No URLs checked"

        success_rate = (self.prices_found / self.total_urls_checked) * 100
        emoji = self._get_success_emoji(success_rate)
        urls_text = pluralize(self.total_urls_checked, "URL", "URLs")

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
            error_text = pluralize(self.fetch_errors, "fetch error", "fetch errors")
            issues.append(f"🌐 {self.fetch_errors} {error_text}")
        if self.extraction_errors > 0:
            error_text = pluralize(self.extraction_errors, "extraction error", "extraction errors")
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


def extract_base_product_name(product_name: str) -> str:
    """Extract base product name without size information.

    Args:
        product_name: Full product name (e.g., "Cerave Foaming Cleanser (236ml)")

    Returns:
        Base product name (e.g., "Cerave Foaming Cleanser")
    """
    # Remove size patterns: (236ml), (2x236ml), etc.
    base_name = re.sub(r"\s*\(\d+(?:x\d+)?(?:\.\d+)?ml\)\s*$", "", product_name, flags=re.IGNORECASE)
    return base_name.strip()


# Keep private alias for backward compatibility within this module
_extract_base_product_name = extract_base_product_name


def _group_products_by_base_name(
    prices: Dict[str, Optional[PriceResult]],
) -> Dict[str, List[tuple[str, Optional[PriceResult]]]]:
    """Group products by their base name (without size info).

    Args:
        prices: Dictionary of product names to PriceResult objects

    Returns:
        Dictionary mapping base names to lists of (product_name, result) tuples
    """
    product_families: Dict[str, List[tuple[str, Optional[PriceResult]]]] = {}

    for product_name, price_result in prices.items():
        base_name = _extract_base_product_name(product_name)
        product_families.setdefault(base_name, []).append((product_name, price_result))

    return product_families


def _select_best_from_family(
    products_list: List[tuple[str, Optional[PriceResult]]],
) -> Dict[str, Optional[PriceResult]]:
    """Select the best value product from a family.

    Args:
        products_list: List of (product_name, result) tuples in the same family

    Returns:
        Dictionary with the best value product(s)
    """
    # Separate products with and without price_per_100ml
    with_value = [(name, result) for name, result in products_list if result and result.price_per_100ml]
    without_value = [(name, result) for name, result in products_list if not result or not result.price_per_100ml]

    if with_value:
        # Return the one with lowest price per 100ml
        best_product = min(with_value, key=lambda x: x[1].price_per_100ml or float("inf"))
        return {best_product[0]: best_product[1]}

    # No comparable values - keep all products without value info
    return dict(without_value)


def _copy_search_statistics(source: SearchResults, target: SearchResults) -> None:
    """Copy statistics from source to target SearchResults.

    Args:
        source: Source SearchResults with statistics
        target: Target SearchResults to copy statistics to
    """
    target.total_products = source.total_products
    target.total_urls_checked = source.total_urls_checked
    target.prices_found = source.prices_found
    target.out_of_stock = source.out_of_stock
    target.fetch_errors = source.fetch_errors
    target.extraction_errors = source.extraction_errors
    target.out_of_stock_items = source.out_of_stock_items
    target.failed_urls = source.failed_urls


def filter_best_value_sizes(results: SearchResults) -> SearchResults:
    """Filter results to show only the best value (lowest price per 100ml) for each product family.

    Products are grouped by their base name (without size info). For each group,
    only the size with the lowest price per 100ml is kept.

    Args:
        results: SearchResults with all product sizes

    Returns:
        New SearchResults with only best value sizes
    """
    # Group products by base name
    product_families = _group_products_by_base_name(results.prices)

    # For each family, select the best value
    filtered_prices: Dict[str, Optional[PriceResult]] = {}
    for products_list in product_families.values():
        best_products = _select_best_from_family(products_list)
        filtered_prices.update(best_products)

    # Create new SearchResults with filtered prices
    filtered_results = SearchResults()
    filtered_results.prices = filtered_prices
    _copy_search_statistics(results, filtered_results)

    return filtered_results


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

        # Parse product info once for all URLs of this product
        product_info = parse_product_name(product_name)

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
                # Calculate price per 100ml if volume information is available
                price_per_100ml = None
                if product_info.total_volume_ml:
                    price_per_100ml = calculate_price_per_100ml(price, product_info.total_volume_ml)
                    print(
                        f"    Found price: €{price:.2f} ({price_per_100ml:.2f}/100ml)",
                        file=sys.stderr,
                    )
                else:
                    print(f"    Found price: €{price:.2f}", file=sys.stderr)

                price_result = PriceResult(price=price, url=url, price_per_100ml=price_per_100ml)
                prices.append(price_result)
                results.prices_found += 1
            else:
                print("    Could not find price", file=sys.stderr)
                results.extraction_errors += 1
                results.failed_urls.append(url)
                # Remove from cache so we can retry later
                http_client.remove_from_cache(url)

        if prices:
            # Find cheapest by absolute price
            cheapest = min(prices, key=lambda x: x.price)
            results.prices[product_name] = cheapest
        else:
            results.prices[product_name] = None

    return results


def find_all_prices(products: Dict[str, List[str]], http_client: HttpClient) -> Dict[str, List[PriceResult]]:
    """Find ALL available prices for each product across all stores.

    Similar to find_cheapest_prices() but returns all valid prices instead of just
    the cheapest one. Used for optimization across stores.

    Args:
        products: Dictionary mapping product names to lists of URLs
        http_client: HttpClient instance for fetching pages

    Returns:
        Dictionary mapping product names to lists of PriceResult objects
        (one per store with product in stock and valid price)
    """
    all_prices: Dict[str, List[PriceResult]] = {}

    for product_name, urls in products.items():
        print(f"\nCollecting prices for {product_name}...", file=sys.stderr)
        prices = []

        # Parse product info once for all URLs of this product
        product_info = parse_product_name(product_name)

        for url in urls:
            print(f"  Fetching: {url}", file=sys.stderr)
            soup = http_client.fetch_page(url)

            if not soup:
                print("    Could not fetch page", file=sys.stderr)
                continue

            # Check stock status first
            if is_out_of_stock(soup):
                print("    Out of stock - skipping", file=sys.stderr)
                continue

            price = extract_price(soup, url)

            if price:
                # Calculate price per 100ml if volume information is available
                price_per_100ml = None
                if product_info.total_volume_ml:
                    price_per_100ml = calculate_price_per_100ml(price, product_info.total_volume_ml)
                    print(
                        f"    Found price: €{price:.2f} ({price_per_100ml:.2f}/100ml)",
                        file=sys.stderr,
                    )
                else:
                    print(f"    Found price: €{price:.2f}", file=sys.stderr)

                price_result = PriceResult(price=price, url=url, price_per_100ml=price_per_100ml)
                prices.append(price_result)
            else:
                print("    Could not find price", file=sys.stderr)
                # Remove from cache so we can retry later
                http_client.remove_from_cache(url)

        all_prices[product_name] = prices

    return all_prices
