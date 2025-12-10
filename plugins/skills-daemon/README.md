# Skills Daemon

Central FastAPI-based daemon for Claude Code skills. Provides a unified HTTP interface with plugin architecture for skill backends.

## Features

- **Concurrent Request Handling** - FastAPI async architecture handles multiple agents calling simultaneously
- **Plugin Architecture** - Auto-discovery of plugins without hardcoded paths
- **Unified CLI** - Single thin client for all skills with fast startup (~10ms)
- **Auto-generated API Docs** - Swagger UI at `/docs`, OpenAPI spec at `/openapi.json`
- **Lifecycle Management** - Auto-start on first use, auto-stop after 30min idle
- **Structured Logging** - JSON logs to `~/.local/share/skills-daemon/logs/daemon.log`
- **Output Formatting** - Pluggable formatters (human, json, ai, markdown)

## Architecture

```
CLI Entry Points
┌─────────────────────────────────────────────────────────────────────┐
│ ~/.local/bin/<plugin>  → skills-client <plugin> ...                 │
└─────────────────────────────────────────────────────────────────────┘
                         ↓ HTTP :9100
┌─────────────────────────────────────────────────────────────────────┐
│ Skills Daemon (FastAPI + uvicorn)                                   │
│                                                                     │
│   Core Endpoints:                                                   │
│   ├── GET  /health          Health check + plugin status            │
│   ├── GET  /plugins         List plugins and their endpoints        │
│   ├── GET  /docs            Swagger UI (auto-generated)             │
│   └── POST /shutdown        Graceful shutdown                       │
│                                                                     │
│   Plugin Routes (auto-mounted):                                     │
│   └── /<plugin>/*           Plugin-specific endpoints               │
└─────────────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────────┐
│ Backend Services (plugin-specific)                                  │
└─────────────────────────────────────────────────────────────────────┘
```

## Quick Start

```bash
# Check daemon health
skills-client health

# List available plugins
skills-client plugins

# Use a plugin
skills-client <plugin> <command> [--param value]

# View API documentation
curl http://127.0.0.1:9100/docs
```

## Installation

The daemon uses `uv` for fast venv setup:

```bash
cd ~/.claude/plugins/marketplaces/sebastian-marketplace/plugins/skills-daemon

# Automatic setup (via skills-daemon wrapper)
skills-daemon start

# Manual setup
uv venv
uv pip install -e .
```

## Daemon Management

```bash
skills-daemon start      # Start daemon (auto-starts on first CLI use)
skills-daemon stop       # Stop daemon
skills-daemon status     # Show health and plugins
skills-daemon restart    # Restart daemon
skills-daemon logs       # Tail daemon logs
```

## CLI Usage

The thin client (`skills-client`) uses stdlib-only for fast startup:

```bash
skills-client <plugin> <command> [--param value ...]

# Examples
skills-client health                           # Daemon health
skills-client plugins                          # List plugins
skills-client --json <plugin> <command>        # JSON output
```

Individual CLI wrappers route to `skills-client`:

```bash
# These are equivalent:
<plugin> <command>
skills-client <plugin> <command>
```

## API Documentation

Interactive API docs available when daemon is running:

- **Swagger UI**: http://127.0.0.1:9100/docs
- **OpenAPI JSON**: http://127.0.0.1:9100/openapi.json
- **Plugin List**: http://127.0.0.1:9100/plugins

## Directory Structure

```
skills-daemon/
├── pyproject.toml              # Package definition (fastapi, uvicorn)
├── README.md                   # This file
├── skills_daemon/
│   ├── __init__.py             # Constants (port 9100, timeouts)
│   ├── main.py                 # FastAPI app, plugin discovery
│   ├── lifecycle.py            # PID, signals, idle timeout
│   ├── logging.py              # Structured JSON logging
│   ├── formatters.py           # Output formatters (human, json, ai, markdown)
│   └── plugins/
│       └── __init__.py         # SkillPlugin ABC + registry
├── cli/
│   ├── daemon_ctl.py           # Daemon management (start/stop/status)
│   └── skills_client.py        # Thin HTTP client (stdlib only)
└── .venv/                      # Virtual environment (auto-created)
```

## Plugin Architecture

Plugins are auto-discovered from `~/.claude/plugins/**/skills_plugin/` directories.

### Plugin Discovery Order

1. `SKILLS_DAEMON_PLUGINS` environment variable (colon-separated paths)
2. `~/.config/skills-daemon/plugins.conf` (one path per line)
3. Convention: scan `~/.claude/plugins/**/skills_plugin/`

### Creating a Plugin

Create a `skills_plugin/__init__.py` in your skill's scripts directory:

```python
from fastapi import APIRouter, Query
from skills_daemon.plugins import SkillPlugin
from skills_daemon.formatters import format_response, get_formatter

class MyPlugin(SkillPlugin):
    @property
    def name(self) -> str:
        return "myplugin"  # URL prefix: /myplugin/*

    @property
    def description(self) -> str:
        return "Description for /plugins endpoint"

    @property
    def router(self) -> APIRouter:
        router = APIRouter()

        @router.get("/status")
        async def status(format: str = Query("json")):
            data = {"status": "ok"}
            return formatted_response(data, format)

        @router.post("/action")
        async def action(param: str, format: str = Query("json")):
            result = do_something(param)
            return formatted_response(result, format)

        return router

    async def startup(self) -> None:
        """Called on daemon startup."""
        pass

    async def shutdown(self) -> None:
        """Called on daemon shutdown."""
        pass

    def health_check(self) -> dict:
        """Return plugin health for /health endpoint."""
        return {"status": "ok"}
```

### Custom Formatters

Plugins can register custom formatters for their data types:

```python
# In skills_plugin/__init__.py
from skills_daemon.formatters import HumanFormatter, formatter_registry

class MyDataFormatter(HumanFormatter):
    # Override icons for your data type
    ICONS = {**HumanFormatter.ICONS, "item": "→"}

    def format(self, data):
        if isinstance(data, list):
            return "\n".join(f"{self.icon('item')} {item}" for item in data)
        return super().format(data)

# Register: (plugin, data_type, format_name, FormatterClass)
formatter_registry.register("myplugin", "items", "human", MyDataFormatter)
```

### Plugin Response Format

Plugins should return responses in this format:

```python
# Success (JSON)
{"success": True, "data": <result>}

# Error (JSON)
{"success": False, "error": "message", "hint": "optional hint"}

# Formatted (PlainTextResponse for human/ai/markdown)
PlainTextResponse(content=formatted_string)
```

### Output Formats

Plugins can support multiple output formats via `?format=` parameter:

| Format | Use Case | Content-Type |
|--------|----------|--------------|
| `json` | Programmatic use | application/json |
| `human` | Terminal with colors | text/plain |
| `ai` | LLM consumption | text/plain |
| `markdown` | Documentation | text/plain |

## Configuration

| Setting | Default | Environment Variable |
|---------|---------|---------------------|
| Host | `127.0.0.1` | `SKILLS_DAEMON_HOST` |
| Port | `9100` | `SKILLS_DAEMON_PORT` |
| Idle timeout | `1800s` (30min) | `SKILLS_DAEMON_TIMEOUT` |
| Shutdown timeout | `10s` | `SKILLS_DAEMON_SHUTDOWN_TIMEOUT` |
| Log level | `INFO` | `SKILLS_DAEMON_LOG_LEVEL` |
| Runtime dir | `~/.local/share/skills-daemon` | `SKILLS_DAEMON_RUNTIME_DIR` |

### Runtime Directory Structure

```
~/.local/share/skills-daemon/
├── logs/daemon.log    # Daemon logs (5MB rotation, 3 backups)
├── state/daemon.pid   # PID file
└── venv/              # Virtual environment
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Connection refused" | Run `skills-daemon start` |
| "Plugin not found" | Check `skills-daemon status` for loaded plugins |
| Slow startup | Ensure daemon is running (auto-starts otherwise) |
| "command not found" | Add `~/.local/bin` to PATH |

### Logs

```bash
# Tail live logs
skills-daemon logs

# Or directly
tail -f ~/.local/share/skills-daemon/logs/daemon.log

# JSON format for parsing
cat ~/.local/share/skills-daemon/logs/daemon.log | jq .
```

### Health Check

```bash
curl http://127.0.0.1:9100/health
# Returns: {"status":"running","version":"1.0.0","plugins":[...],...}
```

## Development

```bash
cd ~/.claude/plugins/marketplaces/sebastian-marketplace/plugins/skills-daemon

# Install dev dependencies
uv pip install -e ".[dev]"

# Run daemon in foreground (for debugging)
PYTHONPATH="$PWD" .venv/bin/python -m skills_daemon.main

# Test endpoints
curl http://127.0.0.1:9100/health
curl http://127.0.0.1:9100/plugins
```

## Dependencies

```toml
[project.dependencies]
fastapi>=0.109.0           # Web framework with auto-docs
uvicorn[standard]>=0.27.0  # ASGI server
```

## Plugin Documentation

Each plugin provides its own README with:
- Available endpoints
- CLI commands
- Configuration options
- Usage examples

See the plugin's directory: `~/.claude/plugins/**/skills_plugin/README.md`
