"""Formatters for displaying optimized shopping plans."""

from typing import Optional

from .optimizer import OptimizedPlan
from .shipping import ShippingConfig, NO_FREE_SHIPPING_THRESHOLD


def _pluralize(count: int, singular: str, plural: str) -> str:
    """Return singular or plural form based on count.

    Args:
        count: The number to check
        singular: Singular form (e.g., "item")
        plural: Plural form (e.g., "items")

    Returns:
        Appropriate form based on count
    """
    return singular if count == 1 else plural


def print_plan_text(plan: OptimizedPlan, shipping_config: Optional[ShippingConfig] = None) -> None:
    """Print optimized plan in text format (terminal-friendly).

    Args:
        plan: OptimizedPlan to display
        shipping_config: Optional shipping config to show thresholds
    """
    if not plan.carts:
        print("\nNo shopping plan generated.")
        return

    print("\n🛒 Optimized Shopping Plan")
    print()

    for cart in plan.carts:
        # Add free shipping threshold info if available
        threshold_info = ""
        if shipping_config:
            shipping_info = shipping_config.get_shipping_info(cart.site)
            if shipping_info.free_over < NO_FREE_SHIPPING_THRESHOLD:
                threshold_info = f" (Free shipping over €{shipping_info.free_over:.2f})"

        print(f"Store: {cart.site}{threshold_info}")
        print("─" * 60)

        for product_name, price_result in cart.items:
            price_str = f"€{price_result.price:.2f}"

            if price_result.price_per_100ml:
                value_str = f"(€{price_result.price_per_100ml:.2f}/100ml)"
                print(f"  {product_name:<42} {price_str:>8} {value_str}")
            else:
                print(f"  {product_name:<42} {price_str:>8}")

        if cart.free_shipping_eligible:
            print(f"  {'Shipping':<42} {'FREE':>8}")
        else:
            print(f"  {'Shipping':<42} €{cart.shipping_cost:>7.2f}")

        print("  " + "─" * 58)
        print(f"  {'Store Total':<42} €{cart.total:>7.2f}")
        print()

    print("═" * 60)
    print(f"Grand Total: €{plan.grand_total:.2f}")
    print(f"Total Shipping: €{plan.total_shipping:.2f}")
    item_word = _pluralize(plan.total_products, "item", "items")
    store_word = _pluralize(len(plan.carts), "store", "stores")
    print(f"Products: {plan.total_products} {item_word} from {len(plan.carts)} {store_word}")
    print("═" * 60)
    print()


def print_plan_markdown(plan: OptimizedPlan, shipping_config: Optional[ShippingConfig] = None) -> None:
    """Print optimized plan in markdown format.

    Args:
        plan: OptimizedPlan to display
        shipping_config: Optional shipping config to show thresholds
    """
    if not plan.carts:
        print("\nNo shopping plan generated.")
        return

    print("\n# 🛒 Optimized Shopping Plan\n")

    for cart in plan.carts:
        # Add free shipping threshold info if available
        threshold_info = ""
        if shipping_config:
            shipping_info = shipping_config.get_shipping_info(cart.site)
            if shipping_info.free_over < NO_FREE_SHIPPING_THRESHOLD:
                threshold_info = f" *(Free shipping over €{shipping_info.free_over:.2f})*"

        print(f"## Store: {cart.site}{threshold_info}\n")
        print("| Product | Price | Value |")
        print("|---------|-------|-------|")

        for product_name, price_result in cart.items:
            price_str = f"€{price_result.price:.2f}"

            if price_result.price_per_100ml:
                value_str = f"€{price_result.price_per_100ml:.2f}/100ml"
            else:
                value_str = "-"

            print(f"| {product_name} | {price_str} | {value_str} |")

        print()

        if cart.free_shipping_eligible:
            print("**Shipping:** FREE  ")
        else:
            print(f"**Shipping:** €{cart.shipping_cost:.2f}  ")

        print(f"**Store Total:** €{cart.total:.2f}\n")

    print("---\n")
    print(f"**Grand Total:** €{plan.grand_total:.2f}  ")
    print(f"**Total Shipping:** €{plan.total_shipping:.2f}  ")
    item_word = _pluralize(plan.total_products, "item", "items")
    store_word = _pluralize(len(plan.carts), "store", "stores")
    print(f"**Products:** {plan.total_products} {item_word} from {len(plan.carts)} {store_word}\n")
