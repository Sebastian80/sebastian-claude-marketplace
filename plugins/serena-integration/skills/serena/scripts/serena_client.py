#!/usr/bin/env python3
"""
Serena MCP HTTP Client

Provides session-managed access to Serena's MCP server over HTTP.
No external dependencies - uses only Python stdlib.

Usage:
    from serena_client import SerenaClient

    client = SerenaClient()
    result = client.call("list_memories", {})
    print(result)
"""

import json
import os
import urllib.request
from typing import Any


class SerenaClient:
    """MCP HTTP client for Serena with automatic session management."""

    def __init__(self, url: str = None):
        self.url = url or os.environ.get("SERENA_URL", "http://localhost:9121/mcp")
        self.session_id = None
        self._request_id = 0

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    def _make_request(self, payload: dict, include_session: bool = True) -> dict:
        """Make HTTP request to MCP server."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }
        if include_session and self.session_id:
            headers["mcp-session-id"] = self.session_id

        data = json.dumps(payload).encode()
        req = urllib.request.Request(self.url, data=data, method="POST", headers=headers)

        with urllib.request.urlopen(req, timeout=60) as resp:
            # Capture session ID from response
            if not self.session_id:
                self.session_id = resp.headers.get("mcp-session-id")

            body = resp.read().decode()

            # Parse SSE response
            for line in body.split('\n'):
                if line.startswith('data: '):
                    return json.loads(line[6:])

            # Fallback for non-SSE response
            if body.strip():
                return json.loads(body)
            return {}

    def initialize(self) -> dict:
        """Initialize MCP session."""
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "serena-skill", "version": "1.0.0"}
            }
        }
        result = self._make_request(payload, include_session=False)

        # Send initialized notification
        notif = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }
        self._make_request(notif)

        return result

    def ensure_session(self):
        """Ensure we have an active session."""
        if not self.session_id:
            self.initialize()

    def call(self, tool_name: str, arguments: dict = None) -> Any:
        """Call a Serena tool."""
        self.ensure_session()

        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments or {}
            }
        }

        response = self._make_request(payload)

        if "error" in response:
            raise Exception(f"Serena error: {response['error']}")

        result = response.get("result", {})

        # Extract structured content if available
        if "structuredContent" in result:
            return result["structuredContent"].get("result", result["structuredContent"])

        # Fall back to text content
        content = result.get("content", [])
        if content and isinstance(content, list):
            texts = [c.get("text", "") for c in content if c.get("type") == "text"]
            return "\n".join(texts)

        return result

    def list_tools(self) -> list:
        """List available tools."""
        self.ensure_session()

        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/list",
            "params": {}
        }

        response = self._make_request(payload)
        return response.get("result", {}).get("tools", [])


# Convenience functions for direct script usage
_client = None

def get_client() -> SerenaClient:
    """Get or create singleton client."""
    global _client
    if _client is None:
        _client = SerenaClient()
    return _client


def call(tool_name: str, **kwargs) -> Any:
    """Quick call to Serena tool."""
    return get_client().call(tool_name, kwargs)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: serena_client.py <tool_name> [key=value ...]")
        print("Example: serena_client.py list_memories")
        print("Example: serena_client.py find_symbol name_path_pattern=Customer")
        sys.exit(1)

    tool = sys.argv[1]
    args = {}
    for arg in sys.argv[2:]:
        if "=" in arg:
            k, v = arg.split("=", 1)
            # Handle Python-style booleans
            if v.lower() == 'true':
                args[k] = True
            elif v.lower() == 'false':
                args[k] = False
            else:
                # Try to parse as JSON for complex values
                try:
                    args[k] = json.loads(v)
                except json.JSONDecodeError:
                    args[k] = v

    try:
        result = call(tool, **args)
        if isinstance(result, str):
            print(result)
        else:
            print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
