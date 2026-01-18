"""Tests for utils.text_formatter module."""

import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from utils.price_models import PriceResult, SearchResults
from utils.text_formatter import print_results_text, print_plan_text
from test.test_formatter_fixtures import (
    create_empty_plan,
    create_single_product_cart,
    create_multi_product_cart,
    create_plan_with_single_cart,
    create_plan_with_multiple_carts,
    create_shipping_config,
)


class TestPrintResultsText(unittest.TestCase):
    """Test text format output function."""

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_print_results_text_with_prices(self, mock_stdout):
        """Test text output with products that have prices."""
        results = SearchResults()
        results.prices = {
            "Product A": PriceResult(price=29.99, url="https://www.example.com/product-a"),
            "Product B": PriceResult(price=15.50, url="https://store.com/product-b"),
        }

        print_results_text(results)

        output = mock_stdout.getvalue()
        # Check header
        self.assertIn("🛒 Best Prices", output)
        # Check separator exists (dynamic length)
        self.assertIn("=====", output)

        # Check Product A (sorted - should be second since €29.99 > €15.50)
        self.assertIn("Product A", output)
        self.assertIn("€29.99", output)
        self.assertIn("https://www.example.com/product-a", output)

        # Check Product B (sorted - should be first since €15.50 is cheaper)
        self.assertIn("Product B", output)
        self.assertIn("€15.50", output)
        self.assertIn("https://store.com/product-b", output)

        # Verify sorting: Product B (€15.50) should appear before Product A (€29.99)
        pos_b = output.find("Product B")
        pos_a = output.find("Product A")
        self.assertLess(pos_b, pos_a, "Product B (cheaper) should appear before Product A")

        # Should NOT contain markdown markers
        self.assertNotIn("**", output)
        self.assertNotIn("|", output)  # No markdown table syntax
        self.assertNotIn("🔗", output)  # No link emoji (that's for markdown)

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_print_results_text_no_prices(self, mock_stdout):
        """Test text output with products that have no prices."""
        results = SearchResults()
        results.prices = {
            "Product A": None,
            "Product B": None,
        }

        print_results_text(results)

        output = mock_stdout.getvalue()
        # Check header
        self.assertIn("🛒 Best Prices", output)

        # Check products with no prices
        self.assertIn("Product A", output)
        self.assertIn("⚠️  No prices found", output)
        self.assertIn("Product B", output)

        # Should NOT contain price information
        self.assertNotIn("€", output)
        self.assertNotIn("Price:", output)
        self.assertNotIn("Store:", output)
        self.assertNotIn("Link:", output)

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_print_results_text_mixed(self, mock_stdout):
        """Test text output with mix of products (some with prices, some without)."""
        results = SearchResults()
        results.prices = {
            "Product A": PriceResult(price=29.99, url="https://example.com/product-a"),
            "Product B": None,
            "Product C": PriceResult(price=45.00, url="https://shop.com/product-c"),
        }

        print_results_text(results)

        output = mock_stdout.getvalue()
        # Check Product A (has price €29.99)
        self.assertIn("Product A", output)
        self.assertIn("€29.99", output)

        # Check Product B (no price - should appear last)
        self.assertIn("Product B", output)
        self.assertIn("⚠️  No prices found", output)

        # Check Product C (has price €45.00)
        self.assertIn("Product C", output)
        self.assertIn("€45.00", output)

        # Verify sorting: A (€29.99) before C (€45.00) before B (no price)
        pos_a = output.find("Product A")
        pos_c = output.find("Product C")
        pos_b = output.find("Product B")
        self.assertLess(pos_a, pos_c, "Product A (€29.99) should appear before Product C (€45.00)")
        self.assertLess(
            pos_c,
            pos_b,
            "Product C (has price) should appear before Product B (no price)",
        )

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_print_results_text_with_full_urls(self, mock_stdout):
        """Test text output includes full URLs and sorts by price."""
        results = SearchResults()
        results.prices = {
            "Product A": PriceResult(price=29.99, url="https://www.example.com/path/to/product"),
            "Product B": PriceResult(price=15.50, url="https://subdomain.store.com/item"),
        }

        print_results_text(results)

        output = mock_stdout.getvalue()
        # Should include product, full URL, and price at the end
        self.assertIn("Product A", output)
        self.assertIn("€29.99", output)
        self.assertIn("https://www.example.com/path/to/product", output)

        self.assertIn("Product B", output)
        self.assertIn("€15.50", output)
        self.assertIn("https://subdomain.store.com/item", output)

        # Verify sorting: Product B (€15.50) should appear before Product A (€29.99)
        pos_b = output.find("Product B")
        pos_a = output.find("Product A")
        self.assertLess(pos_b, pos_a, "Product B (cheaper) should appear before Product A")

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_print_results_text_separator_lines(self, mock_stdout):
        """Test text output has proper separator lines."""
        results = SearchResults()
        results.prices = {"Product A": PriceResult(price=29.99, url="https://example.com/a")}

        print_results_text(results)

        output = mock_stdout.getvalue()
        # Should have separator lines at top and bottom (dynamic length)
        lines = output.strip().split("\n")
        # Find separator lines (lines with only equals signs)
        separator_lines = [line for line in lines if line and all(c == "=" for c in line)]
        # Should have exactly 2 separator lines (after header and at end)
        self.assertEqual(len(separator_lines), 2)
        # Both separators should be the same length
        self.assertEqual(len(separator_lines[0]), len(separator_lines[1]))

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_print_results_text_empty_results(self, mock_stdout):
        """Test text output with no products."""
        results = SearchResults()
        results.prices = {}

        print_results_text(results)

        output = mock_stdout.getvalue()
        # Should still have header
        self.assertIn("🛒 Best Prices", output)
        # Should show empty message
        self.assertIn("No products to display", output)
        # Should have separators
        self.assertIn("=====", output)
        # Should not have any product information
        self.assertNotIn("Price:", output)
        self.assertNotIn("Store:", output)
        self.assertNotIn("€", output)

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_print_results_text_dynamic_product_name_width(self, mock_stdout):
        """Test that product name column width adjusts to longest name."""
        results = SearchResults()
        results.prices = {
            "Short": PriceResult(price=10.00, url="https://example.com/short"),
            "Medium Length Name": PriceResult(price=20.00, url="https://example.com/medium"),
            "Very Long Product Name Here": PriceResult(price=30.00, url="https://example.com/long"),
        }

        print_results_text(results)

        output = mock_stdout.getvalue()
        lines = output.strip().split("\n")

        # Get content lines with prices
        content_lines = [line for line in lines if line and "€" in line and "http" in line]

        # Extract the position of the euro sign in each line (start of price column)
        euro_positions = [line.find("€") for line in content_lines]

        # All euro signs should be at the same position (price column alignment)
        self.assertEqual(
            len(set(euro_positions)),
            1,
            "All prices should start at the same column position",
        )

        # Verify the longest product name determines the column width
        longest_name = "Very Long Product Name Here"
        # The euro sign should appear after the longest name + 1 space
        expected_euro_pos = len(longest_name) + 1
        self.assertEqual(
            euro_positions[0],
            expected_euro_pos,
            f"Price column should start at position {expected_euro_pos} " f"(after longest product name + 1 space)",
        )

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_print_results_text_decimal_point_alignment(self, mock_stdout):
        """Test that prices are aligned by decimal point."""
        results = SearchResults()
        results.prices = {
            "Product A": PriceResult(price=5.50, url="https://example.com/a"),
            "Product B": PriceResult(price=99.99, url="https://example.com/b"),
            "Product C": PriceResult(price=123.45, url="https://example.com/c"),
        }

        print_results_text(results)

        output = mock_stdout.getvalue()
        lines = output.strip().split("\n")

        # Get content lines with prices
        price_lines = [line for line in lines if "€" in line and "http" in line]

        # Extract the position of the decimal point in each line
        decimal_positions = []
        for line in price_lines:
            # Find the position of the decimal point in the price
            euro_pos = line.find("€")
            if euro_pos != -1:
                # Find decimal point after the euro sign
                decimal_pos = line.find(".", euro_pos)
                if decimal_pos != -1:
                    decimal_positions.append(decimal_pos)

        # All decimal points should be at the same position
        self.assertEqual(
            len(set(decimal_positions)),
            1,
            "All decimal points should align at the same column",
        )

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_print_results_text_dynamic_separator_width(self, mock_stdout):
        """Test that separator width is at least as wide as content (with minimum)."""
        results = SearchResults()
        results.prices = {
            "Product": PriceResult(price=10.00, url="https://short.com/a"),
        }

        print_results_text(results)

        output = mock_stdout.getvalue()
        lines = output.strip().split("\n")

        # Get separator lines
        separator_lines = [line for line in lines if line and all(c == "=" for c in line)]
        # Get content line with price and URL
        content_line = [line for line in lines if "€" in line and "http" in line][0]

        # Separator should be at least as wide as the content line
        self.assertGreaterEqual(
            len(separator_lines[0]),
            len(content_line),
            "Separator should be at least as wide as content",
        )
        # Separator should be at least the minimum width (50)
        self.assertGreaterEqual(len(separator_lines[0]), 50, "Separator should meet minimum width of 50")

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_print_results_text_all_items_without_prices(self, mock_stdout):
        """Test that items without prices are properly formatted and aligned."""
        results = SearchResults()
        results.prices = {
            "Product A": None,
            "Product B": None,
            "Very Long Product Name": None,
        }

        print_results_text(results)

        output = mock_stdout.getvalue()
        lines = output.strip().split("\n")

        # Get content lines with the warning message
        content_lines = [line for line in lines if "⚠️  No prices found" in line]

        # Should have 3 lines (one for each product)
        self.assertEqual(len(content_lines), 3)

        # Extract the position where the warning message starts in each line
        warning_positions = [line.find("⚠️") for line in content_lines]

        # All warning messages should start at the same position (proper alignment)
        self.assertEqual(
            len(set(warning_positions)),
            1,
            "All 'No prices found' messages should be aligned",
        )

        # Verify the longest product name determines the column width
        longest_name = "Very Long Product Name"
        # The warning should appear after the longest name + 1 space
        expected_warning_pos = len(longest_name) + 1
        self.assertEqual(
            warning_positions[0],
            expected_warning_pos,
            f"Warning messages should start at position {expected_warning_pos}",
        )

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_print_results_text_mixed_small_prices_alignment(self, mock_stdout):
        """Test that warning messages fit properly in mixed scenarios with small prices.

        When prices are small (e.g., €5.50 = 5 chars) but some products have no prices,
        the price column must be wide enough to fit the warning message (19 chars).
        This ensures the warning message doesn't extend beyond the column and break layout.
        """
        results = SearchResults()
        results.prices = {
            "Product A": PriceResult(price=5.50, url="https://example.com/a"),  # Small price (5 chars)
            "Product B": None,  # Warning message is 19 chars
            "Product C": PriceResult(price=9.99, url="https://example.com/c"),  # Small price (5 chars)
        }

        print_results_text(results)

        output = mock_stdout.getvalue()
        lines = output.strip().split("\n")

        # Get content lines
        product_lines = [line for line in lines if "Product" in line]

        self.assertEqual(len(product_lines), 3, "Should have 3 product lines")

        # Verify all product lines have consistent structure
        longest_product = max("Product A", "Product B", "Product C", key=len)

        for line in product_lines:
            # Find where content after product name starts (price column)
            product_end = line.find("Product") + len(longest_product) + 1
            # The next non-space character should be within the expected column
            next_char_pos = len(line[:product_end].rstrip()) + 1
            self.assertLessEqual(
                next_char_pos,
                product_end + 1,
                "Price column should start at consistent position",
            )

        # Verify warning message and URL don't collide
        warning_line = [line for line in product_lines if "⚠️" in line][0]
        # Warning line should not have a URL (since it has no price)
        self.assertNotIn("http", warning_line)

        # Price lines should have URLs
        price_lines = [line for line in product_lines if "€" in line]
        for line in price_lines:
            self.assertIn("http", line, "Lines with prices should have URLs")

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_print_results_text_separator_matches_longest_line(self, mock_stdout):
        """Test that separator adjusts to the longest line (with long URL)."""
        results = SearchResults()
        results.prices = {
            "Short": PriceResult(price=1.00, url="https://example.com/short"),
            "Long": PriceResult(price=2.00, url="https://verylongdomainname.com/very/long/path/to/product"),
        }

        print_results_text(results)

        output = mock_stdout.getvalue()
        lines = output.strip().split("\n")

        # Get separator lines
        separator_lines = [line for line in lines if line and all(c == "=" for c in line)]
        # Get all content lines
        content_lines = [line for line in lines if "€" in line]

        # Find the longest content line
        max_content_len = max(len(line) for line in content_lines)

        # Separator should match the longest content line
        self.assertEqual(
            len(separator_lines[0]),
            max_content_len,
            "Separator should match the longest line",
        )

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_print_results_text_with_price_per_100ml(self, mock_stdout):
        """Test text output displays price per 100ml when available."""
        results = SearchResults()
        results.prices = {
            "Product A": PriceResult(price=15.00, url="https://example.com/a", price_per_100ml=3.75),
            "Product B": PriceResult(price=20.00, url="https://example.com/b"),
        }

        print_results_text(results)

        output = mock_stdout.getvalue()
        # Product A should show price per 100ml in parentheses
        self.assertIn("€15.00 (€3.75/100ml)", output)
        # Product B should show only regular price (without 100ml info)
        self.assertIn("€20.00", output)
        # Verify Product A line contains both price and 100ml value
        lines = output.split("\n")
        product_a_line = [line for line in lines if "Product A" in line][0]
        self.assertIn("€15.00 (€3.75/100ml)", product_a_line)
        # Verify Product B line does not contain 100ml info
        product_b_line = [line for line in lines if "Product B" in line][0]
        self.assertNotIn("100ml", product_b_line)


class TestPlanTextFormatterEmptyPlan(unittest.TestCase):
    """Test plan text formatter with empty plans."""

    def test_when_no_carts_then_displays_no_plan_message(self):
        """
        Given an empty optimized plan
        When printing in text format
        Then should display "No shopping plan generated."
        """
        # Given
        plan = create_empty_plan()

        # When
        output = io.StringIO()
        with redirect_stdout(output):
            print_plan_text(plan)

        # Then
        result = output.getvalue()
        self.assertIn("No shopping plan generated", result)


class TestPlanTextFormatterSingleStore(unittest.TestCase):
    """Test plan text formatter with single store plans."""

    def test_when_single_store_single_product_then_displays_correctly(self):
        """
        Given a plan with one product from one store
        When printing in text format
        Then should display store name, product, price, shipping, and total
        """
        # Given
        cart = create_single_product_cart(price=25.00, shipping_cost=3.99)
        plan = create_plan_with_single_cart(cart)

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
        cart = create_single_product_cart(price=15.00, free_shipping=True, price_per_100ml=3.75)
        plan = create_plan_with_single_cart(cart)

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
        cart = create_single_product_cart(price=55.00, free_shipping=True)
        plan = create_plan_with_single_cart(cart)

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
        cart = create_single_product_cart(price=25.00, shipping_cost=3.99)
        plan = create_plan_with_single_cart(cart)
        shipping_config = create_shipping_config(shipping_cost=3.99, free_over=50.00)

        # When
        output = io.StringIO()
        with redirect_stdout(output):
            print_plan_text(plan, shipping_config)

        # Then
        result = output.getvalue()
        self.assertIn("Free shipping over €50.00", result)


class TestPlanTextFormatterMultipleStores(unittest.TestCase):
    """Test plan text formatter with multiple stores."""

    def test_when_multiple_stores_then_displays_all_stores(self):
        """
        Given a plan with products from multiple stores
        When printing in text format
        Then should display all stores with their products
        """
        # Given
        cart1 = create_single_product_cart(site="store1.com", product_name="Product A", price=10.00, shipping_cost=3.50)
        cart2 = create_single_product_cart(site="store2.com", product_name="Product B", price=20.00, shipping_cost=4.00)
        plan = create_plan_with_multiple_carts([cart1, cart2])

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
        cart = create_multi_product_cart(
            site="example.com",
            products=[("Product A", 10.00), ("Product B", 15.00), ("Product C", 20.00)],
            shipping_cost=3.99,
        )
        plan = create_plan_with_single_cart(cart)

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


class TestPlanFormatterSummaryStatistics(unittest.TestCase):
    """Test that plan summary statistics are displayed correctly."""

    def test_when_plan_has_statistics_then_displays_in_text(self):
        """
        Given a plan with specific statistics
        When printing in text format
        Then should display total products and store count
        """
        # Given
        cart1 = create_single_product_cart(site="store1.com", product_name="A", price=10.0, free_shipping=True)
        cart2 = create_single_product_cart(site="store2.com", product_name="B", price=20.0, free_shipping=True)
        plan = create_plan_with_multiple_carts([cart1, cart2])

        # When
        output = io.StringIO()
        with redirect_stdout(output):
            print_plan_text(plan)

        # Then
        result = output.getvalue()
        self.assertIn("Products: 2 items from 2 stores", result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
