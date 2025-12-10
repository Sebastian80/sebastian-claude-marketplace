# Skills Daemon Developer Guide

This document explains the architecture, development workflow, and best practices for the skills-daemon.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        skills-daemon                             │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  FastAPI     │  │  Lifecycle   │  │  Plugin Registry     │  │
│  │  Application │  │  Manager     │  │                      │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘  │
│         │                 │                      │              │
│         └─────────────────┴──────────────────────┘              │
│                           │                                      │
│  ┌────────────────────────┴────────────────────────┐            │
│  │                    Plugins                       │            │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐      │            │
│  │  │ Serena   │  │  Jira    │  │  Custom  │ ...  │            │
│  │  │ Plugin   │  │  Plugin  │  │  Plugin  │      │            │
│  │  └──────────┘  └──────────┘  └──────────┘      │            │
│  └─────────────────────────────────────────────────┘            │
└─────────────────────────────────────────────────────────────────┘
```

### Key Components

| Component | File | Purpose |
|-----------|------|---------|
| **Main App** | `skills_daemon/main.py` | FastAPI app, lifespan management, middleware |
| **Config** | `skills_daemon/config.py` | Centralized configuration with env var support |
| **Lifecycle** | `skills_daemon/lifecycle.py` | PID management, signals, idle timeout |
| **Logging** | `skills_daemon/logging.py` | Structured JSON logging, rotation, async I/O |
| **Plugins** | `skills_daemon/plugins/` | Plugin base class and registry |
| **CLI** | `cli/daemon_ctl.py` | Daemon control (start/stop/status) |
| **Client** | `cli/skills_client.py` | Universal HTTP client with retry |

## Plugin Development

### Creating a Plugin

1. Create a `skills_plugin/` directory in your Claude Code plugin
2. Create `__init__.py` with your plugin class:

```python
from fastapi import APIRouter
from skills_daemon.plugins import SkillPlugin

class MyPlugin(SkillPlugin):
    """My custom plugin."""

    @property
    def name(self) -> str:
        return "my-plugin"  # URL prefix: /my-plugin/

    @property
    def description(self) -> str:
        return "Does something useful"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def router(self) -> APIRouter:
        router = APIRouter()

        @router.get("/hello")
        async def hello(name: str = "World"):
            return {"message": f"Hello, {name}!"}

        return router

    async def startup(self) -> None:
        """Called when daemon starts."""
        # Initialize resources (connections, caches, etc.)
        pass

    async def shutdown(self) -> None:
        """Called when daemon stops."""
        # Cleanup resources
        pass

    def health_check(self) -> dict:
        """Return plugin health status."""
        return {"status": "ok", "connections": 1}
```

### Plugin Discovery

Plugins are discovered in this order:

1. **Environment variable**: `SKILLS_DAEMON_PLUGINS` (colon-separated paths)
2. **Config file**: `~/.config/skills-daemon/plugins.conf` (one path per line)
3. **Convention**: Scan `~/.claude/plugins/**/skills_plugin/`

### Response Format

Use consistent response format:

```python
# Success
{"success": True, "data": result}

# Error
{"success": False, "error": "Description", "hint": "How to fix"}
```

### Plugin Lifecycle

```
__init__()  →  startup()  →  connect()  →  [running]  →  shutdown()
```

| Method | Purpose | Called |
|--------|---------|--------|
| `startup()` | Initialize local resources (caches, configs) | On daemon start |
| `connect()` | Establish backend connections (APIs, DBs) | After startup() |
| `reconnect()` | Re-establish failed connections | On connection failure |
| `shutdown()` | Cleanup all resources | On daemon stop |
| `health_check()` | Quick status check | On /health requests |

### Plugin Best Practices

- **Separate startup and connect**: Use `startup()` for local init, `connect()` for external connections
- **Graceful failures**: `connect()` exceptions are logged but don't prevent daemon from running
- **Implement reconnect()**: For custom reconnection logic (e.g., exponential backoff)
- **Health checks**: Return meaningful status including connection state
- **Timeouts**: Use asyncio timeouts for external calls
- **Errors**: Return structured error responses, don't raise HTTP exceptions

## Configuration

### Environment Variables

All config uses `SKILLS_DAEMON_` prefix:

| Variable | Default | Description |
|----------|---------|-------------|
| `SKILLS_DAEMON_HOST` | `127.0.0.1` | Bind address |
| `SKILLS_DAEMON_PORT` | `9100` | Port number |
| `SKILLS_DAEMON_TIMEOUT` | `1800` | Idle timeout (seconds) |
| `SKILLS_DAEMON_SHUTDOWN_TIMEOUT` | `10` | Shutdown timeout (seconds) |
| `SKILLS_DAEMON_LOG_LEVEL` | `INFO` | Log level (DEBUG/INFO/WARNING/ERROR) |
| `SKILLS_DAEMON_RUNTIME_DIR` | `~/.local/share/skills-daemon` | Runtime directory (logs, state, venv) |

Runtime directory structure:
```
~/.local/share/skills-daemon/
├── logs/daemon.log    # Log file (5MB rotation, 3 backups)
├── state/daemon.pid   # PID file
└── venv/              # Virtual environment
```

### Accessing Configuration

```python
from skills_daemon.config import config

print(config.port)           # 9100
print(config.log_level)      # INFO
print(config.daemon_url)     # http://127.0.0.1:9100
```

## Logging

### Structured Logging

Logs are JSON-formatted for easy parsing:

```json
{
  "timestamp": "2024-12-10T19:00:00Z",
  "level": "INFO",
  "logger": "skills-daemon",
  "message": "Plugin started",
  "request_id": "a1b2c3d4",
  "plugin": "serena"
}
```

### Using the Logger

```python
from skills_daemon.logging import logger

# Simple logging
logger.info("Plugin started")
logger.warning("Connection slow")
logger.error("Failed to connect")

# Structured logging with context
logger.info("Request processed", duration_ms=42, path="/health")
```

### Request Correlation

All requests get a correlation ID for tracing:

```python
from skills_daemon.logging import get_request_id, set_request_id

# In middleware, ID is auto-generated
# In your code, get the current ID:
request_id = get_request_id()
logger.info("Processing", request_id=request_id)
```

### Log Rotation

- **Max size**: 5MB per file
- **Backups**: 3 rotated files kept
- **Async I/O**: Logging doesn't block requests

## Testing

### Running Tests

```bash
# All tests
.venv/bin/pytest

# With coverage
.venv/bin/pytest --cov=skills_daemon

# Specific test file
.venv/bin/pytest tests/unit/test_config.py -v

# Run specific test
.venv/bin/pytest tests/unit/test_config.py::TestDaemonConfig::test_defaults -v
```

### Test Structure

```
tests/
├── conftest.py           # Shared fixtures
├── unit/
│   ├── test_config.py    # Config module tests
│   ├── test_colors.py    # Colors module tests
│   ├── test_registry.py  # Plugin registry tests
│   ├── test_lifecycle.py # Lifecycle tests
│   └── test_client.py    # Client retry tests
└── integration/
    └── test_endpoints.py # Core endpoint tests
```

### Writing Tests

Use the fixtures in `conftest.py`:

```python
import pytest

def test_plugin_registration(isolated_registry, simple_plugin):
    """isolated_registry provides clean registry for each test."""
    isolated_registry.register(simple_plugin)
    assert "test-simple" in isolated_registry.names()

@pytest.mark.asyncio
async def test_async_operation():
    """Use @pytest.mark.asyncio for async tests."""
    result = await some_async_function()
    assert result == expected
```

## Debugging

### Enable Debug Logging

```bash
export SKILLS_DAEMON_LOG_LEVEL=DEBUG
skills-daemon restart
```

### View Logs

```bash
# Real-time
skills-daemon logs

# Or directly
tail -f ~/.local/share/skills-daemon/logs/daemon.log | jq .
```

### Check Health

```bash
skills-client health

# Or directly
curl http://127.0.0.1:9100/health | jq .
```

### Slow Request Detection

Requests > 1000ms are logged at WARNING level:

```json
{
  "level": "WARNING",
  "message": "slow_request",
  "path": "/serena/symbols",
  "duration_ms": 1542
}
```

## Deployment

### Manual Start

```bash
skills-daemon start
skills-daemon status
skills-daemon stop
```

### Systemd User Service

```bash
# Install service
cd contrib/systemd
./install.sh --enable --start

# Manage
systemctl --user status skills-daemon
systemctl --user restart skills-daemon
journalctl --user -u skills-daemon -f
```

### Auto-Start on Login

The skills-client auto-starts the daemon when needed:

```bash
# This will start daemon if not running
skills-client health
```

## Self-Healing Features

### HTTP Retry

Client retries transient failures with exponential backoff:
- **Max retries**: 3
- **Backoff**: 0.5s, 1.0s, 2.0s
- **Retried errors**: Connection refused, timeout
- **Not retried**: HTTP 4xx/5xx

### Shutdown Timeout

Plugins that hang during shutdown are force-terminated:
- **Timeout**: 10 seconds (configurable)
- **Logged**: Warning when timeout occurs

### Idle Timeout

Daemon shuts down after 30 minutes of inactivity:
- **Timeout**: 1800 seconds (configurable)
- **Auto-restart**: Client starts daemon on next request

### Systemd Auto-Restart

With systemd service installed:
- **Restart on failure**: Yes
- **Restart delay**: 5 seconds
- **Max restarts**: 3 per minute
- **Memory limit**: 256MB
- **CPU limit**: 50%

## Code Style

### Module Organization

```
skills_daemon/
├── __init__.py      # Version, constants, re-exports
├── config.py        # Configuration (immutable dataclass)
├── colors.py        # TTY-aware terminal colors
├── logging.py       # Structured logging
├── lifecycle.py     # Daemon lifecycle management
├── main.py          # FastAPI app
├── formatters.py    # Output formatters (if needed)
└── plugins/
    └── __init__.py  # SkillPlugin base class, registry
```

### Principles

1. **DRY**: Shared code in dedicated modules (config, colors, logging)
2. **SOLID**: Single responsibility, dependency injection via config
3. **YAGNI**: Only implement what's needed now
4. **Type hints**: Use throughout for clarity
5. **Docstrings**: Module, class, and function level
6. **Tests**: Unit tests for all new code

### Error Handling

```python
# Good: Return structured errors
return {"success": False, "error": "Not found", "hint": "Check the key"}

# Avoid: Raising HTTP exceptions (let FastAPI handle it)
raise HTTPException(status_code=404, detail="Not found")
```

## Troubleshooting

### Daemon Won't Start

1. Check if port is in use: `ss -tlnp | grep 9100`
2. Check for stale PID: `cat ~/.local/share/skills-daemon/state/daemon.pid && ps aux | grep skills`
3. Check logs: `tail ~/.local/share/skills-daemon/logs/daemon.log`

### Plugin Not Loading

1. Verify discovery path: `ls ~/.claude/plugins/**/skills_plugin/__init__.py`
2. Check plugin syntax: `python -c "import skills_plugin"`
3. Check daemon logs for errors

### Slow Performance

1. Enable debug logging
2. Check for slow requests in logs
3. Review plugin health: `skills-client health`
4. Profile with `py-spy` if needed

### Connection Errors

1. Verify daemon running: `skills-daemon status`
2. Check firewall: `curl http://127.0.0.1:9100/health`
3. Client auto-starts daemon, wait 3 seconds
