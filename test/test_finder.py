"""Tests for price comparison logic."""

# pylint: disable=too-many-lines

import io
import unittest
from unittest.mock import patch, MagicMock
from bs4 import BeautifulSoup

from utils.finder import find_cheapest_prices, find_all_prices
from utils.price_models import SearchResults
from utils.search_results_formatter import SearchResultsFormatter
from utils.string_utils import pluralize
from utils.url_utils import extract_domain


class TestFindCheapestPrices(unittest.TestCase):
    """Test finding cheapest prices across multiple products and URLs."""

    def create_soup(self, html):
        """Helper to create BeautifulSoup from HTML."""
        return BeautifulSoup(html, "lxml")

    def create_mock_http_client(self):
        """Helper to create a mock HttpClient."""
        return MagicMock()

    @patch("utils.price_collection.is_out_of_stock")
    @patch("utils.price_collection.extract_price")
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
        result = results.prices["Product A"]
        self.assertEqual(result.price, 30.00)
        self.assertEqual(result.url, "https://example.com/product2")

        # Check summary statistics
        self.assertEqual(results.statistics.total_products, 1)
        self.assertEqual(results.statistics.total_urls_checked, 3)
        self.assertEqual(results.statistics.prices_found, 3)

    @patch("utils.price_collection.is_out_of_stock")
    @patch("utils.price_collection.extract_price")
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
        result = results.prices["Product B"]
        # Should get cheapest in-stock price (60.00), not the out-of-stock one
        self.assertEqual(result.price, 60.00)
        self.assertEqual(result.url, "https://example.com/product3")

        # Check summary statistics
        self.assertEqual(results.statistics.out_of_stock, 1)
        self.assertEqual(results.statistics.prices_found, 2)
        self.assertEqual(results.statistics.total_urls_checked, 3)
        # Check out_of_stock_items tracking
        self.assertIn("Product B", results.statistics.out_of_stock_items)
        self.assertEqual(results.statistics.out_of_stock_items["Product B"], ["https://example.com/product1"])

    @patch("utils.price_collection.is_out_of_stock")
    @patch("utils.price_collection.extract_price")
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
        self.assertEqual(results.statistics.extraction_errors, 2)
        # Check failed_urls tracking
        self.assertEqual(len(results.statistics.failed_urls), 2)
        self.assertIn("https://example.com/product1", results.statistics.failed_urls)
        self.assertIn("https://example.com/product2", results.statistics.failed_urls)

    @patch("utils.price_collection.is_out_of_stock")
    @patch("utils.price_collection.extract_price")
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
        self.assertEqual(results.statistics.out_of_stock, 2)

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
        self.assertEqual(results.statistics.fetch_errors, 1)
        # Check failed_urls tracking
        self.assertEqual(len(results.statistics.failed_urls), 1)
        self.assertIn("https://example.com/product1", results.statistics.failed_urls)

    @patch("utils.price_collection.is_out_of_stock")
    @patch("utils.price_collection.extract_price")
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
        result_a = results.prices["Product A"]
        self.assertEqual(result_a.price, 20.00)
        self.assertEqual(result_a.url, "https://example.com/a2")

        assert results.prices["Product B"] is not None  # Type narrowing for mypy
        result_b = results.prices["Product B"]
        self.assertEqual(result_b.price, 15.00)
        self.assertEqual(result_b.url, "https://example.com/b1")

        # Check summary statistics
        self.assertEqual(results.statistics.total_products, 2)
        self.assertEqual(results.statistics.prices_found, 3)

    def test_handles_empty_products(self):
        """Test handles empty products dictionary."""
        products: dict[str, list[str]] = {}

        # Mock HttpClient (won't be used)
        mock_client = self.create_mock_http_client()

        results = find_cheapest_prices(products, mock_client)

        self.assertEqual(results.prices, {})
        self.assertEqual(results.statistics.total_products, 0)


class TestSearchResults(unittest.TestCase):
    """Test SearchResultsFormatter formatting and display methods."""

    def test_pluralize(self):
        """Test pluralization logic."""
        # Singular (count = 1)
        self.assertEqual(pluralize(1, "product", "products"), "product")
        # Plural (count != 1)
        self.assertEqual(pluralize(0, "product", "products"), "products")
        self.assertEqual(pluralize(2, "product", "products"), "products")

    def test_extract_domain_normal_url(self):
        """Test domain extraction from normal URL."""
        self.assertEqual(extract_domain("https://example.com/product"), "example.com")

    def test_extract_domain_with_www(self):
        """Test domain extraction removes www. prefix."""
        self.assertEqual(extract_domain("https://www.example.com/product"), "example.com")

    def test_extract_domain_malformed_url(self):
        """Test domain extraction with malformed URLs returns full URL."""
        # Relative path (no netloc)
        self.assertEqual(extract_domain("/path/to/resource"), "/path/to/resource")
        # Just a path
        self.assertEqual(extract_domain("product/123"), "product/123")

    def test_extract_domain_no_scheme(self):
        """Test domain extraction from URL without scheme."""
        # Without scheme, urlparse might not extract netloc correctly
        result = extract_domain("example.com/product")
        # Should return the full string as fallback
        self.assertIn("example.com", result)

    def test_extract_domain_empty_string(self):
        """Test domain extraction with empty string."""
        self.assertEqual(extract_domain(""), "")

    def test_get_success_emoji(self):
        """Test emoji selection based on success rate."""
        results = SearchResults()
        formatter = SearchResultsFormatter(results)
        # High (≥80%)
        self.assertEqual(formatter._get_success_emoji(100.0), "✅")
        self.assertEqual(formatter._get_success_emoji(80.0), "✅")
        # Medium (50-79%)
        self.assertEqual(formatter._get_success_emoji(79.9), "⚠️")
        self.assertEqual(formatter._get_success_emoji(50.0), "⚠️")
        # Low (<50%)
        self.assertEqual(formatter._get_success_emoji(49.9), "❌")
        self.assertEqual(formatter._get_success_emoji(0.0), "❌")

    def test_format_success_line_no_urls(self):
        """Test success line when no URLs were checked."""
        results = SearchResults()
        results.statistics.total_products = 5
        results.statistics.total_urls_checked = 0
        formatter = SearchResultsFormatter(results)

        line = formatter._format_success_line(markdown=True)
        self.assertEqual(line, "**5 products** · No URLs checked")

    def test_format_success_line_with_urls(self):
        """Test success line with URLs checked."""
        results = SearchResults()
        results.statistics.total_products = 3
        results.statistics.total_urls_checked = 10
        results.statistics.prices_found = 8
        formatter = SearchResultsFormatter(results)

        line = formatter._format_success_line(markdown=True)
        self.assertIn("8/10 URLs", line)
        self.assertIn("80% success", line)
        self.assertIn("3 products", line)
        self.assertIn("✅", line)

    def test_format_issues_line_no_issues(self):
        """Test issues line when there are no issues."""
        results = SearchResults()
        formatter = SearchResultsFormatter(results)
        line = formatter._format_issues_line(markdown=True)
        self.assertIsNone(line)

    def test_format_issues_line_single_issue(self):
        """Test issues line with single issue type."""
        results = SearchResults()
        results.statistics.out_of_stock = 3
        formatter = SearchResultsFormatter(results)

        line = formatter._format_issues_line(markdown=True)
        assert line is not None  # Type narrowing for mypy
        self.assertIn("📦 3 out of stock", line)
        self.assertNotIn("fetch errors", line)
        self.assertNotIn("extraction errors", line)

    def test_format_issues_line_multiple_issues(self):
        """Test issues line with multiple issue types."""
        results = SearchResults()
        results.statistics.out_of_stock = 2
        results.statistics.fetch_errors = 1
        results.statistics.extraction_errors = 3
        formatter = SearchResultsFormatter(results)

        line = formatter._format_issues_line(markdown=True)
        assert line is not None  # Type narrowing for mypy
        self.assertIn("📦 2 out of stock", line)
        self.assertIn("🌐 1 fetch error", line)
        self.assertIn("🔍 3 extraction errors", line)
        self.assertIn(" · ", line)  # Should have separators

    def test_format_issues_line_singular_forms(self):
        """Test issues line uses singular forms when count is 1."""
        results = SearchResults()
        results.statistics.fetch_errors = 1
        results.statistics.extraction_errors = 1

        formatter = SearchResultsFormatter(results)
        line = formatter._format_issues_line(markdown=True)
        assert line is not None  # Type narrowing for mypy
        self.assertIn("🌐 1 fetch error", line)
        self.assertIn("🔍 1 extraction error", line)
        self.assertNotIn("errors", line)

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_print_out_of_stock_items_empty(self, mock_stdout):
        """Test printing out-of-stock items when none exist."""
        results = SearchResults()
        formatter = SearchResultsFormatter(results)
        formatter._print_out_of_stock_items(markdown=True)

        output = mock_stdout.getvalue()
        self.assertEqual(output, "")

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_print_out_of_stock_items_single_product(self, mock_stdout):
        """Test printing out-of-stock items for single product."""
        results = SearchResults()
        results.statistics.out_of_stock_items = {
            "Product A": ["https://www.example.com/product1", "https://store.com/item"]
        }

        formatter = SearchResultsFormatter(results)
        formatter._print_out_of_stock_items(markdown=True)

        output = mock_stdout.getvalue()
        self.assertIn("**Out of Stock:**", output)
        self.assertIn("**Product A**", output)
        self.assertIn("example.com", output)
        self.assertIn("store.com", output)

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_print_out_of_stock_items_multiple_products(self, mock_stdout):
        """Test printing out-of-stock items for multiple products."""
        results = SearchResults()
        results.statistics.out_of_stock_items = {
            "Product A": ["https://example.com/a"],
            "Product B": ["https://store.com/b", "https://shop.com/b"],
        }

        formatter = SearchResultsFormatter(results)
        formatter._print_out_of_stock_items(markdown=True)

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
        results.statistics.out_of_stock_items = {
            "Product A": [
                "https://example.com/product",
                "/relative/path",
                "malformed-url",
            ]
        }

        formatter = SearchResultsFormatter(results)
        formatter._print_out_of_stock_items(markdown=True)

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
        formatter = SearchResultsFormatter(results)
        formatter._print_failed_urls(markdown=True)

        output = mock_stdout.getvalue()
        self.assertEqual(output, "")

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_print_failed_urls_few(self, mock_stdout):
        """Test printing failed URLs when 3 or fewer."""
        results = SearchResults()
        results.statistics.failed_urls = ["https://example.com/1", "https://example.com/2"]

        formatter = SearchResultsFormatter(results)
        formatter._print_failed_urls(markdown=True)

        output = mock_stdout.getvalue()
        self.assertIn("**Failed URLs** (2):", output)
        self.assertIn("https://example.com/1", output)
        self.assertIn("https://example.com/2", output)
        self.assertNotIn("more...", output)

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_print_failed_urls_many(self, mock_stdout):
        """Test printing failed URLs with truncation (>3)."""
        results = SearchResults()
        results.statistics.failed_urls = [
            "https://example.com/1",
            "https://example.com/2",
            "https://example.com/3",
            "https://example.com/4",
            "https://example.com/5",
        ]

        formatter = SearchResultsFormatter(results)
        formatter._print_failed_urls(markdown=True)

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
        results.statistics.total_products = 1
        results.statistics.total_urls_checked = 1
        results.statistics.prices_found = 1

        results.print_summary(markdown=True)

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
        results.statistics.total_products = 5
        results.statistics.total_urls_checked = 15
        results.statistics.prices_found = 10
        results.statistics.out_of_stock = 2
        results.statistics.fetch_errors = 1
        results.statistics.extraction_errors = 2
        results.statistics.out_of_stock_items = {"Product A": ["https://example.com/a"]}
        # failed_urls should match fetch_errors + extraction_errors = 1 + 2 = 3
        results.statistics.failed_urls = [
            "https://example.com/failed1",
            "https://example.com/failed2",
            "https://example.com/failed3",
        ]

        results.print_summary(markdown=True)

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

    # ========================================================================
    # Text format tests (markdown=False)
    # ========================================================================

    def test_format_success_line_text_no_urls(self):
        """Test success line in text format when no URLs were checked."""
        results = SearchResults()
        results.statistics.total_products = 5
        results.statistics.total_urls_checked = 0

        formatter = SearchResultsFormatter(results)
        line = formatter._format_success_line(markdown=False)
        self.assertEqual(line, "5 products · No URLs checked")
        # Should NOT contain markdown bold markers
        self.assertNotIn("**", line)

    def test_format_success_line_text_with_urls(self):
        """Test success line in text format with URLs checked."""
        results = SearchResults()
        results.statistics.total_products = 3
        results.statistics.total_urls_checked = 10
        results.statistics.prices_found = 8

        formatter = SearchResultsFormatter(results)
        line = formatter._format_success_line(markdown=False)
        self.assertIn("8/10 URLs", line)
        self.assertIn("80% success", line)
        self.assertIn("3 products", line)
        self.assertIn("✅", line)
        # Should NOT contain markdown bold markers
        self.assertNotIn("**", line)

    def test_format_issues_line_text_multiple_issues(self):
        """Test issues line in text format with multiple issue types."""
        results = SearchResults()
        results.statistics.out_of_stock = 2
        results.statistics.fetch_errors = 1
        results.statistics.extraction_errors = 3

        formatter = SearchResultsFormatter(results)
        line = formatter._format_issues_line(markdown=False)
        assert line is not None  # Type narrowing for mypy
        self.assertIn("Issues:", line)
        self.assertIn("📦 2 out of stock", line)
        self.assertIn("🌐 1 fetch error", line)
        self.assertIn("🔍 3 extraction errors", line)
        # Should NOT contain markdown italic markers
        self.assertNotIn("_", line)

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_print_out_of_stock_items_text_single_product(self, mock_stdout):
        """Test printing out-of-stock items in text format."""
        results = SearchResults()
        results.statistics.out_of_stock_items = {
            "Product A": ["https://www.example.com/product1", "https://store.com/item"]
        }

        formatter = SearchResultsFormatter(results)
        formatter._print_out_of_stock_items(markdown=False)

        output = mock_stdout.getvalue()
        self.assertIn("Out of Stock:", output)
        self.assertIn("Product A", output)
        self.assertIn("example.com", output)
        self.assertIn("store.com", output)
        # Should use bullet points (•) instead of markdown list syntax
        self.assertIn("  •", output)
        # Should NOT contain markdown bold markers
        self.assertNotIn("**", output)

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_print_out_of_stock_items_text_multiple_products(self, mock_stdout):
        """Test printing out-of-stock items in text format for multiple products."""
        results = SearchResults()
        results.statistics.out_of_stock_items = {
            "Product A": ["https://example.com/a"],
            "Product B": ["https://store.com/b", "https://shop.com/b"],
        }

        formatter = SearchResultsFormatter(results)
        formatter._print_out_of_stock_items(markdown=False)

        output = mock_stdout.getvalue()
        self.assertIn("Product A", output)
        self.assertIn("Product B", output)
        self.assertIn("example.com", output)
        self.assertIn("store.com", output)
        self.assertIn("shop.com", output)
        # Should use bullet points (•) instead of markdown list syntax
        self.assertIn("  •", output)
        # Should NOT contain markdown markers
        self.assertNotIn("**", output)
        self.assertNotIn("- **", output)

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_print_failed_urls_text_few(self, mock_stdout):
        """Test printing failed URLs in text format when 3 or fewer."""
        results = SearchResults()
        results.statistics.failed_urls = ["https://example.com/1", "https://example.com/2"]

        formatter = SearchResultsFormatter(results)
        formatter._print_failed_urls(markdown=False)

        output = mock_stdout.getvalue()
        self.assertIn("Failed URLs (2):", output)
        self.assertIn("https://example.com/1", output)
        self.assertIn("https://example.com/2", output)
        # Should use bullet points (•) instead of markdown list syntax
        self.assertIn("  •", output)
        # Should NOT contain markdown markers
        self.assertNotIn("**", output)
        self.assertNotIn("`", output)  # No backticks around URLs
        self.assertNotIn("more...", output)

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_print_failed_urls_text_many(self, mock_stdout):
        """Test printing failed URLs in text format with truncation (>3)."""
        results = SearchResults()
        results.statistics.failed_urls = [
            "https://example.com/1",
            "https://example.com/2",
            "https://example.com/3",
            "https://example.com/4",
            "https://example.com/5",
        ]

        formatter = SearchResultsFormatter(results)
        formatter._print_failed_urls(markdown=False)

        output = mock_stdout.getvalue()
        self.assertIn("Failed URLs (5):", output)
        self.assertIn("https://example.com/1", output)
        self.assertIn("https://example.com/2", output)
        self.assertIn("https://example.com/3", output)
        self.assertNotIn("https://example.com/4", output)
        self.assertNotIn("https://example.com/5", output)
        self.assertIn("2 more...", output)
        # Should NOT contain markdown markers
        self.assertNotIn("**", output)
        self.assertNotIn("`", output)  # No backticks
        self.assertNotIn("_", output)  # No italic markers

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_print_summary_text_minimal(self, mock_stdout):
        """Test print_summary in text format with minimal data."""
        results = SearchResults()
        results.statistics.total_products = 1
        results.statistics.total_urls_checked = 1
        results.statistics.prices_found = 1

        results.print_summary(markdown=False)

        output = mock_stdout.getvalue()
        # Should have text format header with separator line
        self.assertIn("📊 Search Summary", output)
        self.assertIn("=" * 70, output)
        # Should NOT have markdown header
        self.assertNotIn("##", output)
        self.assertIn("1/1 URL", output)
        self.assertIn("100% success", output)
        self.assertIn("1 product", output)
        # Should NOT contain markdown markers
        self.assertNotIn("**", output)

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_print_summary_text_with_issues(self, mock_stdout):
        """Test print_summary in text format with various issues."""
        results = SearchResults()
        results.statistics.total_products = 5
        results.statistics.total_urls_checked = 15
        results.statistics.prices_found = 10
        results.statistics.out_of_stock = 2
        results.statistics.fetch_errors = 1
        results.statistics.extraction_errors = 2
        results.statistics.out_of_stock_items = {"Product A": ["https://example.com/a"]}
        results.statistics.failed_urls = [
            "https://example.com/failed1",
            "https://example.com/failed2",
            "https://example.com/failed3",
        ]

        results.print_summary(markdown=False)

        output = mock_stdout.getvalue()
        # Should have text format header with separator line
        self.assertIn("📊 Search Summary", output)
        self.assertIn("=" * 70, output)
        # Should NOT have markdown header
        self.assertNotIn("##", output)
        self.assertIn("10/15 URLs", output)
        self.assertIn("67% success", output)
        self.assertIn("Issues:", output)
        self.assertIn("📦 2 out of stock", output)
        self.assertIn("🌐 1 fetch error", output)
        self.assertIn("🔍 2 extraction errors", output)
        self.assertIn("Out of Stock:", output)
        self.assertIn("Product A", output)
        self.assertIn("Failed URLs (3):", output)
        # Should NOT contain markdown markers
        self.assertNotIn("**", output)
        self.assertNotIn("_📦", output)  # No italic markers around issues


class TestFindAllPrices(unittest.TestCase):
    """Test finding all prices for optimization across stores."""

    def create_soup(self, html: str) -> BeautifulSoup:
        """Helper to create BeautifulSoup from HTML.

        Args:
            html: HTML string to parse

        Returns:
            BeautifulSoup object
        """
        return BeautifulSoup(html, "lxml")

    def create_mock_http_client(self) -> MagicMock:
        """Helper to create a mock HttpClient.

        Returns:
            Mock HttpClient
        """
        return MagicMock()

    @patch("utils.price_collection.is_out_of_stock")
    @patch("utils.price_collection.extract_price")
    def test_returns_all_prices_not_just_cheapest(self, mock_extract: MagicMock, mock_stock: MagicMock) -> None:
        """Test returns ALL prices across stores, not just the cheapest."""
        products = {
            "Product A (100ml)": [
                "https://store1.com/product",
                "https://store2.com/product",
                "https://store3.com/product",
            ]
        }

        # Mock HttpClient
        mock_client = self.create_mock_http_client()
        mock_client.fetch_page.return_value = self.create_soup("<div>test</div>")

        # All in stock
        mock_stock.return_value = False
        # Different prices: 50.00, 30.00, 45.00
        mock_extract.side_effect = [50.00, 30.00, 45.00]

        all_prices = find_all_prices(products, mock_client)

        # Should return ALL three prices, not just cheapest
        self.assertIn("Product A (100ml)", all_prices)
        self.assertEqual(len(all_prices["Product A (100ml)"]), 3)

        prices = [p.price for p in all_prices["Product A (100ml)"]]
        self.assertEqual(sorted(prices), [30.00, 45.00, 50.00])

        # Check that each price has correct URL
        urls = [p.url for p in all_prices["Product A (100ml)"]]
        self.assertEqual(len(urls), 3)
        self.assertIn("https://store1.com/product", urls)
        self.assertIn("https://store2.com/product", urls)
        self.assertIn("https://store3.com/product", urls)

    @patch("utils.price_collection.is_out_of_stock")
    @patch("utils.price_collection.extract_price")
    def test_returns_empty_list_when_all_out_of_stock(self, mock_extract: MagicMock, mock_stock: MagicMock) -> None:
        """Test returns empty list when all URLs are out of stock."""
        products = {
            "Product B": [
                "https://store1.com/product",
                "https://store2.com/product",
            ]
        }

        # Mock HttpClient
        mock_client = self.create_mock_http_client()
        mock_client.fetch_page.return_value = self.create_soup("<div>test</div>")

        # All out of stock
        mock_stock.return_value = True

        all_prices = find_all_prices(products, mock_client)

        # Should return empty list
        self.assertIn("Product B", all_prices)
        self.assertEqual(all_prices["Product B"], [])

    @patch("utils.price_collection.is_out_of_stock")
    @patch("utils.price_collection.extract_price")
    def test_skips_out_of_stock_includes_in_stock(self, mock_extract: MagicMock, mock_stock: MagicMock) -> None:
        """Test skips out-of-stock items but includes in-stock ones."""
        products = {
            "Product C": [
                "https://store1.com/product",
                "https://store2.com/product",
                "https://store3.com/product",
            ]
        }

        # Mock HttpClient
        mock_client = self.create_mock_http_client()
        mock_client.fetch_page.return_value = self.create_soup("<div>test</div>")

        # First and third are out of stock, second is in stock
        mock_stock.side_effect = [True, False, True]
        # Only one price should be requested (for in-stock item)
        mock_extract.return_value = 25.00

        all_prices = find_all_prices(products, mock_client)

        # Should only have one price
        self.assertIn("Product C", all_prices)
        self.assertEqual(len(all_prices["Product C"]), 1)
        self.assertEqual(all_prices["Product C"][0].price, 25.00)
        self.assertEqual(all_prices["Product C"][0].url, "https://store2.com/product")

    @patch("utils.price_collection.is_out_of_stock")
    @patch("utils.price_collection.extract_price")
    def test_handles_fetch_failures_gracefully(self, mock_extract: MagicMock, mock_stock: MagicMock) -> None:
        """Test handles fetch failures gracefully and continues."""
        products = {
            "Product D": [
                "https://store1.com/product",
                "https://store2.com/product",
                "https://store3.com/product",
            ]
        }

        # Mock HttpClient - first fetch fails, others succeed
        mock_client = self.create_mock_http_client()
        mock_client.fetch_page.side_effect = [
            None,  # Fetch failure
            self.create_soup("<div>test</div>"),
            self.create_soup("<div>test</div>"),
        ]

        # In stock for successful fetches
        mock_stock.return_value = False
        mock_extract.side_effect = [40.00, 35.00]

        all_prices = find_all_prices(products, mock_client)

        # Should have two prices (one fetch failed)
        self.assertIn("Product D", all_prices)
        self.assertEqual(len(all_prices["Product D"]), 2)
        prices = [p.price for p in all_prices["Product D"]]
        self.assertEqual(sorted(prices), [35.00, 40.00])

    @patch("utils.price_collection.is_out_of_stock")
    @patch("utils.price_collection.extract_price")
    def test_handles_price_extraction_failures(self, mock_extract: MagicMock, mock_stock: MagicMock) -> None:
        """Test handles price extraction failures gracefully."""
        products = {
            "Product E": [
                "https://store1.com/product",
                "https://store2.com/product",
                "https://store3.com/product",
            ]
        }

        # Mock HttpClient
        mock_client = self.create_mock_http_client()
        mock_client.fetch_page.return_value = self.create_soup("<div>test</div>")

        # All in stock
        mock_stock.return_value = False
        # First extraction fails (returns None), others succeed
        mock_extract.side_effect = [None, 42.00, 38.00]

        all_prices = find_all_prices(products, mock_client)

        # Should have two prices (one extraction failed)
        self.assertIn("Product E", all_prices)
        self.assertEqual(len(all_prices["Product E"]), 2)
        prices = [p.price for p in all_prices["Product E"]]
        self.assertEqual(sorted(prices), [38.00, 42.00])

        # Should call remove_from_cache for failed extraction
        mock_client.remove_from_cache.assert_called_once_with("https://store1.com/product")

    @patch("utils.price_collection.is_out_of_stock")
    @patch("utils.price_collection.extract_price")
    def test_calculates_price_per_100ml_when_volume_available(
        self, mock_extract: MagicMock, mock_stock: MagicMock
    ) -> None:
        """Test calculates price_per_100ml correctly when volume info is available."""
        products = {
            "Cerave Cleanser (236ml)": [
                "https://store1.com/product",
                "https://store2.com/product",
            ]
        }

        # Mock HttpClient
        mock_client = self.create_mock_http_client()
        mock_client.fetch_page.return_value = self.create_soup("<div>test</div>")

        # All in stock
        mock_stock.return_value = False
        mock_extract.side_effect = [10.00, 12.00]

        all_prices = find_all_prices(products, mock_client)

        # Should have both prices with price_per_100ml calculated
        self.assertIn("Cerave Cleanser (236ml)", all_prices)
        self.assertEqual(len(all_prices["Cerave Cleanser (236ml)"]), 2)

        # Check first price: €10.00 for 236ml = €4.24/100ml
        price1 = all_prices["Cerave Cleanser (236ml)"][0]
        self.assertEqual(price1.price, 10.00)
        self.assertIsNotNone(price1.price_per_100ml)
        assert price1.price_per_100ml is not None  # Type narrowing
        self.assertAlmostEqual(price1.price_per_100ml, 4.24, places=2)

        # Check second price: €12.00 for 236ml = €5.08/100ml
        price2 = all_prices["Cerave Cleanser (236ml)"][1]
        self.assertEqual(price2.price, 12.00)
        self.assertIsNotNone(price2.price_per_100ml)
        assert price2.price_per_100ml is not None  # Type narrowing
        self.assertAlmostEqual(price2.price_per_100ml, 5.08, places=2)

    @patch("utils.price_collection.is_out_of_stock")
    @patch("utils.price_collection.extract_price")
    def test_price_per_100ml_none_when_no_volume_info(self, mock_extract: MagicMock, mock_stock: MagicMock) -> None:
        """Test price_per_100ml is None when product name has no volume info."""
        products = {
            "Some Product": [
                "https://store1.com/product",
            ]
        }

        # Mock HttpClient
        mock_client = self.create_mock_http_client()
        mock_client.fetch_page.return_value = self.create_soup("<div>test</div>")

        mock_stock.return_value = False
        mock_extract.return_value = 20.00

        all_prices = find_all_prices(products, mock_client)

        # Should have price but price_per_100ml should be None
        self.assertIn("Some Product", all_prices)
        self.assertEqual(len(all_prices["Some Product"]), 1)
        self.assertEqual(all_prices["Some Product"][0].price, 20.00)
        self.assertIsNone(all_prices["Some Product"][0].price_per_100ml)

    @patch("utils.price_collection.is_out_of_stock")
    @patch("utils.price_collection.extract_price")
    def test_works_with_multiple_products(self, mock_extract: MagicMock, mock_stock: MagicMock) -> None:
        """Test correctly processes multiple products."""
        products = {
            "Product A (100ml)": [
                "https://store1.com/productA",
                "https://store2.com/productA",
            ],
            "Product B (200ml)": [
                "https://store1.com/productB",
                "https://store2.com/productB",
            ],
        }

        # Mock HttpClient
        mock_client = self.create_mock_http_client()
        mock_client.fetch_page.return_value = self.create_soup("<div>test</div>")

        # All in stock
        mock_stock.return_value = False
        # Prices for Product A, then Product B
        mock_extract.side_effect = [10.00, 12.00, 20.00, 22.00]

        all_prices = find_all_prices(products, mock_client)

        # Should have both products
        self.assertIn("Product A (100ml)", all_prices)
        self.assertIn("Product B (200ml)", all_prices)

        # Product A should have 2 prices
        self.assertEqual(len(all_prices["Product A (100ml)"]), 2)
        prices_a = [p.price for p in all_prices["Product A (100ml)"]]
        self.assertEqual(sorted(prices_a), [10.00, 12.00])

        # Product B should have 2 prices
        self.assertEqual(len(all_prices["Product B (200ml)"]), 2)
        prices_b = [p.price for p in all_prices["Product B (200ml)"]]
        self.assertEqual(sorted(prices_b), [20.00, 22.00])

    @patch("utils.price_collection.is_out_of_stock")
    @patch("utils.price_collection.extract_price")
    def test_empty_products_returns_empty_dict(self, mock_extract: MagicMock, mock_stock: MagicMock) -> None:
        """Test returns empty dict when given empty products dict."""
        products: dict[str, list[str]] = {}

        mock_client = self.create_mock_http_client()

        all_prices = find_all_prices(products, mock_client)

        self.assertEqual(all_prices, {})
        # Should not call fetch_page at all
        mock_client.fetch_page.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
