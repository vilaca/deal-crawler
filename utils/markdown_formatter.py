"""Markdown output formatting utilities for Deal Crawler."""

from typing import Optional
from urllib.parse import urlparse

from .finder import SearchResults
from .optimizer import OptimizedPlan
from .shipping import ShippingConfig, NO_FREE_SHIPPING_THRESHOLD
from .string_utils import pluralize


def print_results_markdown(search_results: SearchResults) -> None:
    """Print search results in markdown format.

    Args:
        search_results: SearchResults object with prices
    """
    print("\n# 🛒 Best Prices\n")
    print("| Product | Price | Link |")
    print("|---------|-------|------|")

    for product_name, result in search_results.prices.items():
        if result:
            domain = urlparse(result.url).netloc.replace("www.", "")
            # Add price per 100ml if available
            if result.price_per_100ml:
                price_display = f"€{result.price:.2f}<br>_(€{result.price_per_100ml:.2f}/100ml)_"
            else:
                price_display = f"€{result.price:.2f}"
            print(f"| **{product_name}** | {price_display} | [🔗 {domain}]({result.url}) |")
        else:
            print(f"| **{product_name}** | _No prices found_ | - |")

    print("\n---\n")


def print_plan_markdown(plan: OptimizedPlan, shipping_config: Optional[ShippingConfig] = None) -> None:
    """Print optimized shopping plan in markdown format.

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
    item_word = pluralize(plan.total_products, "item", "items")
    store_word = pluralize(len(plan.carts), "store", "stores")
    print(f"**Products:** {plan.total_products} {item_word} from {len(plan.carts)} {store_word}\n")
