# AI Tool Bridge

A plugin-based daemon that bridges AI agents to external services via a unified HTTP API.

## Features

- **Plugin Architecture** - Extensible design with auto-discovery
- **Idle Shutdown** - Auto-stops when inactive to save resources
- **Unified CLI** - Single `bridge` command for all operations
- **Connector Registry** - Centralized lifecycle management for external services

## Installation

```bash
# From the plugin directory
pip install -e .

# Or with development dependencies
pip install -e ".[dev]"
```

## Quick Start

```bash
# Start the daemon
bridge start

# Check status
bridge status

# List plugins
bridge plugins

# Stop daemon
bridge stop
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `bridge start [-f]` | Start daemon (`-f` for foreground) |
| `bridge stop` | Stop daemon gracefully |
| `bridge restart` | Restart daemon |
| `bridge status` | Show daemon and component status |
| `bridge health` | Quick health check |
| `bridge plugins` | List loaded plugins |
| `bridge connectors` | List connectors and circuit states |
| `bridge reconnect NAME` | Force reconnect a connector |

### Plugin Commands

Plugins register CLI wrappers automatically. Help is available at any level:

```bash
bridge jira --help           # List all jira commands
bridge jira issue --help     # Help for issue command
jira issue --help            # Same (via CLI wrapper)
```

## Architecture

```
toolbus/
├── contracts/        # Protocol definitions (interfaces)
│   ├── connector.py  # ConnectorProtocol (lifecycle only)
│   └── plugin.py     # PluginProtocol
├── connectors/       # External service management
│   └── registry.py   # Connector registry (connect/disconnect all)
├── plugins/          # Plugin system
│   ├── discovery.py  # Auto-discover from ~/.claude/plugins
│   ├── loader.py     # Load plugins from manifest
│   └── registry.py   # Plugin lifecycle management
├── lifecycle/        # Process management
│   ├── pid.py        # PID file handling
│   ├── signals.py    # Signal handling (SIGTERM, SIGINT)
│   └── idle.py       # Idle shutdown monitoring
├── app/              # FastAPI application
│   ├── factory.py    # Application factory
│   ├── routes.py     # Core routes (/health, /status, etc.)
│   └── middleware.py # Activity tracking, logging, errors
└── cli/              # Command-line interface
    ├── main.py       # Entry point, argument parsing
    ├── daemon.py     # Daemon management (start/stop)
    └── client.py     # HTTP client for CLI commands
```

The bridge is intentionally minimal - plugins bring their own HTTP clients, formatters, and transport logic.

## Configuration

Environment variables (prefix: `BRIDGE_`):

| Variable | Default | Description |
|----------|---------|-------------|
| `BRIDGE_HOST` | `::` | Bind address (IPv4/IPv6 dual-stack) |
| `BRIDGE_PORT` | `9100` | Port number |
| `BRIDGE_TIMEOUT` | `1800` | Idle timeout (seconds) |
| `BRIDGE_LOG_LEVEL` | `INFO` | Log level |
| `BRIDGE_RUNTIME_DIR` | `~/.local/share/ai-tool-bridge` | Runtime directory |

## Writing Plugins

Plugins are discovered from `~/.claude/plugins/` directories.

### Plugin Structure

```
my-plugin/
├── manifest.json
├── src/
│   └── my_plugin/
│       ├── __init__.py
│       └── plugin.py
└── pyproject.toml
```

### manifest.json

```json
{
  "name": "my-plugin",
  "version": "1.0.0",
  "entry_point": "my_plugin.plugin:MyPlugin",
  "description": "My awesome plugin",
  "dependencies": ["httpx>=0.25.0"],
  "bridge_api": "1.0.0"
}
```

### Plugin Class

```python
from fastapi import APIRouter

class MyPlugin:
    """Plugin implementing PluginProtocol."""

    name = "my-plugin"
    version = "1.0.0"
    description = "My awesome plugin"

    def __init__(self, context: dict | None = None):
        self.router = APIRouter()
        self._setup_routes()

    def _setup_routes(self):
        @self.router.get("/hello")
        async def hello():
            return {"message": "Hello from my plugin!"}

    async def startup(self):
        """Called when bridge starts."""
        pass

    async def shutdown(self):
        """Called when bridge stops."""
        pass

    async def health_check(self) -> dict:
        """Return health status."""
        return {"name": self.name, "status": "healthy"}
```

### Using Connectors

Plugins register their own connectors implementing `ConnectorProtocol` (lifecycle only):

```python
import httpx

class MyConnector:
    """Connector implementing lifecycle protocol."""

    def __init__(self):
        self._client: httpx.AsyncClient | None = None
        self._healthy = False

    @property
    def name(self) -> str:
        return "my-service"

    @property
    def healthy(self) -> bool:
        return self._healthy

    @property
    def circuit_state(self) -> str:
        return "closed" if self._healthy else "open"

    async def connect(self) -> None:
        self._client = httpx.AsyncClient(base_url="https://api.example.com")
        self._healthy = True

    async def disconnect(self) -> None:
        if self._client:
            await self._client.aclose()
        self._healthy = False

    async def check_health(self) -> bool:
        # Plugin implements its own health check
        return self._healthy

    def status(self) -> dict:
        return {"name": self.name, "healthy": self.healthy}

    # Transport methods (NOT in protocol - plugin's own API)
    async def get(self, path: str) -> dict:
        resp = await self._client.get(path)
        return resp.json()


class MyPlugin:
    def __init__(self, context: dict | None = None):
        self.connector_registry = context.get("connector_registry")
        self.connector = MyConnector()

    async def startup(self):
        self.connector_registry.register(self.connector)

    async def shutdown(self):
        self.connector_registry.unregister("my-service")
```

The bridge only manages connector lifecycle (connect/disconnect all on startup/shutdown). Transport-specific methods (HTTP, MCP, CLI) are implemented by plugins.

### Tools Framework

The `toolbus.tools` module provides a Pydantic-based abstraction for defining plugin tools:

```python
from pydantic import Field
from toolbus.tools import Tool, ToolContext, ToolResult, register_tools

class GetIssue(Tool):
    """Get issue by key."""
    key: str = Field(..., description="Issue key like PROJ-123")
    format: str = Field("ai", description="Output format")

    class Meta:
        method = "GET"
        path = "/issue/{key}"
        tags = ["issues"]

    async def execute(self, ctx: ToolContext) -> Any:
        issue = ctx.client.issue(self.key)
        return ctx.format(issue, self.format, "issue")

# Register in plugin router
router = APIRouter()
register_tools(router, [GetIssue], Depends(client), formatter=formatted)
```

Features:
- Auto-generates FastAPI routes with OpenAPI documentation
- Path parameters extracted from `{placeholder}` syntax
- Automatic fallback routes for missing required parameters
- Subcommand help support (`plugin command --help`)

## API Endpoints

### Core Routes

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Basic health check |
| `/ready` | GET | Readiness with component health |
| `/status` | GET | Detailed status |
| `/plugins` | GET | List all plugins |
| `/plugins/{name}` | GET | Plugin details |
| `/connectors` | GET | List connectors |
| `/connectors/{name}/reconnect` | POST | Force reconnect |

### Plugin Routes

Plugin routes are mounted at `/{plugin-name}/...`

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Type checking
mypy src/

# Linting
ruff check src/
ruff format src/
```

## License

MIT
