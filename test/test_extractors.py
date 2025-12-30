"""Tests for price extraction logic."""

import unittest
from bs4 import BeautifulSoup

from utils.extractors import parse_price_string, extract_price, extract_price_notino


class TestParsePriceString(unittest.TestCase):
    """Test price string parsing with various formats."""

    def test_euro_with_comma(self):
        """Test European format with comma decimal separator."""
        self.assertEqual(parse_price_string("29,99"), 29.99)

    def test_euro_with_dot(self):
        """Test format with dot decimal separator."""
        self.assertEqual(parse_price_string("29.99"), 29.99)
        self.assertEqual(parse_price_string("1234.56"), 1234.56)

    def test_with_currency_symbols(self):
        """Test prices with currency symbols."""
        self.assertEqual(parse_price_string("€29.99"), 29.99)
        self.assertEqual(parse_price_string("$29.99"), 29.99)
        self.assertEqual(parse_price_string("£29.99"), 29.99)
        self.assertEqual(parse_price_string("29,99€"), 29.99)

    def test_with_spaces(self):
        """Test prices with spaces."""
        self.assertEqual(parse_price_string("€ 29.99"), 29.99)
        self.assertEqual(parse_price_string("29.99 €"), 29.99)

    def test_empty_string(self):
        """Test empty string returns None."""
        self.assertIsNone(parse_price_string(""))
        self.assertIsNone(parse_price_string(None))

    def test_invalid_string(self):
        """Test invalid strings return None."""
        self.assertIsNone(parse_price_string("abc"))
        self.assertIsNone(parse_price_string("not a price"))

    def test_whole_numbers(self):
        """Test whole number prices."""
        self.assertEqual(parse_price_string("50"), 50.0)
        self.assertEqual(parse_price_string("€100"), 100.0)

    def test_very_small_prices(self):
        """Test very small prices."""
        self.assertEqual(parse_price_string("0.99"), 0.99)
        self.assertEqual(parse_price_string("0,50"), 0.5)

    def test_multiple_prices_in_text(self):
        """Test parsing text with multiple prices returns first price."""
        # Sweetcare.pt case: "€ 79,07€ 87,86-10%"
        self.assertEqual(parse_price_string("€ 79,07€ 87,86-10%"), 79.07)
        self.assertEqual(parse_price_string("€ 60,47€ 67,19-10%"), 60.47)

    def test_prevents_price_merging(self):
        """Test that spaces don't cause prices to merge."""
        # This should extract 52.10, not 52.1087
        result = parse_price_string("€ 52,10€ 87,86")
        self.assertEqual(result, 52.10)
        # Not 52.1087 which would happen if spaces removed before extraction
        self.assertNotEqual(result, 52.1087)


class TestExtractPriceNotino(unittest.TestCase):
    """Test notino.pt specific price extraction."""

    def create_soup(self, html):
        """Helper to create BeautifulSoup from HTML."""
        return BeautifulSoup(html, "lxml")

    def test_none_soup(self):
        """Test None soup returns None."""
        self.assertIsNone(extract_price_notino(None))

    def test_json_with_price(self):
        """Test extraction from JSON data."""
        html = """
        <script>
        var productData = {"price": 83.20, "currency": "EUR"};
        </script>
        """
        soup = self.create_soup(html)
        price = extract_price_notino(soup)
        self.assertEqual(price, 83.20)

    def test_json_with_multiple_prices(self):
        """Test extraction returns first valid price."""
        html = """
        <script>
        var data = {"oldPrice": 0.5, "price": 65.00, "otherPrice": 2000};
        </script>
        """
        soup = self.create_soup(html)
        price = extract_price_notino(soup)
        self.assertEqual(price, 65.00)

    def test_price_outside_range(self):
        """Test price outside valid range is skipped."""
        html = """
        <script>
        var data = {"price": 0.5};
        </script>
        """
        soup = self.create_soup(html)
        price = extract_price_notino(soup)
        self.assertIsNone(price)

    def test_no_price_in_script(self):
        """Test returns None when no price found."""
        html = '<script>var data = {"name": "product"};</script>'
        soup = self.create_soup(html)
        self.assertIsNone(extract_price_notino(soup))


class TestExtractPrice(unittest.TestCase):
    """Test generic price extraction."""

    def create_soup(self, html):
        """Helper to create BeautifulSoup from HTML."""
        return BeautifulSoup(html, "lxml")

    def test_none_soup(self):
        """Test None soup returns None."""
        self.assertIsNone(extract_price(None, "https://example.com"))

    def test_meta_tag_price(self):
        """Test extraction from meta tag."""
        html = '<meta property="product:price:amount" content="29.99">'
        soup = self.create_soup(html)
        price = extract_price(soup, "https://example.com")
        self.assertEqual(price, 29.99)

    def test_data_price_attribute(self):
        """Test extraction from data-price attribute."""
        html = '<div data-price="69.41"></div>'
        soup = self.create_soup(html)
        price = extract_price(soup, "https://example.com")
        self.assertEqual(price, 69.41)

    def test_actual_price_class(self):
        """Test prioritizes actual price over old price."""
        html = """
        <span class="price-old">99.99€</span>
        <span class="price-actual">69.99€</span>
        """
        soup = self.create_soup(html)
        price = extract_price(soup, "https://example.com")
        self.assertEqual(price, 69.99)

    def test_ignores_old_price_class(self):
        """Test ignores elements with 'old' in class name."""
        html = """
        <span class="price-old">99.99€</span>
        <span class="price">69.99€</span>
        """
        soup = self.create_soup(html)
        price = extract_price(soup, "https://example.com")
        self.assertEqual(price, 69.99)

    def test_text_pattern_extraction(self):
        """Test extraction from page text patterns."""
        html = "<div>The price is €45.50 for this item</div>"
        soup = self.create_soup(html)
        price = extract_price(soup, "https://example.com")
        self.assertEqual(price, 45.50)

    def test_notino_url_uses_special_extraction(self):
        """Test notino.pt URL uses special extraction method."""
        html = '<script>var data = {"price": 83.20};</script>'
        soup = self.create_soup(html)
        price = extract_price(soup, "https://www.notino.pt/product")
        self.assertEqual(price, 83.20)

    def test_parse_price_string_with_attribute_error(self):
        """Test parse_price_string handles non-string types gracefully."""
        # This should handle the AttributeError case
        result = parse_price_string(["not", "a", "string"])
        self.assertIsNone(result)

    def test_extract_price_notino_with_script_without_string(self):
        """Test extract_price_notino handles scripts without string content."""
        html = '<script src="external.js"></script><div>content</div>'
        soup = self.create_soup(html)
        price = extract_price_notino(soup)
        self.assertIsNone(price)

    def test_extract_price_notino_with_invalid_price_format(self):
        """Test extract_price_notino handles invalid price JSON."""
        html = '<script>{"price": "not_a_number"}</script>'
        soup = self.create_soup(html)
        price = extract_price_notino(soup)
        self.assertIsNone(price)

    def test_priority_classes_with_content_attribute(self):
        """Test extraction from priority class with content attribute."""
        html = '<span class="price-actual" content="55.99">Display: 60</span>'
        soup = self.create_soup(html)
        price = extract_price(soup, "https://example.com")
        self.assertEqual(price, 55.99)

    def test_priority_classes_with_text_only(self):
        """Test extraction from priority class with text content only."""
        html = '<span class="price-current">€48.75</span>'
        soup = self.create_soup(html)
        price = extract_price(soup, "https://example.com")
        self.assertEqual(price, 48.75)

    def test_generic_classes_with_content_attribute(self):
        """Test extraction from generic price class with content attribute."""
        html = '<div class="product-price" content="39.99">Price</div>'
        soup = self.create_soup(html)
        price = extract_price(soup, "https://example.com")
        self.assertEqual(price, 39.99)

    def test_text_pattern_with_price_range_validation(self):
        """Test text pattern extraction validates price range."""
        html = "<div>Price: €15000.00</div>"  # Outside MAX_PRICE
        soup = self.create_soup(html)
        price = extract_price(soup, "https://example.com")
        # Should not return prices outside the valid range
        self.assertIsNone(price)

    def test_skips_hidden_display_none_class(self):
        """Test skips elements with display-none class."""
        html = """
        <div class="price-product display-none">€ 52,10</div>
        <div class="price-product">€ 60,47</div>
        """
        soup = self.create_soup(html)
        price = extract_price(soup, "https://example.com")
        # Should extract visible price, not hidden one
        self.assertEqual(price, 60.47)

    def test_skips_hidden_class(self):
        """Test skips elements with 'hidden' class."""
        html = """
        <div class="price hidden">€ 100,00</div>
        <div class="price">€ 50,00</div>
        """
        soup = self.create_soup(html)
        price = extract_price(soup, "https://example.com")
        self.assertEqual(price, 50.0)

    def test_skips_d_none_class(self):
        """Test skips elements with Bootstrap d-none class."""
        html = """
        <div class="price d-none">€ 100,00</div>
        <div class="price">€ 75,00</div>
        """
        soup = self.create_soup(html)
        price = extract_price(soup, "https://example.com")
        self.assertEqual(price, 75.0)

    def test_skips_inline_style_display_none(self):
        """Test skips elements with inline style display:none."""
        html = """
        <div class="price" style="display:none">€ 100,00</div>
        <div class="price">€ 45,00</div>
        """
        soup = self.create_soup(html)
        price = extract_price(soup, "https://example.com")
        self.assertEqual(price, 45.0)

    def test_skips_inline_style_visibility_hidden(self):
        """Test skips elements with inline style visibility:hidden."""
        html = """
        <div class="price" style="visibility:hidden">€ 100,00</div>
        <div class="price">€ 35,00</div>
        """
        soup = self.create_soup(html)
        price = extract_price(soup, "https://example.com")
        self.assertEqual(price, 35.0)

    def test_multiple_prices_picks_visible(self):
        """Test extracts visible price when multiple prices present (sweetcare.pt case)."""
        html = """
        <div class="price-product display-none">€ 52,09€ 57,88-10%</div>
        <div class="price-product">€ 60,47€ 67,19-10%</div>
        <div class="price-product display-none">€ 79,07€ 87,86-10%</div>
        """
        soup = self.create_soup(html)
        price = extract_price(soup, "https://example.com")
        # Should get the visible price (60.47), not hidden ones
        self.assertEqual(price, 60.47)

    def test_price_product_class_priority(self):
        """Test price-product class has extraction priority."""
        html = """
        <div class="some-price">€ 100,00</div>
        <div class="price-product">€ 79,07</div>
        <div class="generic-price">€ 50,00</div>
        """
        soup = self.create_soup(html)
        price = extract_price(soup, "https://example.com")
        # Should prioritize price-product class
        self.assertEqual(price, 79.07)


if __name__ == "__main__":
    unittest.main(verbosity=2)
