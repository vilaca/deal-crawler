"""Product filtering utilities for Deal Crawler."""

from typing import Dict, List
from urllib.parse import urlparse


def filter_by_sites(products: Dict[str, List[str]], sites: List[str]) -> Dict[str, List[str]]:
    """Filter products to only include URLs from specified sites.

    Args:
        products: Dictionary of product names to URL lists
        sites: List of site domains to include (e.g., ["notino.pt", "wells.pt"])

    Returns:
        Filtered products dictionary
    """
    filtered = {}
    for product_name, urls in products.items():
        filtered_urls = [url for url in urls if any(site.lower() in urlparse(url).netloc.lower() for site in sites)]
        if filtered_urls:
            filtered[product_name] = filtered_urls
    return filtered


def filter_by_products(products: Dict[str, List[str]], substrings: List[str]) -> Dict[str, List[str]]:
    """Filter products to only include those matching substring(s).

    Args:
        products: Dictionary of product names to URL lists
        substrings: List of substrings to match (case-insensitive)

    Returns:
        Filtered products dictionary
    """
    filtered = {}
    for product_name, urls in products.items():
        if any(substring.lower() in product_name.lower() for substring in substrings):
            filtered[product_name] = urls
    return filtered
