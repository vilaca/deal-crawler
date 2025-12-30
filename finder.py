"""Main price comparison logic."""

from typing import Dict, List, Optional, Tuple

from http_client import HttpClient
from stock_checker import is_out_of_stock
from extractors import extract_price


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
        print(f"\nChecking prices for {product_name}...")
        prices = []

        for url in urls:
            print(f"  Fetching: {url}")
            soup = http_client.fetch_page(url)

            if not soup:
                print("    Could not fetch page")
                continue

            # Check stock status first
            if is_out_of_stock(soup):
                print("    Out of stock - skipping")
                continue

            price = extract_price(soup, url)

            if price:
                print(f"    Found price: €{price:.2f}")
                prices.append((price, url))
            else:
                print("    Could not find price")

        if prices:
            cheapest = min(prices, key=lambda x: x[0])
            results[product_name] = cheapest
        else:
            results[product_name] = None

    return results
