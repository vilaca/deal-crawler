"""Tests for shipping configuration module."""

import tempfile
import unittest
from pathlib import Path

from utils.shipping import (
    ShippingConfig,
    ShippingInfo,
    get_shipping_cost,
    get_shipping_info_for_url,
    load_shipping_config,
)


class TestShippingInfo(unittest.TestCase):
    """Tests for ShippingInfo dataclass."""

    def test_shipping_info_creation(self):
        """Test creating a ShippingInfo object."""
        info = ShippingInfo(site="example.com", shipping_cost=3.50, free_over=40.00)
        self.assertEqual(info.site, "example.com")
        self.assertEqual(info.shipping_cost, 3.50)
        self.assertEqual(info.free_over, 40.00)


class TestShippingConfig(unittest.TestCase):
    """Tests for ShippingConfig dataclass."""

    def test_shipping_config_creation(self):
        """Test creating a ShippingConfig object."""
        config = ShippingConfig()
        self.assertIsInstance(config.stores, dict)
        self.assertEqual(config.default_shipping, 3.99)

    def test_shipping_config_with_stores(self):
        """Test creating a ShippingConfig with stores."""
        info1 = ShippingInfo(site="example.com", shipping_cost=3.50, free_over=40.00)
        info2 = ShippingInfo(site="test.com", shipping_cost=4.00, free_over=50.00)

        config = ShippingConfig(stores={"example.com": info1, "test.com": info2})

        self.assertEqual(len(config.stores), 2)
        self.assertEqual(config.stores["example.com"].shipping_cost, 3.50)
        self.assertEqual(config.stores["test.com"].shipping_cost, 4.00)


class TestLoadShippingConfig(unittest.TestCase):
    """Tests for load_shipping_config function."""

    def test_load_valid_shipping_file(self):
        """Test loading a valid shipping configuration file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""- site: aveirofarma.pt
  shipping: 3.90
  free-over: 49.00
- site: farmacentral.pt
  shipping: 3.50
  free-over: 40.00
- site: www.notino.pt
  shipping: 5.95
  free-over: 45.00
""")
            f.flush()
            filepath = f.name

        try:
            config = load_shipping_config(filepath)

            # Should have 3 unique sites + normalized versions
            self.assertGreaterEqual(len(config.stores), 3)

            # Check aveirofarma.pt
            self.assertIn("aveirofarma.pt", config.stores)
            self.assertEqual(config.stores["aveirofarma.pt"].shipping_cost, 3.90)
            self.assertEqual(config.stores["aveirofarma.pt"].free_over, 49.00)

            # Check farmacentral.pt
            self.assertIn("farmacentral.pt", config.stores)
            self.assertEqual(config.stores["farmacentral.pt"].shipping_cost, 3.50)
            self.assertEqual(config.stores["farmacentral.pt"].free_over, 40.00)

            # Check notino.pt (both with and without www.)
            self.assertIn("www.notino.pt", config.stores)
            self.assertIn("notino.pt", config.stores)
            self.assertEqual(config.stores["www.notino.pt"].shipping_cost, 5.95)
            self.assertEqual(config.stores["notino.pt"].shipping_cost, 5.95)

        finally:
            Path(filepath).unlink()

    def test_load_nonexistent_file(self):
        """Test loading a non-existent file raises FileNotFoundError."""
        with self.assertRaises(FileNotFoundError):
            load_shipping_config("/nonexistent/path/shipping.yaml")

    def test_load_invalid_yaml(self):
        """Test loading invalid YAML raises YAMLError."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: content: [unclosed")
            f.flush()
            filepath = f.name

        try:
            with self.assertRaises(Exception):  # yaml.YAMLError
                load_shipping_config(filepath)
        finally:
            Path(filepath).unlink()

    def test_load_empty_file(self):
        """Test loading an empty file raises ValueError."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("")
            f.flush()
            filepath = f.name

        try:
            with self.assertRaises(ValueError):
                load_shipping_config(filepath)
        finally:
            Path(filepath).unlink()

    def test_load_non_list_yaml(self):
        """Test loading YAML that's not a list raises ValueError."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""site: example.com
shipping: 3.50
free-over: 40.00
""")
            f.flush()
            filepath = f.name

        try:
            with self.assertRaises(ValueError):
                load_shipping_config(filepath)
        finally:
            Path(filepath).unlink()

    def test_load_with_missing_fields(self):
        """Test loading entries with missing fields (should skip them with warning)."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""- site: valid.com
  shipping: 3.50
  free-over: 40.00
- site: missing-shipping.com
  free-over: 50.00
- shipping: 4.00
  free-over: 60.00
""")
            f.flush()
            filepath = f.name

        try:
            config = load_shipping_config(filepath)

            # Should only have valid.com (and its normalized version if different)
            self.assertIn("valid.com", config.stores)
            self.assertNotIn("missing-shipping.com", config.stores)

        finally:
            Path(filepath).unlink()

    def test_load_with_invalid_numbers(self):
        """Test loading entries with invalid numeric values (should skip them)."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""- site: valid.com
  shipping: 3.50
  free-over: 40.00
- site: invalid.com
  shipping: not-a-number
  free-over: 40.00
""")
            f.flush()
            filepath = f.name

        try:
            config = load_shipping_config(filepath)

            # Should only have valid.com
            self.assertIn("valid.com", config.stores)
            self.assertNotIn("invalid.com", config.stores)

        finally:
            Path(filepath).unlink()


class TestGetShippingCost(unittest.TestCase):
    """Tests for get_shipping_cost function."""

    def test_shipping_below_threshold(self):
        """Test shipping cost when subtotal is below free shipping threshold."""
        info = ShippingInfo(site="example.com", shipping_cost=3.50, free_over=40.00)

        self.assertEqual(get_shipping_cost(10.00, info), 3.50)
        self.assertEqual(get_shipping_cost(39.99, info), 3.50)

    def test_shipping_at_threshold(self):
        """Test free shipping when subtotal equals threshold."""
        info = ShippingInfo(site="example.com", shipping_cost=3.50, free_over=40.00)

        self.assertEqual(get_shipping_cost(40.00, info), 0.0)

    def test_shipping_above_threshold(self):
        """Test free shipping when subtotal exceeds threshold."""
        info = ShippingInfo(site="example.com", shipping_cost=3.50, free_over=40.00)

        self.assertEqual(get_shipping_cost(40.01, info), 0.0)
        self.assertEqual(get_shipping_cost(100.00, info), 0.0)

    def test_shipping_zero_subtotal(self):
        """Test shipping cost with zero subtotal."""
        info = ShippingInfo(site="example.com", shipping_cost=3.50, free_over=40.00)

        self.assertEqual(get_shipping_cost(0.0, info), 3.50)


class TestGetShippingInfoForUrl(unittest.TestCase):
    """Tests for get_shipping_info_for_url function."""

    def test_get_shipping_info_exact_match(self):
        """Test getting shipping info with exact domain match."""
        info = ShippingInfo(site="example.com", shipping_cost=3.50, free_over=40.00)
        config = ShippingConfig(stores={"example.com": info})

        result = get_shipping_info_for_url("https://example.com/product", config)

        self.assertEqual(result.site, "example.com")
        self.assertEqual(result.shipping_cost, 3.50)
        self.assertEqual(result.free_over, 40.00)

    def test_get_shipping_info_with_www(self):
        """Test getting shipping info for URL with www. prefix."""
        info = ShippingInfo(site="www.example.com", shipping_cost=3.50, free_over=40.00)
        config = ShippingConfig(stores={"www.example.com": info, "example.com": info})

        result = get_shipping_info_for_url("https://www.example.com/product", config)

        self.assertEqual(result.site, "www.example.com")
        self.assertEqual(result.shipping_cost, 3.50)

    def test_get_shipping_info_normalized_match(self):
        """Test getting shipping info when domain matches after normalization."""
        info = ShippingInfo(site="example.com", shipping_cost=3.50, free_over=40.00)
        config = ShippingConfig(stores={"example.com": info})

        result = get_shipping_info_for_url("https://www.example.com/product", config)

        self.assertEqual(result.shipping_cost, 3.50)

    def test_get_shipping_info_unknown_store(self):
        """Test getting shipping info for unknown store (should return default)."""
        config = ShippingConfig(stores={}, default_shipping=4.99)

        result = get_shipping_info_for_url("https://unknown-store.com/product", config)

        self.assertEqual(result.shipping_cost, 4.99)
        self.assertEqual(result.site, "unknown-store.com")
        # Default has very high free shipping threshold
        self.assertGreater(result.free_over, 500)


if __name__ == "__main__":
    unittest.main()
