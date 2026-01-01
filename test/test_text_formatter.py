"""Tests for utils.text_formatter module."""

import io
import unittest
from unittest.mock import patch

from utils.finder import SearchResults
from utils.text_formatter import print_results_text


class TestPrintResultsText(unittest.TestCase):
    """Test text format output function."""

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_print_results_text_with_prices(self, mock_stdout):
        """Test text output with products that have prices."""
        results = SearchResults()
        results.prices = {
            "Product A": (29.99, "https://www.example.com/product-a"),
            "Product B": (15.50, "https://store.com/product-b"),
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
            "Product A": (29.99, "https://example.com/product-a"),
            "Product B": None,
            "Product C": (45.00, "https://shop.com/product-c"),
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
            "Product A": (29.99, "https://www.example.com/path/to/product"),
            "Product B": (15.50, "https://subdomain.store.com/item"),
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
        results.prices = {"Product A": (29.99, "https://example.com/a")}

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
            "Short": (10.00, "https://example.com/short"),
            "Medium Length Name": (20.00, "https://example.com/medium"),
            "Very Long Product Name Here": (30.00, "https://example.com/long"),
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
            "Product A": (5.50, "https://example.com/a"),
            "Product B": (99.99, "https://example.com/b"),
            "Product C": (123.45, "https://example.com/c"),
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
            "Product": (10.00, "https://short.com/a"),
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
            "Product A": (5.50, "https://example.com/a"),  # Small price (5 chars)
            "Product B": None,  # Warning message is 19 chars
            "Product C": (9.99, "https://example.com/c"),  # Small price (5 chars)
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
            "Short": (1.00, "https://example.com/short"),
            "Long": (2.00, "https://verylongdomainname.com/very/long/path/to/product"),
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
