#!/usr/bin/env python3
"""JetBrains MCP Client - async SSE transport for PhpStorm/IntelliJ tools"""
import urllib.request
import json
import threading
import queue
import time
import sys
import subprocess
import shutil


def _try_dismiss_dialog():
    """Try to dismiss modal dialogs in PhpStorm/IntelliJ using xdotool.

    Modal dialogs block the JetBrains MCP server. This function sends Escape
    key to dismiss them. Returns True if xdotool is available and command ran.
    """
    xdotool = shutil.which("xdotool")
    if not xdotool:
        return False

    try:
        # Find PhpStorm/IntelliJ windows and send Escape key
        subprocess.run(
            [xdotool, "search", "--name", "PhpStorm", "key", "Escape"],
            capture_output=True,
            timeout=2
        )
        # Also try IntelliJ IDEA
        subprocess.run(
            [xdotool, "search", "--name", "IntelliJ IDEA", "key", "Escape"],
            capture_output=True,
            timeout=2
        )
        # Give IDE time to process
        time.sleep(0.5)
        return True
    except (subprocess.TimeoutExpired, subprocess.SubprocessError):
        return False


class JetBrainsMCP:
    """Client for JetBrains IDE MCP server via HTTP/SSE"""

    def __init__(self, base_url="http://127.0.0.1:64342"):
        self.base_url = base_url
        self.session_id = None
        self.endpoint = None
        self.request_id = 0
        self.responses = queue.Queue()
        self.ready = threading.Event()
        self.running = False
        self._sse_thread = None

    def connect(self, timeout=5):
        """Start SSE connection in background, wait for session"""
        self.running = True
        self._sse_thread = threading.Thread(target=self._sse_loop, daemon=True)
        self._sse_thread.start()

        if not self.ready.wait(timeout=timeout):
            self.running = False
            raise ConnectionError("Failed to connect to JetBrains IDE. Is PhpStorm running?")

        return True

    def _sse_loop(self):
        """Single SSE connection - gets session and receives all responses"""
        req = urllib.request.Request(
            f"{self.base_url}/sse",
            headers={"Accept": "text/event-stream"}
        )

        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                for line in resp:
                    if not self.running:
                        break

                    text = line.decode().strip()

                    # Get session ID from first data line
                    if text.startswith("data:") and "sessionId=" in text and not self.session_id:
                        self.endpoint = text.split("data:")[1].strip()
                        self.session_id = text.split("sessionId=")[1]
                        self.ready.set()
                        continue

                    # Parse JSON-RPC responses
                    if text.startswith("data:"):
                        data = text[5:].strip()
                        if data.startswith("{"):
                            try:
                                msg = json.loads(data)
                                self.responses.put(msg)
                            except json.JSONDecodeError:
                                pass
        except urllib.error.URLError as e:
            if self.running:
                self.ready.set()  # Unblock waiter
        except Exception as e:
            if self.running:
                pass  # Silent fail for daemon thread

    def call(self, method, params=None, timeout=30):
        """Call MCP method and wait for response"""
        if not self.session_id:
            raise RuntimeError("Not connected")

        self.request_id += 1
        req_id = self.request_id

        payload = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params or {}
        }

        url = f"{self.base_url}{self.endpoint}"
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode(),
            headers={
                "Content-Type": "application/json",
                "Accept": "text/event-stream"
            }
        )

        # Send request
        with urllib.request.urlopen(req, timeout=10) as resp:
            status = resp.status
            body = resp.read().decode()

        if status not in (200, 202):
            raise RuntimeError(f"HTTP {status}: {body}")

        # Wait for response with matching ID
        pending = []
        start = time.time()
        while time.time() - start < timeout:
            try:
                msg = self.responses.get(timeout=0.5)
                if msg.get("id") == req_id:
                    for m in pending:
                        self.responses.put(m)
                    return msg
                pending.append(msg)
            except queue.Empty:
                pass

        raise TimeoutError(f"No response for request {req_id} within {timeout}s")

    def call_tool(self, name, arguments=None, timeout=30, retry_with_dismiss=True):
        """Call a tool by name and return the result.

        If retry_with_dismiss is True and a timeout occurs, attempts to dismiss
        any modal dialogs in PhpStorm using xdotool and retries once.
        """
        try:
            result = self.call("tools/call", {
                "name": name,
                "arguments": arguments or {}
            }, timeout=timeout)
        except TimeoutError:
            if retry_with_dismiss and _try_dismiss_dialog():
                # Retry once after dismissing dialog
                result = self.call("tools/call", {
                    "name": name,
                    "arguments": arguments or {}
                }, timeout=timeout)
            else:
                raise

        if "error" in result:
            raise RuntimeError(f"Tool error: {result['error']}")

        return result.get("result", {})

    def list_tools(self):
        """List available tools"""
        result = self.call("tools/list")
        return result.get("result", {}).get("tools", [])

    def close(self):
        """Close the connection"""
        self.running = False


# Singleton for CLI use
_client = None


def get_client():
    """Get or create singleton MCP client"""
    global _client
    if _client is None or not _client.running:
        _client = JetBrainsMCP()
        _client.connect()
        # Initialize
        _client.call("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "jetbrains-cli", "version": "1.0"}
        })
    return _client


def format_tool_result(result):
    """Format tool result for CLI output"""
    # Check for structuredContent first (preferred)
    if "structuredContent" in result:
        return json.dumps(result["structuredContent"], indent=2, ensure_ascii=False)

    # Fall back to content array
    content = result.get("content", [])
    if content and isinstance(content, list):
        texts = [c.get("text", "") for c in content if c.get("type") == "text"]
        if texts:
            # Try to parse and pretty-print JSON
            try:
                data = json.loads(texts[0])
                return json.dumps(data, indent=2, ensure_ascii=False)
            except json.JSONDecodeError:
                return "\n".join(texts)

    return json.dumps(result, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    # Test connection
    client = get_client()
    print("Connected to JetBrains IDE")
    tools = client.list_tools()
    print(f"Available tools: {len(tools)}")
    for t in tools:
        print(f"  - {t['name']}")
