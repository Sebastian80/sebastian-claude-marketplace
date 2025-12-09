"""
HTTP daemon server for Serena CLI.

Keeps Python interpreter and httpx connections warm for fast responses.
Uses stdlib http.server with asyncio for the Serena client.
"""

from __future__ import annotations

import asyncio
import json
import os
import signal
import sys
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Optional
from urllib.parse import parse_qs, urlparse

# Add parent to path for serena_cli imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from serena_cli.client import SerenaClient, SerenaError, ToolError
from serena_daemon import DEFAULT_HOST, DEFAULT_PORT, IDLE_TIMEOUT, PID_FILE


class JsonResponse:
    """Helper for JSON responses."""

    @staticmethod
    def success(data: Any) -> tuple[int, dict]:
        return 200, {"success": True, "data": data}

    @staticmethod
    def error(message: str, code: int = 400, hint: str = None) -> tuple[int, dict]:
        resp = {"success": False, "error": message}
        if hint:
            resp["hint"] = hint
        return code, resp


class SerenaDaemonHandler(BaseHTTPRequestHandler):
    """HTTP request handler for Serena daemon."""

    # Class-level client and event loop (shared across requests)
    _client: Optional[SerenaClient] = None
    _loop: Optional[asyncio.AbstractEventLoop] = None
    _last_request_time: float = 0
    _lock = threading.Lock()

    def log_message(self, format: str, *args) -> None:
        """Suppress default logging."""
        pass

    @classmethod
    def get_client(cls) -> SerenaClient:
        """Get or create shared SerenaClient."""
        with cls._lock:
            if cls._client is None:
                cls._client = SerenaClient()
                cls._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(cls._loop)
                cls._loop.run_until_complete(cls._client.connect())
            cls._last_request_time = time.time()
            return cls._client

    @classmethod
    def get_loop(cls) -> asyncio.AbstractEventLoop:
        """Get the event loop."""
        cls.get_client()  # Ensure initialized
        return cls._loop

    @classmethod
    def check_idle_timeout(cls) -> bool:
        """Check if daemon should shut down due to idle timeout."""
        if cls._last_request_time == 0:
            return False
        return (time.time() - cls._last_request_time) > IDLE_TIMEOUT

    def _send_json(self, status: int, data: dict) -> None:
        """Send JSON response."""
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def _run_async(self, coro) -> Any:
        """Run async function in the daemon's event loop."""
        loop = self.get_loop()
        return loop.run_until_complete(coro)

    def _parse_params(self) -> dict:
        """Parse query parameters and POST body."""
        params = {}

        # Parse query string
        parsed = urlparse(self.path)
        query_params = parse_qs(parsed.query)
        for key, values in query_params.items():
            params[key] = values[0] if len(values) == 1 else values

        # Parse POST body if present
        if self.command == "POST":
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length > 0:
                body = self.rfile.read(content_length).decode()
                try:
                    body_params = json.loads(body)
                    if isinstance(body_params, dict):
                        params.update(body_params)
                except json.JSONDecodeError:
                    pass

        return params

    def _convert_param(self, value: str, param_type: str) -> Any:
        """Convert string parameter to appropriate type."""
        if param_type == "bool":
            return value.lower() in ("true", "1", "yes")
        elif param_type == "int":
            return int(value)
        elif param_type == "list":
            return value.split(",") if isinstance(value, str) else value
        return value

    def do_GET(self) -> None:
        """Handle GET requests."""
        self._handle_request()

    def do_POST(self) -> None:
        """Handle POST requests."""
        self._handle_request()

    def _handle_request(self) -> None:
        """Route and handle request."""
        parsed = urlparse(self.path)
        path = parsed.path.strip("/")
        params = self._parse_params()

        try:
            client = self.get_client()

            # Route to handler
            if path == "" or path == "health":
                status, data = self._handle_health()
            elif path == "find":
                status, data = self._handle_find(client, params)
            elif path == "refs":
                status, data = self._handle_refs(client, params)
            elif path == "overview":
                status, data = self._handle_overview(client, params)
            elif path == "search":
                status, data = self._handle_search(client, params)
            elif path == "status":
                status, data = self._handle_status(client)
            elif path == "activate":
                status, data = self._handle_activate(client, params)
            elif path.startswith("memory/"):
                status, data = self._handle_memory(client, path, params)
            elif path.startswith("edit/"):
                status, data = self._handle_edit(client, path, params)
            elif path == "recipe":
                status, data = self._handle_recipe(client, params)
            elif path == "shutdown":
                status, data = self._handle_shutdown()
            else:
                status, data = JsonResponse.error(f"Unknown endpoint: {path}", 404)

            self._send_json(status, data)

        except ToolError as e:
            self._send_json(*JsonResponse.error(str(e), 400, e.details.get("hint")))
        except SerenaError as e:
            self._send_json(*JsonResponse.error(str(e), 500))
        except Exception as e:
            self._send_json(*JsonResponse.error(f"Internal error: {e}", 500))

    def _handle_health(self) -> tuple[int, dict]:
        """Health check endpoint."""
        return JsonResponse.success({
            "status": "running",
            "version": "1.0.0",
            "uptime": time.time() - self._last_request_time if self._last_request_time else 0,
        })

    def _handle_find(self, client: SerenaClient, params: dict) -> tuple[int, dict]:
        """Handle find symbol request."""
        pattern = params.get("pattern")
        if not pattern:
            return JsonResponse.error("Missing required parameter: pattern")

        result = self._run_async(client.find_symbol(
            pattern,
            kind=params.get("kind"),
            path=params.get("path"),
            body=self._convert_param(params.get("body", "false"), "bool"),
            depth=self._convert_param(params.get("depth", "0"), "int"),
            exact=self._convert_param(params.get("exact", "false"), "bool"),
        ))
        return JsonResponse.success(result)

    def _handle_refs(self, client: SerenaClient, params: dict) -> tuple[int, dict]:
        """Handle find references request."""
        symbol = params.get("symbol")
        file = params.get("file")
        if not symbol or not file:
            return JsonResponse.error("Missing required parameters: symbol, file")

        result = self._run_async(client.find_refs(
            symbol, file,
            all_refs=self._convert_param(params.get("all", "false"), "bool"),
        ))
        return JsonResponse.success(result)

    def _handle_overview(self, client: SerenaClient, params: dict) -> tuple[int, dict]:
        """Handle file overview request."""
        file = params.get("file")
        if not file:
            return JsonResponse.error("Missing required parameter: file")

        result = self._run_async(client.get_overview(file))
        return JsonResponse.success(result)

    def _handle_search(self, client: SerenaClient, params: dict) -> tuple[int, dict]:
        """Handle code search request."""
        pattern = params.get("pattern")
        if not pattern:
            return JsonResponse.error("Missing required parameter: pattern")

        result = self._run_async(client.search(
            pattern,
            glob=params.get("glob"),
            path=params.get("path"),
        ))
        return JsonResponse.success(result)

    def _handle_status(self, client: SerenaClient) -> tuple[int, dict]:
        """Handle status request."""
        result = self._run_async(client.get_status())
        return JsonResponse.success(result)

    def _handle_activate(self, client: SerenaClient, params: dict) -> tuple[int, dict]:
        """Handle project activation."""
        project = params.get("project")
        result = self._run_async(client.activate_project(project))
        return JsonResponse.success(result)

    def _handle_memory(self, client: SerenaClient, path: str, params: dict) -> tuple[int, dict]:
        """Handle memory operations."""
        action = path.split("/")[1] if "/" in path else ""

        if action == "list":
            result = self._run_async(client.memory_list(params.get("folder")))
        elif action == "read":
            name = params.get("name")
            if not name:
                return JsonResponse.error("Missing required parameter: name")
            result = self._run_async(client.memory_read(name))
        elif action == "write":
            name = params.get("name")
            content = params.get("content")
            if not name or not content:
                return JsonResponse.error("Missing required parameters: name, content")
            result = self._run_async(client.memory_write(name, content))
        elif action == "delete":
            name = params.get("name")
            if not name:
                return JsonResponse.error("Missing required parameter: name")
            result = self._run_async(client.memory_delete(name))
        elif action == "tree":
            result = self._run_async(client.memory_tree(params.get("folder")))
        elif action == "search":
            pattern = params.get("pattern")
            if not pattern:
                return JsonResponse.error("Missing required parameter: pattern")
            result = self._run_async(client.memory_search(pattern, params.get("folder")))
        elif action == "archive":
            name = params.get("name")
            if not name:
                return JsonResponse.error("Missing required parameter: name")
            result = self._run_async(client.memory_archive(name, params.get("category")))
        else:
            return JsonResponse.error(f"Unknown memory action: {action}", 404)

        return JsonResponse.success(result)

    def _handle_edit(self, client: SerenaClient, path: str, params: dict) -> tuple[int, dict]:
        """Handle edit operations."""
        action = path.split("/")[1] if "/" in path else ""

        symbol = params.get("symbol")
        file = params.get("file")

        if not symbol or not file:
            return JsonResponse.error("Missing required parameters: symbol, file")

        if action == "replace":
            body = params.get("body")
            if not body:
                return JsonResponse.error("Missing required parameter: body")
            result = self._run_async(client.edit_replace(symbol, file, body))
        elif action == "after":
            code = params.get("code")
            if not code:
                return JsonResponse.error("Missing required parameter: code")
            result = self._run_async(client.edit_after(symbol, file, code))
        elif action == "before":
            code = params.get("code")
            if not code:
                return JsonResponse.error("Missing required parameter: code")
            result = self._run_async(client.edit_before(symbol, file, code))
        elif action == "rename":
            new_name = params.get("new_name")
            if not new_name:
                return JsonResponse.error("Missing required parameter: new_name")
            result = self._run_async(client.edit_rename(symbol, file, new_name))
        else:
            return JsonResponse.error(f"Unknown edit action: {action}", 404)

        return JsonResponse.success(result)

    def _handle_recipe(self, client: SerenaClient, params: dict) -> tuple[int, dict]:
        """Handle recipe execution."""
        name = params.get("name", "list")

        recipes = {
            "entities": lambda: client.search(r"#\[ORM\\Entity", glob="src/**/*.php"),
            "controllers": lambda: client.find_symbol("Controller", kind="class"),
            "services": lambda: client.find_symbol("Service", kind="class"),
            "interfaces": lambda: client.find_symbol("Interface", kind="interface"),
            "tests": lambda: client.find_symbol("Test", kind="class"),
        }

        if name == "list":
            return JsonResponse.success({"recipes": list(recipes.keys())})

        if name not in recipes:
            return JsonResponse.error(f"Unknown recipe: {name}", hint=f"Available: {', '.join(recipes.keys())}")

        result = self._run_async(recipes[name]())
        return JsonResponse.success(result)

    def _handle_shutdown(self) -> tuple[int, dict]:
        """Handle shutdown request."""
        def shutdown():
            time.sleep(0.1)
            os.kill(os.getpid(), signal.SIGTERM)

        threading.Thread(target=shutdown).start()
        return JsonResponse.success({"message": "Shutting down..."})


class SerenaDaemon:
    """Daemon server with lifecycle management."""

    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
        self.host = host
        self.port = port
        self.server: Optional[HTTPServer] = None
        self._shutdown_event = threading.Event()

    def start(self, daemonize: bool = True) -> None:
        """Start the daemon server."""
        # Write PID file
        with open(PID_FILE, "w") as f:
            f.write(str(os.getpid()))

        # Set up signal handlers
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)

        # Create and start server
        self.server = HTTPServer((self.host, self.port), SerenaDaemonHandler)
        self.server.timeout = 60  # Check idle timeout every 60s

        print(f"Serena daemon listening on http://{self.host}:{self.port}")

        try:
            while not self._shutdown_event.is_set():
                self.server.handle_request()

                # Check idle timeout
                if SerenaDaemonHandler.check_idle_timeout():
                    print("Idle timeout reached, shutting down...")
                    break
        finally:
            self._cleanup()

    def _handle_signal(self, signum, frame) -> None:
        """Handle shutdown signals."""
        print(f"Received signal {signum}, shutting down...")
        self._shutdown_event.set()

    def _cleanup(self) -> None:
        """Clean up resources."""
        if self.server:
            self.server.server_close()

        # Close SerenaClient
        if SerenaDaemonHandler._client:
            loop = SerenaDaemonHandler._loop
            if loop:
                loop.run_until_complete(SerenaDaemonHandler._client.close())

        # Remove PID file
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)

        print("Daemon stopped.")


def main():
    """Entry point for daemon."""
    import argparse

    parser = argparse.ArgumentParser(description="Serena daemon server")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Host to bind to")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Port to bind to")
    parser.add_argument("--foreground", "-f", action="store_true", help="Run in foreground")

    args = parser.parse_args()

    daemon = SerenaDaemon(host=args.host, port=args.port)
    daemon.start(daemonize=not args.foreground)


if __name__ == "__main__":
    main()
