"""Tests for shopping plan optimizer using MILP (BDD style)."""

import unittest
from typing import Dict, List

from utils.finder import PriceResult
from utils.optimizer import _extract_base_product_name, optimize_shopping_plan
from utils.shipping import ShippingConfig, ShippingInfo


class TestBaseProductNameExtraction(unittest.TestCase):
    """Test extracting base product names without size information."""

    def test_when_product_has_size_in_ml_then_extracts_base_name(self):
        """
        Given a product name with size in ml
        When extracting the base name
        Then size suffix should be removed
        """
        # Given
        product_name = "Cerave Foaming Cleanser (236ml)"

        # When
        base_name = _extract_base_product_name(product_name)

        # Then
        self.assertEqual(base_name, "Cerave Foaming Cleanser")

    def test_when_product_has_multiple_units_then_extracts_base_name(self):
        """
        Given a product name with multiple units (e.g., 2x236ml)
        When extracting the base name
        Then size suffix should be removed
        """
        # Given
        product_name = "Medik8 Serum (2x30ml)"

        # When
        base_name = _extract_base_product_name(product_name)

        # Then
        self.assertEqual(base_name, "Medik8 Serum")

    def test_when_product_has_no_size_then_returns_unchanged(self):
        """
        Given a product name without size information
        When extracting the base name
        Then name should be returned unchanged
        """
        # Given
        product_name = "Cerave Moisturizing Cream"

        # When
        base_name = _extract_base_product_name(product_name)

        # Then
        self.assertEqual(base_name, "Cerave Moisturizing Cream")


class TestSingleProductOptimization(unittest.TestCase):
    """Test optimization with single product scenarios."""

    def test_when_single_product_single_store_then_selects_that_option(self):
        """
        Given one product available at one store
        When optimizing the shopping plan
        Then that product should be selected from that store
        """
        # Given
        all_prices = {"Product A": [PriceResult(price=10.00, url="https://store1.com/product-a", price_per_100ml=4.00)]}
        shipping_config = ShippingConfig(
            stores={"store1.com": ShippingInfo(site="store1.com", shipping_cost=3.99, free_over=50.00)}
        )

        # When
        plan = optimize_shopping_plan(all_prices, shipping_config)

        # Then
        self.assertEqual(len(plan.carts), 1)
        self.assertEqual(plan.carts[0].site, "store1.com")
        self.assertEqual(len(plan.carts[0].items), 1)
        self.assertEqual(plan.carts[0].items[0][0], "Product A")
        self.assertEqual(plan.carts[0].items[0][1].price, 10.00)
        self.assertEqual(plan.carts[0].shipping_cost, 3.99)
        self.assertEqual(plan.grand_total, 13.99)

    def test_when_single_product_multiple_stores_then_selects_cheapest(self):
        """
        Given one product available at multiple stores with different prices
        When optimizing the shopping plan
        Then the cheapest option should be selected
        """
        # Given
        all_prices = {
            "Product A": [
                PriceResult(price=15.00, url="https://store1.com/product-a"),
                PriceResult(price=12.00, url="https://store2.com/product-a"),
                PriceResult(price=18.00, url="https://store3.com/product-a"),
            ]
        }
        shipping_config = ShippingConfig(
            stores={
                "store1.com": ShippingInfo(site="store1.com", shipping_cost=3.99, free_over=50.00),
                "store2.com": ShippingInfo(site="store2.com", shipping_cost=3.99, free_over=50.00),
                "store3.com": ShippingInfo(site="store3.com", shipping_cost=3.99, free_over=50.00),
            }
        )

        # When
        plan = optimize_shopping_plan(all_prices, shipping_config)

        # Then
        self.assertEqual(len(plan.carts), 1)
        self.assertEqual(plan.carts[0].site, "store2.com")
        self.assertEqual(plan.carts[0].items[0][1].price, 12.00)
        self.assertEqual(plan.grand_total, 15.99)  # 12.00 + 3.99 shipping


class TestMultipleProductOptimization(unittest.TestCase):
    """Test optimization with multiple products."""

    def test_when_multiple_products_same_store_cheapest_then_consolidates(self):
        """
        Given multiple products, all cheapest at the same store
        When optimizing the shopping plan
        Then all products should be purchased from that store
        """
        # Given
        all_prices = {
            "Product A": [
                PriceResult(price=10.00, url="https://store1.com/product-a"),
                PriceResult(price=15.00, url="https://store2.com/product-a"),
            ],
            "Product B": [
                PriceResult(price=20.00, url="https://store1.com/product-b"),
                PriceResult(price=25.00, url="https://store2.com/product-b"),
            ],
        }
        shipping_config = ShippingConfig(
            stores={
                "store1.com": ShippingInfo(site="store1.com", shipping_cost=3.99, free_over=50.00),
                "store2.com": ShippingInfo(site="store2.com", shipping_cost=3.99, free_over=50.00),
            }
        )

        # When
        plan = optimize_shopping_plan(all_prices, shipping_config)

        # Then
        self.assertEqual(len(plan.carts), 1)
        self.assertEqual(plan.carts[0].site, "store1.com")
        self.assertEqual(len(plan.carts[0].items), 2)
        self.assertEqual(plan.carts[0].subtotal, 30.00)
        self.assertEqual(plan.grand_total, 33.99)  # 30.00 + 3.99 shipping

    def test_when_products_split_across_stores_then_minimizes_total_cost(self):
        """
        Given products where individual cheapest prices are at different stores
        When optimizing the shopping plan
        Then should minimize total cost including shipping
        """
        # Given
        all_prices = {
            "Product A": [
                PriceResult(price=10.00, url="https://store1.com/product-a"),
                PriceResult(price=11.00, url="https://store2.com/product-a"),
            ],
            "Product B": [
                PriceResult(price=25.00, url="https://store1.com/product-b"),
                PriceResult(price=20.00, url="https://store2.com/product-b"),
            ],
        }
        shipping_config = ShippingConfig(
            stores={
                "store1.com": ShippingInfo(site="store1.com", shipping_cost=3.99, free_over=50.00),
                "store2.com": ShippingInfo(site="store2.com", shipping_cost=3.99, free_over=50.00),
            }
        )

        # When
        plan = optimize_shopping_plan(all_prices, shipping_config)

        # Then
        # Buying separately: store1 (10) + store2 (20) = 30 + 7.98 shipping = 37.98
        # Buying together from store1: 35.00 + 3.99 shipping = 38.99
        # Buying together from store2: 31.00 + 3.99 shipping = 34.99 (best)
        self.assertEqual(len(plan.carts), 1)
        self.assertEqual(plan.carts[0].site, "store2.com")
        self.assertEqual(plan.grand_total, 34.99)


class TestFreeShippingOptimization(unittest.TestCase):
    """Test optimization considering free shipping thresholds."""

    def test_when_consolidation_triggers_free_shipping_then_consolidates(self):
        """
        Given products where consolidation reaches free shipping threshold
        When optimizing the shopping plan
        Then products should be consolidated to save on shipping
        """
        # Given
        all_prices = {
            "Product A": [
                PriceResult(price=7.00, url="https://store1.com/product-a"),
                PriceResult(price=7.50, url="https://store2.com/product-a"),
            ],
            "Product B": [
                PriceResult(price=45.00, url="https://store1.com/product-b"),
                PriceResult(price=45.00, url="https://store2.com/product-b"),
            ],
        }
        shipping_config = ShippingConfig(
            stores={
                "store1.com": ShippingInfo(site="store1.com", shipping_cost=3.50, free_over=50.00),
                "store2.com": ShippingInfo(site="store2.com", shipping_cost=3.00, free_over=50.00),
            }
        )

        # When
        plan = optimize_shopping_plan(all_prices, shipping_config)

        # Then
        # Option 1: Split - store1 (7.00) + 3.50 ship + store2 (45.00) + 3.00 ship = 58.50
        # Option 2: store1 both (52.00) + FREE shipping = 52.00 (best)
        # Option 3: store2 both (52.50) + FREE shipping = 52.50
        self.assertEqual(len(plan.carts), 1)
        self.assertEqual(plan.carts[0].site, "store1.com")
        self.assertEqual(plan.carts[0].subtotal, 52.00)
        self.assertEqual(plan.carts[0].shipping_cost, 0.0)
        self.assertTrue(plan.carts[0].free_shipping_eligible)
        self.assertEqual(plan.grand_total, 52.00)
        self.assertEqual(plan.total_shipping, 0.0)

    def test_when_just_above_threshold_then_qualifies_for_free_shipping(self):
        """
        Given a cart subtotal just above the free shipping threshold
        When optimizing the shopping plan
        Then free shipping should be applied
        """
        # Given
        all_prices = {
            "Product A": [
                PriceResult(price=50.01, url="https://store1.com/product-a"),
            ]
        }
        shipping_config = ShippingConfig(
            stores={
                "store1.com": ShippingInfo(site="store1.com", shipping_cost=5.00, free_over=50.00),
            }
        )

        # When
        plan = optimize_shopping_plan(all_prices, shipping_config)

        # Then
        self.assertEqual(plan.carts[0].subtotal, 50.01)
        self.assertEqual(plan.carts[0].shipping_cost, 0.0)
        self.assertTrue(plan.carts[0].free_shipping_eligible)

    def test_when_just_below_threshold_then_pays_shipping(self):
        """
        Given a cart subtotal just below the free shipping threshold
        When optimizing the shopping plan
        Then shipping cost should be applied
        """
        # Given
        all_prices = {
            "Product A": [
                PriceResult(price=49.99, url="https://store1.com/product-a"),
            ]
        }
        shipping_config = ShippingConfig(
            stores={
                "store1.com": ShippingInfo(site="store1.com", shipping_cost=5.00, free_over=50.00),
            }
        )

        # When
        plan = optimize_shopping_plan(all_prices, shipping_config)

        # Then
        self.assertEqual(plan.carts[0].subtotal, 49.99)
        self.assertEqual(plan.carts[0].shipping_cost, 5.00)
        self.assertFalse(plan.carts[0].free_shipping_eligible)


class TestProductFamilyOptimization(unittest.TestCase):
    """Test optimization with product families (multiple sizes)."""

    def test_when_multiple_sizes_available_then_selects_one_size(self):
        """
        Given a product available in multiple sizes
        When optimizing the shopping plan
        Then exactly one size should be selected
        """
        # Given
        all_prices = {
            "Cerave Cleanser (236ml)": [
                PriceResult(price=10.00, url="https://store1.com/small", price_per_100ml=4.24),
            ],
            "Cerave Cleanser (473ml)": [
                PriceResult(price=18.00, url="https://store1.com/medium", price_per_100ml=3.80),
            ],
            "Cerave Cleanser (1000ml)": [
                PriceResult(price=35.00, url="https://store1.com/large", price_per_100ml=3.50),
            ],
        }
        shipping_config = ShippingConfig(
            stores={
                "store1.com": ShippingInfo(site="store1.com", shipping_cost=3.99, free_over=50.00),
            }
        )

        # When
        plan = optimize_shopping_plan(all_prices, shipping_config)

        # Then
        self.assertEqual(len(plan.carts), 1)
        self.assertEqual(len(plan.carts[0].items), 1)  # Only one size selected
        # Should select cheapest total cost: 236ml (10.00 + 3.99 = 13.99)
        self.assertEqual(plan.carts[0].items[0][0], "Cerave Cleanser (236ml)")
        self.assertEqual(plan.grand_total, 13.99)

    def test_when_multiple_products_with_sizes_then_selects_optimal_combination(self):
        """
        Given multiple products each available in multiple sizes
        When optimizing the shopping plan
        Then should select one size per product with optimal total cost
        """
        # Given
        all_prices = {
            "Product A (100ml)": [
                PriceResult(price=10.00, url="https://store1.com/a-small"),
            ],
            "Product A (200ml)": [
                PriceResult(price=15.00, url="https://store1.com/a-large"),
            ],
            "Product B (50ml)": [
                PriceResult(price=20.00, url="https://store1.com/b-small"),
            ],
            "Product B (100ml)": [
                PriceResult(price=30.00, url="https://store1.com/b-large"),
            ],
        }
        shipping_config = ShippingConfig(
            stores={
                "store1.com": ShippingInfo(site="store1.com", shipping_cost=3.99, free_over=50.00),
            }
        )

        # When
        plan = optimize_shopping_plan(all_prices, shipping_config)

        # Then
        self.assertEqual(len(plan.carts), 1)
        self.assertEqual(len(plan.carts[0].items), 2)  # One of each product
        product_names = [item[0] for item in plan.carts[0].items]
        # Should have one Product A and one Product B
        self.assertTrue(any("Product A" in name for name in product_names))
        self.assertTrue(any("Product B" in name for name in product_names))

    def test_when_larger_size_triggers_free_shipping_then_selects_larger_size(self):
        """
        Given a product in multiple sizes where larger size triggers free shipping
        When optimizing the shopping plan
        Then larger size should be selected if total cost is lower
        """
        # Given
        all_prices = {
            "Product X (100ml)": [
                PriceResult(price=30.00, url="https://store1.com/small"),
            ],
            "Product X (500ml)": [
                PriceResult(price=52.00, url="https://store1.com/large"),
            ],
        }
        shipping_config = ShippingConfig(
            stores={
                "store1.com": ShippingInfo(site="store1.com", shipping_cost=5.00, free_over=50.00),
            }
        )

        # When
        plan = optimize_shopping_plan(all_prices, shipping_config)

        # Then
        # Small: 30.00 + 5.00 shipping = 35.00
        # Large: 52.00 + 0.00 shipping = 52.00
        # Should select small (cheaper total)
        self.assertEqual(plan.carts[0].items[0][0], "Product X (100ml)")
        self.assertEqual(plan.grand_total, 35.00)


class TestValueOptimization(unittest.TestCase):
    """Test optimization in value mode (price per 100ml)."""

    def test_when_value_mode_then_prefers_better_price_per_ml(self):
        """
        Given a product in small and large sizes where large has better value
        When optimizing in value mode
        Then should select the size with better price per 100ml
        """
        # Given
        all_prices = {
            "Product A (100ml)": [
                PriceResult(price=30.00, url="https://store1.com/small", price_per_100ml=30.00),
            ],
            "Product A (500ml)": [
                PriceResult(price=100.00, url="https://store1.com/large", price_per_100ml=20.00),
            ],
        }
        shipping_config = ShippingConfig(
            stores={
                "store1.com": ShippingInfo(site="store1.com", shipping_cost=5.00, free_over=200.00),
            }
        )

        # When
        plan = optimize_shopping_plan(all_prices, shipping_config, optimize_for_value=True)

        # Then
        # Cost mode would choose: small (€30 + €5 = €35)
        # Value mode should choose: large (€20/100ml vs €30/100ml)
        self.assertEqual(len(plan.carts[0].items), 1)
        self.assertEqual(plan.carts[0].items[0][0], "Product A (500ml)")
        self.assertEqual(plan.carts[0].items[0][1].price_per_100ml, 20.00)

    def test_when_cost_mode_then_prefers_lowest_total_cost(self):
        """
        Given the same product sizes
        When optimizing in cost mode (default)
        Then should select the size with lowest total cost
        """
        # Given
        all_prices = {
            "Product A (100ml)": [
                PriceResult(price=30.00, url="https://store1.com/small", price_per_100ml=30.00),
            ],
            "Product A (500ml)": [
                PriceResult(price=100.00, url="https://store1.com/large", price_per_100ml=20.00),
            ],
        }
        shipping_config = ShippingConfig(
            stores={
                "store1.com": ShippingInfo(site="store1.com", shipping_cost=5.00, free_over=200.00),
            }
        )

        # When
        plan = optimize_shopping_plan(all_prices, shipping_config, optimize_for_value=False)

        # Then
        # Should choose small size (€30 + €5 = €35 vs €100 + €5 = €105)
        self.assertEqual(plan.carts[0].items[0][0], "Product A (100ml)")
        self.assertEqual(plan.grand_total, 35.00)

    def test_when_value_mode_with_multiple_stores_then_considers_value_and_shipping(self):
        """
        Given a product at multiple stores with different sizes and shipping costs
        When optimizing in value mode
        Then should balance price per ml with shipping costs
        """
        # Given
        all_prices = {
            "Product X (200ml)": [
                PriceResult(price=40.00, url="https://store1.com/small", price_per_100ml=20.00),
                PriceResult(price=42.00, url="https://store2.com/small", price_per_100ml=21.00),
            ],
            "Product X (500ml)": [
                PriceResult(price=80.00, url="https://store1.com/large", price_per_100ml=16.00),
                PriceResult(price=75.00, url="https://store2.com/large", price_per_100ml=15.00),
            ],
        }
        shipping_config = ShippingConfig(
            stores={
                "store1.com": ShippingInfo(site="store1.com", shipping_cost=5.00, free_over=200.00),
                "store2.com": ShippingInfo(site="store2.com", shipping_cost=3.00, free_over=200.00),
            }
        )

        # When
        plan = optimize_shopping_plan(all_prices, shipping_config, optimize_for_value=True)

        # Then
        # Should choose store2 large (best value: €15/100ml)
        self.assertEqual(plan.carts[0].site, "store2.com")
        self.assertEqual(plan.carts[0].items[0][0], "Product X (500ml)")
        self.assertEqual(plan.carts[0].items[0][1].price_per_100ml, 15.00)

    def test_when_value_mode_with_free_shipping_then_considers_both(self):
        """
        Given sizes where larger triggers free shipping and has better value
        When optimizing in value mode
        Then should select size with best value considering free shipping
        """
        # Given
        all_prices = {
            "Product Y (100ml)": [
                PriceResult(price=35.00, url="https://store1.com/small", price_per_100ml=35.00),
            ],
            "Product Y (500ml)": [
                PriceResult(price=55.00, url="https://store1.com/large", price_per_100ml=11.00),
            ],
        }
        shipping_config = ShippingConfig(
            stores={
                "store1.com": ShippingInfo(site="store1.com", shipping_cost=10.00, free_over=50.00),
            }
        )

        # When
        plan = optimize_shopping_plan(all_prices, shipping_config, optimize_for_value=True)

        # Then
        # Large: €55 + FREE = €55 total, €11/100ml (excellent value)
        # Small: €35 + €10 = €45 total, €35/100ml (worse value)
        # Should choose large for better value
        self.assertEqual(plan.carts[0].items[0][0], "Product Y (500ml)")
        self.assertTrue(plan.carts[0].free_shipping_eligible)

    def test_when_value_mode_without_price_per_ml_then_falls_back_to_price(self):
        """
        Given products without price_per_100ml information
        When optimizing in value mode
        Then should fall back to using absolute price
        """
        # Given
        all_prices = {
            "Product Z": [
                PriceResult(price=20.00, url="https://store1.com/product-z"),
                PriceResult(price=25.00, url="https://store2.com/product-z"),
            ]
        }
        shipping_config = ShippingConfig(
            stores={
                "store1.com": ShippingInfo(site="store1.com", shipping_cost=5.00, free_over=100.00),
                "store2.com": ShippingInfo(site="store2.com", shipping_cost=3.00, free_over=100.00),
            }
        )

        # When
        plan = optimize_shopping_plan(all_prices, shipping_config, optimize_for_value=True)

        # Then
        # Should choose store1 (€20 + €5 = €25 vs €25 + €3 = €28)
        self.assertEqual(plan.carts[0].site, "store1.com")
        self.assertEqual(plan.grand_total, 25.00)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling."""

    def test_when_no_products_then_returns_empty_plan(self):
        """
        Given an empty product list
        When optimizing the shopping plan
        Then an empty plan should be returned
        """
        # Given
        all_prices: Dict[str, List[PriceResult]] = {}
        shipping_config = ShippingConfig(stores={})

        # When
        plan = optimize_shopping_plan(all_prices, shipping_config)

        # Then
        self.assertEqual(len(plan.carts), 0)
        self.assertEqual(plan.grand_total, 0.0)
        self.assertEqual(plan.total_products, 0)
        self.assertEqual(plan.total_shipping, 0.0)

    def test_when_no_prices_for_products_then_returns_empty_plan(self):
        """
        Given products with empty price lists
        When optimizing the shopping plan
        Then an empty plan should be returned
        """
        # Given
        all_prices: Dict[str, List[PriceResult]] = {
            "Product A": [],
            "Product B": [],
        }
        shipping_config = ShippingConfig(stores={})

        # When
        plan = optimize_shopping_plan(all_prices, shipping_config)

        # Then
        self.assertEqual(len(plan.carts), 0)
        self.assertEqual(plan.grand_total, 0.0)

    def test_when_store_not_in_config_then_uses_default_shipping(self):
        """
        Given a product from a store not in shipping config
        When optimizing the shopping plan
        Then default shipping costs should be used
        """
        # Given
        all_prices = {
            "Product A": [
                PriceResult(price=20.00, url="https://unknown-store.com/product-a"),
            ]
        }
        shipping_config = ShippingConfig(stores={})  # Empty config

        # When
        plan = optimize_shopping_plan(all_prices, shipping_config)

        # Then
        self.assertEqual(len(plan.carts), 1)
        self.assertEqual(plan.carts[0].site, "unknown-store.com")
        self.assertEqual(plan.carts[0].shipping_cost, 3.99)  # Default
        self.assertAlmostEqual(plan.grand_total, 23.99, places=2)


class TestPlanSummaryStatistics(unittest.TestCase):
    """Test that plan summary statistics are calculated correctly."""

    def test_when_plan_created_then_statistics_accurate(self):
        """
        Given a shopping plan with multiple stores and products
        When the plan is created
        Then all summary statistics should be accurate
        """
        # Given
        all_prices = {
            "Product A": [
                PriceResult(price=10.00, url="https://store1.com/product-a"),
                PriceResult(price=12.00, url="https://store2.com/product-a"),
            ],
            "Product B": [
                PriceResult(price=20.00, url="https://store1.com/product-b"),
                PriceResult(price=18.00, url="https://store2.com/product-b"),
            ],
            "Product C": [
                PriceResult(price=15.00, url="https://store2.com/product-c"),
            ],
        }
        shipping_config = ShippingConfig(
            stores={
                "store1.com": ShippingInfo(site="store1.com", shipping_cost=3.50, free_over=50.00),
                "store2.com": ShippingInfo(site="store2.com", shipping_cost=4.00, free_over=50.00),
            }
        )

        # When
        plan = optimize_shopping_plan(all_prices, shipping_config)

        # Then
        self.assertEqual(plan.total_products, 3)
        self.assertGreater(len(plan.carts), 0)

        # Verify grand total equals sum of cart totals
        calculated_total = sum(cart.total for cart in plan.carts)
        self.assertAlmostEqual(plan.grand_total, calculated_total, places=2)

        # Verify total shipping equals sum of shipping costs
        calculated_shipping = sum(cart.shipping_cost for cart in plan.carts)
        self.assertAlmostEqual(plan.total_shipping, calculated_shipping, places=2)


if __name__ == "__main__":
    unittest.main()
