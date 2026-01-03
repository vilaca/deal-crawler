"""Formatting utilities for optimized shopping plans."""

from .optimizer import OptimizedPlan


def print_plan_text(plan: OptimizedPlan) -> None:
    """Print optimized plan in text format for terminal.

    Args:
        plan: OptimizedPlan to display
    """
    print("\n🛒 Optimized Shopping Plan")

    if not plan.carts:
        print("\nNo products in plan")
        return

    # Print each store cart
    for cart in plan.carts:
        print(f"\nStore: {cart.site}")
        print("─" * 60)

        # Calculate max product name length for alignment
        max_name_len = max(len(name) for name, _ in cart.items) if cart.items else 0

        # Print items
        for product_name, price_result in cart.items:
            price_str = f"€{price_result.price:.2f}"
            print(f"  {product_name:<{max_name_len}}  {price_str:>8}")

        # Print subtotals separator
        print(f"  {'':<{max_name_len}}  {'─' * 8}")

        # Print subtotal
        subtotal_str = f"€{cart.subtotal:.2f}"
        print(f"  {'Subtotal':<{max_name_len}}  {subtotal_str:>8}")

        # Print shipping
        if cart.free_shipping_eligible:
            shipping_str = f"FREE (over €{cart.items[0][1].price if cart.items else 0:.2f})"
            # Get actual free_over value from shipping info (we'll show a placeholder for now)
            shipping_str = "FREE"
        else:
            shipping_str = f"€{cart.shipping_cost:.2f}"
        print(f"  {'Shipping':<{max_name_len}}  {shipping_str:>8}")

        # Print store total separator
        print("  " + "─" * (max_name_len + 10))

        # Print store total
        total_str = f"€{cart.total:.2f}"
        print(f"  {'Store Total':<{max_name_len}}  {total_str:>8}")

    # Print grand total section
    print("\n" + "═" * 60)
    print(f"Grand Total: €{plan.grand_total:.2f}")
    print(f"Total Shipping: €{plan.total_shipping:.2f}")

    stores_count = len(plan.carts)
    stores_text = "store" if stores_count == 1 else "stores"
    products_text = "item" if plan.total_products == 1 else "items"
    print(f"Products: {plan.total_products} {products_text} from {stores_count} {stores_text}")
    print("═" * 60)


def print_plan_markdown(plan: OptimizedPlan) -> None:
    """Print optimized plan in markdown format.

    Args:
        plan: OptimizedPlan to display
    """
    print("\n# 🛒 Optimized Shopping Plan\n")

    if not plan.carts:
        print("No products in plan\n")
        return

    # Print each store cart
    for cart in plan.carts:
        print(f"## {cart.site}\n")
        print("| Product | Price |")
        print("|---------|-------|")

        # Print items
        for product_name, price_result in cart.items:
            print(f"| {product_name} | €{price_result.price:.2f} |")

        # Print subtotal
        print(f"| **Subtotal** | **€{cart.subtotal:.2f}** |")

        # Print shipping
        if cart.free_shipping_eligible:
            print("| Shipping | ✅ **FREE** |")
        else:
            print(f"| Shipping | €{cart.shipping_cost:.2f} |")

        # Print store total
        print(f"| **Store Total** | **€{cart.total:.2f}** |")
        print()

    # Print grand total section
    print("---\n")
    print(f"**Grand Total:** €{plan.grand_total:.2f}  ")
    print(f"**Total Shipping:** €{plan.total_shipping:.2f}  ")

    stores_count = len(plan.carts)
    stores_text = "store" if stores_count == 1 else "stores"
    products_text = "item" if plan.total_products == 1 else "items"
    print(f"**Products:** {plan.total_products} {products_text} from {stores_count} {stores_text}")
