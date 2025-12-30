"""Tests for configuration class."""

import os
import unittest

from src.config import Config, config


class TestConfig(unittest.TestCase):
    """Test Config class with defaults and environment variables."""

    def test_default_values(self):
        """Test default configuration values."""
        test_config = Config()
        self.assertEqual(test_config.min_price, 1.0)
        self.assertEqual(test_config.max_price, 1000.0)
        self.assertEqual(test_config.request_timeout, 15)
        self.assertEqual(test_config.max_retries, 2)
        self.assertEqual(test_config.notino_delay_min, 4.0)
        self.assertEqual(test_config.notino_delay_max, 7.0)
        self.assertEqual(test_config.default_delay_min, 1.0)
        self.assertEqual(test_config.default_delay_max, 2.0)
        self.assertEqual(test_config.retry_delay_min, 5.0)
        self.assertEqual(test_config.retry_delay_max, 8.0)

    def test_price_range_validation(self):
        """Test price range constants."""
        test_config = Config()
        self.assertLess(test_config.min_price, test_config.max_price)

    def test_constants_are_positive(self):
        """Test all numeric constants are positive."""
        test_config = Config()
        self.assertGreater(test_config.request_timeout, 0)
        self.assertGreater(test_config.max_retries, 0)
        self.assertGreater(test_config.notino_delay_min, 0)
        self.assertGreater(test_config.notino_delay_max, test_config.notino_delay_min)
        self.assertGreater(test_config.default_delay_min, 0)
        self.assertGreater(test_config.default_delay_max, test_config.default_delay_min)
        self.assertGreater(test_config.retry_delay_min, 0)
        self.assertGreater(test_config.retry_delay_max, test_config.retry_delay_min)

    def test_global_config_instance(self):
        """Test that the global config instance exists and works."""
        self.assertIsInstance(config, Config)
        self.assertEqual(config.min_price, 1.0)

    def test_environment_variable_overrides(self):
        """Test configuration can be overridden with environment variables."""
        # Set environment variables
        os.environ["DEAL_CRAWLER_MIN_PRICE"] = "5.0"
        os.environ["DEAL_CRAWLER_MAX_PRICE"] = "500.0"
        os.environ["DEAL_CRAWLER_REQUEST_TIMEOUT"] = "30"
        os.environ["DEAL_CRAWLER_MAX_RETRIES"] = "5"

        # Create new config instance
        test_config = Config()

        # Check overridden values
        self.assertEqual(test_config.min_price, 5.0)
        self.assertEqual(test_config.max_price, 500.0)
        self.assertEqual(test_config.request_timeout, 30)
        self.assertEqual(test_config.max_retries, 5)

        # Clean up environment variables
        del os.environ["DEAL_CRAWLER_MIN_PRICE"]
        del os.environ["DEAL_CRAWLER_MAX_PRICE"]
        del os.environ["DEAL_CRAWLER_REQUEST_TIMEOUT"]
        del os.environ["DEAL_CRAWLER_MAX_RETRIES"]


if __name__ == "__main__":
    unittest.main(verbosity=2)
