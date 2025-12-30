"""Tests for price comparison logic."""

import io
import unittest
from unittest.mock import patch, MagicMock
from bs4 import BeautifulSoup

from utils.finder import find_cheapest_prices, SearchResults


class TestFindCheapestPrices(unittest.TestCase):
    """Test finding cheapest prices across multiple products and URLs."""

    def create_soup(self, html):
        """Helper to create BeautifulSoup from HTML."""
        return BeautifulSoup(html, "lxml")

    def create_mock_http_client(self):
        """Helper to create a mock HttpClient."""
        return MagicMock()

    @patch("utils.finder.is_out_of_stock")
    @patch("utils.finder.extract_price")
    def test_finds_cheapest_among_multiple_urls(self, mock_extract, mock_stock):
        """Test finds cheapest price when multiple URLs have different prices."""
        products = {
            "Product A": [
                "https://example.com/product1",
                "https://example.com/product2",
                "https://example.com/product3",
            ]
        }

        # Mock HttpClient
        mock_client = self.create_mock_http_client()
        mock_client.fetch_page.return_value = self.create_soup("<div>test</div>")

        # Mock stock check to return False (in stock)
        mock_stock.return_value = False
        # Mock prices: 50.00, 30.00, 45.00
        mock_extract.side_effect = [50.00, 30.00, 45.00]

        results = find_cheapest_prices(products, mock_client)

        self.assertIn("Product A", results.prices)
        self.assertIsNotNone(results.prices["Product A"])
        assert results.prices["Product A"] is not None  # Type narrowing for mypy
        price, url = results.prices["Product A"]
        self.assertEqual(price, 30.00)
        self.assertEqual(url, "https://example.com/product2")

        # Check summary statistics
        self.assertEqual(results.total_products, 1)
        self.assertEqual(results.total_urls_checked, 3)
        self.assertEqual(results.prices_found, 3)

    @patch("utils.finder.is_out_of_stock")
    @patch("utils.finder.extract_price")
    def test_excludes_out_of_stock_products(self, mock_extract, mock_stock):
        """Test excludes out-of-stock products from comparison."""
        products = {
            "Product B": [
                "https://example.com/product1",
                "https://example.com/product2",
                "https://example.com/product3",
            ]
        }

        # Mock HttpClient
        mock_client = self.create_mock_http_client()
        mock_client.fetch_page.return_value = self.create_soup("<div>test</div>")

        # First URL is out of stock, others are in stock
        mock_stock.side_effect = [True, False, False]
        # Prices for in-stock items only (first URL skipped)
        mock_extract.side_effect = [80.00, 60.00]

        results = find_cheapest_prices(products, mock_client)

        self.assertIn("Product B", results.prices)
        self.assertIsNotNone(results.prices["Product B"])
        assert results.prices["Product B"] is not None  # Type narrowing for mypy
        price, url = results.prices["Product B"]
        # Should get cheapest in-stock price (60.00), not the out-of-stock one
        self.assertEqual(price, 60.00)
        self.assertEqual(url, "https://example.com/product3")

        # Check summary statistics
        self.assertEqual(results.out_of_stock, 1)
        self.assertEqual(results.prices_found, 2)
        self.assertEqual(results.total_urls_checked, 3)
        # Check out_of_stock_items tracking
        self.assertIn("Product B", results.out_of_stock_items)
        self.assertEqual(
            results.out_of_stock_items["Product B"], ["https://example.com/product1"]
        )

    @patch("utils.finder.is_out_of_stock")
    @patch("utils.finder.extract_price")
    def test_returns_none_when_no_prices_found(self, mock_extract, mock_stock):
        """Test returns None when no prices can be extracted."""
        products = {
            "Product C": [
                "https://example.com/product1",
                "https://example.com/product2",
            ]
        }

        # Mock HttpClient
        mock_client = self.create_mock_http_client()
        mock_client.fetch_page.return_value = self.create_soup("<div>test</div>")

        mock_stock.return_value = False
        # No prices found
        mock_extract.return_value = None

        results = find_cheapest_prices(products, mock_client)

        self.assertIn("Product C", results.prices)
        self.assertIsNone(results.prices["Product C"])

        # Check summary statistics
        self.assertEqual(results.extraction_errors, 2)
        # Check failed_urls tracking
        self.assertEqual(len(results.failed_urls), 2)
        self.assertIn("https://example.com/product1", results.failed_urls)
        self.assertIn("https://example.com/product2", results.failed_urls)

    @patch("utils.finder.is_out_of_stock")
    @patch("utils.finder.extract_price")
    def test_returns_none_when_all_out_of_stock(self, mock_extract, mock_stock):
        """Test returns None when all products are out of stock."""
        products = {
            "Product D": [
                "https://example.com/product1",
                "https://example.com/product2",
            ]
        }

        # Mock HttpClient
        mock_client = self.create_mock_http_client()
        mock_client.fetch_page.return_value = self.create_soup("<div>test</div>")

        # All out of stock
        mock_stock.return_value = True

        results = find_cheapest_prices(products, mock_client)

        self.assertIn("Product D", results.prices)
        self.assertIsNone(results.prices["Product D"])

        # Check summary statistics
        self.assertEqual(results.out_of_stock, 2)

    def test_handles_fetch_failure(self):
        """Test handles fetch_page returning None."""
        products = {"Product E": ["https://example.com/product1"]}

        # Mock HttpClient with fetch returning None
        mock_client = self.create_mock_http_client()
        mock_client.fetch_page.return_value = None

        results = find_cheapest_prices(products, mock_client)

        self.assertIn("Product E", results.prices)
        self.assertIsNone(results.prices["Product E"])

        # Check summary statistics
        self.assertEqual(results.fetch_errors, 1)
        # Check failed_urls tracking
        self.assertEqual(len(results.failed_urls), 1)
        self.assertIn("https://example.com/product1", results.failed_urls)

    @patch("utils.finder.is_out_of_stock")
    @patch("utils.finder.extract_price")
    def test_handles_multiple_products(self, mock_extract, mock_stock):
        """Test handles multiple products correctly."""
        products = {
            "Product A": [
                "https://example.com/a1",
                "https://example.com/a2",
            ],
            "Product B": ["https://example.com/b1"],
        }

        # Mock HttpClient
        mock_client = self.create_mock_http_client()
        mock_client.fetch_page.return_value = self.create_soup("<div>test</div>")

        mock_stock.return_value = False
        # Prices for Product A (two URLs) then Product B (one URL)
        mock_extract.side_effect = [25.00, 20.00, 15.00]

        results = find_cheapest_prices(products, mock_client)

        self.assertEqual(len(results.prices), 2)
        self.assertIn("Product A", results.prices)
        self.assertIn("Product B", results.prices)

        assert results.prices["Product A"] is not None  # Type narrowing for mypy
        price_a, url_a = results.prices["Product A"]
        self.assertEqual(price_a, 20.00)
        self.assertEqual(url_a, "https://example.com/a2")

        assert results.prices["Product B"] is not None  # Type narrowing for mypy
        price_b, url_b = results.prices["Product B"]
        self.assertEqual(price_b, 15.00)
        self.assertEqual(url_b, "https://example.com/b1")

        # Check summary statistics
        self.assertEqual(results.total_products, 2)
        self.assertEqual(results.prices_found, 3)

    def test_handles_empty_products(self):
        """Test handles empty products dictionary."""
        products: dict[str, list[str]] = {}

        # Mock HttpClient (won't be used)
        mock_client = self.create_mock_http_client()

        results = find_cheapest_prices(products, mock_client)

        self.assertEqual(results.prices, {})
        self.assertEqual(results.total_products, 0)


class TestSearchResults(unittest.TestCase):
    """Test SearchResults formatting and display methods."""

    def test_pluralize(self):
        """Test pluralization logic."""
        results = SearchResults()
        # Singular (count = 1)
        self.assertEqual(results._pluralize(1, "product", "products"), "product")
        # Plural (count != 1)
        self.assertEqual(results._pluralize(0, "product", "products"), "products")
        self.assertEqual(results._pluralize(2, "product", "products"), "products")

    def test_extract_domain_normal_url(self):
        """Test domain extraction from normal URL."""
        results = SearchResults()
        self.assertEqual(
            results._extract_domain("https://example.com/product"), "example.com"
        )

    def test_extract_domain_with_www(self):
        """Test domain extraction removes www. prefix."""
        results = SearchResults()
        self.assertEqual(
            results._extract_domain("https://www.example.com/product"), "example.com"
        )

    def test_extract_domain_malformed_url(self):
        """Test domain extraction with malformed URLs returns full URL."""
        results = SearchResults()
        # Relative path (no netloc)
        self.assertEqual(
            results._extract_domain("/path/to/resource"), "/path/to/resource"
        )
        # Just a path
        self.assertEqual(results._extract_domain("product/123"), "product/123")

    def test_extract_domain_no_scheme(self):
        """Test domain extraction from URL without scheme."""
        results = SearchResults()
        # Without scheme, urlparse might not extract netloc correctly
        result = results._extract_domain("example.com/product")
        # Should return the full string as fallback
        self.assertIn("example.com", result)

    def test_extract_domain_empty_string(self):
        """Test domain extraction with empty string."""
        results = SearchResults()
        self.assertEqual(results._extract_domain(""), "")

    def test_get_success_emoji(self):
        """Test emoji selection based on success rate."""
        results = SearchResults()
        # High (≥80%)
        self.assertEqual(results._get_success_emoji(100.0), "✅")
        self.assertEqual(results._get_success_emoji(80.0), "✅")
        # Medium (50-79%)
        self.assertEqual(results._get_success_emoji(79.9), "⚠️")
        self.assertEqual(results._get_success_emoji(50.0), "⚠️")
        # Low (<50%)
        self.assertEqual(results._get_success_emoji(49.9), "❌")
        self.assertEqual(results._get_success_emoji(0.0), "❌")

    def test_format_success_line_no_urls(self):
        """Test success line when no URLs were checked."""
        results = SearchResults()
        results.total_products = 5
        results.total_urls_checked = 0

        line = results._format_success_line()
        self.assertEqual(line, "**5 products** · No URLs checked")

    def test_format_success_line_with_urls(self):
        """Test success line with URLs checked."""
        results = SearchResults()
        results.total_products = 3
        results.total_urls_checked = 10
        results.prices_found = 8

        line = results._format_success_line()
        self.assertIn("8/10 URLs", line)
        self.assertIn("80% success", line)
        self.assertIn("3 products", line)
        self.assertIn("✅", line)

    def test_format_issues_line_no_issues(self):
        """Test issues line when there are no issues."""
        results = SearchResults()
        line = results._format_issues_line()
        self.assertIsNone(line)

    def test_format_issues_line_single_issue(self):
        """Test issues line with single issue type."""
        results = SearchResults()
        results.out_of_stock = 3

        line = results._format_issues_line()
        assert line is not None  # Type narrowing for mypy
        self.assertIn("📦 3 out of stock", line)
        self.assertNotIn("fetch errors", line)
        self.assertNotIn("extraction errors", line)

    def test_format_issues_line_multiple_issues(self):
        """Test issues line with multiple issue types."""
        results = SearchResults()
        results.out_of_stock = 2
        results.fetch_errors = 1
        results.extraction_errors = 3

        line = results._format_issues_line()
        assert line is not None  # Type narrowing for mypy
        self.assertIn("📦 2 out of stock", line)
        self.assertIn("🌐 1 fetch error", line)
        self.assertIn("🔍 3 extraction errors", line)
        self.assertIn(" · ", line)  # Should have separators

    def test_format_issues_line_singular_forms(self):
        """Test issues line uses singular forms when count is 1."""
        results = SearchResults()
        results.fetch_errors = 1
        results.extraction_errors = 1

        line = results._format_issues_line()
        assert line is not None  # Type narrowing for mypy
        self.assertIn("🌐 1 fetch error", line)
        self.assertIn("🔍 1 extraction error", line)
        self.assertNotIn("errors", line)

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_print_out_of_stock_items_empty(self, mock_stdout):
        """Test printing out-of-stock items when none exist."""
        results = SearchResults()
        results._print_out_of_stock_items()

        output = mock_stdout.getvalue()
        self.assertEqual(output, "")

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_print_out_of_stock_items_single_product(self, mock_stdout):
        """Test printing out-of-stock items for single product."""
        results = SearchResults()
        results.out_of_stock_items = {
            "Product A": ["https://www.example.com/product1", "https://store.com/item"]
        }

        results._print_out_of_stock_items()

        output = mock_stdout.getvalue()
        self.assertIn("**Out of Stock:**", output)
        self.assertIn("**Product A**", output)
        self.assertIn("example.com", output)
        self.assertIn("store.com", output)

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_print_out_of_stock_items_multiple_products(self, mock_stdout):
        """Test printing out-of-stock items for multiple products."""
        results = SearchResults()
        results.out_of_stock_items = {
            "Product A": ["https://example.com/a"],
            "Product B": ["https://store.com/b", "https://shop.com/b"],
        }

        results._print_out_of_stock_items()

        output = mock_stdout.getvalue()
        self.assertIn("**Product A**", output)
        self.assertIn("**Product B**", output)
        self.assertIn("example.com", output)
        self.assertIn("store.com", output)
        self.assertIn("shop.com", output)

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_print_out_of_stock_items_with_malformed_urls(self, mock_stdout):
        """Test printing out-of-stock items handles malformed URLs gracefully."""
        results = SearchResults()
        results.out_of_stock_items = {
            "Product A": [
                "https://example.com/product",
                "/relative/path",
                "malformed-url",
            ]
        }

        results._print_out_of_stock_items()

        output = mock_stdout.getvalue()
        self.assertIn("**Out of Stock:**", output)
        self.assertIn("**Product A**", output)
        self.assertIn("example.com", output)
        # Malformed URLs should show the full URL as fallback
        self.assertIn("/relative/path", output)
        self.assertIn("malformed-url", output)

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_print_failed_urls_empty(self, mock_stdout):
        """Test printing failed URLs when none exist."""
        results = SearchResults()
        results._print_failed_urls()

        output = mock_stdout.getvalue()
        self.assertEqual(output, "")

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_print_failed_urls_few(self, mock_stdout):
        """Test printing failed URLs when 3 or fewer."""
        results = SearchResults()
        results.failed_urls = ["https://example.com/1", "https://example.com/2"]

        results._print_failed_urls()

        output = mock_stdout.getvalue()
        self.assertIn("**Failed URLs** (2):", output)
        self.assertIn("https://example.com/1", output)
        self.assertIn("https://example.com/2", output)
        self.assertNotIn("more...", output)

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_print_failed_urls_many(self, mock_stdout):
        """Test printing failed URLs with truncation (>3)."""
        results = SearchResults()
        results.failed_urls = [
            "https://example.com/1",
            "https://example.com/2",
            "https://example.com/3",
            "https://example.com/4",
            "https://example.com/5",
        ]

        results._print_failed_urls()

        output = mock_stdout.getvalue()
        self.assertIn("**Failed URLs** (5):", output)
        self.assertIn("https://example.com/1", output)
        self.assertIn("https://example.com/2", output)
        self.assertIn("https://example.com/3", output)
        self.assertNotIn("https://example.com/4", output)
        self.assertNotIn("https://example.com/5", output)
        self.assertIn("2 more...", output)

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_print_summary_minimal(self, mock_stdout):
        """Test print_summary with minimal data (uses singular forms)."""
        results = SearchResults()
        results.total_products = 1
        results.total_urls_checked = 1
        results.prices_found = 1

        results.print_summary()

        output = mock_stdout.getvalue()
        self.assertIn("## 📊 Search Summary", output)
        self.assertIn("1/1 URL", output)
        self.assertIn("100% success", output)
        self.assertIn("1 product", output)
        # Should not contain plural forms
        self.assertNotIn("URLs", output)
        self.assertNotIn("products", output)

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_print_summary_with_issues(self, mock_stdout):
        """Test print_summary with various issues."""
        results = SearchResults()
        results.total_products = 5
        results.total_urls_checked = 15
        results.prices_found = 10
        results.out_of_stock = 2
        results.fetch_errors = 1
        results.extraction_errors = 2
        results.out_of_stock_items = {"Product A": ["https://example.com/a"]}
        # failed_urls should match fetch_errors + extraction_errors = 1 + 2 = 3
        results.failed_urls = [
            "https://example.com/failed1",
            "https://example.com/failed2",
            "https://example.com/failed3",
        ]

        results.print_summary()

        output = mock_stdout.getvalue()
        self.assertIn("## 📊 Search Summary", output)
        self.assertIn("10/15 URLs", output)
        self.assertIn("67% success", output)
        self.assertIn("📦 2 out of stock", output)
        self.assertIn("🌐 1 fetch error", output)  # Singular form
        self.assertIn("🔍 2 extraction errors", output)
        self.assertIn("**Out of Stock:**", output)
        self.assertIn("**Product A**", output)
        self.assertIn("**Failed URLs** (3):", output)


if __name__ == "__main__":
    unittest.main(verbosity=2)
