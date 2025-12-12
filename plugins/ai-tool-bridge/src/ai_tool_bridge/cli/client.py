"""
CLI Client - HTTP client for communicating with the daemon.

Provides synchronous methods for CLI commands to interact
with the running bridge daemon.
"""

import sys
from typing import Any

import httpx

from ..config import BridgeConfig


class BridgeClient:
    """HTTP client for bridge daemon.

    Provides synchronous methods for CLI commands.

    Example:
        client = BridgeClient()
        if client.is_running():
            status = client.status()
            print(f"Version: {status['version']}")
    """

    def __init__(self, config: BridgeConfig | None = None) -> None:
        self.config = config or BridgeConfig()
        self.base_url = self.config.bridge_url  # Use bridge_url which uses ::1 for localhost
        self._client = httpx.Client(timeout=5.0)

    def is_running(self) -> bool:
        """Check if daemon is running and responding."""
        try:
            response = self._client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except httpx.ConnectError:
            return False

    def health(self) -> dict[str, Any]:
        """Get health status."""
        return self._get("/health")

    def ready(self) -> dict[str, Any]:
        """Get readiness status with component health."""
        return self._get("/ready")

    def status(self) -> dict[str, Any]:
        """Get detailed status information."""
        return self._get("/status")

    def plugins(self) -> list[dict[str, Any]]:
        """List all plugins."""
        return self._get("/plugins")

    def plugin(self, name: str) -> dict[str, Any]:
        """Get details about a specific plugin."""
        return self._get(f"/plugins/{name}")

    def connectors(self) -> dict[str, Any]:
        """List all connectors."""
        return self._get("/connectors")

    def reconnect(self, connector: str) -> dict[str, Any]:
        """Force reconnect a connector."""
        return self._post(f"/connectors/{connector}/reconnect")

    def notifications_status(self) -> dict[str, Any]:
        """Get notifications status."""
        return self._get("/notifications")

    def notifications_action(self, action: str) -> dict[str, Any]:
        """Enable, disable, or test notifications."""
        return self._post(f"/notifications/{action}")

    def _get(self, path: str) -> Any:
        """Make GET request to daemon."""
        response = self._client.get(f"{self.base_url}{path}")
        response.raise_for_status()
        return response.json()

    def _post(self, path: str, json: Any = None) -> Any:
        """Make POST request to daemon."""
        response = self._client.post(f"{self.base_url}{path}", json=json)
        response.raise_for_status()
        return response.json()

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self) -> "BridgeClient":
        return self

    def __exit__(self, *args) -> None:
        self.close()


def print_status(status: dict[str, Any]) -> None:
    """Pretty-print status information."""
    print(f"AI Tool Bridge v{status.get('version', 'unknown')}")
    print()

    plugins = status.get("plugins", [])
    connector_status = status.get("connectors", {})
    connectors = connector_status.get("connectors", {}) if isinstance(connector_status, dict) else {}

    if plugins:
        print("Plugins:")
        for p in plugins:
            name = p["name"]
            started = p.get("started", False)
            state = "[*]" if started else "[ ]"

            # Get connector info for this plugin (assumes same name)
            conn = connectors.get(name, {})
            healthy = conn.get("healthy", False)
            circuit = conn.get("circuit_state", "unknown")

            # Build status line - only show circuit state if not normal (closed)
            if started and healthy:
                conn_status = "healthy"
            elif started and not healthy:
                failure_count = conn.get("failure_count", 0)
                if circuit == "open":
                    conn_status = f"unhealthy [circuit open, {failure_count} failures]"
                elif circuit == "half_open":
                    conn_status = "recovering [circuit half-open]"
                else:
                    conn_status = "unhealthy"
            else:
                conn_status = "not started"

            print(f"  {state} {name} v{p['version']} - {conn_status}")

            # Show CLI if available
            cli = p.get("cli")
            if cli:
                print(f"      CLI: {cli}")
    else:
        print("No plugins loaded")


def print_error(message: str) -> None:
    """Print error message to stderr."""
    print(f"Error: {message}", file=sys.stderr)
