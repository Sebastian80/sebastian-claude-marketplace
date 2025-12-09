# Serena CLI Scripts

Python CLI for Serena semantic code navigation.

## Architecture

```
serena (bash wrapper)
    ↓
serena-daemon-cli (thin stdlib client)
    ↓ HTTP :9122
serena_daemon/server.py (keeps Python/httpx warm)
    ↓ HTTP :9121
Serena MCP Server (30+ LSP backends)
```

**Performance:** ~120ms per command (vs ~270ms without daemon)

## Components

### serena_daemon/ (Daemon Architecture)

| File | Purpose |
|------|---------|
| `__init__.py` | Constants (port 9122, 30min idle timeout) |
| `server.py` | HTTP daemon using stdlib http.server |
| `client.py` | Stdlib-only thin client (~10ms startup) |

### serena_cli/ (Full CLI - used by daemon)

| File | Purpose |
|------|---------|
| `client.py` | httpx async client with connection pooling |
| `cli.py` | typer-based CLI with subcommands |
| `formatters.py` | Colorized output formatting |
| `session.py` | Session persistence |

### Entry Points

| Script | Purpose |
|--------|---------|
| `serena-daemon-cli` | Main entry (uses daemon) |
| `serena-unified` | Legacy full CLI (no daemon) |

## Setup

```bash
# Create venv (requires Python 3.11+)
cd scripts
uv venv
uv pip install httpx typer rich

# Verify
./serena-daemon-cli daemon start
./serena-daemon-cli status
```

## Daemon Commands

```bash
serena daemon start     # Start daemon
serena daemon stop      # Stop daemon
serena daemon status    # Check health
serena daemon restart   # Restart
```

## Development

```bash
# Run daemon in foreground (for debugging)
PYTHONPATH="$PWD:$PYTHONPATH" .venv/bin/python -m serena_daemon.server -f

# Run full CLI directly (bypasses daemon)
PYTHONPATH="$PWD:$PYTHONPATH" .venv/bin/python -m serena_cli status

# Test thin client
PYTHONPATH="$PWD:$PYTHONPATH" .venv/bin/python -m serena_daemon.client status
```

## Configuration

| Setting | Value | Location |
|---------|-------|----------|
| Daemon port | 9122 | `serena_daemon/__init__.py` |
| MCP server port | 9121 | `serena_cli/client.py` |
| Idle timeout | 30 min | `serena_daemon/__init__.py` |
| Session file | `/tmp/serena-session-{uid}.json` | `serena_cli/session.py` |
| PID file | `/tmp/serena-daemon.pid` | `serena_daemon/__init__.py` |
