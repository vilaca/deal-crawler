"""Tests for collect_all_prices module."""

import csv
import io
import unittest
from unittest.mock import patch, MagicMock

from utils.price_models import PriceResult

from collect_all_prices import _write_csv, _collect


class TestWriteCsv(unittest.TestCase):
    """Test CSV writing."""

    def test_writes_header_and_rows(self):
        """Test CSV output contains header and sorted rows."""
        all_prices = {
            "Product B": [PriceResult(price=10.0, url="https://site-b.pt/p", price_per_100ml=5.0)],
            "Product A": [
                PriceResult(price=20.0, url="https://site-a.pt/p", price_per_100ml=None),
                PriceResult(price=15.0, url="https://site-c.pt/p", price_per_100ml=7.5),
            ],
        }
        output = io.StringIO()
        count = _write_csv(output, all_prices)

        self.assertEqual(count, 3)
        output.seek(0)
        reader = csv.reader(output)
        rows = list(reader)
        self.assertEqual(rows[0], ["Product", "Site", "Price", "Price per 100ml", "URL"])
        # Product A first (sorted), cheapest price first within product
        self.assertEqual(rows[1][0], "Product A")
        self.assertEqual(rows[1][2], "15.00")
        self.assertEqual(rows[2][0], "Product A")
        self.assertEqual(rows[2][2], "20.00")
        self.assertEqual(rows[3][0], "Product B")

    def test_empty_prices(self):
        """Test writing with no prices."""
        output = io.StringIO()
        count = _write_csv(output, {})
        self.assertEqual(count, 0)
        output.seek(0)
        lines = output.getvalue().strip().split("\n")
        self.assertEqual(len(lines), 1)  # Header only

    def test_price_per_100ml_empty_when_none(self):
        """Test price_per_100ml is empty string when None."""
        all_prices = {
            "Test": [PriceResult(price=10.0, url="https://example.com/p", price_per_100ml=None)],
        }
        output = io.StringIO()
        _write_csv(output, all_prices)
        output.seek(0)
        reader = csv.reader(output)
        rows = list(reader)
        self.assertEqual(rows[1][3], "")


class TestCollect(unittest.TestCase):
    """Test collect function."""

    @patch("collect_all_prices.find_all_prices")
    @patch("collect_all_prices.HttpClient")
    @patch("collect_all_prices.load_products")
    def test_collect_returns_prices(self, mock_load, mock_http_class, mock_find):
        """Test _collect loads products and returns all prices."""
        mock_load.return_value = {"Product": ["https://example.com"]}
        mock_http_instance = MagicMock()
        mock_http_class.return_value.__enter__ = MagicMock(return_value=mock_http_instance)
        mock_http_class.return_value.__exit__ = MagicMock(return_value=False)
        expected = {"Product": [PriceResult(price=10.0, url="https://example.com")]}
        mock_find.return_value = expected

        result = _collect(verbose=False, show_progress=False, products_filter=None, sites_filter=None)
        self.assertEqual(result, expected)

    @patch("collect_all_prices.load_products")
    def test_collect_exits_on_no_products(self, mock_load):
        """Test _collect exits when no products found."""
        mock_load.return_value = {}
        with self.assertRaises(SystemExit):
            _collect(verbose=False, show_progress=False, products_filter=None, sites_filter=None)

    @patch("collect_all_prices.find_all_prices")
    @patch("collect_all_prices.HttpClient")
    @patch("collect_all_prices.load_products")
    def test_collect_with_product_filter(self, mock_load, mock_http_class, mock_find):
        """Test _collect applies product filter."""
        mock_load.return_value = {
            "Cerave Cleanser": ["https://example.com/1"],
            "Medik8 Retinal": ["https://example.com/2"],
        }
        mock_http_instance = MagicMock()
        mock_http_class.return_value.__enter__ = MagicMock(return_value=mock_http_instance)
        mock_http_class.return_value.__exit__ = MagicMock(return_value=False)
        mock_find.return_value = {}

        _collect(verbose=False, show_progress=False, products_filter="Cerave", sites_filter=None)
        # find_all_prices should be called with only Cerave product
        call_args = mock_find.call_args[0][0]
        self.assertIn("Cerave Cleanser", call_args)
        self.assertNotIn("Medik8 Retinal", call_args)


if __name__ == "__main__":
    unittest.main(verbosity=2)
