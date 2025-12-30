"""Tests for YAML data loading."""

import unittest
import tempfile
import os

from utils.data_loader import load_products


class TestLoadProducts(unittest.TestCase):
    """Test YAML file loading with various inputs."""

    def test_valid_yaml(self):
        """Test loading valid YAML file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write("Product1:\n  - https://example.com/1\n  - https://example.com/2\n")
            yaml_file = f.name

        try:
            products = load_products(yaml_file)
            self.assertEqual(len(products), 1)
            self.assertIn("Product1", products)
            self.assertEqual(len(products["Product1"]), 2)
        finally:
            os.unlink(yaml_file)

    def test_missing_file(self):
        """Test missing file returns empty dict."""
        products = load_products("nonexistent_file.yml")
        self.assertEqual(products, {})

    def test_empty_file(self):
        """Test empty file returns empty dict."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml_file = f.name

        try:
            products = load_products(yaml_file)
            self.assertEqual(products, {})
        finally:
            os.unlink(yaml_file)

    def test_malformed_yaml(self):
        """Test malformed YAML returns empty dict."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write("invalid: yaml: syntax: [unclosed")
            yaml_file = f.name

        try:
            products = load_products(yaml_file)
            self.assertEqual(products, {})
        finally:
            os.unlink(yaml_file)

    def test_invalid_structure_list(self):
        """Test YAML with list at root returns empty dict."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write("- item1\n- item2")
            yaml_file = f.name

        try:
            products = load_products(yaml_file)
            self.assertEqual(products, {})
        finally:
            os.unlink(yaml_file)

    def test_product_with_non_list_value(self):
        """Test product with string value gets empty list."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write("Product1: https://example.com")
            yaml_file = f.name

        try:
            products = load_products(yaml_file)
            self.assertIn("Product1", products)
            self.assertEqual(products["Product1"], [])
        finally:
            os.unlink(yaml_file)

    def test_product_with_non_string_urls(self):
        """Test product with non-string URLs prints warning."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write("Product1:\n  - https://example.com\n  - 123\n  - null\n")
            yaml_file = f.name

        try:
            products = load_products(yaml_file)
            self.assertIn("Product1", products)
            # Should still return the data even with non-string URLs
            self.assertEqual(len(products["Product1"]), 3)
        finally:
            os.unlink(yaml_file)

    def test_generic_exception_handling(self):
        """Test generic exception handling (e.g., permission error)."""
        # Create a file then remove read permissions (Unix-like systems)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write("Product1:\n  - https://example.com\n")
            yaml_file = f.name

        try:
            # Make file unreadable
            os.chmod(yaml_file, 0o000)
            products = load_products(yaml_file)
            self.assertEqual(products, {})
        finally:
            # Restore permissions before deleting
            os.chmod(yaml_file, 0o644)
            os.unlink(yaml_file)


if __name__ == "__main__":
    unittest.main(verbosity=2)
