"""Tests for site-specific handlers."""

import unittest
from unittest.mock import patch
from bs4 import BeautifulSoup

from utils.config import Config
from utils.site_handlers import (
    DefaultSiteHandler,
    FarmacentralHandler,
    NotinoHandler,
    SiteHandlerRegistry,
    get_site_handler,
)


class TestNotinoHandler(unittest.TestCase):
    """Test Notino site handler."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = Config()
        self.handler = NotinoHandler(self.config)

    def test_domain_pattern(self):
        """Test Notino domain pattern."""
        self.assertEqual(self.handler.get_domain_pattern(), "notino.pt")

    def test_delay_range(self):
        """Test Notino delay range."""
        min_delay, max_delay = self.handler.get_delay_range()
        self.assertEqual(min_delay, 4.0)
        self.assertEqual(max_delay, 7.0)

    def test_custom_headers(self):
        """Test Notino custom headers."""
        headers = self.handler.get_custom_headers("www.notino.pt")

        self.assertIn("Referer", headers)
        self.assertIn("Origin", headers)
        self.assertEqual(headers["Origin"], "https://www.notino.pt")
        self.assertIn("DNT", headers)
        self.assertIn("sec-ch-ua-arch", headers)

    def test_referer_randomization(self):
        """Test that referer is randomized."""
        headers1 = self.handler.get_custom_headers("www.notino.pt")
        headers2 = self.handler.get_custom_headers("www.notino.pt")

        # Referer should be present in both
        self.assertIn("Referer", headers1)
        self.assertIn("Referer", headers2)

        # Could be the same or different due to randomization
        # Just verify it's one of the expected values
        expected_referers = [
            "https://www.google.com/",
            "https://www.google.pt/",
            "https://www.notino.pt/",
        ]
        self.assertIn(headers1["Referer"], expected_referers)
        self.assertIn(headers2["Referer"], expected_referers)

    def test_extract_price_from_json(self):
        """Test price extraction from Notino JSON."""
        html = """
            <script>
                {"price": 29.99, "currency": "EUR"}
            </script>
        """
        soup = BeautifulSoup(html, "lxml")
        price = self.handler.extract_price(soup)
        self.assertEqual(price, 29.99)

    def test_extract_price_from_json_multiple_prices(self):
        """Test extracts first valid price from multiple prices."""
        html = """
            <script>
                {"price": 5000.00}
                {"price": 29.99}
                {"price": 39.99}
            </script>
        """
        soup = BeautifulSoup(html, "lxml")
        price = self.handler.extract_price(soup)
        # Should return first price in valid range (29.99)
        self.assertEqual(price, 29.99)

    def test_extract_price_no_json(self):
        """Test returns None when no JSON found."""
        html = "<div>No price here</div>"
        soup = BeautifulSoup(html, "lxml")
        price = self.handler.extract_price(soup)
        self.assertIsNone(price)

    def test_extract_price_invalid_json_format(self):
        """Test handles invalid JSON gracefully."""
        html = '<script>{"price": "not_a_number"}</script>'
        soup = BeautifulSoup(html, "lxml")
        price = self.handler.extract_price(soup)
        self.assertIsNone(price)

    def test_extract_price_outside_range(self):
        """Test skips prices outside valid range."""
        html = '<script>{"price": 5000.00}</script>'
        soup = BeautifulSoup(html, "lxml")
        price = self.handler.extract_price(soup)
        self.assertIsNone(price)  # Too expensive

    def test_extract_price_script_with_no_string(self):
        """Test handles script tags with no string content."""
        html = '<script src="external.js"></script><script>{"price": 29.99}</script>'
        soup = BeautifulSoup(html, "lxml")
        price = self.handler.extract_price(soup)
        # Should skip the first script (no string) and find price in second
        self.assertEqual(price, 29.99)

    @patch("utils.site_handlers.re.findall")
    def test_extract_price_handles_value_error(self, mock_findall):
        """Test handles ValueError during float conversion."""
        html = '<script>{"price": 29.99}</script>'
        soup = BeautifulSoup(html, "lxml")

        # Mock re.findall to return something that causes ValueError
        # when converted to float (though this is contrived)
        mock_findall.return_value = ["not_a_number"]

        price = self.handler.extract_price(soup)
        self.assertIsNone(price)


class TestFarmacentralHandler(unittest.TestCase):
    """Test Farmacentral site handler."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = Config()
        self.handler = FarmacentralHandler(self.config)

    def test_domain_pattern(self):
        """Test Farmacentral domain pattern."""
        self.assertEqual(self.handler.get_domain_pattern(), "farmacentral.pt")

    def test_delay_range(self):
        """Test Farmacentral delay range."""
        min_delay, max_delay = self.handler.get_delay_range()
        self.assertEqual(min_delay, 1.0)
        self.assertEqual(max_delay, 2.0)

    def test_no_custom_headers(self):
        """Test Farmacentral has no custom headers."""
        headers = self.handler.get_custom_headers("farmacentral.pt")
        self.assertEqual(headers, {})

    def test_extract_price_from_nuxt_state_dot_notation(self):
        """Test price extraction from Nuxt state with dot notation."""
        html = """
            <script>
                window.__NUXT__=(function(a){gl.price=7.32;gl.campaign_price=7.32})()
            </script>
        """
        soup = BeautifulSoup(html, "lxml")
        price = self.handler.extract_price(soup)
        self.assertEqual(price, 7.32)

    def test_extract_price_from_nuxt_state_json_notation(self):
        """Test price extraction from Nuxt state with JSON notation."""
        html = """
            <script>
                window.__NUXT__={"product":{"price":15.99}}
            </script>
        """
        soup = BeautifulSoup(html, "lxml")
        price = self.handler.extract_price(soup)
        self.assertEqual(price, 15.99)

    def test_extract_price_from_nuxt_state_single_quotes(self):
        """Test price extraction with single quotes."""
        html = """
            <script>
                window.__NUXT__={'price':22.50}
            </script>
        """
        soup = BeautifulSoup(html, "lxml")
        price = self.handler.extract_price(soup)
        self.assertEqual(price, 22.50)

    def test_extract_price_from_nuxt_state_unquoted_key(self):
        """Test price extraction with unquoted key (JavaScript object literal)."""
        html = """
            <script>
                window.__NUXT__=(function(){return {id:123,sku:456,price:7.32,sifarma_price:9.1}})()
            </script>
        """
        soup = BeautifulSoup(html, "lxml")
        price = self.handler.extract_price(soup)
        self.assertEqual(price, 7.32)

    def test_extract_price_multiple_prices_returns_first_valid(self):
        """Test extracts first valid price from multiple prices."""
        html = """
            <script>
                window.__NUXT__=(function(){
                    gl.sifarma_price=9000.0;
                    gl.price=7.32;
                    gl.old_price=9.1;
                })()
            </script>
        """
        soup = BeautifulSoup(html, "lxml")
        price = self.handler.extract_price(soup)
        # Should return first price in valid range (7.32)
        self.assertEqual(price, 7.32)

    def test_extract_price_no_nuxt_state(self):
        """Test returns None when no Nuxt state found."""
        html = "<div>No Nuxt state here</div>"
        soup = BeautifulSoup(html, "lxml")
        price = self.handler.extract_price(soup)
        self.assertIsNone(price)

    def test_extract_price_invalid_price_format(self):
        """Test handles invalid price format gracefully."""
        html = '<script>window.__NUXT__={price:"not_a_number"}</script>'
        soup = BeautifulSoup(html, "lxml")
        price = self.handler.extract_price(soup)
        self.assertIsNone(price)

    def test_extract_price_outside_range(self):
        """Test skips prices outside valid range."""
        html = "<script>window.__NUXT__={price:5000.00}</script>"
        soup = BeautifulSoup(html, "lxml")
        price = self.handler.extract_price(soup)
        self.assertIsNone(price)  # Too expensive

    def test_extract_price_script_with_no_string(self):
        """Test handles script tags with no string content."""
        html = '<script src="external.js"></script><script>window.__NUXT__={"price":29.99}</script>'
        soup = BeautifulSoup(html, "lxml")
        price = self.handler.extract_price(soup)
        # Should skip the first script (no string) and find price in second
        self.assertEqual(price, 29.99)

    def test_extract_price_without_window_prefix(self):
        """Test extraction works even without 'window.' prefix."""
        html = """
            <script>
                __NUXT__=(function(){gl.price=12.34})()
            </script>
        """
        soup = BeautifulSoup(html, "lxml")
        price = self.handler.extract_price(soup)
        self.assertEqual(price, 12.34)


class TestDefaultSiteHandler(unittest.TestCase):
    """Test default site handler."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = Config()
        self.handler = DefaultSiteHandler(self.config)

    def test_domain_pattern(self):
        """Test default domain pattern matches all."""
        self.assertEqual(self.handler.get_domain_pattern(), "*")

    def test_delay_range(self):
        """Test default delay range."""
        min_delay, max_delay = self.handler.get_delay_range()
        self.assertEqual(min_delay, 1.0)
        self.assertEqual(max_delay, 2.0)

    def test_no_custom_headers(self):
        """Test default handler has no custom headers."""
        headers = self.handler.get_custom_headers("example.com")
        self.assertEqual(headers, {})

    def test_extract_price_returns_none(self):
        """Test default handler defers to generic extraction."""
        html = '<div class="price">€29.99</div>'
        soup = BeautifulSoup(html, "lxml")
        # Default handler always returns None to defer to generic strategies
        self.assertIsNone(self.handler.extract_price(soup))


class TestSiteHandlerRegistry(unittest.TestCase):
    """Test site handler registry."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = Config()

    def test_get_handler_for_notino(self):
        """Test registry returns Notino handler for Notino URL."""
        url = "https://www.notino.pt/product/123"
        handler = get_site_handler(url, self.config)
        self.assertIsInstance(handler, NotinoHandler)

    def test_get_handler_for_notino_subdomain(self):
        """Test registry matches notino in subdomain."""
        url = "https://shop.notino.pt/product/456"
        handler = get_site_handler(url, self.config)
        self.assertIsInstance(handler, NotinoHandler)

    def test_get_handler_for_farmacentral(self):
        """Test registry returns Farmacentral handler for Farmacentral URL."""
        url = "https://farmacentral.pt/pt/artigo/cerave-cleanser-hydrating-limpeza-facial-236ml"
        handler = get_site_handler(url, self.config)
        self.assertIsInstance(handler, FarmacentralHandler)

    def test_get_handler_for_generic_site(self):
        """Test registry returns default handler for unknown site."""
        url = "https://www.example.com/product"
        handler = get_site_handler(url, self.config)
        self.assertIsInstance(handler, DefaultSiteHandler)

    def test_get_handler_for_amazon(self):
        """Test registry returns default handler for Amazon (no handler yet)."""
        url = "https://www.amazon.com/product"
        handler = get_site_handler(url, self.config)
        self.assertIsInstance(handler, DefaultSiteHandler)

    def test_registry_order_matters(self):
        """Test first matching handler class is used."""
        registry = SiteHandlerRegistry()

        registry.register(NotinoHandler)
        registry.register(FarmacentralHandler)

        url = "https://www.notino.pt/product"
        result = registry.get_handler(url, self.config)

        # Should return instance of first matching handler class
        self.assertIsInstance(result, NotinoHandler)

    def test_registry_default_fallback(self):
        """Test registry falls back to default when no match."""
        registry = SiteHandlerRegistry()
        # Don't register any handlers

        url = "https://www.example.com/product"
        handler = registry.get_handler(url, self.config)

        self.assertIsInstance(handler, DefaultSiteHandler)


if __name__ == "__main__":
    unittest.main()
