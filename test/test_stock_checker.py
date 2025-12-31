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

    def test_in_stock_class_indicator(self):
        """Test in-stock CSS class detection."""
        html = '<span class="in_stock">Em Stock</span>'
        soup = self.create_soup(html)
        self.assertFalse(is_out_of_stock(soup))

    def test_em_stock_class_indicator(self):
        """Test Portuguese 'em stock' class detection."""
        html = '<div class="em-stock">Disponível</div>'
        soup = self.create_soup(html)
        self.assertFalse(is_out_of_stock(soup))

    def test_json_ld_in_stock(self):
        """Test JSON-LD InStock availability detection."""
        html = '''
        <script type="application/ld+json">
        {"@type":"Product","availability":"https://schema.org/InStock","price":"12.04"}
        </script>
        '''
        soup = self.create_soup(html)
        self.assertFalse(is_out_of_stock(soup))

    def test_in_stock_class_takes_priority_over_out_of_stock_text(self):
        """Test in-stock indicator takes priority over out-of-stock text.

        This simulates the aveirofarma.pt case where the page has both:
        - An in-stock indicator (class="in_stock")
        - Out-of-stock text (disabled button with "Esgotado")

        The in-stock indicator should take priority.
        """
        html = '''
        <div>
            <span class="in_stock">Em Stock</span>
            <a class="btn btn-outofstock" disabled="">Esgotado</a>
        </div>
        '''
        soup = self.create_soup(html)
        # Should be in stock despite "Esgotado" text
        self.assertFalse(is_out_of_stock(soup))

    def test_json_ld_takes_priority_over_out_of_stock_text(self):
        """Test JSON-LD InStock takes priority over out-of-stock text."""
        html = '''
        <script type="application/ld+json">
        {"availability":"https://schema.org/InStock"}
        </script>
        <div>Produto esgotado</div>
        '''
        soup = self.create_soup(html)
        # Should be in stock despite "esgotado" text
        self.assertFalse(is_out_of_stock(soup))

    def test_ignores_empty_in_stock_icons(self):
        """Test that empty in-stock icon elements are ignored.

        This simulates the blinkshop.com case where the page has:
        - Empty <span class="in-stock-icon"> elements (for other products)
        - Out-of-stock div with "Esgotado" text

        The empty icons should be ignored and out-of-stock detected.
        """
        html = '''
        <div>
            <span class="in-stock-icon zit"></span>
            <span class="in-stock-icon zit"></span>
            <div class="out-of-stock mt0">
                <span>Esgotado.</span>
            </div>
        </div>
        '''
        soup = self.create_soup(html)
        # Should be out of stock despite in-stock-icon elements
        self.assertTrue(is_out_of_stock(soup))

    def test_ignores_backinstock_button(self):
        """Test that 'notify when back in stock' button is not treated as in-stock."""
        html = '''
        <div>
            <a class="register-backinstock" href="#">NOTIFICAR-ME</a>
            <div class="out-of-stock">Esgotado</div>
        </div>
        '''
        soup = self.create_soup(html)
        # Should be out of stock despite "backinstock" class
        self.assertTrue(is_out_of_stock(soup))


if __name__ == "__main__":
    unittest.main(verbosity=2)
