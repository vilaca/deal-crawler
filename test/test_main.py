"""Tests for main.py CLI entry point."""

import unittest
from unittest.mock import MagicMock, patch

from main import main
from utils.finder import PriceResult, SearchResults


class TestMainFunction(unittest.TestCase):
    """Test the main() function entry point."""

    @patch("main.find_cheapest_prices")
    @patch("main.load_products")
    @patch("main.HttpClient")
    @patch("main.print_results_text")
    @patch("sys.argv", ["main.py", "--all-sizes"])
    def test_main_default_text_format(self, mock_print_text, mock_http_client, mock_load_products, mock_find_prices):
        """Test main() uses text format by default (no --markdown flag)."""
        # Setup mocks
        mock_products = {"Product A": ["https://example.com/a"]}
        mock_load_products.return_value = mock_products

        mock_results = MagicMock(spec=SearchResults)
        mock_results.prices = {"Product A": PriceResult(price=29.99, url="https://example.com/a")}
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
    @patch("sys.argv", ["main.py", "--markdown", "--all-sizes"])
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
        mock_results.prices = {"Product A": PriceResult(price=29.99, url="https://example.com/a")}
        mock_find_prices.return_value = mock_results

        # Run main
        main()

        # Verify markdown format was used
        mock_print_markdown.assert_called_once_with(mock_results)
        mock_results.print_summary.assert_called_once_with(markdown=True)

    @patch("main.load_products")
    @patch("sys.argv", ["main.py", "--all-sizes"])
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
    @patch("sys.argv", ["main.py", "--all-sizes"])
    def test_main_uses_http_client_context_manager(
        self, mock_print_text, mock_http_client, mock_load_products, mock_find_prices
    ):
        """Test main() properly uses HttpClient as context manager."""
        # Setup mocks
        mock_products = {"Product A": ["https://example.com/a"]}
        mock_load_products.return_value = mock_products

        mock_results = MagicMock(spec=SearchResults)
        mock_results.prices = {"Product A": PriceResult(price=29.99, url="https://example.com/a")}
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
    @patch("sys.argv", ["main.py", "--all-sizes"])
    def test_main_calls_load_products(self, mock_print_text, mock_http_client, mock_load_products, mock_find_prices):
        """Test main() calls load_products with correct filename."""
        # Setup mocks
        mock_products = {"Product A": ["https://example.com/a"]}
        mock_load_products.return_value = mock_products

        mock_results = MagicMock(spec=SearchResults)
        mock_results.prices = {"Product A": PriceResult(price=29.99, url="https://example.com/a")}
        mock_find_prices.return_value = mock_results

        # Run main
        main()

        # Verify load_products was called with correct file
        mock_load_products.assert_called_once_with("products.yml")

    @patch("main.find_cheapest_prices")
    @patch("main.load_products")
    @patch("main.HttpClient")
    @patch("main.print_results_text")
    @patch("sys.argv", ["main.py", "--sites", "notino.pt", "--all-sizes"])
    def test_main_with_sites_filter(self, mock_print_text, mock_http_client, mock_load_products, mock_find_prices):
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
        mock_results.prices = {"Product A": PriceResult(price=29.99, url="https://www.notino.pt/product-a")}
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
    @patch("sys.argv", ["main.py", "--products", "Product A", "--all-sizes"])
    def test_main_with_products_filter(self, mock_print_text, mock_http_client, mock_load_products, mock_find_prices):
        """Test main() applies --products filter correctly."""
        # Setup mocks
        mock_products = {
            "Product A": ["https://example.com/a"],
            "Product B": ["https://example.com/b"],
        }
        mock_load_products.return_value = mock_products

        mock_results = MagicMock(spec=SearchResults)
        mock_results.prices = {"Product A": PriceResult(price=29.99, url="https://example.com/a")}
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
    @patch("sys.argv", ["main.py", "--sites", "notino.pt", "--products", "Product A", "--all-sizes"])
    def test_main_with_combined_filters(self, mock_print_text, mock_http_client, mock_load_products, mock_find_prices):
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
        mock_results.prices = {"Product A": PriceResult(price=29.99, url="https://www.notino.pt/product-a")}
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
    @patch("sys.argv", ["main.py", "--sites", "nonexistent.com", "--all-sizes"])
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
    @patch("sys.argv", ["main.py", "--products", "NonExistent", "--all-sizes"])
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
    @patch("sys.argv", ["main.py", "--sites", "notino.pt,wells.pt", "--all-sizes"])
    def test_main_with_multiple_sites(self, mock_print_text, mock_http_client, mock_load_products, mock_find_prices):
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
        mock_results.prices = {"Product A": PriceResult(price=29.99, url="https://www.notino.pt/product-a")}
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
    @patch("sys.argv", ["main.py", "--products", "Product A,Product B", "--all-sizes"])
    def test_main_with_multiple_products(self, mock_print_text, mock_http_client, mock_load_products, mock_find_prices):
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
            "Product A": PriceResult(price=29.99, url="https://example.com/a"),
            "Product B": PriceResult(price=19.99, url="https://example.com/b"),
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

    @patch("main.find_cheapest_prices")
    @patch("main.load_products")
    @patch("main.HttpClient")
    @patch("main.print_results_text")
    @patch("sys.argv", ["main.py", "--no-cache", "--all-sizes"])
    def test_main_with_no_cache_flag(self, mock_print_text, mock_http_client, mock_load_products, mock_find_prices):
        """Test main() passes use_cache=False with --no-cache flag."""
        # Setup mocks
        mock_products = {"Product A": ["https://example.com/a"]}
        mock_load_products.return_value = mock_products

        mock_results = MagicMock(spec=SearchResults)
        mock_results.prices = {"Product A": PriceResult(price=29.99, url="https://example.com/a")}
        mock_find_prices.return_value = mock_results

        # Run main
        main()

        # Verify HttpClient was called with use_cache=False and default timeout/cache_duration
        mock_http_client.assert_called_once_with(use_cache=False, timeout=15, cache_duration=3600)

    @patch("main.find_cheapest_prices")
    @patch("main.load_products")
    @patch("main.HttpClient")
    @patch("main.print_results_text")
    @patch("sys.argv", ["main.py", "--all-sizes"])
    def test_main_without_no_cache_flag(self, mock_print_text, mock_http_client, mock_load_products, mock_find_prices):
        """Test main() passes use_cache=True by default (no --no-cache flag)."""
        # Setup mocks
        mock_products = {"Product A": ["https://example.com/a"]}
        mock_load_products.return_value = mock_products

        mock_results = MagicMock(spec=SearchResults)
        mock_results.prices = {"Product A": PriceResult(price=29.99, url="https://example.com/a")}
        mock_find_prices.return_value = mock_results

        # Run main
        main()

        # Verify HttpClient was called with use_cache=True (default) and default timeout/cache_duration
        mock_http_client.assert_called_once_with(use_cache=True, timeout=15, cache_duration=3600)

    @patch("main.find_cheapest_prices")
    @patch("main.load_products")
    @patch("main.HttpClient")
    @patch("main.print_results_text")
    @patch("sys.argv", ["main.py", "--products-file", "custom_products.yml", "--all-sizes"])
    def test_main_with_custom_products_file(
        self, mock_print_text, mock_http_client, mock_load_products, mock_find_prices
    ):
        """Test main() uses custom products file with --products-file flag."""
        # Setup mocks
        mock_products = {"Product A": ["https://example.com/a"]}
        mock_load_products.return_value = mock_products

        mock_results = MagicMock(spec=SearchResults)
        mock_results.prices = {"Product A": PriceResult(price=29.99, url="https://example.com/a")}
        mock_find_prices.return_value = mock_results

        # Run main
        main()

        # Verify load_products was called with custom file
        mock_load_products.assert_called_once_with("custom_products.yml")

    @patch("main.find_cheapest_prices")
    @patch("main.load_products")
    @patch("main.HttpClient")
    @patch("main.print_results_text")
    @patch("sys.argv", ["main.py", "--all-sizes"])
    def test_main_uses_default_products_file(
        self, mock_print_text, mock_http_client, mock_load_products, mock_find_prices
    ):
        """Test main() uses default products file (products.yml) when no --products-file flag."""
        # Setup mocks
        mock_products = {"Product A": ["https://example.com/a"]}
        mock_load_products.return_value = mock_products

        mock_results = MagicMock(spec=SearchResults)
        mock_results.prices = {"Product A": PriceResult(price=29.99, url="https://example.com/a")}
        mock_find_prices.return_value = mock_results

        # Run main
        main()

        # Verify load_products was called with default file
        mock_load_products.assert_called_once_with("products.yml")

    @patch("main.filter_best_value_sizes")
    @patch("main.find_cheapest_prices")
    @patch("main.load_products")
    @patch("main.HttpClient")
    @patch("main.print_results_text")
    @patch("sys.argv", ["main.py"])
    def test_main_filters_by_best_value_by_default(  # pylint: disable=too-many-positional-arguments
        self,
        mock_print_text,
        mock_http_client,
        mock_load_products,
        mock_find_prices,
        mock_filter_sizes,
    ):
        """Test main() applies best value filtering by default (no --all-sizes flag)."""
        # Setup mocks
        mock_products = {"Product A": ["https://example.com/a"]}
        mock_load_products.return_value = mock_products

        mock_results = MagicMock(spec=SearchResults)
        mock_results.prices = {"Product A": PriceResult(price=29.99, url="https://example.com/a")}
        mock_find_prices.return_value = mock_results

        mock_filtered_results = MagicMock(spec=SearchResults)
        mock_filter_sizes.return_value = mock_filtered_results

        # Run main
        main()

        # Verify filter_best_value_sizes was called
        mock_filter_sizes.assert_called_once_with(mock_results)

        # Verify filtered results were used for display
        mock_print_text.assert_called_once_with(mock_filtered_results)

    @patch("main.filter_best_value_sizes")
    @patch("main.find_cheapest_prices")
    @patch("main.load_products")
    @patch("main.HttpClient")
    @patch("main.print_results_text")
    @patch("sys.argv", ["main.py", "--all-sizes"])
    def test_main_skips_filtering_with_all_sizes_flag(  # pylint: disable=too-many-positional-arguments
        self,
        mock_print_text,
        mock_http_client,
        mock_load_products,
        mock_find_prices,
        mock_filter_sizes,
    ):
        """Test main() skips filtering when --all-sizes flag is present."""
        # Setup mocks
        mock_products = {"Product A": ["https://example.com/a"]}
        mock_load_products.return_value = mock_products

        mock_results = MagicMock(spec=SearchResults)
        mock_results.prices = {"Product A": PriceResult(price=29.99, url="https://example.com/a")}
        mock_find_prices.return_value = mock_results

        # Run main
        main()

        # Verify filter_best_value_sizes was NOT called
        mock_filter_sizes.assert_not_called()

        # Verify original results were used for display
        mock_print_text.assert_called_once_with(mock_results)

    @patch("main.filter_best_value_sizes")
    @patch("main.find_cheapest_prices")
    @patch("main.load_products")
    @patch("main.HttpClient")
    @patch("main.print_results_text")
    @patch("sys.argv", ["main.py"])
    @patch.dict("os.environ", {"DEAL_CRAWLER_ALL_SIZES": "true"})
    def test_main_respects_env_variable_for_all_sizes(  # pylint: disable=too-many-positional-arguments
        self,
        mock_print_text,
        mock_http_client,
        mock_load_products,
        mock_find_prices,
        mock_filter_sizes,
    ):
        """Test main() respects DEAL_CRAWLER_ALL_SIZES environment variable."""
        # Setup mocks
        mock_products = {"Product A": ["https://example.com/a"]}
        mock_load_products.return_value = mock_products

        mock_results = MagicMock(spec=SearchResults)
        mock_results.prices = {"Product A": PriceResult(price=29.99, url="https://example.com/a")}
        mock_find_prices.return_value = mock_results

        # Run main (with DEAL_CRAWLER_ALL_SIZES=true set via patch.dict)
        main()

        # Verify filter_best_value_sizes was NOT called
        mock_filter_sizes.assert_not_called()

        # Verify original results were used for display
        mock_print_text.assert_called_once_with(mock_results)

    @patch("main.find_cheapest_prices")
    @patch("main.load_products")
    @patch("main.HttpClient")
    @patch("main.print_results_text")
    @patch("sys.argv", ["main.py", "--cache-duration", "7200", "--all-sizes"])
    def test_main_with_custom_cache_duration(
        self, mock_print_text, mock_http_client, mock_load_products, mock_find_prices
    ):
        """Test main() passes custom cache_duration to HttpClient."""
        # Setup mocks
        mock_products = {"Product A": ["https://example.com/a"]}
        mock_load_products.return_value = mock_products

        mock_results = MagicMock(spec=SearchResults)
        mock_results.prices = {"Product A": PriceResult(price=29.99, url="https://example.com/a")}
        mock_find_prices.return_value = mock_results

        # Run main
        main()

        # Verify HttpClient was called with custom cache_duration
        mock_http_client.assert_called_once_with(use_cache=True, timeout=15, cache_duration=7200)

    @patch("main.find_cheapest_prices")
    @patch("main.load_products")
    @patch("main.HttpClient")
    @patch("main.print_results_text")
    @patch("sys.argv", ["main.py", "--request-timeout", "30", "--all-sizes"])
    def test_main_with_custom_request_timeout(
        self, mock_print_text, mock_http_client, mock_load_products, mock_find_prices
    ):
        """Test main() passes custom timeout to HttpClient."""
        # Setup mocks
        mock_products = {"Product A": ["https://example.com/a"]}
        mock_load_products.return_value = mock_products

        mock_results = MagicMock(spec=SearchResults)
        mock_results.prices = {"Product A": PriceResult(price=29.99, url="https://example.com/a")}
        mock_find_prices.return_value = mock_results

        # Run main
        main()

        # Verify HttpClient was called with custom timeout
        mock_http_client.assert_called_once_with(use_cache=True, timeout=30, cache_duration=3600)

    @patch("main.find_cheapest_prices")
    @patch("main.load_products")
    @patch("main.HttpClient")
    @patch("main.print_results_text")
    @patch("sys.argv", ["main.py", "--all-sizes"])
    @patch.dict("os.environ", {"DEAL_CRAWLER_CACHE_DURATION": "7200"})
    def test_main_respects_env_variable_for_cache_duration(
        self, mock_print_text, mock_http_client, mock_load_products, mock_find_prices
    ):
        """Test main() respects DEAL_CRAWLER_CACHE_DURATION environment variable."""
        # Setup mocks
        mock_products = {"Product A": ["https://example.com/a"]}
        mock_load_products.return_value = mock_products

        mock_results = MagicMock(spec=SearchResults)
        mock_results.prices = {"Product A": PriceResult(price=29.99, url="https://example.com/a")}
        mock_find_prices.return_value = mock_results

        # Run main
        main()

        # Verify HttpClient was called with cache_duration from env var
        mock_http_client.assert_called_once_with(use_cache=True, timeout=15, cache_duration=7200)

    @patch("main.find_cheapest_prices")
    @patch("main.load_products")
    @patch("main.HttpClient")
    @patch("main.print_results_text")
    @patch("sys.argv", ["main.py", "--all-sizes"])
    @patch.dict("os.environ", {"DEAL_CRAWLER_REQUEST_TIMEOUT": "30"})
    def test_main_respects_env_variable_for_request_timeout(
        self, mock_print_text, mock_http_client, mock_load_products, mock_find_prices
    ):
        """Test main() respects DEAL_CRAWLER_REQUEST_TIMEOUT environment variable."""
        # Setup mocks
        mock_products = {"Product A": ["https://example.com/a"]}
        mock_load_products.return_value = mock_products

        mock_results = MagicMock(spec=SearchResults)
        mock_results.prices = {"Product A": PriceResult(price=29.99, url="https://example.com/a")}
        mock_find_prices.return_value = mock_results

        # Run main
        main()

        # Verify HttpClient was called with timeout from env var
        mock_http_client.assert_called_once_with(use_cache=True, timeout=30, cache_duration=3600)

    @patch("main.find_cheapest_prices")
    @patch("main.load_products")
    @patch("main.HttpClient")
    @patch("main.print_results_text")
    @patch("sys.argv", ["main.py", "--request-timeout", "45", "--all-sizes"])
    @patch.dict("os.environ", {"DEAL_CRAWLER_REQUEST_TIMEOUT": "30"})
    def test_main_cli_overrides_env_variable_for_timeout(
        self, mock_print_text, mock_http_client, mock_load_products, mock_find_prices
    ):
        """Test main() CLI flag overrides environment variable for timeout."""
        # Setup mocks
        mock_products = {"Product A": ["https://example.com/a"]}
        mock_load_products.return_value = mock_products

        mock_results = MagicMock(spec=SearchResults)
        mock_results.prices = {"Product A": PriceResult(price=29.99, url="https://example.com/a")}
        mock_find_prices.return_value = mock_results

        # Run main
        main()

        # Verify HttpClient was called with CLI flag value (45), not env var (30)
        mock_http_client.assert_called_once_with(use_cache=True, timeout=45, cache_duration=3600)

    @patch("main.find_cheapest_prices")
    @patch("main.load_products")
    @patch("main.HttpClient")
    @patch("main.print_results_text")
    @patch("sys.argv", ["main.py", "--markdown", "--all-sizes"])
    @patch.dict("os.environ", {"DEAL_CRAWLER_MARKDOWN": "false"})
    def test_main_cli_overrides_env_variable_for_markdown(
        self, mock_print_text, mock_http_client, mock_load_products, mock_find_prices
    ):
        """Test main() CLI flag overrides environment variable for markdown."""
        # Setup mocks
        mock_products = {"Product A": ["https://example.com/a"]}
        mock_load_products.return_value = mock_products

        mock_results = MagicMock(spec=SearchResults)
        mock_results.prices = {"Product A": PriceResult(price=29.99, url="https://example.com/a")}
        mock_find_prices.return_value = mock_results

        # Run main (CLI has --markdown despite env var being false)
        main()

        # Verify markdown format was used (CLI flag wins)
        mock_print_text.assert_not_called()
        mock_results.print_summary.assert_called_once_with(markdown=True)

    @patch("main.find_cheapest_prices")
    @patch("main.load_products")
    @patch("main.HttpClient")
    @patch("main.print_results_markdown")
    @patch("sys.argv", ["main.py", "--all-sizes"])
    @patch.dict("os.environ", {"DEAL_CRAWLER_MARKDOWN": "true"})
    def test_main_respects_env_variable_for_markdown(
        self, mock_print_markdown, mock_http_client, mock_load_products, mock_find_prices
    ):
        """Test main() respects DEAL_CRAWLER_MARKDOWN environment variable."""
        # Setup mocks
        mock_products = {"Product A": ["https://example.com/a"]}
        mock_load_products.return_value = mock_products

        mock_results = MagicMock(spec=SearchResults)
        mock_results.prices = {"Product A": PriceResult(price=29.99, url="https://example.com/a")}
        mock_find_prices.return_value = mock_results

        # Run main
        main()

        # Verify markdown format was used
        mock_print_markdown.assert_called_once_with(mock_results)
        mock_results.print_summary.assert_called_once_with(markdown=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
