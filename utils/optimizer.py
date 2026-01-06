"""Mixed Integer Linear Programming optimizer for shopping plan."""

import re
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List
from urllib.parse import urlparse

import pulp  # type: ignore[import-untyped]

from .finder import PriceResult, extract_base_product_name
from .shipping import ShippingConfig

# Scale factor for value optimization to make price_per_100ml comparable to shipping costs
VALUE_OPTIMIZATION_SCALE_FACTOR = 10.0


def _sanitize_constraint_name(name: str) -> str:
    """Sanitize a name for use in PuLP constraint names.

    Replaces special characters that might not be valid in constraint names
    (spaces, dots, hyphens, parentheses) with underscores.

    Args:
        name: Name to sanitize (e.g., "notino.pt", "Product (100ml)")

    Returns:
        Sanitized name safe for constraint names (e.g., "notino_pt", "Product__100ml_")
    """
    return re.sub(r"[.\s\-()]", "_", name)


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
    """Extract domain from URL with fallback for malformed URLs.

    Args:
        url: Full URL

    Returns:
        Domain (e.g., 'notino.pt'), or the full URL if domain cannot be extracted
    """
    parsed = urlparse(url)
    domain = parsed.netloc
    
    # Fallback to full URL if netloc is empty (malformed URL)
    if not domain:
        return url
    
    # Remove www. prefix if present
    if domain.startswith("www."):
        return domain[4:]  # Remove "www."
    return domain


def _build_price_index(
    all_prices: Dict[str, List[PriceResult]],
) -> tuple[List[str], List[str], Dict[tuple[str, str, int], PriceResult]]:
    """Build index structures from all_prices.

    Args:
        all_prices: Dict mapping product names to lists of PriceResult objects

    Returns:
        Tuple of (products, stores, price_options)
    """
    products = list(all_prices.keys())
    stores_set = set()
    price_options: Dict[tuple[str, str, int], PriceResult] = {}

    for product, price_list in all_prices.items():
        for size_idx, price_result in enumerate(price_list):
            store = _extract_domain(price_result.url)
            stores_set.add(store)
            price_options[(product, store, size_idx)] = price_result

    stores = sorted(stores_set)
    return products, stores, price_options


def _group_product_families(products: List[str]) -> Dict[str, List[str]]:
    """Group products by their base name (without size info).

    Args:
        products: List of product names

    Returns:
        Dict mapping base names to lists of product names
    """
    product_families: Dict[str, List[str]] = {}
    for product in products:
        base_name = extract_base_product_name(product)
        if base_name not in product_families:
            product_families[base_name] = []
        product_families[base_name].append(product)
    return product_families


def _create_objective(
    prob: Any,
    x: Dict[Any, Any],
    *,
    price_options: Dict[tuple[str, str, int], PriceResult],
    use_store: Dict[Any, Any],
    free_ship: Dict[Any, Any],
    stores: List[str],
    shipping_config: ShippingConfig,
    optimize_for_value: bool,
) -> None:
    """Create and add objective function to MILP problem.

    Args:
        prob: PuLP problem instance
        x: Buy decision variables
        price_options: Price options mapping
        use_store: Store usage variables
        free_ship: Free shipping variables
        stores: List of stores
        shipping_config: Shipping configuration
        optimize_for_value: Whether to optimize for value or cost
    """
    if optimize_for_value:

        def get_value_cost(key: tuple[str, str, int]) -> float:
            """Calculate value-based cost for a product option.

            Uses price per 100ml scaled by VALUE_OPTIMIZATION_SCALE_FACTOR
            to make comparable with shipping costs.
            Falls back to regular price if volume info is unavailable.

            Args:
                key: Tuple of (product, store, size_index)

            Returns:
                Scaled value cost or regular price
            """
            price_result = price_options[key]
            if price_result.price_per_100ml is not None:
                return price_result.price_per_100ml * VALUE_OPTIMIZATION_SCALE_FACTOR
            return price_result.price

        product_cost = pulp.lpSum(get_value_cost((p, s, i)) * x.get((p, s, i), 0) for (p, s, i) in price_options)
    else:
        product_cost = pulp.lpSum(price_options[(p, s, i)].price * x.get((p, s, i), 0) for (p, s, i) in price_options)

    shipping_cost = pulp.lpSum(
        shipping_config.get_shipping_info(s).shipping_cost * (use_store[s] - free_ship[s]) for s in stores
    )
    prob += product_cost + shipping_cost, "Total_Cost"


def _add_constraints(
    prob: Any,
    x: Dict[Any, Any],
    *,
    use_store: Dict[Any, Any],
    free_ship: Dict[Any, Any],
    products: List[str],
    stores: List[str],
    product_families: Dict[str, List[str]],
    price_options: Dict[tuple[str, str, int], PriceResult],
    all_prices: Dict[str, List[PriceResult]],
    shipping_config: ShippingConfig,
) -> None:
    """Add all constraints to MILP problem.

    Args:
        prob: PuLP problem instance
        x: Buy decision variables
        use_store: Store usage variables
        free_ship: Free shipping variables
        products: List of products
        stores: List of stores
        product_families: Product families mapping
        price_options: Price options mapping
        all_prices: All prices dictionary
        shipping_config: Shipping configuration
    """
    # Constraint 1: Each product family bought exactly once
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
            f"Buy_{_sanitize_constraint_name(base_name)}_once",
        )

    # Constraint 2: Link product selection to store usage
    for p, s, i in price_options:
        prob += (
            x[(p, s, i)] <= use_store[s],
            f"Link_{_sanitize_constraint_name(p)}_{_sanitize_constraint_name(s)}_{i}_to_store",
        )

    # Constraint 3: Free shipping threshold
    for store in stores:
        shipping_info = shipping_config.get_shipping_info(store)
        subtotal = pulp.lpSum(
            price_options[(p, s, i)].price * x.get((p, s, i), 0) for (p, s, i) in price_options if s == store
        )
        sanitized_store = _sanitize_constraint_name(store)
        prob += subtotal >= shipping_info.free_over * free_ship[store], f"Free_shipping_threshold_{sanitized_store}"
        prob += free_ship[store] <= use_store[store], f"Free_ship_requires_use_{sanitized_store}"


def _extract_solution(
    x: Dict[Any, Any],
    price_options: Dict[tuple[str, str, int], PriceResult],
    shipping_config: ShippingConfig,
) -> OptimizedPlan:
    """Extract solution from solved MILP problem.

    Args:
        x: Decision variables dict
        price_options: Price options mapping
        shipping_config: Shipping configuration

    Returns:
        OptimizedPlan with store assignments
    """
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
    """
    # Build index structures
    products, stores, price_options = _build_price_index(all_prices)

    if not products or not stores:
        return OptimizedPlan()

    # Create MILP problem and decision variables
    prob = pulp.LpProblem("Shopping_Optimization", pulp.LpMinimize)
    x = pulp.LpVariable.dicts(
        "buy",
        ((p, s, i) for p in products for s in stores for i in range(len(all_prices[p]))),
        cat=pulp.LpBinary,
    )
    use_store = pulp.LpVariable.dicts("use_store", stores, cat=pulp.LpBinary)
    free_ship = pulp.LpVariable.dicts("free_ship", stores, cat=pulp.LpBinary)

    # Set objective and constraints
    _create_objective(
        prob,
        x,
        price_options=price_options,
        use_store=use_store,
        free_ship=free_ship,
        stores=stores,
        shipping_config=shipping_config,
        optimize_for_value=optimize_for_value,
    )
    product_families = _group_product_families(products)
    _add_constraints(
        prob,
        x,
        use_store=use_store,
        free_ship=free_ship,
        products=products,
        stores=stores,
        product_families=product_families,
        price_options=price_options,
        all_prices=all_prices,
        shipping_config=shipping_config,
    )

    # Solve
    prob.solve(pulp.PULP_CBC_CMD(msg=0))

    if prob.status != pulp.LpStatusOptimal:
        print(
            f"Warning: Optimization did not find optimal solution. Status: {pulp.LpStatus[prob.status]}",
            file=sys.stderr,
        )
        return OptimizedPlan()

    return _extract_solution(x, price_options, shipping_config)
