"""Crawl product URLs and print prices to stdout."""

import sys

import yaml

from utils.config import Config
from utils.data_loader import load_products
from utils.extractors import extract_price
from utils.http_client import HttpClient
from utils.product_info import calculate_price_per_100ml, parse_product_name
from utils.stock_checker import is_out_of_stock_with_url

PRODUCTS_FILE = "products.yml"


def crawl_prices(products_file: str) -> None:
    products = load_products(products_file)
    if not products:
        print("No products found.", file=sys.stderr)
        sys.exit(1)

    config = Config()

    with HttpClient(config=config, use_cache=False, verbose=False) as http:
        for product_name, urls in products.items():
            product_info = parse_product_name(product_name)

            for url in urls:
                soup = http.fetch_page(url)

                if not soup:
                    print(f"{product_name}\tN/A\tFetch error\t{url}")
                    continue

                if is_out_of_stock_with_url(soup, url, config):
                    print(f"{product_name}\tN/A\tOut of stock\t{url}")
                    continue

                price = extract_price(soup, url, config)

                if price is None:
                    print(f"{product_name}\tN/A\tPrice not found\t{url}")
                    continue

                if product_info.total_volume_ml:
                    price_per_100ml = calculate_price_per_100ml(price, product_info.total_volume_ml)
                    print(f"{product_name}\t{price:.2f}\t{price_per_100ml:.2f}/100ml\t{url}")
                else:
                    print(f"{product_name}\t{price:.2f}\t\t{url}")


if __name__ == "__main__":
    products_file = sys.argv[1] if len(sys.argv) > 1 else PRODUCTS_FILE
    crawl_prices(products_file)
