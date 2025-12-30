"""Tests for stock availability checking."""

import unittest
from bs4 import BeautifulSoup

from utils.stock_checker import is_out_of_stock


class TestIsOutOfStock(unittest.TestCase):
    """Test stock detection with various patterns."""

    def create_soup(self, html):
        """Helper to create BeautifulSoup from HTML."""
        return BeautifulSoup(html, "lxml")

    def test_none_soup(self):
        """Test None soup returns False."""
        self.assertFalse(is_out_of_stock(None))

    def test_in_stock_meta_tag(self):
        """Test in-stock meta tag detection."""
        html = '<meta property="product:availability" content="in stock">'
        soup = self.create_soup(html)
        self.assertFalse(is_out_of_stock(soup))

    def test_out_of_stock_meta_tag(self):
        """Test out-of-stock meta tag detection."""
        html = '<meta property="product:availability" content="outofstock">'
        soup = self.create_soup(html)
        self.assertTrue(is_out_of_stock(soup))

    def test_out_of_stock_text_english(self):
        """Test English out-of-stock text."""
        html = "<div>This product is out of stock</div>"
        soup = self.create_soup(html)
        self.assertTrue(is_out_of_stock(soup))

    def test_out_of_stock_text_portuguese(self):
        """Test Portuguese out-of-stock text."""
        html = "<div>Produto esgotado</div>"
        soup = self.create_soup(html)
        self.assertTrue(is_out_of_stock(soup))

    def test_sold_out_text(self):
        """Test sold out text detection."""
        html = "<div>Sold out</div>"
        soup = self.create_soup(html)
        self.assertTrue(is_out_of_stock(soup))

    def test_out_of_stock_class(self):
        """Test out-of-stock CSS class detection."""
        html = '<span class="out-of-stock">Unavailable</span>'
        soup = self.create_soup(html)
        self.assertTrue(is_out_of_stock(soup))

    def test_in_stock_no_indicators(self):
        """Test in-stock when no indicators present."""
        html = "<div>Product available</div>"
        soup = self.create_soup(html)
        self.assertFalse(is_out_of_stock(soup))


if __name__ == "__main__":
    unittest.main(verbosity=2)
