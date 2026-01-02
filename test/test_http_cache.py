"""Tests for utils.http_cache module."""

import json
import os
import tempfile
import time
import unittest

from utils.http_cache import HttpCache


class TestHttpCache(unittest.TestCase):
    """Test the HttpCache class."""

    def setUp(self):
        """Create a temporary cache file for each test."""
        self.temp_fd, self.temp_cache_file = tempfile.mkstemp(suffix=".json")
        os.close(self.temp_fd)

    def tearDown(self):
        """Remove temporary cache file after each test."""
        if os.path.exists(self.temp_cache_file):
            os.remove(self.temp_cache_file)

    def test_cache_miss(self):
        """Test that uncached URLs return None."""
        cache = HttpCache(self.temp_cache_file, cache_duration=3600)

        result = cache.get("https://example.com/product")

        self.assertIsNone(result)

    def test_cache_hit(self):
        """Test that cached data is returned."""
        cache = HttpCache(self.temp_cache_file, cache_duration=3600)
        html_content = "<html><body>Test Product</body></html>"

        # Cache the content
        cache.set("https://example.com/product", html_content)

        # Retrieve from cache
        result = cache.get("https://example.com/product")

        self.assertEqual(result, html_content)

    def test_cache_expiration(self):
        """Test that expired entries return None."""
        # Use a very short cache duration (0.1 seconds)
        cache = HttpCache(self.temp_cache_file, cache_duration=0.1)
        html_content = "<html><body>Test Product</body></html>"

        # Cache the content
        cache.set("https://example.com/product", html_content)

        # Wait for cache to expire
        time.sleep(0.2)

        # Try to retrieve - should be None due to expiration
        result = cache.get("https://example.com/product")

        self.assertIsNone(result)

    def test_cache_persistence(self):
        """Test that cache survives instance recreation."""
        html_content = "<html><body>Test Product</body></html>"

        # Create first cache instance and store data
        cache1 = HttpCache(self.temp_cache_file, cache_duration=3600)
        cache1.set("https://example.com/product", html_content)

        # Create second cache instance with same file
        cache2 = HttpCache(self.temp_cache_file, cache_duration=3600)
        result = cache2.get("https://example.com/product")

        self.assertEqual(result, html_content)

    def test_clear_expired(self):
        """Test that clear_expired removes old entries."""
        cache = HttpCache(self.temp_cache_file, cache_duration=0.1)

        # Add multiple entries
        cache.set("https://example.com/product1", "<html>1</html>")
        cache.set("https://example.com/product2", "<html>2</html>")
        cache.set("https://example.com/product3", "<html>3</html>")

        # Wait for entries to expire
        time.sleep(0.2)

        # Clear expired entries explicitly (before automatic cleanup)
        removed_count = cache.clear_expired()

        # Should have removed 3 expired entries
        self.assertEqual(removed_count, 3)

        # Expired entries should be gone
        self.assertIsNone(cache.get("https://example.com/product1"))
        self.assertIsNone(cache.get("https://example.com/product2"))
        self.assertIsNone(cache.get("https://example.com/product3"))

        # Add a fresh entry after cleanup
        cache.set("https://example.com/product4", "<html>4</html>")

        # Fresh entry should be available
        self.assertEqual(cache.get("https://example.com/product4"), "<html>4</html>")

    def test_corrupted_cache_file(self):
        """Test graceful handling of corrupted JSON."""
        # Write invalid JSON to cache file
        with open(self.temp_cache_file, "w", encoding="utf-8") as f:
            f.write("{ invalid json content }")

        # Cache should handle this gracefully and start fresh
        cache = HttpCache(self.temp_cache_file, cache_duration=3600)
        result = cache.get("https://example.com/product")

        self.assertIsNone(result)

        # Should be able to set new values
        cache.set("https://example.com/product", "<html>test</html>")
        result = cache.get("https://example.com/product")

        self.assertEqual(result, "<html>test</html>")

    def test_cache_file_missing(self):
        """Test that cache creates new file if missing."""
        # Remove the temp file to simulate missing cache
        os.remove(self.temp_cache_file)

        cache = HttpCache(self.temp_cache_file, cache_duration=3600)

        # Should handle missing file gracefully
        result = cache.get("https://example.com/product")
        self.assertIsNone(result)

        # Should be able to create new cache
        cache.set("https://example.com/product", "<html>test</html>")
        result = cache.get("https://example.com/product")

        self.assertEqual(result, "<html>test</html>")
        self.assertTrue(os.path.exists(self.temp_cache_file))

    def test_corrupted_cache_entries(self):
        """Test handling of cache entries with missing required keys."""
        # Create cache with various corrupted entries
        corrupted_cache = {
            "https://example.com/missing-timestamp": {"html": "<html>no timestamp</html>"},
            "https://example.com/missing-html": {"timestamp": time.time()},
            "https://example.com/not-a-dict": "invalid entry",
            "https://example.com/valid": {"html": "<html>valid</html>", "timestamp": time.time()},
        }

        # Write corrupted cache to file
        with open(self.temp_cache_file, "w", encoding="utf-8") as f:
            json.dump(corrupted_cache, f)

        cache = HttpCache(self.temp_cache_file, cache_duration=3600)

        # Corrupted entries should return None (cache miss)
        self.assertIsNone(cache.get("https://example.com/missing-timestamp"))
        self.assertIsNone(cache.get("https://example.com/missing-html"))
        self.assertIsNone(cache.get("https://example.com/not-a-dict"))

        # Valid entry should work
        self.assertEqual(cache.get("https://example.com/valid"), "<html>valid</html>")

    def test_clear_expired_removes_corrupted_entries(self):
        """Test that clear_expired removes corrupted entries along with expired ones."""
        # Create cache with corrupted and valid entries
        cache_data = {
            "https://example.com/missing-timestamp": {"html": "<html>no timestamp</html>"},
            "https://example.com/missing-html": {"timestamp": time.time()},
            "https://example.com/not-a-dict": "invalid entry",
            "https://example.com/valid": {"html": "<html>valid</html>", "timestamp": time.time()},
        }

        # Write cache to file
        with open(self.temp_cache_file, "w", encoding="utf-8") as f:
            json.dump(cache_data, f)

        cache = HttpCache(self.temp_cache_file, cache_duration=3600)

        # Clear expired (should also remove corrupted entries)
        removed_count = cache.clear_expired()

        # Should have removed 3 corrupted entries (not-a-dict, missing-timestamp, missing-html)
        self.assertEqual(removed_count, 3)

        # Valid entry should still exist
        self.assertEqual(cache.get("https://example.com/valid"), "<html>valid</html>")

    def test_multiple_cache_entries(self):
        """Test caching multiple URLs."""
        cache = HttpCache(self.temp_cache_file, cache_duration=3600)

        # Cache multiple URLs
        cache.set("https://example.com/product1", "<html>Product 1</html>")
        cache.set("https://example.com/product2", "<html>Product 2</html>")
        cache.set("https://example.com/product3", "<html>Product 3</html>")

        # Verify all are cached correctly
        self.assertEqual(cache.get("https://example.com/product1"), "<html>Product 1</html>")
        self.assertEqual(cache.get("https://example.com/product2"), "<html>Product 2</html>")
        self.assertEqual(cache.get("https://example.com/product3"), "<html>Product 3</html>")

    def test_cache_update(self):
        """Test that setting a URL again updates the cache."""
        cache = HttpCache(self.temp_cache_file, cache_duration=3600)

        # Cache initial content
        cache.set("https://example.com/product", "<html>Version 1</html>")
        self.assertEqual(cache.get("https://example.com/product"), "<html>Version 1</html>")

        # Update with new content
        cache.set("https://example.com/product", "<html>Version 2</html>")
        result = cache.get("https://example.com/product")

        self.assertEqual(result, "<html>Version 2</html>")

    def test_cache_structure(self):
        """Test that cache file has correct JSON structure."""
        cache = HttpCache(self.temp_cache_file, cache_duration=3600)
        html_content = "<html>test</html>"

        cache.set("https://example.com/product", html_content)

        # Read the cache file directly
        with open(self.temp_cache_file, "r", encoding="utf-8") as f:
            cache_data = json.load(f)

        # Verify structure
        self.assertIn("https://example.com/product", cache_data)
        entry = cache_data["https://example.com/product"]
        self.assertIn("html", entry)
        self.assertIn("timestamp", entry)
        self.assertEqual(entry["html"], html_content)
        self.assertIsInstance(entry["timestamp"], (int, float))

        # Should NOT have status field (per user requirement)
        self.assertNotIn("status", entry)

    def test_automatic_cleanup_on_save(self):
        """Test that expired entries are cleaned up when saving."""
        cache = HttpCache(self.temp_cache_file, cache_duration=0.1)

        # Add entries that will expire
        cache.set("https://example.com/old1", "<html>old1</html>")
        cache.set("https://example.com/old2", "<html>old2</html>")

        # Wait for expiration
        time.sleep(0.2)

        # Add a fresh entry (triggers save and cleanup)
        cache.set("https://example.com/fresh", "<html>fresh</html>")

        # Read cache file to verify cleanup happened
        with open(self.temp_cache_file, "r", encoding="utf-8") as f:
            cache_data = json.load(f)

        # Only fresh entry should be in file
        self.assertEqual(len(cache_data), 1)
        self.assertIn("https://example.com/fresh", cache_data)
        self.assertNotIn("https://example.com/old1", cache_data)
        self.assertNotIn("https://example.com/old2", cache_data)

    def test_remove_url_from_cache(self):
        """Test removing a URL from cache."""
        cache = HttpCache(self.temp_cache_file, cache_duration=3600)

        # Add multiple entries
        cache.set("https://example.com/product1", "<html>Product 1</html>")
        cache.set("https://example.com/product2", "<html>Product 2</html>")
        cache.set("https://example.com/product3", "<html>Product 3</html>")

        # Verify all are cached
        self.assertIsNotNone(cache.get("https://example.com/product1"))
        self.assertIsNotNone(cache.get("https://example.com/product2"))
        self.assertIsNotNone(cache.get("https://example.com/product3"))

        # Remove one entry
        cache.remove("https://example.com/product2")

        # Verify product2 is gone but others remain
        self.assertIsNotNone(cache.get("https://example.com/product1"))
        self.assertIsNone(cache.get("https://example.com/product2"))
        self.assertIsNotNone(cache.get("https://example.com/product3"))

    def test_remove_nonexistent_url_does_nothing(self):
        """Test removing a URL that doesn't exist in cache."""
        cache = HttpCache(self.temp_cache_file, cache_duration=3600)

        cache.set("https://example.com/product", "<html>Product</html>")

        # Remove non-existent URL - should not raise error
        cache.remove("https://example.com/nonexistent")

        # Original entry should still be there
        self.assertIsNotNone(cache.get("https://example.com/product"))

    def test_remove_persists_to_file(self):
        """Test that removal is persisted to the cache file."""
        cache = HttpCache(self.temp_cache_file, cache_duration=3600)

        cache.set("https://example.com/product1", "<html>Product 1</html>")
        cache.set("https://example.com/product2", "<html>Product 2</html>")

        # Remove one entry
        cache.remove("https://example.com/product1")

        # Create new cache instance to verify persistence
        cache2 = HttpCache(self.temp_cache_file, cache_duration=3600)
        self.assertIsNone(cache2.get("https://example.com/product1"))
        self.assertIsNotNone(cache2.get("https://example.com/product2"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
