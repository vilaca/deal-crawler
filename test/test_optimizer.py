"""Tests for optimizer module."""

import unittest

from utils.finder import PriceResult
from utils.optimizer import (
    OptimizedPlan,
    StoreCart,
    _calculate_cart_costs,
    _extract_domain,
    optimize_shopping_plan,
)
from utils.shipping import ShippingConfig, ShippingInfo


class TestExtractDomain(unittest.TestCase):
    """Tests for _extract_domain function."""

    def test_extract_domain_simple(self):
        """Test extracting domain from simple URL."""
        self.assertEqual(_extract_domain("https://example.com/product"), "example.com")

    def test_extract_domain_with_www(self):
        """Test extracting domain removes www. prefix."""
        self.assertEqual(_extract_domain("https://www.example.com/product"), "example.com")

    def test_extract_domain_with_path(self):
        """Test extracting domain with complex path."""
        self.assertEqual(_extract_domain("https://example.com/path/to/product?id=123"), "example.com")


class TestCalculateCartCosts(unittest.TestCase):
    """Tests for _calculate_cart_costs function."""

    def test_calculate_costs_below_threshold(self):
        """Test cost calculation when subtotal is below free shipping threshold."""
        cart = StoreCart(site="example.com")
        cart.items = [
            ("Product A", PriceResult(price=10.00, url="https://example.com/a")),
            ("Product B", PriceResult(price=15.00, url="https://example.com/b")),
        ]

        shipping_info = ShippingInfo(site="example.com", shipping_cost=3.50, free_over=40.00)

        _calculate_cart_costs(cart, shipping_info)

        self.assertEqual(cart.subtotal, 25.00)
        self.assertEqual(cart.shipping_cost, 3.50)
        self.assertEqual(cart.total, 28.50)
        self.assertFalse(cart.free_shipping_eligible)

    def test_calculate_costs_at_threshold(self):
        """Test cost calculation when subtotal equals free shipping threshold."""
        cart = StoreCart(site="example.com")
        cart.items = [
            ("Product A", PriceResult(price=20.00, url="https://example.com/a")),
            ("Product B", PriceResult(price=20.00, url="https://example.com/b")),
        ]

        shipping_info = ShippingInfo(site="example.com", shipping_cost=3.50, free_over=40.00)

        _calculate_cart_costs(cart, shipping_info)

        self.assertEqual(cart.subtotal, 40.00)
        self.assertEqual(cart.shipping_cost, 0.0)
        self.assertEqual(cart.total, 40.00)
        self.assertTrue(cart.free_shipping_eligible)

    def test_calculate_costs_above_threshold(self):
        """Test cost calculation when subtotal exceeds free shipping threshold."""
        cart = StoreCart(site="example.com")
        cart.items = [
            ("Product A", PriceResult(price=30.00, url="https://example.com/a")),
            ("Product B", PriceResult(price=25.00, url="https://example.com/b")),
        ]

        shipping_info = ShippingInfo(site="example.com", shipping_cost=3.50, free_over=40.00)

        _calculate_cart_costs(cart, shipping_info)

        self.assertEqual(cart.subtotal, 55.00)
        self.assertEqual(cart.shipping_cost, 0.0)
        self.assertEqual(cart.total, 55.00)
        self.assertTrue(cart.free_shipping_eligible)

    def test_calculate_costs_empty_cart(self):
        """Test cost calculation with empty cart."""
        cart = StoreCart(site="example.com")
        shipping_info = ShippingInfo(site="example.com", shipping_cost=3.50, free_over=40.00)

        _calculate_cart_costs(cart, shipping_info)

        self.assertEqual(cart.subtotal, 0.0)
        self.assertEqual(cart.shipping_cost, 3.50)
        self.assertEqual(cart.total, 3.50)
        self.assertFalse(cart.free_shipping_eligible)


class TestOptimizeShoppingPlan(unittest.TestCase):
    """Tests for optimize_shopping_plan function."""

    def test_single_product_single_store(self):
        """Test optimization with one product at one store."""
        all_prices = {
            "Product A": [PriceResult(price=10.00, url="https://example.com/a")],
        }

        shipping_config = ShippingConfig(
            stores={"example.com": ShippingInfo(site="example.com", shipping_cost=3.50, free_over=40.00)}
        )

        plan = optimize_shopping_plan(all_prices, shipping_config)

        self.assertEqual(plan.total_products, 1)
        self.assertEqual(len(plan.carts), 1)
        self.assertEqual(plan.carts[0].site, "example.com")
        self.assertEqual(len(plan.carts[0].items), 1)
        self.assertEqual(plan.carts[0].subtotal, 10.00)
        self.assertEqual(plan.carts[0].shipping_cost, 3.50)
        self.assertEqual(plan.carts[0].total, 13.50)
        self.assertEqual(plan.grand_total, 13.50)
        self.assertEqual(plan.total_shipping, 3.50)

    def test_multiple_products_same_store(self):
        """Test optimization with multiple products from same store."""
        all_prices = {
            "Product A": [PriceResult(price=10.00, url="https://example.com/a")],
            "Product B": [PriceResult(price=15.00, url="https://example.com/b")],
            "Product C": [PriceResult(price=20.00, url="https://example.com/c")],
        }

        shipping_config = ShippingConfig(
            stores={"example.com": ShippingInfo(site="example.com", shipping_cost=3.50, free_over=40.00)}
        )

        plan = optimize_shopping_plan(all_prices, shipping_config)

        self.assertEqual(plan.total_products, 3)
        self.assertEqual(len(plan.carts), 1)
        self.assertEqual(plan.carts[0].site, "example.com")
        self.assertEqual(len(plan.carts[0].items), 3)
        self.assertEqual(plan.carts[0].subtotal, 45.00)
        # Should have free shipping since 45 > 40
        self.assertEqual(plan.carts[0].shipping_cost, 0.0)
        self.assertTrue(plan.carts[0].free_shipping_eligible)
        self.assertEqual(plan.carts[0].total, 45.00)
        self.assertEqual(plan.grand_total, 45.00)

    def test_multiple_products_consolidation_saves_money(self):
        """Test that consolidation-first optimizer prefers single store when cheaper."""
        all_prices = {
            "Product A": [
                PriceResult(price=10.00, url="https://store1.com/a"),
                PriceResult(price=12.00, url="https://store2.com/a"),
            ],
            "Product B": [
                PriceResult(price=25.00, url="https://store1.com/b"),
                PriceResult(price=20.00, url="https://store2.com/b"),
            ],
        }

        shipping_config = ShippingConfig(
            stores={
                "store1.com": ShippingInfo(site="store1.com", shipping_cost=3.50, free_over=40.00),
                "store2.com": ShippingInfo(site="store2.com", shipping_cost=4.00, free_over=50.00),
            }
        )

        plan = optimize_shopping_plan(all_prices, shipping_config)

        self.assertEqual(plan.total_products, 2)
        # Consolidation-first: buy both from store2 (€12 + €20 + €4.00 = €36.00)
        # This is cheaper than multi-store: (€10 + €3.50) + (€20 + €4.00) = €37.50
        self.assertEqual(len(plan.carts), 1)

        cart = plan.carts[0]
        self.assertEqual(cart.site, "store2.com")
        self.assertEqual(len(cart.items), 2)

        # Verify both products are in store2
        product_names = {item[0] for item in cart.items}
        self.assertIn("Product A", product_names)
        self.assertIn("Product B", product_names)

        # Verify costs
        self.assertEqual(cart.subtotal, 32.00)  # €12 + €20
        self.assertEqual(cart.shipping_cost, 4.00)
        self.assertEqual(cart.total, 36.00)

        # Verify plan totals
        self.assertEqual(plan.grand_total, 36.00)
        self.assertEqual(plan.total_shipping, 4.00)

    def test_empty_prices(self):
        """Test optimization with no products."""
        all_prices = {}
        shipping_config = ShippingConfig()

        plan = optimize_shopping_plan(all_prices, shipping_config)

        self.assertEqual(plan.total_products, 0)
        self.assertEqual(len(plan.carts), 0)
        self.assertEqual(plan.grand_total, 0.0)
        self.assertEqual(plan.total_shipping, 0.0)

    def test_product_with_no_prices(self):
        """Test optimization when product has no available prices."""
        all_prices = {
            "Product A": [],  # No prices found
            "Product B": [PriceResult(price=10.00, url="https://example.com/b")],
        }

        shipping_config = ShippingConfig(
            stores={"example.com": ShippingInfo(site="example.com", shipping_cost=3.50, free_over=40.00)}
        )

        plan = optimize_shopping_plan(all_prices, shipping_config)

        # Only Product B should be in plan
        self.assertEqual(plan.total_products, 1)
        self.assertEqual(len(plan.carts), 1)
        self.assertEqual(plan.carts[0].items[0][0], "Product B")

    def test_free_shipping_threshold_exactly_met(self):
        """Test that free shipping applies when threshold is exactly met."""
        all_prices = {
            "Product A": [PriceResult(price=40.00, url="https://example.com/a")],
        }

        shipping_config = ShippingConfig(
            stores={"example.com": ShippingInfo(site="example.com", shipping_cost=5.00, free_over=40.00)}
        )

        plan = optimize_shopping_plan(all_prices, shipping_config)

        self.assertEqual(plan.total_products, 1)
        self.assertEqual(plan.carts[0].subtotal, 40.00)
        self.assertEqual(plan.carts[0].shipping_cost, 0.0)
        self.assertTrue(plan.carts[0].free_shipping_eligible)
        self.assertEqual(plan.grand_total, 40.00)


class TestStoreCartDataclass(unittest.TestCase):
    """Tests for StoreCart dataclass."""

    def test_store_cart_creation(self):
        """Test creating a StoreCart object."""
        cart = StoreCart(site="example.com")
        self.assertEqual(cart.site, "example.com")
        self.assertEqual(cart.items, [])
        self.assertEqual(cart.subtotal, 0.0)
        self.assertEqual(cart.shipping_cost, 0.0)
        self.assertEqual(cart.total, 0.0)
        self.assertFalse(cart.free_shipping_eligible)


class TestOptimizedPlanDataclass(unittest.TestCase):
    """Tests for OptimizedPlan dataclass."""

    def test_optimized_plan_creation(self):
        """Test creating an OptimizedPlan object."""
        plan = OptimizedPlan()
        self.assertEqual(plan.carts, [])
        self.assertEqual(plan.grand_total, 0.0)
        self.assertEqual(plan.total_products, 0)
        self.assertEqual(plan.total_shipping, 0.0)


if __name__ == "__main__":
    unittest.main()
