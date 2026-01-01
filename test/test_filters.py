"""Tests for utils.filters module."""

import unittest

from utils.filters import filter_by_sites, filter_by_products


class TestFilterBySites(unittest.TestCase):
    """Test site filtering functionality."""

    def test_filter_single_site(self):
        """Test filtering by a single site."""
        products = {
            "Product A": [
                "https://www.notino.pt/product-a",
                "https://wells.pt/product-a",
                "https://atida.com/product-a",
            ],
            "Product B": ["https://www.notino.pt/product-b"],
        }
        result = filter_by_sites(products, ["notino.pt"])

        self.assertEqual(len(result), 2)
        self.assertEqual(len(result["Product A"]), 1)
        self.assertIn("notino.pt", result["Product A"][0])
        self.assertEqual(len(result["Product B"]), 1)

    def test_filter_multiple_sites(self):
        """Test filtering by multiple sites."""
        products = {
            "Product A": [
                "https://www.notino.pt/product-a",
                "https://wells.pt/product-a",
                "https://atida.com/product-a",
            ]
        }
        result = filter_by_sites(products, ["notino.pt", "wells.pt"])

        self.assertEqual(len(result), 1)
        self.assertEqual(len(result["Product A"]), 2)

    def test_filter_no_matches(self):
        """Test filtering when no URLs match."""
        products = {
            "Product A": ["https://www.notino.pt/product-a"],
            "Product B": ["https://wells.pt/product-b"],
        }
        result = filter_by_sites(products, ["amazon.com"])

        self.assertEqual(len(result), 0)

    def test_filter_case_insensitive(self):
        """Test filtering is case-insensitive."""
        products = {"Product A": ["https://www.NOTINO.PT/product-a"]}
        result = filter_by_sites(products, ["notino.pt"])

        self.assertEqual(len(result), 1)
        self.assertEqual(len(result["Product A"]), 1)

    def test_filter_partial_domain_match(self):
        """Test filtering matches partial domains."""
        products = {"Product A": ["https://subdomain.notino.pt/product-a"]}
        result = filter_by_sites(products, ["notino.pt"])

        self.assertEqual(len(result), 1)

    def test_filter_removes_products_with_no_matching_urls(self):
        """Test products with no matching URLs are removed."""
        products = {
            "Product A": ["https://www.notino.pt/product-a"],
            "Product B": ["https://atida.com/product-b"],
        }
        result = filter_by_sites(products, ["notino.pt"])

        self.assertEqual(len(result), 1)
        self.assertIn("Product A", result)
        self.assertNotIn("Product B", result)


class TestFilterByProducts(unittest.TestCase):
    """Test product name filtering functionality."""

    def test_filter_single_substring(self):
        """Test filtering by a single substring."""
        products = {
            "Medik8 Crystal Retinal 6": ["https://example.com/1"],
            "LRP Anthelios SPF50": ["https://example.com/2"],
            "Medik8 Super Ferrulic": ["https://example.com/3"],
        }
        result = filter_by_products(products, ["Crystal"])

        self.assertEqual(len(result), 1)
        self.assertIn("Medik8 Crystal Retinal 6", result)

    def test_filter_multiple_substrings(self):
        """Test filtering by multiple substrings (OR logic)."""
        products = {
            "Medik8 Crystal Retinal 6": ["https://example.com/1"],
            "LRP Anthelios SPF50": ["https://example.com/2"],
            "Medik8 Super Ferrulic": ["https://example.com/3"],
        }
        result = filter_by_products(products, ["Crystal", "SPF50"])

        self.assertEqual(len(result), 2)
        self.assertIn("Medik8 Crystal Retinal 6", result)
        self.assertIn("LRP Anthelios SPF50", result)

    def test_filter_case_insensitive(self):
        """Test filtering is case-insensitive."""
        products = {
            "Medik8 Crystal Retinal 6": ["https://example.com/1"],
            "LRP Anthelios SPF50": ["https://example.com/2"],
        }
        result = filter_by_products(products, ["crystal", "spf50"])

        self.assertEqual(len(result), 2)

    def test_filter_no_matches(self):
        """Test filtering when no products match."""
        products = {
            "Medik8 Crystal Retinal 6": ["https://example.com/1"],
            "LRP Anthelios SPF50": ["https://example.com/2"],
        }
        result = filter_by_products(products, ["NonExistent"])

        self.assertEqual(len(result), 0)

    def test_filter_partial_match(self):
        """Test filtering matches partial product names."""
        products = {
            "Medik8 Crystal Retinal 6": ["https://example.com/1"],
            "Medik8 Crystal Retinal 3": ["https://example.com/2"],
        }
        result = filter_by_products(products, ["Retinal 6"])

        self.assertEqual(len(result), 1)
        self.assertIn("Medik8 Crystal Retinal 6", result)

    def test_filter_preserves_urls(self):
        """Test filtering preserves all URLs for matched products."""
        products = {
            "Medik8 Crystal Retinal 6": [
                "https://example.com/1",
                "https://example.com/2",
                "https://example.com/3",
            ]
        }
        result = filter_by_products(products, ["Crystal"])

        self.assertEqual(len(result["Medik8 Crystal Retinal 6"]), 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
