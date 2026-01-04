"""Tests for HTTP client operations."""

import unittest
from unittest.mock import patch, MagicMock, Mock
import requests

from utils.http_client import HttpClient
from utils.config import config


class TestHttpClient(unittest.TestCase):
    """Test HttpClient class functionality."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock the cache to avoid file I/O and ensure tests don't hit cache
        self.cache_patcher = patch("utils.http_client.HttpCache")
        mock_cache_class = self.cache_patcher.start()
        mock_cache = MagicMock()
        mock_cache.get.return_value = None  # Always cache miss
        mock_cache_class.return_value = mock_cache

        self.client = HttpClient()
        self.mock_cache = mock_cache

    def tearDown(self):
        """Clean up after tests."""
        self.client.close()
        self.cache_patcher.stop()

    def test_default_headers(self):
        """Test default headers for regular sites."""
        headers = self.client.get_headers_for_site("https://example.com/product")
        self.assertIn("User-Agent", headers)
        self.assertIn("Accept", headers)
        self.assertNotIn("Referer", headers)

    def test_notino_specific_headers(self):
        """Test notino.pt gets special headers."""
        headers = self.client.get_headers_for_site("https://www.notino.pt/product")
        self.assertIn("User-Agent", headers)
        self.assertIn("Referer", headers)
        # Referer is randomized, check it's one of the valid options
        valid_referers = [
            "https://www.google.com/",
            "https://www.google.pt/",
            "https://www.notino.pt/",
        ]
        self.assertIn(headers["Referer"], valid_referers)
        self.assertIn("Origin", headers)
        self.assertEqual(headers["Origin"], "https://www.notino.pt")
        self.assertIn("sec-ch-ua", headers)
        self.assertIn("sec-ch-ua-arch", headers)
        self.assertIn("sec-ch-ua-bitness", headers)

    def test_headers_are_dict(self):
        """Test headers return a dictionary."""
        headers = self.client.get_headers_for_site("https://example.com")
        self.assertIsInstance(headers, dict)

    def test_context_manager(self):
        """Test HttpClient works as context manager."""
        with HttpClient() as client:
            self.assertIsNotNone(client.session)
        # Session should be closed after exiting context
        # We can't directly test if session is closed, but we can verify
        # that close() was called by checking the client still exists
        self.assertIsNotNone(client)

    @patch("utils.http_client.requests.Session")
    def test_close_method(self, mock_session_class):
        """Test close method closes the session."""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        client = HttpClient()
        client.close()

        mock_session.close.assert_called_once()

    def test_initialization_with_custom_config(self):
        """Test HttpClient can be initialized with custom configuration."""
        client = HttpClient(timeout=30, max_retries=5)
        self.assertEqual(client.timeout, 30)
        self.assertEqual(client.max_retries, 5)
        client.close()

    def test_get_delay_for_notino_url(self):
        """Test delay calculation for notino.pt URLs."""
        delay = self.client._get_delay_for_url("https://www.notino.pt/product")
        self.assertGreaterEqual(delay, config.notino_delay_min)
        self.assertLessEqual(delay, config.notino_delay_max)

    def test_get_delay_for_regular_url(self):
        """Test delay calculation for regular URLs."""
        delay = self.client._get_delay_for_url("https://example.com/product")
        self.assertGreaterEqual(delay, config.default_delay_min)
        self.assertLessEqual(delay, config.default_delay_max)

    @patch("utils.http_client.time.sleep")
    @patch("utils.http_client.BeautifulSoup")
    def test_fetch_page_success(self, mock_soup, mock_sleep):
        """Test successful page fetch."""
        # Mock the response
        mock_response = Mock()
        mock_response.content = b"<html><body>Test</body></html>"
        mock_response.text = "<html><body>Test</body></html>"
        mock_response.raise_for_status = Mock()
        self.client.session.get = Mock(return_value=mock_response)  # type: ignore[method-assign]

        # Mock BeautifulSoup
        mock_soup_instance = Mock()
        mock_soup.return_value = mock_soup_instance

        result = self.client.fetch_page("https://example.com/product")

        self.assertEqual(result, mock_soup_instance)
        self.client.session.get.assert_called_once()
        mock_sleep.assert_called_once()  # Should have one delay
        mock_soup.assert_called_once_with("<html><body>Test</body></html>", "lxml")

    @patch("utils.http_client.time.sleep")
    def test_fetch_page_http_error_non_403(self, mock_sleep):
        """Test fetch_page handles non-403 HTTP errors."""
        # Mock 404 error
        mock_response = Mock()
        mock_response.status_code = 404
        http_error = requests.exceptions.HTTPError()
        http_error.response = mock_response

        self.client.session.get = Mock(side_effect=http_error)  # type: ignore[method-assign]

        result = self.client.fetch_page("https://example.com/product")

        self.assertIsNone(result)
        self.client.session.get.assert_called_once()

    @patch("utils.http_client.time.sleep")
    @patch("utils.http_client.BeautifulSoup")
    def test_fetch_page_403_retry_then_success(self, mock_soup, mock_sleep):
        """Test fetch_page retries on 403 then succeeds."""
        # Mock 403 error on first call, success on second
        mock_response_403 = Mock()
        mock_response_403.status_code = 403
        http_error = requests.exceptions.HTTPError()
        http_error.response = mock_response_403

        mock_response_success = Mock()
        mock_response_success.content = b"<html><body>Success</body></html>"
        mock_response_success.raise_for_status = Mock()

        self.client.session.get = Mock(side_effect=[http_error, mock_response_success])  # type: ignore[method-assign]

        mock_soup_instance = Mock()
        mock_soup.return_value = mock_soup_instance

        result = self.client.fetch_page("https://example.com/product")

        self.assertEqual(result, mock_soup_instance)
        self.assertEqual(self.client.session.get.call_count, 2)
        # Should have: initial delay + retry delay + second attempt delay
        self.assertEqual(mock_sleep.call_count, 3)

    @patch("utils.http_client.time.sleep")
    def test_fetch_page_403_max_retries_exceeded(self, mock_sleep):
        """Test fetch_page gives up after max retries on 403."""
        # Mock 403 error on all attempts
        mock_response_403 = Mock()
        mock_response_403.status_code = 403
        http_error = requests.exceptions.HTTPError()
        http_error.response = mock_response_403

        self.client.session.get = Mock(side_effect=http_error)  # type: ignore[method-assign]

        result = self.client.fetch_page("https://example.com/product", retry_count=2)

        self.assertIsNone(result)
        # Should try: initial + 2 retries = 3 attempts
        self.assertEqual(self.client.session.get.call_count, 3)

    @patch("utils.http_client.time.sleep")
    def test_fetch_page_generic_exception(self, mock_sleep):
        """Test fetch_page handles generic exceptions."""
        self.client.session.get = Mock(side_effect=Exception("Network error"))  # type: ignore[method-assign]

        result = self.client.fetch_page("https://example.com/product")

        self.assertIsNone(result)
        self.client.session.get.assert_called_once()

    @patch("utils.http_client.time.sleep")
    def test_fetch_page_uses_default_retry_count(self, mock_sleep):
        """Test fetch_page uses default max_retries when not specified."""
        # Test with 403 errors which do retry
        self.client.max_retries = 3
        mock_response_403 = Mock()
        mock_response_403.status_code = 403
        http_error = requests.exceptions.HTTPError()
        http_error.response = mock_response_403
        self.client.session.get = Mock(side_effect=http_error)  # type: ignore[method-assign]

        result = self.client.fetch_page("https://example.com/product")

        self.assertIsNone(result)
        # Should try: initial + 3 retries = 4 attempts
        self.assertEqual(self.client.session.get.call_count, 4)

    @patch("utils.http_client.BeautifulSoup")
    @patch("utils.http_client.time.sleep")
    def test_fetch_page_retries_on_connection_error(self, mock_sleep, mock_soup):
        """Test fetch_page retries on ConnectionError."""
        # Fail twice, then succeed
        self.client.session.get = Mock(  # type: ignore[method-assign]
            side_effect=[
                requests.exceptions.ConnectionError("Connection failed"),
                requests.exceptions.ConnectionError("Connection failed"),
                Mock(status_code=200, content=b"<html>Success</html>"),
            ]
        )

        result = self.client.fetch_page("https://example.com/product")

        self.assertIsNotNone(result)
        self.assertEqual(self.client.session.get.call_count, 3)

    @patch("utils.http_client.BeautifulSoup")
    @patch("utils.http_client.time.sleep")
    def test_fetch_page_retries_on_timeout(self, mock_sleep, mock_soup):
        """Test fetch_page retries on Timeout."""
        # Timeout once, then succeed
        self.client.session.get = Mock(  # type: ignore[method-assign]
            side_effect=[
                requests.exceptions.Timeout("Request timed out"),
                Mock(status_code=200, content=b"<html>Success</html>"),
            ]
        )

        result = self.client.fetch_page("https://example.com/product")

        self.assertIsNotNone(result)
        self.assertEqual(self.client.session.get.call_count, 2)

    @patch("utils.http_client.time.sleep")
    def test_fetch_page_retries_on_chunked_encoding_error(self, mock_sleep):
        """Test fetch_page retries on ChunkedEncodingError."""
        self.client.session.get = Mock(  # type: ignore[method-assign]
            side_effect=requests.exceptions.ChunkedEncodingError("Incomplete read")
        )

        result = self.client.fetch_page("https://example.com/product")

        self.assertIsNone(result)
        # Should try: initial + 2 retries = 3 attempts
        self.assertEqual(self.client.session.get.call_count, 3)

    @patch("utils.http_client.time.sleep")
    def test_fetch_page_exhausts_retries_on_connection_error(self, mock_sleep):
        """Test fetch_page gives up after max retries on connection errors."""
        self.client.session.get = Mock(  # type: ignore[method-assign]
            side_effect=requests.exceptions.ConnectionError("Connection failed")
        )

        result = self.client.fetch_page("https://example.com/product")

        self.assertIsNone(result)
        # Should try: initial + 2 retries = 3 attempts
        self.assertEqual(self.client.session.get.call_count, 3)

    @patch("utils.http_client.time.sleep")
    def test_fetch_page_does_not_retry_on_non_transient_errors(self, mock_sleep):
        """Test fetch_page does not retry on non-transient errors."""
        # ValueError is not a transient error
        self.client.session.get = Mock(side_effect=ValueError("Invalid URL"))  # type: ignore[method-assign]

        result = self.client.fetch_page("https://example.com/product")

        self.assertIsNone(result)
        # Should only try once (no retries)
        self.assertEqual(self.client.session.get.call_count, 1)

    @patch("utils.http_client.time.sleep")
    @patch("utils.http_client.BeautifulSoup")
    def test_cache_hit_returns_cached_html(self, mock_soup, mock_sleep):
        """Test that cache hit returns cached HTML without making HTTP request."""
        # Configure cache to return cached HTML
        cached_html = "<html><body>Cached Content</body></html>"
        self.mock_cache.get.return_value = cached_html

        # Mock session.get to verify it's not called
        self.client.session.get = Mock()  # type: ignore[method-assign]

        mock_soup_instance = Mock()
        mock_soup.return_value = mock_soup_instance

        result = self.client.fetch_page("https://example.com/product")

        # Should use cache
        self.mock_cache.get.assert_called_once_with("https://example.com/product")
        self.assertEqual(result, mock_soup_instance)

        # Should NOT make HTTP request
        self.client.session.get.assert_not_called()

        # Should NOT apply rate limiting delay
        mock_sleep.assert_not_called()

        # Should parse cached HTML
        mock_soup.assert_called_once_with(cached_html, "lxml")

    @patch("utils.http_client.time.sleep")
    @patch("utils.http_client.BeautifulSoup")
    def test_cache_miss_makes_http_request(self, mock_soup, mock_sleep):
        """Test that cache miss makes HTTP request and caches result."""
        # Configure cache to return None (cache miss)
        self.mock_cache.get.return_value = None

        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"<html><body>Fresh Content</body></html>"
        mock_response.text = "<html><body>Fresh Content</body></html>"
        mock_response.raise_for_status = Mock()
        self.client.session.get = Mock(return_value=mock_response)  # type: ignore[method-assign]

        mock_soup_instance = Mock()
        mock_soup.return_value = mock_soup_instance

        result = self.client.fetch_page("https://example.com/product")

        # Should check cache
        self.mock_cache.get.assert_called_once_with("https://example.com/product")

        # Should make HTTP request
        self.client.session.get.assert_called_once()

        # Should cache the response
        self.mock_cache.set.assert_called_once_with(
            "https://example.com/product", "<html><body>Fresh Content</body></html>"
        )

        # Should apply rate limiting delay
        mock_sleep.assert_called_once()

        # Should return parsed content
        self.assertEqual(result, mock_soup_instance)

    @patch("utils.http_client.time.sleep")
    def test_cache_only_stores_200_responses(self, mock_sleep):
        """Test that only HTTP 200 responses are cached."""
        # Configure cache miss
        self.mock_cache.get.return_value = None

        # Mock 404 error
        mock_response = Mock()
        mock_response.status_code = 404
        http_error = requests.exceptions.HTTPError()
        http_error.response = mock_response
        self.client.session.get = Mock(side_effect=http_error)  # type: ignore[method-assign]

        result = self.client.fetch_page("https://example.com/product")

        # Should NOT cache the failed response
        self.mock_cache.set.assert_not_called()

        self.assertIsNone(result)

    def test_use_cache_false_disables_caching(self):
        """Test that use_cache=False disables cache."""
        client = HttpClient(use_cache=False)

        # Cache should be None when disabled
        self.assertIsNone(client.cache)
        self.assertFalse(client.use_cache)

        client.close()

    @patch("utils.http_client.time.sleep")
    @patch("utils.http_client.BeautifulSoup")
    def test_no_cache_bypasses_cache_read(self, mock_soup, mock_sleep):
        """Test that use_cache=False bypasses cache read."""
        # Create client with caching disabled
        with patch("utils.http_client.HttpCache"):
            client = HttpClient(use_cache=False)

        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"<html><body>Fresh Content</body></html>"
        mock_response.raise_for_status = Mock()
        client.session.get = Mock(return_value=mock_response)  # type: ignore[method-assign]

        mock_soup_instance = Mock()
        mock_soup.return_value = mock_soup_instance

        result = client.fetch_page("https://example.com/product")

        # Should make HTTP request (not use cache)
        client.session.get.assert_called_once()

        # Should return result
        self.assertEqual(result, mock_soup_instance)

        client.close()

    @patch("utils.http_client.time.sleep")
    @patch("utils.http_client.BeautifulSoup")
    def test_no_cache_bypasses_cache_write(self, mock_soup, mock_sleep):
        """Test that use_cache=False bypasses cache write."""
        # Create client with caching disabled
        with patch("utils.http_client.HttpCache"):
            client = HttpClient(use_cache=False)

        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"<html><body>Test</body></html>"
        mock_response.raise_for_status = Mock()
        client.session.get = Mock(return_value=mock_response)  # type: ignore[method-assign]

        mock_soup_instance = Mock()
        mock_soup.return_value = mock_soup_instance

        result = client.fetch_page("https://example.com/product")

        # Should NOT attempt to cache (cache is None)
        self.assertIsNone(client.cache)

        # Should still return result
        self.assertEqual(result, mock_soup_instance)

        client.close()

    @patch("utils.http_client.HttpCache")
    def test_initialization_with_custom_cache_duration(self, mock_cache_class):
        """Test HttpClient can be initialized with custom cache_duration."""
        mock_cache = MagicMock()
        mock_cache_class.return_value = mock_cache

        client = HttpClient(cache_duration=7200)

        # Verify HttpCache was initialized with custom cache_duration
        mock_cache_class.assert_called_once_with(config.cache_file, 7200)
        client.close()

    @patch("utils.http_client.HttpCache")
    def test_initialization_with_custom_cache_file(self, mock_cache_class):
        """Test HttpClient can be initialized with custom cache_file."""
        mock_cache = MagicMock()
        mock_cache_class.return_value = mock_cache

        client = HttpClient(cache_file="custom_cache.json")

        # Verify HttpCache was initialized with custom cache_file
        mock_cache_class.assert_called_once_with("custom_cache.json", config.cache_duration)
        client.close()

    @patch("utils.http_client.HttpCache")
    def test_initialization_with_custom_cache_duration_and_file(self, mock_cache_class):
        """Test HttpClient can be initialized with both custom cache_duration and cache_file."""
        mock_cache = MagicMock()
        mock_cache_class.return_value = mock_cache

        client = HttpClient(cache_duration=7200, cache_file="custom_cache.json")

        # Verify HttpCache was initialized with both custom parameters
        mock_cache_class.assert_called_once_with("custom_cache.json", 7200)
        client.close()

    @patch("utils.http_client.HttpCache")
    def test_initialization_cache_duration_defaults_to_config(self, mock_cache_class):
        """Test HttpClient uses config.cache_duration when not specified."""
        mock_cache = MagicMock()
        mock_cache_class.return_value = mock_cache

        client = HttpClient()

        # Verify HttpCache was initialized with default cache_duration from config
        mock_cache_class.assert_called_once_with(config.cache_file, config.cache_duration)
        client.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
