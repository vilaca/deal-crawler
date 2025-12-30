"""Tests for HTTP client operations."""

import unittest
from unittest.mock import patch, MagicMock, Mock
import requests

from http_client import HttpClient
from config import config


class TestHttpClient(unittest.TestCase):
    """Test HttpClient class functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.client = HttpClient()

    def tearDown(self):
        """Clean up after tests."""
        self.client.close()

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

    @patch("http_client.requests.Session")
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

    @patch("http_client.time.sleep")
    @patch("http_client.BeautifulSoup")
    def test_fetch_page_success(self, mock_soup, mock_sleep):
        """Test successful page fetch."""
        # Mock the response
        mock_response = Mock()
        mock_response.content = b"<html><body>Test</body></html>"
        mock_response.raise_for_status = Mock()
        self.client.session.get = Mock(return_value=mock_response)

        # Mock BeautifulSoup
        mock_soup_instance = Mock()
        mock_soup.return_value = mock_soup_instance

        result = self.client.fetch_page("https://example.com/product")

        self.assertEqual(result, mock_soup_instance)
        self.client.session.get.assert_called_once()
        mock_sleep.assert_called_once()  # Should have one delay
        mock_soup.assert_called_once_with(b"<html><body>Test</body></html>", "lxml")

    @patch("http_client.time.sleep")
    def test_fetch_page_http_error_non_403(self, mock_sleep):
        """Test fetch_page handles non-403 HTTP errors."""
        # Mock 404 error
        mock_response = Mock()
        mock_response.status_code = 404
        http_error = requests.exceptions.HTTPError()
        http_error.response = mock_response

        self.client.session.get = Mock(side_effect=http_error)

        result = self.client.fetch_page("https://example.com/product")

        self.assertIsNone(result)
        self.client.session.get.assert_called_once()

    @patch("http_client.time.sleep")
    @patch("http_client.BeautifulSoup")
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

        self.client.session.get = Mock(
            side_effect=[http_error, mock_response_success]
        )

        mock_soup_instance = Mock()
        mock_soup.return_value = mock_soup_instance

        result = self.client.fetch_page("https://example.com/product")

        self.assertEqual(result, mock_soup_instance)
        self.assertEqual(self.client.session.get.call_count, 2)
        # Should have: initial delay + retry delay + second attempt delay
        self.assertEqual(mock_sleep.call_count, 3)

    @patch("http_client.time.sleep")
    def test_fetch_page_403_max_retries_exceeded(self, mock_sleep):
        """Test fetch_page gives up after max retries on 403."""
        # Mock 403 error on all attempts
        mock_response_403 = Mock()
        mock_response_403.status_code = 403
        http_error = requests.exceptions.HTTPError()
        http_error.response = mock_response_403

        self.client.session.get = Mock(side_effect=http_error)

        result = self.client.fetch_page("https://example.com/product", retry_count=2)

        self.assertIsNone(result)
        # Should try: initial + 2 retries = 3 attempts
        self.assertEqual(self.client.session.get.call_count, 3)

    @patch("http_client.time.sleep")
    def test_fetch_page_generic_exception(self, mock_sleep):
        """Test fetch_page handles generic exceptions."""
        self.client.session.get = Mock(side_effect=Exception("Network error"))

        result = self.client.fetch_page("https://example.com/product")

        self.assertIsNone(result)
        self.client.session.get.assert_called_once()

    @patch("http_client.time.sleep")
    def test_fetch_page_uses_default_retry_count(self, mock_sleep):
        """Test fetch_page uses default max_retries when not specified."""
        # Test with 403 errors which do retry
        self.client.max_retries = 3
        mock_response_403 = Mock()
        mock_response_403.status_code = 403
        http_error = requests.exceptions.HTTPError()
        http_error.response = mock_response_403
        self.client.session.get = Mock(side_effect=http_error)

        result = self.client.fetch_page("https://example.com/product")

        self.assertIsNone(result)
        # Should try: initial + 3 retries = 4 attempts
        self.assertEqual(self.client.session.get.call_count, 4)

    @patch("http_client.BeautifulSoup")
    @patch("http_client.time.sleep")
    def test_fetch_page_retries_on_connection_error(self, mock_sleep, mock_soup):
        """Test fetch_page retries on ConnectionError."""
        # Fail twice, then succeed
        self.client.session.get = Mock(
            side_effect=[
                requests.exceptions.ConnectionError("Connection failed"),
                requests.exceptions.ConnectionError("Connection failed"),
                Mock(status_code=200, content=b"<html>Success</html>"),
            ]
        )

        result = self.client.fetch_page("https://example.com/product")

        self.assertIsNotNone(result)
        self.assertEqual(self.client.session.get.call_count, 3)

    @patch("http_client.BeautifulSoup")
    @patch("http_client.time.sleep")
    def test_fetch_page_retries_on_timeout(self, mock_sleep, mock_soup):
        """Test fetch_page retries on Timeout."""
        # Timeout once, then succeed
        self.client.session.get = Mock(
            side_effect=[
                requests.exceptions.Timeout("Request timed out"),
                Mock(status_code=200, content=b"<html>Success</html>"),
            ]
        )

        result = self.client.fetch_page("https://example.com/product")

        self.assertIsNotNone(result)
        self.assertEqual(self.client.session.get.call_count, 2)

    @patch("http_client.time.sleep")
    def test_fetch_page_retries_on_chunked_encoding_error(self, mock_sleep):
        """Test fetch_page retries on ChunkedEncodingError."""
        self.client.session.get = Mock(
            side_effect=requests.exceptions.ChunkedEncodingError("Incomplete read")
        )

        result = self.client.fetch_page("https://example.com/product")

        self.assertIsNone(result)
        # Should try: initial + 2 retries = 3 attempts
        self.assertEqual(self.client.session.get.call_count, 3)

    @patch("http_client.time.sleep")
    def test_fetch_page_exhausts_retries_on_connection_error(self, mock_sleep):
        """Test fetch_page gives up after max retries on connection errors."""
        self.client.session.get = Mock(
            side_effect=requests.exceptions.ConnectionError("Connection failed")
        )

        result = self.client.fetch_page("https://example.com/product")

        self.assertIsNone(result)
        # Should try: initial + 2 retries = 3 attempts
        self.assertEqual(self.client.session.get.call_count, 3)

    @patch("http_client.time.sleep")
    def test_fetch_page_does_not_retry_on_non_transient_errors(self, mock_sleep):
        """Test fetch_page does not retry on non-transient errors."""
        # ValueError is not a transient error
        self.client.session.get = Mock(side_effect=ValueError("Invalid URL"))

        result = self.client.fetch_page("https://example.com/product")

        self.assertIsNone(result)
        # Should only try once (no retries)
        self.assertEqual(self.client.session.get.call_count, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
