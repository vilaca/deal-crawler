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

        # Verify HttpClient was called with use_cache=False
        mock_http_client.assert_called_once_with(use_cache=False)

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

        # Verify HttpClient was called with use_cache=True (default)
        mock_http_client.assert_called_once_with(use_cache=True)

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

    @patch("main.config")
    @patch("main.filter_best_value_sizes")
    @patch("main.find_cheapest_prices")
    @patch("main.load_products")
    @patch("main.HttpClient")
    @patch("main.print_results_text")
    @patch("sys.argv", ["main.py"])
    def test_main_respects_env_variable_for_show_all_sizes(  # pylint: disable=too-many-positional-arguments
        self,
        mock_print_text,
        mock_http_client,
        mock_load_products,
        mock_find_prices,
        mock_filter_sizes,
        mock_config,
    ):
        """Test main() respects SHOW_ALL_SIZES environment variable."""
        # Setup mocks
        mock_products = {"Product A": ["https://example.com/a"]}
        mock_load_products.return_value = mock_products

        mock_results = MagicMock(spec=SearchResults)
        mock_results.prices = {"Product A": PriceResult(price=29.99, url="https://example.com/a")}
        mock_find_prices.return_value = mock_results

        # Set env variable to true
        mock_config.show_all_sizes = True
        mock_config.products_file = "products.yml"

        # Run main
        main()

        # Verify filter_best_value_sizes was NOT called
        mock_filter_sizes.assert_not_called()

        # Verify original results were used for display
        mock_print_text.assert_called_once_with(mock_results)


    @patch("main.print_plan_text")
    @patch("main.optimize_shopping_plan")
    @patch("main.load_shipping_config")
    @patch("main.find_all_prices")
    @patch("main.load_products")
    @patch("main.HttpClient")
    @patch("sys.argv", ["main.py", "--plan", "Product A,Product B"])
    def test_main_with_plan_flag(
        self,
        mock_http_client,
        mock_load_products,
        mock_find_all_prices,
        mock_load_shipping_config,
        mock_optimize,
        mock_print_plan,
    ):  # pylint: disable=too-many-positional-arguments
        """Test main() with --plan flag optimizes purchases."""
        from utils.finder import PriceResult
        from utils.shipping import ShippingConfig, ShippingInfo

        # Setup mocks
        mock_products = {
            "Product A": ["https://store1.com/a", "https://store2.com/a"],
            "Product B": ["https://store1.com/b", "https://store2.com/b"],
        }
        mock_load_products.return_value = mock_products

        mock_all_prices = {
            "Product A": [PriceResult(price=10.0, url="https://store1.com/a", price_per_100ml=1.0)],
            "Product B": [PriceResult(price=20.0, url="https://store2.com/b", price_per_100ml=2.0)],
        }
        mock_find_all_prices.return_value = mock_all_prices

        mock_shipping_config = ShippingConfig(
            stores={
                "store1.com": ShippingInfo(site="store1.com", shipping_cost=3.0, free_over=50.0),
                "store2.com": ShippingInfo(site="store2.com", shipping_cost=3.5, free_over=40.0),
            }
        )
        mock_load_shipping_config.return_value = mock_shipping_config

        mock_plan = MagicMock()
        mock_plan.total_shipping = 0.0  # No shipping cost
        mock_optimize.return_value = mock_plan

        # Run main
        main()

        # Verify shipping config was loaded
        mock_load_shipping_config.assert_called_once_with("shipping.yaml")

        # Verify find_all_prices was called (not find_cheapest_prices)
        mock_find_all_prices.assert_called_once()

        # Verify optimizer was called
        mock_optimize.assert_called_once_with(mock_all_prices, mock_shipping_config)

        # Verify plan was printed
        mock_print_plan.assert_called_once_with(mock_plan)

    @patch("main.print_plan_text")
    @patch("main.optimize_shopping_plan")
    @patch("main.load_shipping_config")
    @patch("main.find_all_prices")
    @patch("main.load_products")
    @patch("main.HttpClient")
    @patch("sys.argv", ["main.py", "--products", "Product A,Product B", "--plan", "Product A"])
    def test_main_plan_and_products_work_together(
        self,
        mock_http_client,
        mock_load_products,
        mock_find_all_prices,
        mock_load_shipping_config,
        mock_optimize,
        mock_print_plan,
    ):  # pylint: disable=too-many-positional-arguments
        """Test that --plan and --products can be used together."""
        # Setup mocks
        mock_products = {
            "Product A": ["https://store1.com/a"],
            "Product B": ["https://store1.com/b"],
            "Product C": ["https://store1.com/c"],
        }
        mock_load_products.return_value = mock_products

        from utils.finder import PriceResult
        from utils.shipping import ShippingConfig, ShippingInfo

        mock_all_prices = {"Product A": [PriceResult(price=10.0, url="https://store1.com/a", price_per_100ml=1.0)]}
        mock_find_all_prices.return_value = mock_all_prices

        mock_shipping_config = ShippingConfig(
            stores={"store1.com": ShippingInfo(site="store1.com", shipping_cost=3.0, free_over=50.0)}
        )
        mock_load_shipping_config.return_value = mock_shipping_config

        mock_plan = MagicMock()
        mock_plan.total_shipping = 0.0  # No shipping cost
        mock_optimize.return_value = mock_plan

        # Run main
        main()

        # Should only optimize Product A (filtered by both --products and --plan)
        mock_optimize.assert_called_once()
        mock_print_plan.assert_called_once()

    @patch("main.print_plan_text")
    @patch("main.optimize_shopping_plan")
    @patch("main.load_shipping_config")
    @patch("main.find_all_prices")
    @patch("main.load_products")
    @patch("main.HttpClient")
    @patch("sys.argv", ["main.py", "--plan"])
    def test_main_plan_without_value_optimizes_all(
        self,
        mock_http_client,
        mock_load_products,
        mock_find_all_prices,
        mock_load_shipping_config,
        mock_optimize,
        mock_print_plan,
    ):  # pylint: disable=too-many-positional-arguments
        """Test that --plan without a value optimizes all products."""
        # Setup mocks
        mock_products = {
            "Product A": ["https://store1.com/a"],
            "Product B": ["https://store1.com/b"],
        }
        mock_load_products.return_value = mock_products

        from utils.finder import PriceResult
        from utils.shipping import ShippingConfig, ShippingInfo

        mock_all_prices = {
            "Product A": [PriceResult(price=10.0, url="https://store1.com/a", price_per_100ml=1.0)],
            "Product B": [PriceResult(price=20.0, url="https://store1.com/b", price_per_100ml=2.0)],
        }
        mock_find_all_prices.return_value = mock_all_prices

        mock_shipping_config = ShippingConfig(
            stores={"store1.com": ShippingInfo(site="store1.com", shipping_cost=3.0, free_over=50.0)}
        )
        mock_load_shipping_config.return_value = mock_shipping_config

        mock_plan = MagicMock()
        mock_plan.total_shipping = 0.0  # No shipping cost
        mock_optimize.return_value = mock_plan

        # Run main
        main()

        # Should optimize all products
        mock_optimize.assert_called_once()
        mock_print_plan.assert_called_once()

    @patch("main.load_products")
    @patch("sys.argv", ["main.py", "--plan", "NonExistent"])
    def test_main_plan_with_no_matches(self, mock_load_products):
        """Test --plan with no matching products."""
        mock_products = {
            "Product A": ["https://example.com/a"],
        }
        mock_load_products.return_value = mock_products

        with self.assertRaises(SystemExit) as cm:
            main()

        self.assertEqual(cm.exception.code, 1)

    @patch("main.print_plan_markdown")
    @patch("main.optimize_shopping_plan")
    @patch("main.load_shipping_config")
    @patch("main.find_all_prices")
    @patch("main.load_products")
    @patch("main.HttpClient")
    @patch("sys.argv", ["main.py", "--plan", "Product A", "--markdown"])
    def test_main_plan_with_markdown_flag(
        self,
        mock_http_client,
        mock_load_products,
        mock_find_all_prices,
        mock_load_shipping_config,
        mock_optimize,
        mock_print_markdown,
    ):  # pylint: disable=too-many-positional-arguments
        """Test --plan with --markdown flag uses markdown formatter."""
        # Setup mocks
        mock_products = {"Product A": ["https://example.com/a"]}
        mock_load_products.return_value = mock_products

        from utils.finder import PriceResult
        from utils.shipping import ShippingConfig, ShippingInfo

        mock_all_prices = {"Product A": [PriceResult(price=10.0, url="https://example.com/a", price_per_100ml=1.0)]}
        mock_find_all_prices.return_value = mock_all_prices

        mock_shipping_config = ShippingConfig(
            stores={"example.com": ShippingInfo(site="example.com", shipping_cost=3.0, free_over=50.0)}
        )
        mock_load_shipping_config.return_value = mock_shipping_config

        mock_plan = MagicMock()
        mock_plan.total_shipping = 0.0  # No shipping cost
        mock_optimize.return_value = mock_plan

        # Run main
        main()

        # Verify markdown formatter was used
        mock_print_markdown.assert_called_once_with(mock_plan)


if __name__ == "__main__":
    unittest.main(verbosity=2)
