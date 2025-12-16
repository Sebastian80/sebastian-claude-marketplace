---
name: bridge
description: "AI Tool Bridge daemon management. Use for: starting/stopping bridge, checking status, managing external service connectors. Auto-installs Python venv on first use."
---

# AI Tool Bridge

Plugin-based daemon that bridges AI agents to external services via unified HTTP API.

## Quick Reference

| Command | Description |
|---------|-------------|
| `bridge setup` | Force reinstall/setup venv |
| `bridge start` | Start daemon (background) |
| `bridge start -f` | Start in foreground |
| `bridge stop` | Stop daemon gracefully |
| `bridge restart` | Restart daemon |
| `bridge status` | Show daemon and component status |
| `bridge health` | Quick health check |
| `bridge plugins` | List loaded plugins |
| `bridge connectors` | List connectors and states |
| `bridge reconnect NAME` | Force reconnect a connector |

## Auto-Setup

The bridge **automatically sets up** its Python environment on first use:
- Creates `.venv` in the plugin directory
- Installs the ai-tool-bridge package
- No manual setup required

Force reinstall: `bridge setup`

## Usage Patterns

### Check if bridge is running
```bash
bridge status
```

### Start bridge for a session
```bash
bridge start
# Bridge auto-shuts down after idle timeout
```

### For plugins that depend on bridge
Other plugins can check bridge availability:
```bash
bridge health && echo "Bridge ready"
```

## Architecture

The bridge is **infrastructure** for other plugins:
- Provides unified HTTP API at `http://localhost:8765`
- Plugins register routes via the plugin system
- Auto-discovers plugins from `~/.claude/plugins`
- Idle shutdown saves resources when not in use

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "bridge: command not found" | Plugin not installed - run `/plugin install ai-tool-bridge` |
| "Connection refused" | Bridge not running - `bridge start` |
| Setup fails | Check Python 3.8+ available: `python3 --version` |
| Stale PID | `bridge stop` then `bridge start` |
