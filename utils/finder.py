"""Main price comparison logic and public API."""

import re
from typing import Dict, List, Optional

from .http_client import HttpClient
from .price_collection import collect_prices_for_products
from .price_models import PriceResult, SearchResults


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


def find_cheapest_prices(
    products: Dict[str, List[str]],
    http_client: HttpClient,
    verbose: bool = True,
    show_progress: bool = True,
) -> SearchResults:
    """Find the cheapest price for each product, excluding out-of-stock items.

    Args:
        products: Dictionary mapping product names to lists of URLs
        http_client: HttpClient instance for fetching pages
        verbose: If True, print detailed progress messages
        show_progress: If True, display progress bar

    Returns:
        SearchResults object with prices and summary statistics
    """
    all_prices, results = collect_prices_for_products(
        products, http_client, verbose, show_progress, "Finding best prices"
    )

    # Select cheapest price for each product
    for product_name, prices in all_prices.items():
        if prices:
            # Find cheapest by absolute price
            cheapest = min(prices, key=lambda x: x.price)
            results.prices[product_name] = cheapest
        else:
            results.prices[product_name] = None

    return results


def find_all_prices(
    products: Dict[str, List[str]],
    http_client: HttpClient,
    verbose: bool = True,
    show_progress: bool = True,
) -> Dict[str, List[PriceResult]]:
    """Find ALL available prices for each product across all stores.

    Similar to find_cheapest_prices() but returns all valid prices instead of just
    the cheapest one. Used for optimization across stores.

    Args:
        products: Dictionary mapping product names to lists of URLs
        http_client: HttpClient instance for fetching pages
        verbose: If True, print detailed progress messages
        show_progress: If True, display progress bar

    Returns:
        Dictionary mapping product names to lists of PriceResult objects
    """
    all_prices, _results = collect_prices_for_products(
        products, http_client, verbose, show_progress, "Finding all prices"
    )

    return all_prices


def group_by_product_family(results: SearchResults) -> Dict[str, Dict[str, Optional[PriceResult]]]:
    """Group search results by product family (base name without size info).

    Args:
        results: SearchResults object with prices

    Returns:
        Dictionary mapping base product names to dictionaries of {product_name: result}
    """
    product_families = _group_products_by_base_name(results.prices)

    # Convert list of tuples to dict for each family
    return {base_name: dict(products_list) for base_name, products_list in product_families.items()}
