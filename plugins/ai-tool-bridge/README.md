# AI Tool Bridge

A plugin-based daemon that bridges AI agents to external services via a unified HTTP API.

## Features

- **Plugin Architecture** - Extensible design with auto-discovery
- **Circuit Breaker** - Self-healing connections to external services
- **Idle Shutdown** - Auto-stops when inactive to save resources
- **Unified CLI** - Single `bridge` command for all operations
- **Multiple Formatters** - JSON, human-readable, AI-optimized, Markdown

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

## Architecture

```
ai_tool_bridge/
├── contracts/        # Protocol definitions (interfaces)
│   ├── connector.py  # ConnectorProtocol
│   ├── formatter.py  # FormatterProtocol
│   └── plugin.py     # PluginProtocol
├── connectors/       # HTTP client infrastructure
│   ├── circuit.py    # Circuit breaker pattern
│   ├── http.py       # HTTP connector implementation
│   ├── registry.py   # Connector registry
│   └── health.py     # Background health monitoring
├── formatters/       # Response formatting
│   └── registry.py   # Formatter registry
├── builtins/         # Default implementations
│   └── formatters.py # JSON, Human, AI, Markdown formatters
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

Plugins can use the connector registry for external services:

```python
from ai_tool_bridge.connectors import HTTPConnector, ConnectorConfig

class MyPlugin:
    def __init__(self, context: dict | None = None):
        self.connector_registry = context.get("connector_registry")

        # Create connector with circuit breaker
        config = ConnectorConfig(
            base_url="https://api.example.com",
            timeout=30.0,
        )
        self.connector = HTTPConnector("example", config)

    async def startup(self):
        # Register connector
        self.connector_registry.register(self.connector)
        await self.connector.connect()

    async def shutdown(self):
        await self.connector.disconnect()
        self.connector_registry.unregister("example")
```

## Circuit Breaker

Connectors use the circuit breaker pattern for resilience:

```
CLOSED ──[failures >= threshold]──> OPEN
   ↑                                  │
   │                                  │ [timeout]
   │                                  ↓
   └───────[success]─────────── HALF_OPEN
                                      │
                              [failure]│
                                      ↓
                                   OPEN
```

- **CLOSED**: Normal operation, requests pass through
- **OPEN**: Requests fail immediately (circuit tripped)
- **HALF_OPEN**: Testing recovery with limited requests

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
