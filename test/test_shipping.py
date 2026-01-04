"""Tests for shipping configuration and cost calculation (BDD style)."""

import tempfile
import unittest
from pathlib import Path

import yaml

from utils.shipping import ShippingConfig, ShippingInfo, NO_FREE_SHIPPING_THRESHOLD


class TestShippingInfoCalculation(unittest.TestCase):
    """Test shipping cost calculation behavior."""

    def test_when_subtotal_meets_threshold_then_shipping_is_free(self):
        """
        Given a store with free shipping over €50
        When the subtotal is exactly €50
        Then shipping cost should be €0.00
        """
        # Given
        shipping_info = ShippingInfo(site="example.com", shipping_cost=3.99, free_over=50.00)

        # When
        subtotal = 50.00
        shipping = shipping_info.calculate_shipping(subtotal)

        # Then
        self.assertEqual(shipping, 0.0)

    def test_when_subtotal_exceeds_threshold_then_shipping_is_free(self):
        """
        Given a store with free shipping over €50
        When the subtotal is €75
        Then shipping cost should be €0.00
        """
        # Given
        shipping_info = ShippingInfo(site="example.com", shipping_cost=3.99, free_over=50.00)

        # When
        subtotal = 75.00
        shipping = shipping_info.calculate_shipping(subtotal)

        # Then
        self.assertEqual(shipping, 0.0)

    def test_when_subtotal_below_threshold_then_shipping_cost_applies(self):
        """
        Given a store with €3.99 shipping and free over €50
        When the subtotal is €49.99
        Then shipping cost should be €3.99
        """
        # Given
        shipping_info = ShippingInfo(site="example.com", shipping_cost=3.99, free_over=50.00)

        # When
        subtotal = 49.99
        shipping = shipping_info.calculate_shipping(subtotal)

        # Then
        self.assertEqual(shipping, 3.99)

    def test_when_subtotal_is_zero_then_shipping_cost_applies(self):
        """
        Given a store with €3.99 shipping
        When the subtotal is €0
        Then shipping cost should be €3.99
        """
        # Given
        shipping_info = ShippingInfo(site="example.com", shipping_cost=3.99, free_over=50.00)

        # When
        subtotal = 0.0
        shipping = shipping_info.calculate_shipping(subtotal)

        # Then
        self.assertEqual(shipping, 3.99)


class TestShippingConfigLoading(unittest.TestCase):
    """Test loading shipping configuration from YAML files."""

    def test_when_valid_yaml_loaded_then_all_stores_available(self):
        """
        Given a valid shipping.yaml with 3 stores
        When the config is loaded
        Then all 3 stores should be accessible
        """
        # Given
        yaml_content = [
            {"site": "store1.com", "shipping": 3.99, "free-over": 50.00},
            {"site": "store2.com", "shipping": 4.50, "free-over": 45.00},
            {"site": "store3.com", "shipping": 2.99, "free-over": 60.00},
        ]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(yaml_content, f)
            temp_path = f.name

        try:
            # When
            config = ShippingConfig.load_from_file(temp_path)

            # Then
            self.assertEqual(len(config.stores), 3)
            self.assertIn("store1.com", config.stores)
            self.assertIn("store2.com", config.stores)
            self.assertIn("store3.com", config.stores)
        finally:
            Path(temp_path).unlink()

    def test_when_store_loaded_then_values_correct(self):
        """
        Given a shipping.yaml with specific store values
        When the config is loaded
        Then the store should have correct shipping cost and threshold
        """
        # Given
        yaml_content = [
            {"site": "example.com", "shipping": 3.99, "free-over": 49.90},
        ]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(yaml_content, f)
            temp_path = f.name

        try:
            # When
            config = ShippingConfig.load_from_file(temp_path)
            store = config.stores["example.com"]

            # Then
            self.assertEqual(store.site, "example.com")
            self.assertEqual(store.shipping_cost, 3.99)
            self.assertEqual(store.free_over, 49.90)
        finally:
            Path(temp_path).unlink()

    def test_when_file_not_found_then_raises_error(self):
        """
        Given a non-existent YAML file path
        When trying to load the config
        Then FileNotFoundError should be raised
        """
        # Given
        nonexistent_path = Path(tempfile.gettempdir()) / "nonexistent_shipping_file_12345.yaml"

        # When/Then
        with self.assertRaises(FileNotFoundError):
            ShippingConfig.load_from_file(str(nonexistent_path))

    def test_when_invalid_yaml_then_raises_error(self):
        """
        Given an invalid YAML file
        When trying to load the config
        Then yaml.YAMLError should be raised
        """
        # Given
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: content: [\n")
            temp_path = f.name

        try:
            # When/Then
            with self.assertRaises(yaml.YAMLError):
                ShippingConfig.load_from_file(temp_path)
        finally:
            Path(temp_path).unlink()


class TestShippingConfigRetrieval(unittest.TestCase):
    """Test retrieving shipping info from config."""

    def test_when_store_exists_then_returns_correct_info(self):
        """
        Given a config with a specific store
        When requesting that store's shipping info
        Then the correct ShippingInfo should be returned
        """
        # Given
        shipping_info = ShippingInfo(site="example.com", shipping_cost=3.99, free_over=50.00)
        config = ShippingConfig(stores={"example.com": shipping_info})

        # When
        result = config.get_shipping_info("example.com")

        # Then
        self.assertEqual(result.site, "example.com")
        self.assertEqual(result.shipping_cost, 3.99)
        self.assertEqual(result.free_over, 50.00)

    def test_when_store_not_found_then_returns_default(self):
        """
        Given a config without a specific store
        When requesting that store's shipping info
        Then a default ShippingInfo should be returned
        """
        # Given
        config = ShippingConfig(stores={})

        # When
        result = config.get_shipping_info("unknown.com")

        # Then
        self.assertEqual(result.site, "unknown.com")
        self.assertEqual(result.shipping_cost, 3.99)  # Default
        self.assertEqual(result.free_over, NO_FREE_SHIPPING_THRESHOLD)

    def test_when_store_not_found_then_custom_default_used(self):
        """
        Given a config without a specific store
        When requesting that store's shipping info with custom default
        Then a ShippingInfo with custom default should be returned
        """
        # Given
        config = ShippingConfig(stores={})

        # When
        result = config.get_shipping_info("unknown.com", default_shipping=5.50)

        # Then
        self.assertEqual(result.site, "unknown.com")
        self.assertEqual(result.shipping_cost, 5.50)
        self.assertEqual(result.free_over, NO_FREE_SHIPPING_THRESHOLD)


if __name__ == "__main__":
    unittest.main()
