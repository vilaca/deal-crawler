"""Mixed Integer Linear Programming optimizer for shopping plan."""

import re
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from urllib.parse import urlparse

import pulp

from .finder import PriceResult
from .shipping import ShippingConfig


def _extract_base_product_name(product_name: str) -> str:
    """Extract base product name without size information.

    Args:
        product_name: Full product name (e.g., "Cerave Foaming Cleanser (236ml)")

    Returns:
        Base product name (e.g., "Cerave Foaming Cleanser")
    """
    # Remove size patterns: (236ml), (2x236ml), (1000ml), etc.
    base_name = re.sub(r"\s*\([\d.]+(?:x[\d.]+)?ml\)\s*$", "", product_name, flags=re.IGNORECASE)
    return base_name.strip()


@dataclass
class StoreCart:
    """Shopping cart for a single store."""

    site: str
    items: List[tuple[str, PriceResult]] = field(default_factory=list)
    subtotal: float = 0.0
    shipping_cost: float = 0.0
    total: float = 0.0
    free_shipping_eligible: bool = False


@dataclass
class OptimizedPlan:
    """Optimized shopping plan across multiple stores."""

    carts: List[StoreCart] = field(default_factory=list)
    grand_total: float = 0.0
    total_products: int = 0
    total_shipping: float = 0.0


def _extract_domain(url: str) -> str:
    """Extract domain from URL.

    Args:
        url: Full URL

    Returns:
        Domain (e.g., 'notino.pt')
    """
    parsed = urlparse(url)
    domain = parsed.netloc
    # Remove www. prefix if present
    if domain.startswith("www."):
        return domain
    return domain


def optimize_shopping_plan(
    all_prices: Dict[str, List[PriceResult]],
    shipping_config: ShippingConfig,
    optimize_for_value: bool = False,
) -> OptimizedPlan:
    """Optimize shopping plan using Mixed Integer Linear Programming.

    Args:
        all_prices: Dict mapping product names to lists of PriceResult objects
        shipping_config: Shipping configuration with costs and thresholds
        optimize_for_value: If True, optimize for best price per 100ml instead of lowest total cost

    Returns:
        OptimizedPlan with optimal store assignments

    MILP Formulation:
        Decision Variables:
            - x[p,s,i]: Binary, 1 if product p bought in size i from store s
            - use_store[s]: Binary, 1 if any product bought from store s
            - free_ship[s]: Binary, 1 if store s qualifies for free shipping

        Objective (cost mode):
            Minimize: sum of product prices + shipping costs

        Objective (value mode):
            Minimize: sum of (price_per_100ml * scaling_factor) + shipping costs
            Prefers products with better price per ml, even if absolute price is higher

        Constraints:
            1. Each product bought exactly once:
               sum_{s,i} x[p,s,i] = 1  for all p
            2. Link product selection to store usage:
               x[p,s,i] <= use_store[s]  for all p,s,i
            3. Free shipping threshold:
               subtotal[s] >= free_threshold[s] * free_ship[s]
               free_ship[s] <= use_store[s]
    """
    # Create the optimization problem
    prob = pulp.LpProblem("Shopping_Optimization", pulp.LpMinimize)

    # Build index structures
    products = list(all_prices.keys())
    stores = set()

    # Map (product, store, size_index) to PriceResult
    price_options: Dict[tuple[str, str, int], PriceResult] = {}

    for product, price_list in all_prices.items():
        for size_idx, price_result in enumerate(price_list):
            store = _extract_domain(price_result.url)
            stores.add(store)
            price_options[(product, store, size_idx)] = price_result

    stores = sorted(stores)

    if not products or not stores:
        return OptimizedPlan()

    # Decision variables
    # x[p,s,i] = 1 if we buy product p in size i from store s
    x = pulp.LpVariable.dicts(
        "buy",
        ((p, s, i) for p in products for s in stores for i in range(len(all_prices[p]))),
        cat=pulp.LpBinary,
    )

    # use_store[s] = 1 if we buy anything from store s
    use_store = pulp.LpVariable.dicts("use_store", stores, cat=pulp.LpBinary)

    # free_ship[s] = 1 if store s gets free shipping
    free_ship = pulp.LpVariable.dicts("free_ship", stores, cat=pulp.LpBinary)

    # Objective: minimize total cost or value
    if optimize_for_value:
        # In value mode, prefer products with better price per 100ml
        # Use price_per_100ml when available, fallback to price for products without volume info
        # Scale by 10 to make magnitudes comparable with shipping costs
        product_cost = pulp.lpSum(
            (price_options[(p, s, i)].price_per_100ml * 10.0
             if price_options[(p, s, i)].price_per_100ml is not None
             else price_options[(p, s, i)].price) * x.get((p, s, i), 0)
            for (p, s, i) in price_options.keys()
        )
    else:
        # In cost mode, minimize absolute prices
        product_cost = pulp.lpSum(
            price_options[(p, s, i)].price * x.get((p, s, i), 0)
            for (p, s, i) in price_options.keys()
        )

    shipping_cost = pulp.lpSum(
        shipping_config.get_shipping_info(s).shipping_cost * (use_store[s] - free_ship[s])
        for s in stores
    )

    prob += product_cost + shipping_cost, "Total_Cost"

    # Constraint 1: Each product family (base name) must be bought exactly once
    # Group products by base name (without size info)
    product_families: Dict[str, List[str]] = {}
    for product in products:
        base_name = _extract_base_product_name(product)
        if base_name not in product_families:
            product_families[base_name] = []
        product_families[base_name].append(product)

    # For each product family, buy exactly one size
    for base_name, family_products in product_families.items():
        prob += (
            pulp.lpSum(
                x.get((product, s, i), 0)
                for product in family_products
                for s in stores
                for i in range(len(all_prices[product]))
                if (product, s, i) in price_options
            )
            == 1,
            f"Buy_{base_name.replace(' ', '_')}_once",
        )

    # Constraint 2: Link x to use_store
    for (p, s, i) in price_options.keys():
        prob += x[(p, s, i)] <= use_store[s], f"Link_{p}_{s}_{i}_to_store"

    # Constraint 3: Free shipping threshold
    for store in stores:
        shipping_info = shipping_config.get_shipping_info(store)

        # Calculate subtotal for this store
        subtotal = pulp.lpSum(
            price_options[(p, s, i)].price * x.get((p, s, i), 0)
            for (p, s, i) in price_options.keys()
            if s == store
        )

        # If free_ship[store] = 1, then subtotal >= free_threshold
        prob += (
            subtotal >= shipping_info.free_over * free_ship[store],
            f"Free_shipping_threshold_{store}",
        )

        # free_ship can only be 1 if we use the store
        prob += free_ship[store] <= use_store[store], f"Free_ship_requires_use_{store}"

    # Solve the problem
    prob.solve(pulp.PULP_CBC_CMD(msg=0))

    # Check if solution was found
    if prob.status != pulp.LpStatusOptimal:
        print(f"Warning: Optimization did not find optimal solution. Status: {pulp.LpStatus[prob.status]}",
              file=sys.stderr)
        return OptimizedPlan()

    # Extract solution
    plan = OptimizedPlan()
    store_carts: Dict[str, StoreCart] = {}

    for (p, s, i), var in x.items():
        if var.varValue and var.varValue > 0.5:  # Binary variable is 1
            if s not in store_carts:
                store_carts[s] = StoreCart(site=s)

            price_result = price_options[(p, s, i)]
            store_carts[s].items.append((p, price_result))
            store_carts[s].subtotal += price_result.price

    # Calculate shipping for each store
    for s, cart in store_carts.items():
        shipping_info = shipping_config.get_shipping_info(s)
        cart.free_shipping_eligible = cart.subtotal >= shipping_info.free_over
        cart.shipping_cost = 0.0 if cart.free_shipping_eligible else shipping_info.shipping_cost
        cart.total = cart.subtotal + cart.shipping_cost

    plan.carts = sorted(store_carts.values(), key=lambda c: c.site)
    plan.total_products = sum(len(cart.items) for cart in plan.carts)
    plan.total_shipping = sum(cart.shipping_cost for cart in plan.carts)
    plan.grand_total = sum(cart.total for cart in plan.carts)

    return plan
