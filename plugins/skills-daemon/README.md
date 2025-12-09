# Skills Daemon

Central FastAPI-based daemon for Claude Code skills. Provides a unified HTTP interface with plugin architecture for multiple skill backends (Serena, Jira, JetBrains, etc.).

## Features

- **Concurrent Request Handling** - FastAPI async architecture handles multiple agents calling simultaneously
- **Plugin Architecture** - Auto-discovery of plugins without hardcoded paths
- **Unified CLI** - Single thin client for all skills with fast startup (~10ms)
- **Auto-generated API Docs** - Swagger UI at `/docs`, OpenAPI spec at `/openapi.json`
- **Lifecycle Management** - Auto-start on first use, auto-stop after 30min idle
- **Structured Logging** - JSON logs to `/tmp/skills-daemon.log`

## Architecture

```
CLI Entry Points
┌─────────────────────────────────────────────────────────────────────┐
│ ~/.local/bin/serena      → skills-client serena ...                 │
│ ~/.local/bin/jira        → skills-client jira ...      (future)     │
│ ~/.local/bin/jetbrains   → skills-client jetbrains ... (future)     │
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
│   ├── /serena/*             Semantic code navigation                │
│   ├── /jira/*               Jira integration (future)               │
│   └── /jetbrains/*          JetBrains IDE (future)                  │
└─────────────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────────┐
│ Backend Services                                                    │
│   ├── Serena MCP Server (:9121)   30+ language servers              │
│   ├── Jira REST API               (future)                          │
│   └── JetBrains IDE (:63342)      (future)                          │
└─────────────────────────────────────────────────────────────────────┘
```

## Quick Start

```bash
# Check daemon health
skills-client health

# Use Serena via the daemon
serena status
serena find --pattern Customer --kind class
serena refs --symbol "Customer/getName" --file src/Entity/Customer.php

# View API documentation
curl http://127.0.0.1:9100/docs
```

## Installation

The daemon uses `uv` for fast venv setup:

```bash
cd ~/.claude/plugins/marketplaces/sebastian-marketplace/skills-daemon

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
skills-client serena find --pattern Customer   # Find symbols
skills-client serena refs --symbol X --file f  # Find references
skills-client --json serena status             # JSON output
```

Individual CLI wrappers route to `skills-client`:

```bash
# These are equivalent:
serena find --pattern Customer
skills-client serena find --pattern Customer
```

## API Documentation

Interactive API docs available when daemon is running:

- **Swagger UI**: http://127.0.0.1:9100/docs
- **OpenAPI JSON**: http://127.0.0.1:9100/openapi.json
- **Plugin List**: http://127.0.0.1:9100/plugins

## Directory Structure

```
skills-daemon/
├── pyproject.toml              # Package definition (fastapi, uvicorn, httpx)
├── README.md                   # This file
├── skills_daemon/
│   ├── __init__.py             # Constants (port 9100, timeouts)
│   ├── main.py                 # FastAPI app, plugin discovery
│   ├── lifecycle.py            # PID, signals, idle timeout
│   ├── logging.py              # Structured JSON logging
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
from fastapi import APIRouter
from skills_daemon.plugins import SkillPlugin

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
        async def status():
            return {"success": True, "data": {"status": "ok"}}

        @router.post("/action")
        async def action(param: str):
            result = do_something(param)
            return {"success": True, "data": result}

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

### Plugin Response Format

Plugins should return responses in this format:

```python
# Success
{"success": True, "data": <result>}

# Error
{"success": False, "error": "message", "hint": "optional hint"}
```

## Configuration

| Setting | Default | Location |
|---------|---------|----------|
| Daemon port | 9100 | `skills_daemon/__init__.py` |
| Idle timeout | 1800s (30min) | `skills_daemon/__init__.py` |
| PID file | `/tmp/skills-daemon.pid` | `skills_daemon/__init__.py` |
| Log file | `/tmp/skills-daemon.log` | `skills_daemon/__init__.py` |
| Log level | INFO | `skills_daemon/logging.py` |

## Registered Plugins

### Serena Plugin

Location: `~/.claude/plugins/.../serena-integration/skills/serena/scripts/skills_plugin/`

Provides semantic code navigation via Serena MCP server:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/serena/status` | GET | Project status |
| `/serena/activate` | POST | Activate project |
| `/serena/find` | GET | Find symbols |
| `/serena/refs` | GET | Find references |
| `/serena/overview` | GET | File structure |
| `/serena/search` | GET | Regex search |
| `/serena/recipe` | GET | Pre-built searches |
| `/serena/memory/*` | GET/POST/DELETE | Memory operations |
| `/serena/edit/*` | POST | Symbol-based editing |

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
tail -f /tmp/skills-daemon.log

# JSON format for parsing
cat /tmp/skills-daemon.log | jq .
```

### Health Check

```bash
curl http://127.0.0.1:9100/health
# Returns: {"status":"running","version":"1.0.0","plugins":["serena"],...}
```

## Development

```bash
cd ~/.claude/plugins/marketplaces/sebastian-marketplace/skills-daemon

# Install dev dependencies
uv pip install -e ".[dev]"

# Run daemon in foreground (for debugging)
PYTHONPATH="$PWD" .venv/bin/python -m skills_daemon.main

# Test endpoints
curl http://127.0.0.1:9100/health
curl http://127.0.0.1:9100/plugins
curl "http://127.0.0.1:9100/serena/find?pattern=Customer"
```

## Dependencies

```toml
[project.dependencies]
fastapi>=0.109.0      # Web framework with auto-docs
uvicorn[standard]>=0.27.0  # ASGI server
httpx>=0.26.0         # Async HTTP client
```

## Future Plugins

| Plugin | Backend | Status |
|--------|---------|--------|
| serena | Serena MCP Server | Active |
| jira | Jira REST API | Planned |
| jetbrains | JetBrains Gateway | Planned |
| github | GitHub API | Planned |
