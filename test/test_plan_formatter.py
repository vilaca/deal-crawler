"""Tests for plan formatter module."""

import io
import sys
import unittest
from contextlib import redirect_stdout

from utils.finder import PriceResult
from utils.optimizer import OptimizedPlan, StoreCart
from utils.plan_formatter import print_plan_markdown, print_plan_text


class TestPrintPlanText(unittest.TestCase):
    """Tests for print_plan_text function."""

    def test_print_single_store(self):
        """Test printing plan with single store."""
        plan = OptimizedPlan()
        cart = StoreCart(site="example.com")
        cart.items = [
            ("Product A", PriceResult(price=10.00, url="https://example.com/a")),
            ("Product B", PriceResult(price=15.00, url="https://example.com/b")),
        ]
        cart.subtotal = 25.00
        cart.shipping_cost = 3.50
        cart.total = 28.50
        cart.free_shipping_eligible = False

        plan.carts = [cart]
        plan.total_products = 2
        plan.grand_total = 28.50
        plan.total_shipping = 3.50

        # Capture output
        output = io.StringIO()
        with redirect_stdout(output):
            print_plan_text(plan)

        result = output.getvalue()

        # Verify key elements are present
        self.assertIn("🛒 Optimized Shopping Plan", result)
        self.assertIn("Store: example.com", result)
        self.assertIn("Product A", result)
        self.assertIn("Product B", result)
        self.assertIn("€10.00", result)
        self.assertIn("€15.00", result)
        self.assertIn("Subtotal", result)
        self.assertIn("€25.00", result)
        self.assertIn("Shipping", result)
        self.assertIn("€3.50", result)
        self.assertIn("Store Total", result)
        self.assertIn("€28.50", result)
        self.assertIn("Grand Total: €28.50", result)
        self.assertIn("Total Shipping: €3.50", result)
        self.assertIn("2 items from 1 store", result)

    def test_print_multiple_stores(self):
        """Test printing plan with multiple stores."""
        plan = OptimizedPlan()

        # Store 1
        cart1 = StoreCart(site="store1.com")
        cart1.items = [("Product A", PriceResult(price=10.00, url="https://store1.com/a"))]
        cart1.subtotal = 10.00
        cart1.shipping_cost = 3.50
        cart1.total = 13.50
        cart1.free_shipping_eligible = False

        # Store 2
        cart2 = StoreCart(site="store2.com")
        cart2.items = [("Product B", PriceResult(price=20.00, url="https://store2.com/b"))]
        cart2.subtotal = 20.00
        cart2.shipping_cost = 4.00
        cart2.total = 24.00
        cart2.free_shipping_eligible = False

        plan.carts = [cart1, cart2]
        plan.total_products = 2
        plan.grand_total = 37.50
        plan.total_shipping = 7.50

        # Capture output
        output = io.StringIO()
        with redirect_stdout(output):
            print_plan_text(plan)

        result = output.getvalue()

        # Verify both stores are present
        self.assertIn("Store: store1.com", result)
        self.assertIn("Store: store2.com", result)
        self.assertIn("Product A", result)
        self.assertIn("Product B", result)
        self.assertIn("Grand Total: €37.50", result)
        self.assertIn("2 items from 2 stores", result)

    def test_print_empty_plan(self):
        """Test printing empty plan."""
        plan = OptimizedPlan()

        # Capture output
        output = io.StringIO()
        with redirect_stdout(output):
            print_plan_text(plan)

        result = output.getvalue()

        self.assertIn("🛒 Optimized Shopping Plan", result)
        self.assertIn("No products in plan", result)

    def test_print_free_shipping(self):
        """Test printing plan with free shipping."""
        plan = OptimizedPlan()
        cart = StoreCart(site="example.com")
        cart.items = [
            ("Product A", PriceResult(price=50.00, url="https://example.com/a")),
        ]
        cart.subtotal = 50.00
        cart.shipping_cost = 0.0
        cart.total = 50.00
        cart.free_shipping_eligible = True

        plan.carts = [cart]
        plan.total_products = 1
        plan.grand_total = 50.00
        plan.total_shipping = 0.0

        # Capture output
        output = io.StringIO()
        with redirect_stdout(output):
            print_plan_text(plan)

        result = output.getvalue()

        self.assertIn("FREE", result)
        self.assertIn("Total Shipping: €0.00", result)


class TestPrintPlanMarkdown(unittest.TestCase):
    """Tests for print_plan_markdown function."""

    def test_print_single_store_markdown(self):
        """Test printing plan with single store in markdown format."""
        plan = OptimizedPlan()
        cart = StoreCart(site="example.com")
        cart.items = [
            ("Product A", PriceResult(price=10.00, url="https://example.com/a")),
            ("Product B", PriceResult(price=15.00, url="https://example.com/b")),
        ]
        cart.subtotal = 25.00
        cart.shipping_cost = 3.50
        cart.total = 28.50
        cart.free_shipping_eligible = False

        plan.carts = [cart]
        plan.total_products = 2
        plan.grand_total = 28.50
        plan.total_shipping = 3.50

        # Capture output
        output = io.StringIO()
        with redirect_stdout(output):
            print_plan_markdown(plan)

        result = output.getvalue()

        # Verify markdown format
        self.assertIn("# 🛒 Optimized Shopping Plan", result)
        self.assertIn("## example.com", result)
        self.assertIn("| Product | Price |", result)
        self.assertIn("| Product A | €10.00 |", result)
        self.assertIn("| Product B | €15.00 |", result)
        self.assertIn("| **Subtotal** | **€25.00** |", result)
        self.assertIn("| Shipping | €3.50 |", result)
        self.assertIn("| **Store Total** | **€28.50** |", result)
        self.assertIn("**Grand Total:** €28.50", result)
        self.assertIn("**Total Shipping:** €3.50", result)
        self.assertIn("**Products:** 2 items from 1 store", result)

    def test_print_multiple_stores_markdown(self):
        """Test printing plan with multiple stores in markdown format."""
        plan = OptimizedPlan()

        # Store 1
        cart1 = StoreCart(site="store1.com")
        cart1.items = [("Product A", PriceResult(price=10.00, url="https://store1.com/a"))]
        cart1.subtotal = 10.00
        cart1.shipping_cost = 3.50
        cart1.total = 13.50
        cart1.free_shipping_eligible = False

        # Store 2
        cart2 = StoreCart(site="store2.com")
        cart2.items = [("Product B", PriceResult(price=20.00, url="https://store2.com/b"))]
        cart2.subtotal = 20.00
        cart2.shipping_cost = 4.00
        cart2.total = 24.00
        cart2.free_shipping_eligible = False

        plan.carts = [cart1, cart2]
        plan.total_products = 2
        plan.grand_total = 37.50
        plan.total_shipping = 7.50

        # Capture output
        output = io.StringIO()
        with redirect_stdout(output):
            print_plan_markdown(plan)

        result = output.getvalue()

        # Verify both stores are present
        self.assertIn("## store1.com", result)
        self.assertIn("## store2.com", result)
        self.assertIn("| Product A | €10.00 |", result)
        self.assertIn("| Product B | €20.00 |", result)
        self.assertIn("**Grand Total:** €37.50", result)
        self.assertIn("**Products:** 2 items from 2 stores", result)

    def test_print_empty_plan_markdown(self):
        """Test printing empty plan in markdown format."""
        plan = OptimizedPlan()

        # Capture output
        output = io.StringIO()
        with redirect_stdout(output):
            print_plan_markdown(plan)

        result = output.getvalue()

        self.assertIn("# 🛒 Optimized Shopping Plan", result)
        self.assertIn("No products in plan", result)

    def test_print_free_shipping_markdown(self):
        """Test printing plan with free shipping in markdown format."""
        plan = OptimizedPlan()
        cart = StoreCart(site="example.com")
        cart.items = [
            ("Product A", PriceResult(price=50.00, url="https://example.com/a")),
        ]
        cart.subtotal = 50.00
        cart.shipping_cost = 0.0
        cart.total = 50.00
        cart.free_shipping_eligible = True

        plan.carts = [cart]
        plan.total_products = 1
        plan.grand_total = 50.00
        plan.total_shipping = 0.0

        # Capture output
        output = io.StringIO()
        with redirect_stdout(output):
            print_plan_markdown(plan)

        result = output.getvalue()

        self.assertIn("| Shipping | ✅ **FREE** |", result)
        self.assertIn("**Total Shipping:** €0.00", result)


if __name__ == "__main__":
    unittest.main()
