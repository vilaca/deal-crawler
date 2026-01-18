"""Price collection logic for fetching and processing product prices."""

import sys
from typing import Any, Dict, List, Optional

from tqdm import tqdm

from .extractors import extract_price
from .http_client import HttpClient
from .price_models import PriceResult, PriceProcessingResult, SearchResults
from .product_info import ProductInfo, calculate_price_per_100ml, parse_product_name
from .stock_checker import is_out_of_stock


def _create_progress_bar(
    total_urls: int, progress_desc: str, show_progress: bool
) -> Optional[tqdm]:  # type: ignore[type-arg]
    """Create and initialize progress bar for URL tracking.

    Args:
        total_urls: Total number of URLs to process
        progress_desc: Description text for the progress bar
        show_progress: If True, create progress bar; otherwise return None

    Returns:
        tqdm progress bar instance or None if show_progress is False
    """
    if show_progress:
        return tqdm(total=total_urls, desc=progress_desc, unit=" URL", file=sys.stderr, colour="green")
    return None


def _update_progress_bar_product_info(
    pbar: Optional[tqdm], product_count: int, total_products: int, product_name: str  # type: ignore[type-arg]
) -> None:
    """Update progress bar with current product information.

    Args:
        pbar: tqdm progress bar instance (or None)
        product_count: Current product number (1-based)
        total_products: Total number of products
        product_name: Name of current product being processed
    """
    if pbar:
        pbar.set_postfix_str(f"[{product_count}/{total_products} products] {product_name[:40]:<40}")


def _update_progress_bar_on_error(pbar: Optional[tqdm]) -> None:  # type: ignore[type-arg]
    """Update progress bar and flash red color on error.

    Args:
        pbar: tqdm progress bar instance (or None)
    """
    if pbar:
        pbar.colour = "red"
        pbar.update(1)
        pbar.colour = "green"


def _finalize_progress_bar(pbar: Optional[tqdm], prices_found: int, total_urls: int) -> None:  # type: ignore[type-arg]
    """Set final color based on results and close progress bar.

    Args:
        pbar: tqdm progress bar instance (or None)
        prices_found: Number of successful price extractions
        total_urls: Total number of URLs processed
    """
    if pbar:
        if prices_found == total_urls:
            # All URLs successful - green
            pbar.colour = "green"
        elif prices_found == 0:
            # All URLs failed - red
            pbar.colour = "red"
        else:
            # Some issues - yellow
            pbar.colour = "yellow"
        pbar.close()


def _process_single_url(
    url: str,
    product_info: ProductInfo,
    http_client: HttpClient,
    verbose: bool,
    pbar: Optional[tqdm],  # type: ignore[type-arg]
) -> PriceProcessingResult:
    """Process a single URL and return price result.

    Args:
        url: URL to fetch
        product_info: Parsed product information
        http_client: HttpClient instance
        verbose: If True, print detailed messages
        pbar: tqdm progress bar instance (or None)

    Returns:
        PriceProcessingResult with price and status information
    """
    if verbose:
        print(f"  Fetching: {url}", file=sys.stderr)

    soup = http_client.fetch_page(url)

    if not soup:
        if verbose:
            print("    Could not fetch page", file=sys.stderr)
        _update_progress_bar_on_error(pbar)
        return PriceProcessingResult(price_result=None, fetch_error=True)

    # Check stock status first
    if is_out_of_stock(soup):
        if verbose:
            print("    Out of stock - skipping", file=sys.stderr)
        _update_progress_bar_on_error(pbar)
        return PriceProcessingResult(price_result=None, out_of_stock=True)

    price = extract_price(soup, url, http_client.config)

    if not price:
        if verbose:
            print("    Could not find price", file=sys.stderr)
        _update_progress_bar_on_error(pbar)
        http_client.remove_from_cache(url)
        return PriceProcessingResult(price_result=None, extraction_error=True)

    # Calculate price per 100ml if volume information is available
    price_per_100ml = None
    if product_info.total_volume_ml:
        price_per_100ml = calculate_price_per_100ml(price, product_info.total_volume_ml)
        if verbose:
            print(f"    Found price: €{price:.2f} ({price_per_100ml:.2f}/100ml)", file=sys.stderr)
    else:
        if verbose:
            print(f"    Found price: €{price:.2f}", file=sys.stderr)

    if pbar:
        pbar.update(1)

    price_result = PriceResult(price=price, url=url, price_per_100ml=price_per_100ml)
    return PriceProcessingResult(price_result=price_result)


def _process_url_list_for_product(
    product_name: str,
    urls: List[str],
    product_info: Any,
    http_client: HttpClient,
    *,
    verbose: bool,
    pbar: Optional[tqdm],
    results: SearchResults,
) -> List[PriceResult]:
    """Process all URLs for a single product, updating results.

    Args:
        product_name: Name of the product being processed
        urls: List of URLs to check for this product
        product_info: Parsed product information
        http_client: HttpClient instance for fetching pages
        verbose: If True, print detailed progress messages
        pbar: Progress bar instance (or None)
        results: SearchResults object to update with statistics

    Returns:
        List of successfully found PriceResult objects
    """
    prices = []

    for url in urls:
        results.total_urls_checked += 1

        # Process URL and get result
        result = _process_single_url(url, product_info, http_client, verbose, pbar)

        # Update statistics based on result
        if result.fetch_error:
            results.fetch_errors += 1
            results.failed_urls.append(url)
        elif result.out_of_stock:
            results.out_of_stock += 1
            results.out_of_stock_items.setdefault(product_name, []).append(url)
        elif result.extraction_error:
            results.extraction_errors += 1
            results.failed_urls.append(url)
        elif result.is_success and result.price_result:
            # Success - add price result
            prices.append(result.price_result)
            results.prices_found += 1

    return prices


def collect_prices_for_products(
    products: Dict[str, List[str]],
    http_client: HttpClient,
    verbose: bool = True,
    show_progress: bool = True,
    progress_desc: str = "Collecting prices",
) -> tuple[Dict[str, List[PriceResult]], SearchResults]:
    """Collect all prices for products with detailed statistics tracking.

    This function collects ALL prices for each product and tracks comprehensive
    statistics. Public functions in finder.py use this and process the results
    according to their specific needs.

    Args:
        products: Dictionary mapping product names to lists of URLs
        http_client: HttpClient instance for fetching pages
        verbose: If True, print detailed progress messages
        show_progress: If True, display progress bar
        progress_desc: Description for progress bar

    Returns:
        Tuple of (all_prices_dict, search_results_with_statistics)
    """
    all_prices: Dict[str, List[PriceResult]] = {}
    results = SearchResults()
    results.total_products = len(products)

    # Calculate total URLs and create progress bar
    total_urls = sum(len(urls) for urls in products.values())
    pbar = _create_progress_bar(total_urls, progress_desc, show_progress)

    product_count = 0
    for product_name, urls in products.items():
        product_count += 1

        # Update progress bar with current product info
        _update_progress_bar_product_info(pbar, product_count, results.total_products, product_name)

        if verbose:
            print(f"\nChecking prices for {product_name}...", file=sys.stderr)

        # Parse product info once for all URLs of this product
        product_info = parse_product_name(product_name)

        # Process all URLs for this product
        prices = _process_url_list_for_product(
            product_name, urls, product_info, http_client, verbose=verbose, pbar=pbar, results=results
        )

        all_prices[product_name] = prices

    # Finalize progress bar with appropriate color
    _finalize_progress_bar(pbar, results.prices_found, total_urls)

    return all_prices, results
