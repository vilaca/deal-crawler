"""Tests for utils.markdown_formatter module."""

import io
import unittest
from unittest.mock import patch

from utils.finder import PriceResult, SearchResults
from utils.markdown_formatter import print_results_markdown


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


if __name__ == "__main__":
    unittest.main(verbosity=2)
