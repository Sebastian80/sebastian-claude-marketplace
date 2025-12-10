"""
TTY-aware terminal colors for skills daemon.

Provides consistent color output that automatically disables
when stdout is not a terminal (piped, redirected, etc.).
"""

import sys
from typing import Callable


# ANSI color codes
_CODES = {
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "cyan": "\033[36m",
    "white": "\033[37m",
    "dim": "\033[2m",
    "bold": "\033[1m",
    "reset": "\033[0m",
}


def _is_tty() -> bool:
    """Check if stdout is a terminal."""
    return sys.stdout.isatty()


def colored(text: str, color: str) -> str:
    """Apply color to text if stdout is a TTY.

    Args:
        text: Text to colorize
        color: Color name (red, green, yellow, cyan, dim, bold, etc.)

    Returns:
        Colored text if TTY, plain text otherwise
    """
    if not _is_tty():
        return text
    code = _CODES.get(color, "")
    if not code:
        return text
    return f"{code}{text}{_CODES['reset']}"


def red(text: str) -> str:
    """Red text (errors)."""
    return colored(text, "red")


def green(text: str) -> str:
    """Green text (success)."""
    return colored(text, "green")


def yellow(text: str) -> str:
    """Yellow text (warnings)."""
    return colored(text, "yellow")


def cyan(text: str) -> str:
    """Cyan text (info)."""
    return colored(text, "cyan")


def dim(text: str) -> str:
    """Dim text (secondary info)."""
    return colored(text, "dim")


def bold(text: str) -> str:
    """Bold text (emphasis)."""
    return colored(text, "bold")


# For backward compatibility with inline tuple pattern
def get_color_tuple() -> tuple[str, str, str, str, str, str, str]:
    """Get color codes tuple (RED, GREEN, YELLOW, CYAN, DIM, BOLD, RESET).

    Returns empty strings if not a TTY.
    """
    if _is_tty():
        return (
            _CODES["red"],
            _CODES["green"],
            _CODES["yellow"],
            _CODES["cyan"],
            _CODES["dim"],
            _CODES["bold"],
            _CODES["reset"],
        )
    return ("", "", "", "", "", "", "")
