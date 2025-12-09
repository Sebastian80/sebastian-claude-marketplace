"""
Serena CLI - Unified Python CLI for Serena MCP Server.

A professional, async-first CLI that replaces both serena-fast (bash) and
the legacy Python serena script with a single, maintainable codebase.

Features:
    - httpx-based async HTTP with connection pooling
    - Persistent sessions across invocations
    - SSE streaming support for real-time responses
    - Rich output formatting with colors
    - Type-safe with full type hints

Example:
    >>> from serena_cli import SerenaClient
    >>> async with SerenaClient() as client:
    ...     result = await client.find_symbol("Customer", kind="class")
    ...     print(result)
"""

__version__ = "2.0.0"
__author__ = "Sebastian"

from .client import SerenaClient
from .session import SessionManager

__all__ = ["SerenaClient", "SessionManager", "__version__"]
