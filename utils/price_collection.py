"""Price collection logic for fetching and processing product prices."""

import sys
from typing import Any, Dict, List, Optional

from tqdm import tqdm

from .extractors import extract_price
from .http_client import HttpClient
from .price_models import PriceResult, PriceProcessingResult, SearchResults
from .product_info import ProductInfo, calculate_price_per_100ml, parse_product_name
from .stock_checker import is_out_of_stock_with_url


class ProgressBarManager:
    """Manages progress bar state and updates for price collection.

    Encapsulates progress bar creation, updates, and finalization logic
    to avoid passing progress bar instance around as a parameter.
    """

    def __init__(self, total_urls: int, description: str, enabled: bool):
        """Initialize progress bar manager.

        Args:
            total_urls: Total number of URLs to process
            description: Description text for the progress bar
            enabled: If True, create progress bar; otherwise no-op
        """
        self.total_urls = total_urls
        self.pbar: Optional[tqdm] = None  # type: ignore[type-arg]
        self.base_desc = description  # Store base description

        if enabled:
            self.pbar = tqdm(
                total=total_urls,
                desc=description,
                unit="URL",
                file=sys.stderr,
                colour="green",
                # Use {desc} which we'll update to include product info
                bar_format="{desc}|{percentage:3.0f}%|{bar}|{n_fmt}/{total_fmt}|{elapsed}->{remaining}|{rate_fmt}",
            )

    def update_product_info(self, product_count: int, total_products: int, product_name: str) -> None:
        """Update progress bar with current product information.

        Args:
            product_count: Current product number (1-based)
            total_products: Total number of products
            product_name: Name of current product being processed
        """
        if self.pbar:
            # Update bar_format to include product info at the end
            product_suffix = f"|{product_count}/{total_products} products|{product_name[:40]:<40}"
            self.pbar.bar_format = (
                "{desc}|{percentage:3.0f}%|{bar}|{n_fmt}/{total_fmt}|{elapsed}->{remaining}|{rate_fmt}" + product_suffix
            )
            self.pbar.refresh()

    def update_on_error(self) -> None:
        """Update progress bar and flash red color on error."""
        if self.pbar:
            self.pbar.colour = "red"
            self.pbar.update(1)
            self.pbar.colour = "green"

    def update(self, n: int = 1) -> None:
        """Update progress by n steps.

        Args:
            n: Number of steps to increment (default: 1)
        """
        if self.pbar:
            self.pbar.update(n)

    def finalize(self, prices_found: int) -> None:
        """Set final color based on results and close progress bar.

        Args:
            prices_found: Number of successful price extractions
        """
        if self.pbar:
            if prices_found == self.total_urls:
                # All URLs successful - green
                self.pbar.colour = "green"
            elif prices_found == 0:
                # All URLs failed - red
                self.pbar.colour = "red"
            else:
                # Some issues - yellow
                self.pbar.colour = "yellow"
            self.pbar.close()


def _process_single_url(
    url: str,
    product_info: ProductInfo,
    http_client: HttpClient,
    verbose: bool,
    progress: ProgressBarManager,
) -> PriceProcessingResult:
    """Process a single URL and return price result.

    Args:
        url: URL to fetch
        product_info: Parsed product information
        http_client: HttpClient instance
        verbose: If True, print detailed messages
        progress: Progress bar manager for tracking progress

    Returns:
        PriceProcessingResult with price and status information
    """
    if verbose:
        print(f"  Fetching: {url}", file=sys.stderr)

    soup = http_client.fetch_page(url)

    if not soup:
        if verbose:
            print("    Could not fetch page", file=sys.stderr)
        progress.update_on_error()
        return PriceProcessingResult(price_result=None, fetch_error=True)

    # Check stock status first (using site-specific handlers)
    if is_out_of_stock_with_url(soup, url, http_client.config):
        if verbose:
            print("    Out of stock - skipping", file=sys.stderr)
        progress.update_on_error()
        http_client.remove_from_cache(url)  # Don't cache out-of-stock pages - stock status can change
        return PriceProcessingResult(price_result=None, out_of_stock=True)

    price = extract_price(soup, url, http_client.config)

    if not price:
        if verbose:
            print("    Could not find price", file=sys.stderr)
        progress.update_on_error()
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

    progress.update()

    price_result = PriceResult(price=price, url=url, price_per_100ml=price_per_100ml)
    return PriceProcessingResult(price_result=price_result)


def _process_url_list_for_product(
    product_name: str,
    urls: List[str],
    product_info: Any,
    http_client: HttpClient,
    *,
    verbose: bool,
    progress: ProgressBarManager,
    results: SearchResults,
) -> List[PriceResult]:
    """Process all URLs for a single product, updating results.

    Args:
        product_name: Name of the product being processed
        urls: List of URLs to check for this product
        product_info: Parsed product information
        http_client: HttpClient instance for fetching pages
        verbose: If True, print detailed progress messages
        progress: Progress bar manager for tracking progress
        results: SearchResults object to update with statistics

    Returns:
        List of successfully found PriceResult objects
    """
    prices = []

    for url in urls:
        results.statistics.total_urls_checked += 1

        # Process URL and get result
        result = _process_single_url(url, product_info, http_client, verbose, progress)

        # Update statistics based on result
        if result.fetch_error:
            results.statistics.fetch_errors += 1
            results.statistics.failed_urls.append(url)
        elif result.out_of_stock:
            results.statistics.out_of_stock += 1
            results.statistics.out_of_stock_items.setdefault(product_name, []).append(url)
        elif result.extraction_error:
            results.statistics.extraction_errors += 1
            results.statistics.failed_urls.append(url)
        elif result.is_success and result.price_result:
            # Success - add price result
            prices.append(result.price_result)
            results.statistics.prices_found += 1

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
    results.statistics.total_products = len(products)

    # Calculate total URLs and create progress bar manager
    total_urls = sum(len(urls) for urls in products.values())
    progress = ProgressBarManager(total_urls, progress_desc, show_progress)

    product_count = 0
    for product_name, urls in products.items():
        product_count += 1

        # Update progress bar with current product info
        progress.update_product_info(product_count, results.statistics.total_products, product_name)

        if verbose:
            print(f"\nChecking prices for {product_name}...", file=sys.stderr)

        # Parse product info once for all URLs of this product
        product_info = parse_product_name(product_name)

        # Process all URLs for this product
        prices = _process_url_list_for_product(
            product_name, urls, product_info, http_client, verbose=verbose, progress=progress, results=results
        )

        all_prices[product_name] = prices

    # Finalize progress bar with appropriate color
    progress.finalize(results.statistics.prices_found)

    return all_prices, results
