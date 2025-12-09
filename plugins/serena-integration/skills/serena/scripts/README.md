# Serena CLI Scripts

Python CLI and plugin for Serena semantic code navigation.

## Architecture

```
~/.local/bin/serena (bash wrapper)
    ↓
skills-client serena (thin stdlib client)
    ↓ HTTP :9100
Skills Daemon (FastAPI, central daemon)
    ├── SerenaPlugin (auto-discovered from skills_plugin/)
    │   ↓ async httpx
    │   Serena MCP Server (:9121, 30+ LSP backends)
    ├── JiraPlugin (future)
    └── JetBrainsPlugin (future)
```

**Key Points:**
- Serena is now a plugin for the central skills-daemon (port 9100)
- Plugin auto-discovered from `scripts/skills_plugin/__init__.py`
- Skills daemon handles concurrency, logging, lifecycle
- SerenaClient reused from serena_cli for MCP communication

## Components

### skills_plugin/ (Daemon Plugin)

| File | Purpose |
|------|---------|
| `__init__.py` | SerenaPlugin class with FastAPI routes |

The plugin implements `SkillPlugin` interface from skills-daemon and exposes all Serena operations as HTTP endpoints at `/serena/*`.

### serena_cli/ (Core Client Library)

| File | Purpose |
|------|---------|
| `client.py` | httpx async client for Serena MCP server |
| `cli.py` | typer-based CLI (legacy, for direct use) |
| `formatters.py` | Colorized output formatting |
| `session.py` | Session persistence |

### serena_daemon/ (Legacy Standalone Daemon)

**Note:** This is the old standalone daemon on port 9122. The new architecture uses the central skills-daemon on port 9100 instead.

| File | Purpose |
|------|---------|
| `__init__.py` | Constants (port 9122 - legacy) |
| `server.py` | HTTP daemon using stdlib http.server |
| `client.py` | Stdlib-only thin client |

### Entry Points

| Script | Purpose | Status |
|--------|---------|--------|
| `~/.local/bin/serena` | Routes to skills-daemon | **Active** |
| `serena-daemon-cli` | Legacy direct daemon | Deprecated |
| `serena-unified` | Legacy full CLI (no daemon) | Deprecated |

## Setup

The central skills-daemon is set up automatically on first use:

```bash
# Uses skills-daemon (auto-starts if needed)
serena status
serena find --pattern Customer
```

For development of the serena_cli library:

```bash
cd scripts
uv venv
uv pip install httpx typer rich
```

## Configuration

| Setting | Value | Location |
|---------|-------|----------|
| Skills daemon port | 9100 | `~/.local/bin/skills-daemon` |
| Serena MCP port | 9121 | `serena_cli/client.py` |
| Session file | `/tmp/serena-session-{uid}.json` | `serena_cli/session.py` |

## Plugin Development

The SerenaPlugin in `skills_plugin/__init__.py`:

1. Imports `SkillPlugin` base class from skills-daemon
2. Imports `SerenaClient` from serena_cli
3. Exposes all Serena operations as FastAPI routes
4. Handles client lifecycle (lazy init, cleanup on shutdown)

```python
class SerenaPlugin(SkillPlugin):
    @property
    def name(self) -> str:
        return "serena"

    @property
    def router(self) -> APIRouter:
        router = APIRouter()

        @router.get("/find")
        async def find(pattern: str, ...):
            c = await get_client()
            result = await c.find_symbol(pattern, ...)
            return {"success": True, "data": result}

        return router
```

## API Reference

See skills-daemon API docs: http://127.0.0.1:9100/docs

Key endpoints:
- `GET /serena/status` - Project status
- `POST /serena/activate` - Activate project
- `GET /serena/find` - Find symbols
- `GET /serena/refs` - Find references
- `GET /serena/overview` - File structure
- `GET /serena/search` - Regex search
- `GET /serena/recipe` - Pre-built searches
- `GET/POST/DELETE /serena/memory/*` - Memory operations
- `POST /serena/edit/*` - Symbol-based editing
