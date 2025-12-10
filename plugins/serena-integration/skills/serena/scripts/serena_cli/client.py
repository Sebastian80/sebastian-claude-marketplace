"""
Async HTTP client for Serena MCP Server.

Provides a high-performance, connection-pooled client for communicating
with the Serena MCP server. Uses httpx for async HTTP with automatic
connection reuse.

Key Features:
    - Connection pooling for reduced latency on repeated calls
    - Automatic session management with persistence
    - SSE streaming support for real-time responses
    - Comprehensive error handling with typed exceptions
    - Context manager support for proper resource cleanup

Example:
    >>> async with SerenaClient() as client:
    ...     symbols = await client.find_symbol("Customer", kind="class")
    ...     for sym in symbols:
    ...         print(f"{sym['name_path']} in {sym['relative_path']}")
"""

from __future__ import annotations

import json
import os
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, AsyncIterator, Literal, Optional, TypeVar

import httpx

from .session import Session, SessionManager

# Type for symbol kinds
SymbolKind = Literal["class", "method", "interface", "function", "namespace", "property", "constant"]

# LSP symbol kind mapping
SYMBOL_KIND_MAP: dict[str, int] = {
    "namespace": 3,
    "class": 5,
    "method": 6,
    "property": 7,
    "interface": 11,
    "function": 12,
    "constant": 14,
}

# Default configuration
DEFAULT_URL = "http://localhost:9121/mcp"
DEFAULT_TIMEOUT = 120.0
MCP_PROTOCOL_VERSION = "2024-11-05"


class SerenaError(Exception):
    """Base exception for Serena client errors."""

    pass


class ConnectionError(SerenaError):
    """Failed to connect to Serena server."""

    pass


class SessionError(SerenaError):
    """Session initialization or validation failed."""

    pass


class ToolError(SerenaError):
    """Tool execution failed."""

    def __init__(self, message: str, tool: str, details: Optional[dict] = None):
        super().__init__(message)
        self.tool = tool
        self.details = details or {}


@dataclass
class ToolResult:
    """Result from a tool call with metadata."""

    data: Any
    tool: str
    elapsed_ms: float
    request_id: int


class SerenaClient:
    """
    Async HTTP client for Serena MCP Server.

    Uses httpx with connection pooling for efficient repeated calls.
    Sessions are persisted across invocations to avoid re-initialization.

    Attributes:
        url: The MCP server URL.
        timeout: Request timeout in seconds.

    Example:
        >>> async with SerenaClient() as client:
        ...     # Find all Customer classes
        ...     result = await client.find_symbol("Customer", kind="class")
        ...
        ...     # Get file overview
        ...     overview = await client.get_overview("src/Entity/Customer.php")
        ...
        ...     # Find references
        ...     refs = await client.find_refs("Customer/getName", "src/Entity/Customer.php")
    """

    def __init__(
        self,
        url: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
        session_manager: Optional[SessionManager] = None,
    ):
        """
        Initialize Serena client.

        Args:
            url: MCP server URL. Defaults to SERENA_URL env var or localhost:9121.
            timeout: Request timeout in seconds.
            session_manager: Custom session manager. Uses default if None.
        """
        self.url = url or os.environ.get("SERENA_URL", DEFAULT_URL)
        self.timeout = timeout
        self._session_manager = session_manager or SessionManager()
        self._session: Optional[Session] = None
        self._client: Optional[httpx.AsyncClient] = None
        self._request_id = 0

    async def __aenter__(self) -> SerenaClient:
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()

    async def connect(self) -> None:
        """
        Establish connection and initialize session.

        Attempts to reuse existing session if valid, otherwise
        performs MCP initialization handshake.

        Raises:
            ConnectionError: If server is unreachable.
            SessionError: If session initialization fails.
        """
        # Create HTTP client with connection pooling
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            limits=httpx.Limits(
                max_keepalive_connections=5,
                max_connections=10,
                keepalive_expiry=30.0,
            ),
        )

        # Try to reuse existing session
        existing = self._session_manager.get_session(self.url)
        if existing:
            self._session = existing
            return

        # Initialize new session
        await self._initialize_session()

    async def close(self) -> None:
        """Close HTTP client and save session."""
        if self._session:
            self._session_manager.save_session(self._session)
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _initialize_session(self) -> None:
        """Perform MCP initialization handshake."""
        if not self._client:
            raise SessionError("Client not connected")

        # Send initialize request
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "initialize",
            "params": {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "serena-cli", "version": "2.0.0"},
            },
        }

        try:
            response = await self._client.post(
                self.url,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream",
                },
            )
            response.raise_for_status()
        except httpx.ConnectError as e:
            raise ConnectionError(f"Cannot connect to Serena at {self.url}: {e}") from e
        except httpx.HTTPStatusError as e:
            raise ConnectionError(f"HTTP error from Serena: {e}") from e

        # Extract session ID from response header
        session_id = response.headers.get("mcp-session-id")
        if not session_id:
            raise SessionError("Server did not return session ID")

        # Create and store session
        now = time.time()
        self._session = Session(
            session_id=session_id,
            server_url=self.url,
            created_at=now,
            last_used=now,
        )

        # Send initialized notification
        await self._client.post(
            self.url,
            json={"jsonrpc": "2.0", "method": "notifications/initialized"},
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "mcp-session-id": session_id,
            },
        )

        # Persist session
        self._session_manager.save_session(self._session)

    def _next_id(self) -> int:
        """Generate next request ID."""
        self._request_id += 1
        return self._request_id

    async def _call_tool(self, tool: str, arguments: dict[str, Any]) -> ToolResult:
        """
        Call an MCP tool and return the result.

        Args:
            tool: Tool name to call.
            arguments: Tool arguments.

        Returns:
            ToolResult with parsed response data.

        Raises:
            SessionError: If not connected.
            ToolError: If tool execution fails.
        """
        if not self._client or not self._session:
            raise SessionError("Not connected. Call connect() first.")

        request_id = self._next_id()
        payload = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "tools/call",
            "params": {"name": tool, "arguments": arguments},
        }

        start_time = time.time()

        try:
            response = await self._client.post(
                self.url,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream",
                    "mcp-session-id": self._session.session_id,
                },
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise ToolError(f"HTTP error: {e}", tool)

        elapsed_ms = (time.time() - start_time) * 1000

        # Parse SSE response
        data = self._parse_sse_response(response.text, request_id)

        # Check for error
        if "error" in data:
            error = data["error"]
            raise ToolError(
                error.get("message", "Unknown error"),
                tool,
                {"code": error.get("code"), "data": error.get("data")},
            )

        # Extract result
        result = data.get("result", {})
        parsed = self._extract_result(result)

        # Update session last_used
        self._session.touch()

        return ToolResult(data=parsed, tool=tool, elapsed_ms=elapsed_ms, request_id=request_id)

    def _parse_sse_response(self, text: str, expected_id: int) -> dict:
        """Parse SSE response and extract matching JSON."""
        for line in text.split("\n"):
            if line.startswith("data: "):
                try:
                    data = json.loads(line[6:])
                    if data.get("id") == expected_id:
                        return data
                except json.JSONDecodeError:
                    continue

        # Fallback: try to parse entire response as JSON
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {}

    def _extract_result(self, result: dict) -> Any:
        """Extract actual result from MCP response wrapper."""
        # Handle structuredContent (may be double-encoded)
        if "structuredContent" in result:
            content = result["structuredContent"]
            if "result" in content:
                value = content["result"]
                if isinstance(value, str):
                    # Check for truncation error
                    if value.startswith("The answer is too long"):
                        raise ToolError(
                            "Too many results - use --path to restrict search",
                            "find_symbol",
                            {"hint": "Try: --path src/"}
                        )
                    try:
                        return json.loads(value)
                    except json.JSONDecodeError:
                        return value
                return value
            return content

        # Handle text content array
        if "content" in result:
            texts = [c.get("text", "") for c in result["content"] if c.get("type") == "text"]
            text = "\n".join(texts)
            # Check for truncation error in text content
            if text.startswith("The answer is too long"):
                raise ToolError(
                    "Too many results - use --path to restrict search",
                    "find_symbol",
                    {"hint": "Try: --path src/"}
                )
            return text

        return result

    # =========================================================================
    # High-Level API Methods
    # =========================================================================

    async def find_symbol(
        self,
        pattern: str,
        *,
        kind: Optional[SymbolKind] = None,
        path: Optional[str] = None,
        body: bool = False,
        depth: int = 0,
        exact: bool = False,
    ) -> list[dict]:
        """
        Find symbols by name pattern.

        Args:
            pattern: Symbol name or pattern (supports wildcards like "get*").
            kind: Filter by symbol kind (class, method, interface, etc.).
            path: Restrict search to path (e.g., "src/Meyer/").
            body: Include symbol body/implementation in results.
            depth: Traversal depth (0=symbol only, 1=include children).
            exact: Require exact match instead of substring.

        Returns:
            List of symbol dictionaries with name_path, relative_path, kind, etc.

        Example:
            >>> symbols = await client.find_symbol("Customer", kind="class")
            >>> symbols = await client.find_symbol("get*", kind="method", path="src/")
        """
        args: dict[str, Any] = {
            "name_path_pattern": pattern,
            "substring_matching": not exact,
            "include_body": body,
            "depth": depth,
        }
        if kind:
            args["include_kinds"] = [SYMBOL_KIND_MAP[kind]]
        if path:
            args["relative_path"] = path

        result = await self._call_tool("find_symbol", args)
        return result.data if isinstance(result.data, list) else []

    async def find_refs(
        self,
        symbol: str,
        file: str,
        *,
        all_refs: bool = False,
    ) -> list[dict]:
        """
        Find all references to a symbol.

        Args:
            symbol: Symbol path (e.g., "Customer/getName").
            file: File where symbol is defined.
            all_refs: Return all references (default: top 10 files).

        Returns:
            List of reference dictionaries.

        Example:
            >>> refs = await client.find_refs("Customer/getName", "src/Entity/Customer.php")
        """
        result = await self._call_tool(
            "find_referencing_symbols",
            {"name_path": symbol, "relative_path": file},
        )
        data = result.data if isinstance(result.data, list) else []
        return data if all_refs else data[:10]

    async def get_overview(self, file: str) -> list[dict]:
        """
        Get overview of symbols in a file.

        Args:
            file: Relative path to file.

        Returns:
            List of symbol dictionaries.

        Example:
            >>> overview = await client.get_overview("src/Entity/Customer.php")
        """
        result = await self._call_tool("get_symbols_overview", {"relative_path": file})
        return result.data if isinstance(result.data, list) else []

    async def search(
        self,
        pattern: str,
        *,
        glob: Optional[str] = None,
        path: Optional[str] = None,
    ) -> dict[str, list[str]]:
        """
        Search for regex pattern in code.

        Args:
            pattern: Regex pattern to search for.
            glob: File glob filter (e.g., "*.php").
            path: Restrict to path.

        Returns:
            Dictionary mapping file paths to list of matching lines.

        Example:
            >>> matches = await client.search(r"implements.*Interface", glob="*.php")
        """
        args: dict[str, Any] = {"substring_pattern": pattern}
        if glob:
            args["file_pattern"] = glob
        if path:
            args["relative_path"] = path

        result = await self._call_tool("search_for_pattern", args)
        return result.data if isinstance(result.data, dict) else {}

    async def get_status(self) -> str:
        """
        Get current Serena configuration and status.

        Returns:
            Configuration text with project, languages, active tools, etc.
        """
        result = await self._call_tool("get_current_config", {})
        return str(result.data) if result.data else ""

    async def get_tools(self) -> list[dict]:
        """
        Get list of available Serena MCP tools.

        Returns:
            List of tool dictionaries with name and description.

        Example:
            >>> tools = await client.get_tools()
            >>> for t in tools:
            ...     print(f"{t['name']}: {t['description'][:50]}")
        """
        if not self._client or not self._session:
            raise SessionError("Not connected. Call connect() first.")

        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/list",
            "params": {},
        }

        response = await self._client.post(
            self.url,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "mcp-session-id": self._session.session_id,
            },
        )
        response.raise_for_status()

        # Parse SSE response
        data = self._parse_sse_response(response.text, payload["id"])
        tools = data.get("result", {}).get("tools", [])

        # Return simplified tool info
        return [
            {"name": t.get("name", ""), "description": t.get("description", "")}
            for t in tools
        ]

    async def activate_project(self, project: Optional[str] = None) -> str:
        """
        Activate a project.

        Args:
            project: Project path or name. Defaults to current directory.

        Returns:
            Activation status message.
        """
        project = project or os.getcwd()
        result = await self._call_tool("activate_project", {"project": project})
        return str(result.data)

    # =========================================================================
    # Memory Operations
    # =========================================================================

    async def memory_list(self, folder: Optional[str] = None) -> list[str]:
        """List memories, optionally filtered by folder."""
        args = {"folder": folder} if folder else {}
        result = await self._call_tool("list_memories", args)
        return result.data if isinstance(result.data, list) else []

    async def memory_read(self, name: str) -> str:
        """Read a memory by name."""
        result = await self._call_tool("read_memory", {"memory_file_name": name})
        return str(result.data)

    async def memory_write(self, name: str, content: str) -> str:
        """Write a memory."""
        result = await self._call_tool(
            "write_memory",
            {"memory_file_name": name, "content": content},
        )
        return str(result.data)

    async def memory_delete(self, name: str) -> str:
        """Delete a memory."""
        result = await self._call_tool("delete_memory", {"memory_file_name": name})
        return str(result.data)

    async def memory_tree(self, folder: Optional[str] = None) -> str:
        """Get memory folder tree."""
        args = {"folder": folder} if folder else {}
        result = await self._call_tool("tree_memories", args)
        return str(result.data)

    async def memory_search(self, pattern: str, folder: Optional[str] = None) -> list[dict]:
        """Search memory contents."""
        args: dict[str, Any] = {"pattern": pattern}
        if folder:
            args["folder"] = folder
        result = await self._call_tool("search_memories", args)
        return result.data if isinstance(result.data, list) else []

    async def memory_archive(self, name: str, category: Optional[str] = None) -> str:
        """Archive a memory."""
        args: dict[str, Any] = {"memory_file_name": name}
        if category:
            args["category"] = category
        result = await self._call_tool("archive_memory", args)
        return str(result.data)

    async def memory_move(self, name: str, new_name: str) -> str:
        """Move/rename a memory."""
        result = await self._call_tool(
            "move_memory",
            {"source": name, "dest": new_name},
        )
        return str(result.data)

    async def memory_stats(self) -> dict[str, Any]:
        """Get memory statistics."""
        result = await self._call_tool("memory_stats", {})
        return result.data if isinstance(result.data, dict) else {"raw": str(result.data)}

    # =========================================================================
    # Edit Operations
    # =========================================================================

    async def edit_replace(self, symbol: str, file: str, body: str) -> str:
        """Replace a symbol's body."""
        result = await self._call_tool(
            "replace_symbol_body",
            {"name_path": symbol, "relative_path": file, "body": body},
        )
        return str(result.data)

    async def edit_after(self, symbol: str, file: str, code: str) -> str:
        """Insert code after a symbol."""
        result = await self._call_tool(
            "insert_after_symbol",
            {"name_path": symbol, "relative_path": file, "body": code},
        )
        return str(result.data)

    async def edit_before(self, symbol: str, file: str, code: str) -> str:
        """Insert code before a symbol."""
        result = await self._call_tool(
            "insert_before_symbol",
            {"name_path": symbol, "relative_path": file, "body": code},
        )
        return str(result.data)

    async def edit_rename(self, symbol: str, file: str, new_name: str) -> str:
        """Rename a symbol."""
        result = await self._call_tool(
            "rename_symbol",
            {"name_path": symbol, "relative_path": file, "new_name": new_name},
        )
        return str(result.data)

    # =========================================================================
    # Onboarding Operations
    # =========================================================================

    async def check_onboarding(self) -> str:
        """
        Check whether project onboarding was already performed.

        Returns:
            Status message indicating if onboarding is needed or listing available memories.
        """
        result = await self._call_tool("check_onboarding_performed", {})
        return str(result.data)

    async def onboarding(self) -> str:
        """
        Get onboarding instructions for a new project.

        Should only be called if check_onboarding indicates onboarding is needed.

        Returns:
            Instructions on how to create the onboarding information.
        """
        result = await self._call_tool("onboarding", {})
        return str(result.data)

    async def init_memories(self, include_templates: bool = True) -> str:
        """
        Initialize the recommended memory folder structure.

        Creates:
        - active/tasks, active/sessions (current work)
        - reference/architecture, patterns, integrations, workflows (documentation)
        - learnings/mistakes, discoveries, commands (knowledge base)
        - archive (historical records)
        - .templates (reusable templates)

        Args:
            include_templates: Whether to create template files (default: True)

        Returns:
            Status message about created structure.
        """
        result = await self._call_tool(
            "init_memories",
            {"include_templates": include_templates},
        )
        return str(result.data)
