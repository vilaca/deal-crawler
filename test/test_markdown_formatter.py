"""Tests for utils.markdown_formatter module."""

import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from utils.finder import PriceResult, SearchResults
from utils.markdown_formatter import print_results_markdown, print_plan_markdown
from test.test_formatter_fixtures import (
    create_empty_plan,
    create_single_product_cart,
    create_plan_with_single_cart,
    create_plan_with_multiple_carts,
    create_shipping_config,
)


class TestPrintResultsMarkdown(unittest.TestCase):
    """Test markdown format output function."""

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_print_results_markdown_with_prices(self, mock_stdout):
        """Test markdown output with products that have prices."""
        results = SearchResults()
        results.prices = {
            "Product A": PriceResult(price=29.99, url="https://www.example.com/product-a"),
            "Product B": PriceResult(price=15.50, url="https://store.com/product-b"),
        }

        print_results_markdown(results)

        output = mock_stdout.getvalue()
        # Check header
        self.assertIn("# 🛒 Best Prices", output)

        # Check table header
        self.assertIn("| Product | Price | Link |", output)
        self.assertIn("|---------|-------|------|", output)

        # Check Product A
        self.assertIn("| **Product A** | €29.99 |", output)
        self.assertIn("[🔗 example.com](https://www.example.com/product-a)", output)

        # Check Product B
        self.assertIn("| **Product B** | €15.50 |", output)
        self.assertIn("[🔗 store.com](https://store.com/product-b)", output)

        # Should contain markdown markers
        self.assertIn("**", output)
        self.assertIn("|", output)

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_print_results_markdown_no_prices(self, mock_stdout):
        """Test markdown output with products that have no prices."""
        results = SearchResults()
        results.prices = {
            "Product A": None,
            "Product B": None,
        }

        print_results_markdown(results)

        output = mock_stdout.getvalue()
        # Check header and table structure
        self.assertIn("# 🛒 Best Prices", output)
        self.assertIn("| Product | Price | Link |", output)

        # Check products with no prices
        self.assertIn("| **Product A** | _No prices found_ | - |", output)
        self.assertIn("| **Product B** | _No prices found_ | - |", output)

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_print_results_markdown_mixed(self, mock_stdout):
        """Test markdown output with mix of products."""
        results = SearchResults()
        results.prices = {
            "Product A": PriceResult(price=29.99, url="https://example.com/product-a"),
            "Product B": None,
            "Product C": PriceResult(price=45.00, url="https://shop.com/product-c"),
        }

        print_results_markdown(results)

        output = mock_stdout.getvalue()
        # Check Product A (has price)
        self.assertIn("| **Product A** | €29.99 |", output)
        self.assertIn("[🔗 example.com]", output)

        # Check Product B (no price)
        self.assertIn("| **Product B** | _No prices found_ | - |", output)

        # Check Product C (has price)
        self.assertIn("| **Product C** | €45.00 |", output)
        self.assertIn("[🔗 shop.com]", output)

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_print_results_markdown_domain_extraction(self, mock_stdout):
        """Test markdown output correctly extracts domain from URLs."""
        results = SearchResults()
        results.prices = {
            "Product A": PriceResult(price=29.99, url="https://www.example.com/path/to/product"),
            "Product B": PriceResult(price=15.50, url="https://subdomain.store.com/item"),
        }

        print_results_markdown(results)

        output = mock_stdout.getvalue()
        # Should strip 'www.' from domain in link text
        self.assertIn("[🔗 example.com]", output)
        self.assertNotIn("[🔗 www.example.com]", output)

        # Should keep subdomain
        self.assertIn("[🔗 subdomain.store.com]", output)

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_print_results_markdown_separator_line(self, mock_stdout):
        """Test markdown output has proper separator."""
        results = SearchResults()
        results.prices = {"Product A": PriceResult(price=29.99, url="https://example.com/a")}

        print_results_markdown(results)

        output = mock_stdout.getvalue()
        # Should have separator at the end
        self.assertIn("\n---\n", output)

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_print_results_markdown_empty_results(self, mock_stdout):
        """Test markdown output with no products."""
        results = SearchResults()
        results.prices = {}

        print_results_markdown(results)

        output = mock_stdout.getvalue()
        # Should still have header and table structure
        self.assertIn("# 🛒 Best Prices", output)
        self.assertIn("| Product | Price | Link |", output)
        # Should not have any product rows
        self.assertNotIn("| **", output)

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_print_results_markdown_table_structure(self, mock_stdout):
        """Test markdown table has correct structure."""
        results = SearchResults()
        results.prices = {"Product A": PriceResult(price=29.99, url="https://example.com/a")}

        print_results_markdown(results)

        output = mock_stdout.getvalue()
        lines = output.strip().split("\n")

        # Find table header line
        header_line_idx = None
        for i, line in enumerate(lines):
            if "| Product | Price | Link |" in line:
                header_line_idx = i
                break

        self.assertIsNotNone(header_line_idx, "Table header not found")
        assert header_line_idx is not None  # Type narrowing for mypy

        # Next line should be separator
        separator_line = lines[header_line_idx + 1]
        self.assertIn("|---------|-------|------|", separator_line)

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_print_results_markdown_with_price_per_100ml(self, mock_stdout):
        """Test markdown output displays price per 100ml when available."""
        results = SearchResults()
        results.prices = {
            "Product A": PriceResult(price=15.00, url="https://example.com/a", price_per_100ml=3.75),
            "Product B": PriceResult(price=20.00, url="https://example.com/b"),
        }

        print_results_markdown(results)

        output = mock_stdout.getvalue()
        # Product A should show price per 100ml with <br> and italics
        self.assertIn("€15.00<br>_(€3.75/100ml)_", output)
        # Product B should show only regular price
        self.assertIn("| **Product B** | €20.00 |", output)
        # Should not have price per 100ml for Product B
        self.assertNotIn("Product B** | €20.00<br>", output)


class TestPlanMarkdownFormatterEmptyPlan(unittest.TestCase):
    """Test plan markdown formatter with empty plans."""

    def test_when_no_carts_then_displays_no_plan_message(self):
        """
        Given an empty optimized plan
        When printing in markdown format
        Then should display "No shopping plan generated."
        """
        # Given
        plan = create_empty_plan()

        # When
        output = io.StringIO()
        with redirect_stdout(output):
            print_plan_markdown(plan)

        # Then
        result = output.getvalue()
        self.assertIn("No shopping plan generated", result)


class TestPlanMarkdownFormatterSingleStore(unittest.TestCase):
    """Test plan markdown formatter with single store plans."""

    def test_when_single_store_then_displays_markdown_format(self):
        """
        Given a plan with one store
        When printing in markdown format
        Then should use proper markdown headers and tables
        """
        # Given
        cart = create_single_product_cart(price=25.00, shipping_cost=3.99)
        plan = create_plan_with_single_cart(cart)

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
        cart = create_single_product_cart(
            price=15.00,
            shipping_cost=0.0,
            free_shipping=True,
            price_per_100ml=3.75,
        )
        plan = create_plan_with_single_cart(cart)

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
        cart = create_single_product_cart(
            price=15.00,
            shipping_cost=0.0,
            free_shipping=True,
        )
        plan = create_plan_with_single_cart(cart)

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
        cart = create_single_product_cart(
            price=55.00,
            shipping_cost=0.0,
            free_shipping=True,
        )
        plan = create_plan_with_single_cart(cart)

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
        cart = create_single_product_cart(price=25.00, shipping_cost=3.99)
        plan = create_plan_with_single_cart(cart)
        shipping_config = create_shipping_config()

        # When
        output = io.StringIO()
        with redirect_stdout(output):
            print_plan_markdown(plan, shipping_config)

        # Then
        result = output.getvalue()
        self.assertIn("*(Free shipping over €50.00)*", result)


class TestPlanMarkdownFormatterMultipleStores(unittest.TestCase):
    """Test plan markdown formatter with multiple stores."""

    def test_when_multiple_stores_then_displays_all_with_headers(self):
        """
        Given a plan with multiple stores
        When printing in markdown format
        Then should display each store with separate headers
        """
        # Given
        cart1 = create_single_product_cart(
            site="store1.com",
            product_name="Product A",
            price=10.00,
            shipping_cost=3.50,
        )
        cart2 = create_single_product_cart(
            site="store2.com",
            product_name="Product B",
            price=20.00,
            shipping_cost=4.00,
        )
        plan = create_plan_with_multiple_carts([cart1, cart2])

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


class TestPlanFormatterSummaryStatistics(unittest.TestCase):
    """Test that plan summary statistics are displayed correctly."""

    def test_when_plan_has_statistics_then_displays_in_markdown(self):
        """
        Given a plan with specific statistics
        When printing in markdown format
        Then should display total products and store count in bold
        """
        # Given
        cart = create_single_product_cart(
            site="store.com",
            product_name="A",
            price=10.0,
            shipping_cost=0.0,
            free_shipping=True,
        )
        plan = create_plan_with_single_cart(cart)

        # When
        output = io.StringIO()
        with redirect_stdout(output):
            print_plan_markdown(plan)

        # Then
        result = output.getvalue()
        self.assertIn("**Products:** 1 item from 1 store", result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
