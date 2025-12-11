"""
Built-in implementations - Default formatters and utilities.

These are registered automatically during bridge startup.
Plugins can override or extend these with their own implementations.
"""

from .formatters import (
    AIFormatter,
    HumanFormatter,
    JsonFormatter,
    MarkdownFormatter,
    register_builtin_formatters,
)

__all__ = [
    "JsonFormatter",
    "HumanFormatter",
    "AIFormatter",
    "MarkdownFormatter",
    "register_builtin_formatters",
]
