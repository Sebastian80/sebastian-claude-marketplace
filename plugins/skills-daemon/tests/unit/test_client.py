"""Unit tests for skills_client module."""

import json
import socket
import urllib.error
from unittest.mock import patch, MagicMock

import pytest

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "cli"))

from skills_client import request, MAX_RETRIES, RETRY_BACKOFF_BASE


class TestRequest:
    """Tests for HTTP request function with retry logic."""

    def test_successful_request(self):
        """Successful request returns response data."""
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"success": true, "data": "test"}'
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch('urllib.request.urlopen', return_value=mock_response):
            result = request("health", {})

        assert result == {"success": True, "data": "test"}

    def test_http_error_not_retried(self):
        """HTTP errors (4xx, 5xx) are not retried."""
        error = urllib.error.HTTPError(
            "http://test", 404, "Not Found", {}, None
        )
        error.read = MagicMock(return_value=b'{"success": false, "error": "not found"}')

        with patch('urllib.request.urlopen', side_effect=error) as mock_open:
            result = request("test", {})

        # Should only be called once (no retries)
        assert mock_open.call_count == 1
        assert result == {"success": False, "error": "not found"}

    def test_connection_error_retried(self):
        """Connection errors trigger retry with backoff."""
        error = urllib.error.URLError("Connection refused")

        with patch('urllib.request.urlopen', side_effect=error) as mock_open:
            with patch('time.sleep') as mock_sleep:
                result = request("test", {})

        # Should retry MAX_RETRIES times
        assert mock_open.call_count == MAX_RETRIES
        # Should sleep between retries (MAX_RETRIES - 1 sleeps)
        assert mock_sleep.call_count == MAX_RETRIES - 1
        assert "Connection failed after" in result["error"]

    def test_exponential_backoff(self):
        """Backoff delay increases exponentially."""
        error = urllib.error.URLError("Connection refused")
        sleep_times = []

        def capture_sleep(delay):
            sleep_times.append(delay)

        with patch('urllib.request.urlopen', side_effect=error):
            with patch('time.sleep', side_effect=capture_sleep):
                request("test", {})

        # Verify exponential backoff: 0.5, 1.0 (for MAX_RETRIES=3)
        expected = [RETRY_BACKOFF_BASE * (2 ** i) for i in range(MAX_RETRIES - 1)]
        assert sleep_times == expected

    def test_retry_succeeds_on_second_attempt(self):
        """Request succeeds after initial failure."""
        error = urllib.error.URLError("Connection refused")
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"success": true}'
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        # First call fails, second succeeds
        with patch('urllib.request.urlopen', side_effect=[error, mock_response]) as mock_open:
            with patch('time.sleep'):
                result = request("test", {})

        assert mock_open.call_count == 2
        assert result == {"success": True}

    def test_socket_timeout_retried(self):
        """Socket timeouts trigger retry."""
        with patch('urllib.request.urlopen', side_effect=socket.timeout("timed out")) as mock_open:
            with patch('time.sleep'):
                result = request("test", {})

        assert mock_open.call_count == MAX_RETRIES
        assert "Connection failed after" in result["error"]

    def test_query_params_encoded(self):
        """Query parameters are properly encoded."""
        mock_response = MagicMock()
        mock_response.read.return_value = b'{}'
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch('urllib.request.urlopen', return_value=mock_response) as mock_open:
            request("search", {"query": "test value", "limit": 10})

        # Check URL contains encoded params
        call_args = mock_open.call_args
        req = call_args[0][0]
        assert "query=test+value" in req.full_url or "query=test%20value" in req.full_url
        assert "limit=10" in req.full_url

    def test_none_params_filtered(self):
        """None values are filtered from params."""
        mock_response = MagicMock()
        mock_response.read.return_value = b'{}'
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch('urllib.request.urlopen', return_value=mock_response) as mock_open:
            request("test", {"key": "value", "empty": None})

        req = mock_open.call_args[0][0]
        assert "key=value" in req.full_url
        assert "empty" not in req.full_url
