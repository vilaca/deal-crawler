"""Main price comparison logic."""

import sys
from typing import Dict, List, Optional, Tuple

from src.http_client import HttpClient
from src.stock_checker import is_out_of_stock
from src.extractors import extract_price


def find_cheapest_prices(
    products: Dict[str, List[str]], http_client: HttpClient
) -> Dict[str, Optional[Tuple[float, str]]]:
    """Find the cheapest price for each product, excluding out-of-stock items.

    Args:
        products: Dictionary mapping product names to lists of URLs
        http_client: HttpClient instance for fetching pages

    Returns:
        Dictionary mapping product names to (price, url) tuples or None
    """
    results: Dict[str, Optional[Tuple[float, str]]] = {}

    for product_name, urls in products.items():
        print(f"\nChecking prices for {product_name}...", file=sys.stderr)
        prices = []

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
                print(f"    Found price: €{price:.2f}", file=sys.stderr)
                prices.append((price, url))
            else:
                print("    Could not find price", file=sys.stderr)

        if prices:
            cheapest = min(prices, key=lambda x: x[0])
            results[product_name] = cheapest
        else:
            results[product_name] = None

    return results
