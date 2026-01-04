"""Tests for optimized plan formatters (BDD style)."""

import io
import unittest
from contextlib import redirect_stdout

from utils.finder import PriceResult
from utils.optimizer import OptimizedPlan, StoreCart
from utils.plan_formatter import print_plan_markdown, print_plan_text
from utils.shipping import ShippingConfig, ShippingInfo


class TestTextFormatterEmptyPlan(unittest.TestCase):
    """Test text formatter with empty plans."""

    def test_when_no_carts_then_displays_no_plan_message(self):
        """
        Given an empty optimized plan
        When printing in text format
        Then should display "No shopping plan generated."
        """
        # Given
        plan = OptimizedPlan()

        # When
        output = io.StringIO()
        with redirect_stdout(output):
            print_plan_text(plan)

        # Then
        result = output.getvalue()
        self.assertIn("No shopping plan generated", result)


class TestTextFormatterSingleStore(unittest.TestCase):
    """Test text formatter with single store plans."""

    def test_when_single_store_single_product_then_displays_correctly(self):
        """
        Given a plan with one product from one store
        When printing in text format
        Then should display store name, product, price, shipping, and total
        """
        # Given
        cart = StoreCart(
            site="example.com",
            items=[("Test Product", PriceResult(price=25.00, url="https://example.com/test"))],
            subtotal=25.00,
            shipping_cost=3.99,
            total=28.99,
            free_shipping_eligible=False,
        )
        plan = OptimizedPlan(carts=[cart], grand_total=28.99, total_products=1, total_shipping=3.99)

        # When
        output = io.StringIO()
        with redirect_stdout(output):
            print_plan_text(plan)

        # Then
        result = output.getvalue()
        self.assertIn("example.com", result)
        self.assertIn("Test Product", result)
        self.assertIn("€25.00", result)
        self.assertIn("€3.99", result)
        self.assertIn("€28.99", result)
        self.assertIn("Grand Total: €28.99", result)

    def test_when_product_has_price_per_100ml_then_displays_value(self):
        """
        Given a product with price per 100ml information
        When printing in text format
        Then should display the price per 100ml alongside the price
        """
        # Given
        cart = StoreCart(
            site="example.com",
            items=[("Test Product", PriceResult(price=15.00, url="https://example.com/test", price_per_100ml=3.75))],
            subtotal=15.00,
            shipping_cost=0.0,
            total=15.00,
            free_shipping_eligible=True,
        )
        plan = OptimizedPlan(carts=[cart], grand_total=15.00, total_products=1, total_shipping=0.0)

        # When
        output = io.StringIO()
        with redirect_stdout(output):
            print_plan_text(plan)

        # Then
        result = output.getvalue()
        self.assertIn("€15.00", result)
        self.assertIn("€3.75/100ml", result)

    def test_when_free_shipping_eligible_then_displays_free(self):
        """
        Given a cart that qualifies for free shipping
        When printing in text format
        Then should display "FREE" for shipping
        """
        # Given
        cart = StoreCart(
            site="example.com",
            items=[("Test Product", PriceResult(price=55.00, url="https://example.com/test"))],
            subtotal=55.00,
            shipping_cost=0.0,
            total=55.00,
            free_shipping_eligible=True,
        )
        plan = OptimizedPlan(carts=[cart], grand_total=55.00, total_products=1, total_shipping=0.0)

        # When
        output = io.StringIO()
        with redirect_stdout(output):
            print_plan_text(plan)

        # Then
        result = output.getvalue()
        self.assertIn("FREE", result)

    def test_when_shipping_config_provided_then_displays_threshold(self):
        """
        Given a plan with shipping config
        When printing in text format
        Then should display free shipping threshold for each store
        """
        # Given
        cart = StoreCart(
            site="example.com",
            items=[("Test Product", PriceResult(price=25.00, url="https://example.com/test"))],
            subtotal=25.00,
            shipping_cost=3.99,
            total=28.99,
            free_shipping_eligible=False,
        )
        plan = OptimizedPlan(carts=[cart], grand_total=28.99, total_products=1, total_shipping=3.99)
        shipping_config = ShippingConfig(
            stores={"example.com": ShippingInfo(site="example.com", shipping_cost=3.99, free_over=50.00)}
        )

        # When
        output = io.StringIO()
        with redirect_stdout(output):
            print_plan_text(plan, shipping_config)

        # Then
        result = output.getvalue()
        self.assertIn("Free shipping over €50.00", result)


class TestTextFormatterMultipleStores(unittest.TestCase):
    """Test text formatter with multiple stores."""

    def test_when_multiple_stores_then_displays_all_stores(self):
        """
        Given a plan with products from multiple stores
        When printing in text format
        Then should display all stores with their products
        """
        # Given
        cart1 = StoreCart(
            site="store1.com",
            items=[("Product A", PriceResult(price=10.00, url="https://store1.com/a"))],
            subtotal=10.00,
            shipping_cost=3.50,
            total=13.50,
            free_shipping_eligible=False,
        )
        cart2 = StoreCart(
            site="store2.com",
            items=[("Product B", PriceResult(price=20.00, url="https://store2.com/b"))],
            subtotal=20.00,
            shipping_cost=4.00,
            total=24.00,
            free_shipping_eligible=False,
        )
        plan = OptimizedPlan(carts=[cart1, cart2], grand_total=37.50, total_products=2, total_shipping=7.50)

        # When
        output = io.StringIO()
        with redirect_stdout(output):
            print_plan_text(plan)

        # Then
        result = output.getvalue()
        self.assertIn("store1.com", result)
        self.assertIn("store2.com", result)
        self.assertIn("Product A", result)
        self.assertIn("Product B", result)
        self.assertIn("Grand Total: €37.50", result)
        self.assertIn("Total Shipping: €7.50", result)

    def test_when_multiple_products_per_store_then_displays_all(self):
        """
        Given a plan with multiple products from one store
        When printing in text format
        Then should display all products
        """
        # Given
        cart = StoreCart(
            site="example.com",
            items=[
                ("Product A", PriceResult(price=10.00, url="https://example.com/a")),
                ("Product B", PriceResult(price=15.00, url="https://example.com/b")),
                ("Product C", PriceResult(price=20.00, url="https://example.com/c")),
            ],
            subtotal=45.00,
            shipping_cost=3.99,
            total=48.99,
            free_shipping_eligible=False,
        )
        plan = OptimizedPlan(carts=[cart], grand_total=48.99, total_products=3, total_shipping=3.99)

        # When
        output = io.StringIO()
        with redirect_stdout(output):
            print_plan_text(plan)

        # Then
        result = output.getvalue()
        self.assertIn("Product A", result)
        self.assertIn("Product B", result)
        self.assertIn("Product C", result)
        self.assertIn("3 items from 1 store", result)


class TestMarkdownFormatterEmptyPlan(unittest.TestCase):
    """Test markdown formatter with empty plans."""

    def test_when_no_carts_then_displays_no_plan_message(self):
        """
        Given an empty optimized plan
        When printing in markdown format
        Then should display "No shopping plan generated."
        """
        # Given
        plan = OptimizedPlan()

        # When
        output = io.StringIO()
        with redirect_stdout(output):
            print_plan_markdown(plan)

        # Then
        result = output.getvalue()
        self.assertIn("No shopping plan generated", result)


class TestMarkdownFormatterSingleStore(unittest.TestCase):
    """Test markdown formatter with single store plans."""

    def test_when_single_store_then_displays_markdown_format(self):
        """
        Given a plan with one store
        When printing in markdown format
        Then should use proper markdown headers and tables
        """
        # Given
        cart = StoreCart(
            site="example.com",
            items=[("Test Product", PriceResult(price=25.00, url="https://example.com/test"))],
            subtotal=25.00,
            shipping_cost=3.99,
            total=28.99,
            free_shipping_eligible=False,
        )
        plan = OptimizedPlan(carts=[cart], grand_total=28.99, total_products=1, total_shipping=3.99)

        # When
        output = io.StringIO()
        with redirect_stdout(output):
            print_plan_markdown(plan)

        # Then
        result = output.getvalue()
        self.assertIn("# 🛒 Optimized Shopping Plan", result)
        self.assertIn("## Store: example.com", result)
        self.assertIn("| Product | Price | Value |", result)
        self.assertIn("|---------|-------|-------|", result)
        self.assertIn("**Shipping:**", result)
        self.assertIn("**Store Total:**", result)
        self.assertIn("**Grand Total:**", result)

    def test_when_product_has_value_then_displays_in_table(self):
        """
        Given a product with price per 100ml
        When printing in markdown format
        Then should display value in the table
        """
        # Given
        cart = StoreCart(
            site="example.com",
            items=[("Test Product", PriceResult(price=15.00, url="https://example.com/test", price_per_100ml=3.75))],
            subtotal=15.00,
            shipping_cost=0.0,
            total=15.00,
            free_shipping_eligible=True,
        )
        plan = OptimizedPlan(carts=[cart], grand_total=15.00, total_products=1, total_shipping=0.0)

        # When
        output = io.StringIO()
        with redirect_stdout(output):
            print_plan_markdown(plan)

        # Then
        result = output.getvalue()
        self.assertIn("€3.75/100ml", result)

    def test_when_no_value_then_displays_dash(self):
        """
        Given a product without price per 100ml
        When printing in markdown format
        Then should display "-" in value column
        """
        # Given
        cart = StoreCart(
            site="example.com",
            items=[("Test Product", PriceResult(price=15.00, url="https://example.com/test"))],
            subtotal=15.00,
            shipping_cost=0.0,
            total=15.00,
            free_shipping_eligible=True,
        )
        plan = OptimizedPlan(carts=[cart], grand_total=15.00, total_products=1, total_shipping=0.0)

        # When
        output = io.StringIO()
        with redirect_stdout(output):
            print_plan_markdown(plan)

        # Then
        result = output.getvalue()
        # Check that product row has a dash for value
        lines = result.split("\n")
        product_line = [line for line in lines if "Test Product" in line][0]
        self.assertIn("| - |", product_line)

    def test_when_free_shipping_then_displays_free_bold(self):
        """
        Given a cart with free shipping
        When printing in markdown format
        Then should display "**Shipping:** FREE"
        """
        # Given
        cart = StoreCart(
            site="example.com",
            items=[("Test Product", PriceResult(price=55.00, url="https://example.com/test"))],
            subtotal=55.00,
            shipping_cost=0.0,
            total=55.00,
            free_shipping_eligible=True,
        )
        plan = OptimizedPlan(carts=[cart], grand_total=55.00, total_products=1, total_shipping=0.0)

        # When
        output = io.StringIO()
        with redirect_stdout(output):
            print_plan_markdown(plan)

        # Then
        result = output.getvalue()
        self.assertIn("**Shipping:** FREE", result)

    def test_when_shipping_config_provided_then_displays_threshold_italic(self):
        """
        Given a plan with shipping config
        When printing in markdown format
        Then should display free shipping threshold in italics
        """
        # Given
        cart = StoreCart(
            site="example.com",
            items=[("Test Product", PriceResult(price=25.00, url="https://example.com/test"))],
            subtotal=25.00,
            shipping_cost=3.99,
            total=28.99,
            free_shipping_eligible=False,
        )
        plan = OptimizedPlan(carts=[cart], grand_total=28.99, total_products=1, total_shipping=3.99)
        shipping_config = ShippingConfig(
            stores={"example.com": ShippingInfo(site="example.com", shipping_cost=3.99, free_over=50.00)}
        )

        # When
        output = io.StringIO()
        with redirect_stdout(output):
            print_plan_markdown(plan, shipping_config)

        # Then
        result = output.getvalue()
        self.assertIn("*(Free shipping over €50.00)*", result)


class TestMarkdownFormatterMultipleStores(unittest.TestCase):
    """Test markdown formatter with multiple stores."""

    def test_when_multiple_stores_then_displays_all_with_headers(self):
        """
        Given a plan with multiple stores
        When printing in markdown format
        Then should display each store with separate headers
        """
        # Given
        cart1 = StoreCart(
            site="store1.com",
            items=[("Product A", PriceResult(price=10.00, url="https://store1.com/a"))],
            subtotal=10.00,
            shipping_cost=3.50,
            total=13.50,
            free_shipping_eligible=False,
        )
        cart2 = StoreCart(
            site="store2.com",
            items=[("Product B", PriceResult(price=20.00, url="https://store2.com/b"))],
            subtotal=20.00,
            shipping_cost=4.00,
            total=24.00,
            free_shipping_eligible=False,
        )
        plan = OptimizedPlan(carts=[cart1, cart2], grand_total=37.50, total_products=2, total_shipping=7.50)

        # When
        output = io.StringIO()
        with redirect_stdout(output):
            print_plan_markdown(plan)

        # Then
        result = output.getvalue()
        self.assertIn("## Store: store1.com", result)
        self.assertIn("## Store: store2.com", result)
        self.assertIn("**Total Shipping:** €7.50", result)
        self.assertIn("**Products:** 2 items from 2 stores", result)


class TestFormatterSummaryStatistics(unittest.TestCase):
    """Test that summary statistics are displayed correctly."""

    def test_when_plan_has_statistics_then_displays_in_text(self):
        """
        Given a plan with specific statistics
        When printing in text format
        Then should display total products and store count
        """
        # Given
        cart1 = StoreCart(
            site="store1.com",
            items=[("A", PriceResult(10.0, "url"))],
            subtotal=10,
            shipping_cost=0,
            total=10,
            free_shipping_eligible=True,
        )
        cart2 = StoreCart(
            site="store2.com",
            items=[("B", PriceResult(20.0, "url"))],
            subtotal=20,
            shipping_cost=0,
            total=20,
            free_shipping_eligible=True,
        )
        plan = OptimizedPlan(carts=[cart1, cart2], grand_total=30.0, total_products=2, total_shipping=0.0)

        # When
        output = io.StringIO()
        with redirect_stdout(output):
            print_plan_text(plan)

        # Then
        result = output.getvalue()
        self.assertIn("Products: 2 items from 2 stores", result)

    def test_when_plan_has_statistics_then_displays_in_markdown(self):
        """
        Given a plan with specific statistics
        When printing in markdown format
        Then should display total products and store count in bold
        """
        # Given
        cart = StoreCart(
            site="store.com",
            items=[("A", PriceResult(10.0, "url"))],
            subtotal=10,
            shipping_cost=0,
            total=10,
            free_shipping_eligible=True,
        )
        plan = OptimizedPlan(carts=[cart], grand_total=10.0, total_products=1, total_shipping=0.0)

        # When
        output = io.StringIO()
        with redirect_stdout(output):
            print_plan_markdown(plan)

        # Then
        result = output.getvalue()
        self.assertIn("**Products:** 1 item from 1 store", result)


if __name__ == "__main__":
    unittest.main()
