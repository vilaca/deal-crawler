"""Tests for main.py output formatting functions."""

import io
import unittest
from unittest.mock import MagicMock, patch

from main import (
    main,
    print_results_markdown,
    print_results_text,
    filter_by_sites,
    filter_by_products,
)
from utils.finder import SearchResults


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
        self.assertLess(
            pos_b, pos_a, "Product B (cheaper) should appear before Product A"
        )

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
        self.assertLess(
            pos_a, pos_c, "Product A (€29.99) should appear before Product C (€45.00)"
        )
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
        self.assertLess(
            pos_b, pos_a, "Product B (cheaper) should appear before Product A"
        )

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
        separator_lines = [
            line for line in lines if line and all(c == "=" for c in line)
        ]
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
        content_lines = [
            line for line in lines if line and "€" in line and "http" in line
        ]

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
            f"Price column should start at position {expected_euro_pos} "
            f"(after longest product name + 1 space)",
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
        separator_lines = [
            line for line in lines if line and all(c == "=" for c in line)
        ]
        # Get content line with price and URL
        content_line = [line for line in lines if "€" in line and "http" in line][0]

        # Separator should be at least as wide as the content line
        self.assertGreaterEqual(
            len(separator_lines[0]),
            len(content_line),
            "Separator should be at least as wide as content",
        )
        # Separator should be at least the minimum width (50)
        self.assertGreaterEqual(
            len(separator_lines[0]), 50, "Separator should meet minimum width of 50"
        )

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
        separator_lines = [
            line for line in lines if line and all(c == "=" for c in line)
        ]
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


class TestPrintResultsMarkdown(unittest.TestCase):
    """Test markdown format output function."""

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_print_results_markdown_with_prices(self, mock_stdout):
        """Test markdown output with products that have prices."""
        results = SearchResults()
        results.prices = {
            "Product A": (29.99, "https://www.example.com/product-a"),
            "Product B": (15.50, "https://store.com/product-b"),
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
            "Product A": (29.99, "https://example.com/product-a"),
            "Product B": None,
            "Product C": (45.00, "https://shop.com/product-c"),
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
            "Product A": (29.99, "https://www.example.com/path/to/product"),
            "Product B": (15.50, "https://subdomain.store.com/item"),
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
        results.prices = {"Product A": (29.99, "https://example.com/a")}

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
        results.prices = {"Product A": (29.99, "https://example.com/a")}

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


class TestMainFunction(unittest.TestCase):
    """Test the main() function entry point."""

    @patch("main.find_cheapest_prices")
    @patch("main.load_products")
    @patch("main.HttpClient")
    @patch("main.print_results_text")
    @patch("sys.argv", ["main.py"])
    def test_main_default_text_format(
        self, mock_print_text, mock_http_client, mock_load_products, mock_find_prices
    ):
        """Test main() uses text format by default (no --markdown flag)."""
        # Setup mocks
        mock_products = {"Product A": ["https://example.com/a"]}
        mock_load_products.return_value = mock_products

        mock_results = MagicMock(spec=SearchResults)
        mock_results.prices = {"Product A": (29.99, "https://example.com/a")}
        mock_find_prices.return_value = mock_results

        # Run main
        main()

        # Verify text format was used
        mock_print_text.assert_called_once_with(mock_results)
        mock_results.print_summary.assert_called_once_with(markdown=False)

    @patch("main.find_cheapest_prices")
    @patch("main.load_products")
    @patch("main.HttpClient")
    @patch("main.print_results_markdown")
    @patch("sys.argv", ["main.py", "--markdown"])
    def test_main_markdown_format(
        self,
        mock_print_markdown,
        mock_http_client,
        mock_load_products,
        mock_find_prices,
    ):
        """Test main() uses markdown format with --markdown flag."""
        # Setup mocks
        mock_products = {"Product A": ["https://example.com/a"]}
        mock_load_products.return_value = mock_products

        mock_results = MagicMock(spec=SearchResults)
        mock_results.prices = {"Product A": (29.99, "https://example.com/a")}
        mock_find_prices.return_value = mock_results

        # Run main
        main()

        # Verify markdown format was used
        mock_print_markdown.assert_called_once_with(mock_results)
        mock_results.print_summary.assert_called_once_with(markdown=True)

    @patch("main.load_products")
    @patch("sys.argv", ["main.py"])
    def test_main_exits_when_no_products(self, mock_load_products):
        """Test main() exits with error when no products to compare."""
        # Setup: load_products returns empty dict
        mock_load_products.return_value = {}

        # Should exit with code 1
        with self.assertRaises(SystemExit) as cm:
            main()

        self.assertEqual(cm.exception.code, 1)

    @patch("main.find_cheapest_prices")
    @patch("main.load_products")
    @patch("main.HttpClient")
    @patch("main.print_results_text")
    @patch("sys.argv", ["main.py"])
    def test_main_uses_http_client_context_manager(
        self, mock_print_text, mock_http_client, mock_load_products, mock_find_prices
    ):
        """Test main() properly uses HttpClient as context manager."""
        # Setup mocks
        mock_products = {"Product A": ["https://example.com/a"]}
        mock_load_products.return_value = mock_products

        mock_results = MagicMock(spec=SearchResults)
        mock_results.prices = {"Product A": (29.99, "https://example.com/a")}
        mock_find_prices.return_value = mock_results

        mock_http_instance = mock_http_client.return_value.__enter__.return_value

        # Run main
        main()

        # Verify HttpClient was used as context manager
        mock_http_client.return_value.__enter__.assert_called_once()
        mock_http_client.return_value.__exit__.assert_called_once()

        # Verify find_cheapest_prices was called with http_client instance
        mock_find_prices.assert_called_once_with(mock_products, mock_http_instance)

    @patch("main.find_cheapest_prices")
    @patch("main.load_products")
    @patch("main.HttpClient")
    @patch("main.print_results_text")
    @patch("sys.argv", ["main.py"])
    def test_main_calls_load_products(
        self, mock_print_text, mock_http_client, mock_load_products, mock_find_prices
    ):
        """Test main() calls load_products with correct filename."""
        # Setup mocks
        mock_products = {"Product A": ["https://example.com/a"]}
        mock_load_products.return_value = mock_products

        mock_results = MagicMock(spec=SearchResults)
        mock_results.prices = {"Product A": (29.99, "https://example.com/a")}
        mock_find_prices.return_value = mock_results

        # Run main
        main()

        # Verify load_products was called with correct file
        mock_load_products.assert_called_once_with("data.yml")

    @patch("main.find_cheapest_prices")
    @patch("main.load_products")
    @patch("main.HttpClient")
    @patch("main.print_results_text")
    @patch("sys.argv", ["main.py", "--sites", "notino.pt"])
    def test_main_with_sites_filter(
        self, mock_print_text, mock_http_client, mock_load_products, mock_find_prices
    ):
        """Test main() applies --sites filter correctly."""
        # Setup mocks with multiple sites
        mock_products = {
            "Product A": [
                "https://www.notino.pt/product-a",
                "https://wells.pt/product-a",
            ],
            "Product B": ["https://atida.com/product-b"],
        }
        mock_load_products.return_value = mock_products

        mock_results = MagicMock(spec=SearchResults)
        mock_results.prices = {"Product A": (29.99, "https://www.notino.pt/product-a")}
        mock_find_prices.return_value = mock_results

        # Run main
        main()

        # Verify find_cheapest_prices was called with filtered products
        # Should only include Product A (has notino.pt URL) with only notino.pt URL
        call_args = mock_find_prices.call_args[0][0]
        self.assertIn("Product A", call_args)
        self.assertNotIn("Product B", call_args)
        self.assertEqual(len(call_args["Product A"]), 1)
        self.assertIn("notino.pt", call_args["Product A"][0])

    @patch("main.find_cheapest_prices")
    @patch("main.load_products")
    @patch("main.HttpClient")
    @patch("main.print_results_text")
    @patch("sys.argv", ["main.py", "--products", "Product A"])
    def test_main_with_products_filter(
        self, mock_print_text, mock_http_client, mock_load_products, mock_find_prices
    ):
        """Test main() applies --products filter correctly."""
        # Setup mocks
        mock_products = {
            "Product A": ["https://example.com/a"],
            "Product B": ["https://example.com/b"],
        }
        mock_load_products.return_value = mock_products

        mock_results = MagicMock(spec=SearchResults)
        mock_results.prices = {"Product A": (29.99, "https://example.com/a")}
        mock_find_prices.return_value = mock_results

        # Run main
        main()

        # Verify find_cheapest_prices was called with filtered products
        # Should only include Product A
        call_args = mock_find_prices.call_args[0][0]
        self.assertIn("Product A", call_args)
        self.assertNotIn("Product B", call_args)

    @patch("main.find_cheapest_prices")
    @patch("main.load_products")
    @patch("main.HttpClient")
    @patch("main.print_results_text")
    @patch("sys.argv", ["main.py", "--sites", "notino.pt", "--products", "Product A"])
    def test_main_with_combined_filters(
        self, mock_print_text, mock_http_client, mock_load_products, mock_find_prices
    ):
        """Test main() applies both --sites and --products filters together."""
        # Setup mocks
        mock_products = {
            "Product A": [
                "https://www.notino.pt/product-a",
                "https://wells.pt/product-a",
            ],
            "Product B": ["https://www.notino.pt/product-b"],
        }
        mock_load_products.return_value = mock_products

        mock_results = MagicMock(spec=SearchResults)
        mock_results.prices = {"Product A": (29.99, "https://www.notino.pt/product-a")}
        mock_find_prices.return_value = mock_results

        # Run main
        main()

        # Verify find_cheapest_prices was called with both filters applied
        # Should only include Product A with only notino.pt URL
        call_args = mock_find_prices.call_args[0][0]
        self.assertIn("Product A", call_args)
        self.assertNotIn("Product B", call_args)
        self.assertEqual(len(call_args["Product A"]), 1)
        self.assertIn("notino.pt", call_args["Product A"][0])

    @patch("main.load_products")
    @patch("sys.argv", ["main.py", "--sites", "nonexistent.com"])
    def test_main_exits_when_sites_filter_has_no_matches(self, mock_load_products):
        """Test main() exits with error when --sites filter has no matches."""
        # Setup: products exist but none match the site filter
        mock_products = {
            "Product A": ["https://www.notino.pt/product-a"],
            "Product B": ["https://wells.pt/product-b"],
        }
        mock_load_products.return_value = mock_products

        # Should exit with code 1
        with self.assertRaises(SystemExit) as cm:
            main()

        self.assertEqual(cm.exception.code, 1)

    @patch("main.load_products")
    @patch("sys.argv", ["main.py", "--products", "NonExistent"])
    def test_main_exits_when_products_filter_has_no_matches(self, mock_load_products):
        """Test main() exits with error when --products filter has no matches."""
        # Setup: products exist but none match the product filter
        mock_products = {
            "Product A": ["https://example.com/a"],
            "Product B": ["https://example.com/b"],
        }
        mock_load_products.return_value = mock_products

        # Should exit with code 1
        with self.assertRaises(SystemExit) as cm:
            main()

        self.assertEqual(cm.exception.code, 1)

    @patch("main.find_cheapest_prices")
    @patch("main.load_products")
    @patch("main.HttpClient")
    @patch("main.print_results_text")
    @patch("sys.argv", ["main.py", "--sites", "notino.pt,wells.pt"])
    def test_main_with_multiple_sites(
        self, mock_print_text, mock_http_client, mock_load_products, mock_find_prices
    ):
        """Test main() handles comma-separated sites correctly."""
        # Setup mocks
        mock_products = {
            "Product A": [
                "https://www.notino.pt/product-a",
                "https://wells.pt/product-a",
                "https://atida.com/product-a",
            ]
        }
        mock_load_products.return_value = mock_products

        mock_results = MagicMock(spec=SearchResults)
        mock_results.prices = {"Product A": (29.99, "https://www.notino.pt/product-a")}
        mock_find_prices.return_value = mock_results

        # Run main
        main()

        # Verify find_cheapest_prices was called with filtered products
        # Should include notino.pt and wells.pt URLs, but not atida.com
        call_args = mock_find_prices.call_args[0][0]
        self.assertEqual(len(call_args["Product A"]), 2)

    @patch("main.find_cheapest_prices")
    @patch("main.load_products")
    @patch("main.HttpClient")
    @patch("main.print_results_text")
    @patch("sys.argv", ["main.py", "--products", "Product A,Product B"])
    def test_main_with_multiple_products(
        self, mock_print_text, mock_http_client, mock_load_products, mock_find_prices
    ):
        """Test main() handles comma-separated products correctly."""
        # Setup mocks
        mock_products = {
            "Product A": ["https://example.com/a"],
            "Product B": ["https://example.com/b"],
            "Product C": ["https://example.com/c"],
        }
        mock_load_products.return_value = mock_products

        mock_results = MagicMock(spec=SearchResults)
        mock_results.prices = {
            "Product A": (29.99, "https://example.com/a"),
            "Product B": (19.99, "https://example.com/b"),
        }
        mock_find_prices.return_value = mock_results

        # Run main
        main()

        # Verify find_cheapest_prices was called with filtered products
        # Should include Product A and B, but not C
        call_args = mock_find_prices.call_args[0][0]
        self.assertIn("Product A", call_args)
        self.assertIn("Product B", call_args)
        self.assertNotIn("Product C", call_args)


class TestFilterBySites(unittest.TestCase):
    """Test site filtering functionality."""

    def test_filter_single_site(self):
        """Test filtering by a single site."""
        products = {
            "Product A": [
                "https://www.notino.pt/product-a",
                "https://wells.pt/product-a",
                "https://atida.com/product-a",
            ],
            "Product B": ["https://www.notino.pt/product-b"],
        }
        result = filter_by_sites(products, ["notino.pt"])

        self.assertEqual(len(result), 2)
        self.assertEqual(len(result["Product A"]), 1)
        self.assertIn("notino.pt", result["Product A"][0])
        self.assertEqual(len(result["Product B"]), 1)

    def test_filter_multiple_sites(self):
        """Test filtering by multiple sites."""
        products = {
            "Product A": [
                "https://www.notino.pt/product-a",
                "https://wells.pt/product-a",
                "https://atida.com/product-a",
            ]
        }
        result = filter_by_sites(products, ["notino.pt", "wells.pt"])

        self.assertEqual(len(result), 1)
        self.assertEqual(len(result["Product A"]), 2)

    def test_filter_no_matches(self):
        """Test filtering when no URLs match."""
        products = {
            "Product A": ["https://www.notino.pt/product-a"],
            "Product B": ["https://wells.pt/product-b"],
        }
        result = filter_by_sites(products, ["amazon.com"])

        self.assertEqual(len(result), 0)

    def test_filter_case_insensitive(self):
        """Test filtering is case-insensitive."""
        products = {"Product A": ["https://www.NOTINO.PT/product-a"]}
        result = filter_by_sites(products, ["notino.pt"])

        self.assertEqual(len(result), 1)
        self.assertEqual(len(result["Product A"]), 1)

    def test_filter_partial_domain_match(self):
        """Test filtering matches partial domains."""
        products = {"Product A": ["https://subdomain.notino.pt/product-a"]}
        result = filter_by_sites(products, ["notino.pt"])

        self.assertEqual(len(result), 1)

    def test_filter_removes_products_with_no_matching_urls(self):
        """Test products with no matching URLs are removed."""
        products = {
            "Product A": ["https://www.notino.pt/product-a"],
            "Product B": ["https://atida.com/product-b"],
        }
        result = filter_by_sites(products, ["notino.pt"])

        self.assertEqual(len(result), 1)
        self.assertIn("Product A", result)
        self.assertNotIn("Product B", result)


class TestFilterByProducts(unittest.TestCase):
    """Test product name filtering functionality."""

    def test_filter_single_substring(self):
        """Test filtering by a single substring."""
        products = {
            "Medik8 Crystal Retinal 6": ["https://example.com/1"],
            "LRP Anthelios SPF50": ["https://example.com/2"],
            "Medik8 Super Ferrulic": ["https://example.com/3"],
        }
        result = filter_by_products(products, ["Crystal"])

        self.assertEqual(len(result), 1)
        self.assertIn("Medik8 Crystal Retinal 6", result)

    def test_filter_multiple_substrings(self):
        """Test filtering by multiple substrings (OR logic)."""
        products = {
            "Medik8 Crystal Retinal 6": ["https://example.com/1"],
            "LRP Anthelios SPF50": ["https://example.com/2"],
            "Medik8 Super Ferrulic": ["https://example.com/3"],
        }
        result = filter_by_products(products, ["Crystal", "SPF50"])

        self.assertEqual(len(result), 2)
        self.assertIn("Medik8 Crystal Retinal 6", result)
        self.assertIn("LRP Anthelios SPF50", result)

    def test_filter_case_insensitive(self):
        """Test filtering is case-insensitive."""
        products = {
            "Medik8 Crystal Retinal 6": ["https://example.com/1"],
            "LRP Anthelios SPF50": ["https://example.com/2"],
        }
        result = filter_by_products(products, ["crystal", "spf50"])

        self.assertEqual(len(result), 2)

    def test_filter_no_matches(self):
        """Test filtering when no products match."""
        products = {
            "Medik8 Crystal Retinal 6": ["https://example.com/1"],
            "LRP Anthelios SPF50": ["https://example.com/2"],
        }
        result = filter_by_products(products, ["NonExistent"])

        self.assertEqual(len(result), 0)

    def test_filter_partial_match(self):
        """Test filtering matches partial product names."""
        products = {
            "Medik8 Crystal Retinal 6": ["https://example.com/1"],
            "Medik8 Crystal Retinal 3": ["https://example.com/2"],
        }
        result = filter_by_products(products, ["Retinal 6"])

        self.assertEqual(len(result), 1)
        self.assertIn("Medik8 Crystal Retinal 6", result)

    def test_filter_preserves_urls(self):
        """Test filtering preserves all URLs for matched products."""
        products = {
            "Medik8 Crystal Retinal 6": [
                "https://example.com/1",
                "https://example.com/2",
                "https://example.com/3",
            ]
        }
        result = filter_by_products(products, ["Crystal"])

        self.assertEqual(len(result["Medik8 Crystal Retinal 6"]), 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
