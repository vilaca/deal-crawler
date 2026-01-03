"""Store purchase optimization algorithm."""

import itertools
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from urllib.parse import urlparse

from .finder import PriceResult
from .shipping import ShippingConfig, ShippingInfo, get_shipping_cost, get_shipping_info_for_url


@dataclass
class StoreCart:
    """Products grouped by store with cost breakdown."""

    site: str  # Store domain
    items: List[tuple[str, PriceResult]] = field(default_factory=list)  # (product_name, price_result)
    subtotal: float = 0.0  # Sum of product prices
    shipping_cost: float = 0.0  # Shipping cost for this store
    total: float = 0.0  # subtotal + shipping_cost
    free_shipping_eligible: bool = False  # Whether free shipping applies


@dataclass
class OptimizedPlan:
    """Complete optimized shopping plan."""

    carts: List[StoreCart] = field(default_factory=list)  # Sorted by store
    grand_total: float = 0.0  # Total cost across all stores
    total_products: int = 0  # Number of products
    total_shipping: float = 0.0  # Sum of all shipping costs


def _extract_domain(url: str) -> str:
    """Extract and normalize domain from URL.

    Args:
        url: Product URL

    Returns:
        Normalized domain (without www. prefix)
    """
    parsed = urlparse(url)
    domain = parsed.netloc.replace("www.", "")
    return domain


def _calculate_cart_costs(cart: StoreCart, shipping_info: ShippingInfo) -> None:
    """Calculate and update cart costs (subtotal, shipping, total).

    Args:
        cart: StoreCart to update
        shipping_info: Store shipping configuration
    """
    # Calculate subtotal
    cart.subtotal = sum(price_result.price for _, price_result in cart.items)

    # Calculate shipping cost
    cart.shipping_cost = get_shipping_cost(cart.subtotal, shipping_info)
    cart.free_shipping_eligible = cart.subtotal >= shipping_info.free_over

    # Calculate total
    cart.total = cart.subtotal + cart.shipping_cost


def _group_by_product_family(all_prices: Dict[str, List[PriceResult]]) -> Dict[str, List[str]]:
    """Group product names by their base name (product family).

    Example: "Cerave Cleanser (236ml)" and "Cerave Cleanser (473ml)"
    are grouped under "Cerave Cleanser"

    Args:
        all_prices: Dictionary mapping product names to price lists

    Returns:
        Dictionary mapping base names to lists of full product names
    """
    import re

    families = {}
    for product_name in all_prices.keys():
        # Remove size information in parentheses to get base name
        base_name = re.sub(r'\s*\([^)]*\)\s*$', '', product_name).strip()

        if base_name not in families:
            families[base_name] = []
        families[base_name].append(product_name)

    return families


def optimize_shopping_plan(
    all_prices: Dict[str, List[PriceResult]], shipping_config: ShippingConfig
) -> OptimizedPlan:
    """Optimize shopping plan using exhaustive search solver.

    Uses exhaustive search to explore all possible size and store combinations
    to find the globally optimal solution considering product prices and shipping.

    Strategy:
    - Group products by base name (product families, ignoring size)
    - For each family, enumerate all (size, store) options
    - Generate all combinations: one size per family, any store per size
    - Calculate total cost for each combination (products + shipping)
    - Return the combination with minimum total cost

    Args:
        all_prices: Dictionary mapping product names to lists of PriceResult
        shipping_config: Shipping configuration for all stores

    Returns:
        OptimizedPlan with globally optimal size and store distribution
    """
    if not all_prices:
        return OptimizedPlan()

    # Filter out products with no available prices
    products_with_prices = {name: prices for name, prices in all_prices.items() if prices}
    if not products_with_prices:
        return OptimizedPlan()

    # Group products by family (base name without size)
    product_families = _group_by_product_family(products_with_prices)

    # For each product family, build list of (product_name, store, price_result) options
    # This includes all size variants and all stores for each size
    family_options = []
    family_names = list(product_families.keys())

    for base_name in family_names:
        size_variants = product_families[base_name]
        options = []

        # For each size variant, add all store options
        for product_name in size_variants:
            for price_result in products_with_prices[product_name]:
                store = _extract_domain(price_result.url)
                options.append((product_name, store, price_result))

        family_options.append(options)

    # Generate all possible assignments using cartesian product
    # Each assignment picks ONE (size, store) combination per product family
    best_plan = None
    best_cost = float("inf")

    for assignment in itertools.product(*family_options):
        # Group by store to calculate shipping
        store_carts: Dict[str, StoreCart] = {}

        for product_name, store, price_result in assignment:
            if store not in store_carts:
                store_carts[store] = StoreCart(site=store)
            store_carts[store].items.append((product_name, price_result))

        # Calculate costs for each cart
        total_cost = 0.0
        for store, cart in store_carts.items():
            shipping_info = get_shipping_info_for_url(f"https://{store}/", shipping_config)
            _calculate_cart_costs(cart, shipping_info)
            total_cost += cart.total

        # Check if this is the best solution so far
        if total_cost < best_cost:
            best_cost = total_cost

            # Create optimized plan
            plan = OptimizedPlan()
            plan.carts = sorted(store_carts.values(), key=lambda c: c.site)
            plan.total_products = len(family_names)  # Count families, not size variants
            plan.grand_total = total_cost
            plan.total_shipping = sum(c.shipping_cost for c in plan.carts)
            best_plan = plan

    return best_plan if best_plan else OptimizedPlan()


