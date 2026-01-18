"""Shared test fixtures for formatter tests."""

from typing import Optional

from utils.price_models import PriceResult
from utils.optimizer import OptimizedPlan, StoreCart
from utils.shipping import ShippingConfig, ShippingInfo


def create_empty_plan() -> OptimizedPlan:
    """Create an empty plan for testing.

    Returns:
        Empty OptimizedPlan with no carts
    """
    return OptimizedPlan()


def create_single_product_cart(
    *,
    site: str = "example.com",
    product_name: str = "Test Product",
    price: float = 25.00,
    url: Optional[str] = None,
    shipping_cost: float = 3.99,
    free_shipping: bool = False,
    price_per_100ml: Optional[float] = None,
) -> StoreCart:
    """Create a cart with a single product.

    Args:
        site: Store site name
        product_name: Product name
        price: Product price
        url: Product URL (auto-generated if None)
        shipping_cost: Shipping cost
        free_shipping: Whether cart qualifies for free shipping
        price_per_100ml: Optional price per 100ml

    Returns:
        StoreCart with one product
    """
    if url is None:
        url = f"https://{site}/test"

    result = PriceResult(
        price=price,
        url=url,
        price_per_100ml=price_per_100ml,
    )
    total = price + (0.0 if free_shipping else shipping_cost)

    return StoreCart(
        site=site,
        items=[(product_name, result)],
        subtotal=price,
        shipping_cost=0.0 if free_shipping else shipping_cost,
        total=total,
        free_shipping_eligible=free_shipping,
    )


def create_multi_product_cart(
    site: str,
    products: list[tuple[str, float]],
    shipping_cost: float = 3.99,
    free_shipping: bool = False,
) -> StoreCart:
    """Create a cart with multiple products.

    Args:
        site: Store site name
        products: List of (product_name, price) tuples
        shipping_cost: Shipping cost
        free_shipping: Whether cart qualifies for free shipping

    Returns:
        StoreCart with multiple products
    """
    items = []
    subtotal = 0.0

    for product_name, price in products:
        result = PriceResult(price=price, url=f"https://{site}/{product_name.lower().replace(' ', '')}")
        items.append((product_name, result))
        subtotal += price

    total = subtotal + (0.0 if free_shipping else shipping_cost)

    return StoreCart(
        site=site,
        items=items,
        subtotal=subtotal,
        shipping_cost=0.0 if free_shipping else shipping_cost,
        total=total,
        free_shipping_eligible=free_shipping,
    )


def create_plan_with_single_cart(
    cart: Optional[StoreCart] = None,
) -> OptimizedPlan:
    """Create a plan with a single cart.

    Args:
        cart: StoreCart to include (creates default if None)

    Returns:
        OptimizedPlan with one cart
    """
    if cart is None:
        cart = create_single_product_cart()

    return OptimizedPlan(
        carts=[cart],
        grand_total=cart.total,
        total_products=len(cart.items),
        total_shipping=cart.shipping_cost,
    )


def create_plan_with_multiple_carts(
    carts: list[StoreCart],
) -> OptimizedPlan:
    """Create a plan with multiple carts.

    Args:
        carts: List of StoreCarts to include

    Returns:
        OptimizedPlan with multiple carts
    """
    grand_total = sum(cart.total for cart in carts)
    total_products = sum(len(cart.items) for cart in carts)
    total_shipping = sum(cart.shipping_cost for cart in carts)

    return OptimizedPlan(
        carts=carts,
        grand_total=grand_total,
        total_products=total_products,
        total_shipping=total_shipping,
    )


def create_shipping_config(
    site: str = "example.com",
    shipping_cost: float = 3.99,
    free_over: float = 50.00,
) -> ShippingConfig:
    """Create a shipping config for testing.

    Args:
        site: Store site name
        shipping_cost: Shipping cost
        free_over: Free shipping threshold

    Returns:
        ShippingConfig with one store
    """
    return ShippingConfig(stores={site: ShippingInfo(site=site, shipping_cost=shipping_cost, free_over=free_over)})
