"""Unit tests for colors module."""

import sys
from unittest.mock import patch

import pytest
from skills_daemon.colors import (
    colored,
    red,
    green,
    yellow,
    dim,
    bold,
    get_color_tuple,
    _is_tty,
)


class TestColoredFunction:
    """Test the colored() function."""

    def test_colored_with_tty(self):
        """Colors applied when TTY."""
        with patch.object(sys.stdout, 'isatty', return_value=True):
            result = colored("test", "red")
            assert "\033[31m" in result
            assert "\033[0m" in result
            assert "test" in result

    def test_colored_without_tty(self):
        """Colors stripped when not TTY."""
        with patch.object(sys.stdout, 'isatty', return_value=False):
            result = colored("test", "red")
            assert result == "test"
            assert "\033[" not in result

    def test_colored_unknown_color(self):
        """Unknown color returns plain text."""
        with patch.object(sys.stdout, 'isatty', return_value=True):
            result = colored("test", "unknown")
            assert result == "test"


class TestColorHelpers:
    """Test color helper functions."""

    def test_red(self):
        """red() applies red color."""
        with patch.object(sys.stdout, 'isatty', return_value=True):
            result = red("error")
            assert "\033[31m" in result

    def test_green(self):
        """green() applies green color."""
        with patch.object(sys.stdout, 'isatty', return_value=True):
            result = green("success")
            assert "\033[32m" in result

    def test_dim(self):
        """dim() applies dim styling."""
        with patch.object(sys.stdout, 'isatty', return_value=True):
            result = dim("secondary")
            assert "\033[2m" in result


class TestGetColorTuple:
    """Test get_color_tuple() for backward compatibility."""

    def test_returns_tuple_with_tty(self):
        """Returns color codes tuple when TTY."""
        with patch.object(sys.stdout, 'isatty', return_value=True):
            result = get_color_tuple()
            assert len(result) == 7
            assert all(isinstance(c, str) for c in result)
            assert "\033[31m" in result[0]  # RED

    def test_returns_empty_strings_without_tty(self):
        """Returns empty strings when not TTY."""
        with patch.object(sys.stdout, 'isatty', return_value=False):
            result = get_color_tuple()
            assert len(result) == 7
            assert all(c == "" for c in result)
