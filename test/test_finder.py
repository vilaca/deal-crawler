"""Tests for price comparison logic."""

import unittest
from unittest.mock import patch, MagicMock
from bs4 import BeautifulSoup

from src.finder import find_cheapest_prices


class TestFindCheapestPrices(unittest.TestCase):
    """Test finding cheapest prices across multiple products and URLs."""

    def create_soup(self, html):
        """Helper to create BeautifulSoup from HTML."""
        return BeautifulSoup(html, "lxml")

    def create_mock_http_client(self):
        """Helper to create a mock HttpClient."""
        return MagicMock()

    @patch("src.finder.is_out_of_stock")
    @patch("src.finder.extract_price")
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

        self.assertIn("Product A", results)
        self.assertIsNotNone(results["Product A"])
        price, url = results["Product A"]
        self.assertEqual(price, 30.00)
        self.assertEqual(url, "https://example.com/product2")

    @patch("src.finder.is_out_of_stock")
    @patch("src.finder.extract_price")
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

        self.assertIn("Product B", results)
        price, url = results["Product B"]
        # Should get cheapest in-stock price (60.00), not the out-of-stock one
        self.assertEqual(price, 60.00)
        self.assertEqual(url, "https://example.com/product3")

    @patch("src.finder.is_out_of_stock")
    @patch("src.finder.extract_price")
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

        self.assertIn("Product C", results)
        self.assertIsNone(results["Product C"])

    @patch("src.finder.is_out_of_stock")
    @patch("src.finder.extract_price")
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

        self.assertIn("Product D", results)
        self.assertIsNone(results["Product D"])

    def test_handles_fetch_failure(self):
        """Test handles fetch_page returning None."""
        products = {"Product E": ["https://example.com/product1"]}

        # Mock HttpClient with fetch returning None
        mock_client = self.create_mock_http_client()
        mock_client.fetch_page.return_value = None

        results = find_cheapest_prices(products, mock_client)

        self.assertIn("Product E", results)
        self.assertIsNone(results["Product E"])

    @patch("src.finder.is_out_of_stock")
    @patch("src.finder.extract_price")
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

        self.assertEqual(len(results), 2)
        self.assertIn("Product A", results)
        self.assertIn("Product B", results)

        price_a, url_a = results["Product A"]
        self.assertEqual(price_a, 20.00)
        self.assertEqual(url_a, "https://example.com/a2")

        price_b, url_b = results["Product B"]
        self.assertEqual(price_b, 15.00)
        self.assertEqual(url_b, "https://example.com/b1")

    def test_handles_empty_products(self):
        """Test handles empty products dictionary."""
        products = {}

        # Mock HttpClient (won't be used)
        mock_client = self.create_mock_http_client()

        results = find_cheapest_prices(products, mock_client)

        self.assertEqual(results, {})


if __name__ == "__main__":
    unittest.main(verbosity=2)
