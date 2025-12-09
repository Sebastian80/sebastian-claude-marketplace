# Serena Integration Plugin

Claude Code integration with Serena LSP for semantic code navigation (30+ languages).

## Features

- **serena skill**: Core Serena usage with daemon-based CLI
- **php-explore hook**: Automatically injects Serena context into Explore agent for PHP projects
- **Slash commands**: `/serena:onboard`, `/serena:load`, `/serena:save`
- **Agents**: serena-explore, framework-explore

## Architecture

```
serena CLI (thin) → HTTP daemon (port 9122) → Serena MCP server (port 9121)
     ~10ms              keeps Python warm           30+ LSP backends
```

Performance: ~120ms per command (vs ~270ms without daemon)

## When This Plugin Activates

The explore hook triggers for projects with:
- `composer.json` present (PHP projects)

## Setup

### 1. Enable Plugin

Already enabled via marketplace.

### 2. CLI Wrapper

The CLI wrapper at `~/.local/bin/serena` routes to the daemon-based CLI:

```bash
#!/bin/bash
SCRIPTS_DIR=~/.claude/plugins/marketplaces/sebastian-marketplace/plugins/serena-integration/skills/serena/scripts
exec "$SCRIPTS_DIR/serena-daemon-cli" "$@"
```

Make executable: `chmod +x ~/.local/bin/serena`

### 3. Permissions

Add to `~/.claude/settings.json`:

```json
{
  "permissions": {
    "allow": [
      "Bash(/home/sebastian/.local/bin/serena:*)",
      "Bash(serena:*)",
      "Skill(serena-integration:*)"
    ]
  }
}
```

## Serena CLI Commands

```bash
serena status                        # Check connection
serena daemon status                 # Check daemon health
serena find Customer --kind class    # Find symbol
serena refs "Customer/getName" file  # Find references
serena overview file.php             # File structure
serena memory list                   # List memories
```

## Daemon Management

```bash
serena daemon start     # Start daemon manually
serena daemon stop      # Stop daemon
serena daemon status    # Check if running
serena daemon restart   # Restart daemon
```

The daemon auto-starts on first use and auto-stops after 30min idle.

## Skills

### serena

Core Serena usage - semantic code navigation via LSP. Includes:
- Automatic triggers for code navigation tasks
- Anti-rationalization patterns (Serena-first rule)
- Performance best practices
- Troubleshooting guide

## Scripts Structure

```
skills/serena/scripts/
├── serena-daemon-cli     # Main CLI entry point
├── serena-unified        # Legacy full CLI (httpx/typer)
├── serena_cli/           # Full Python CLI package
│   ├── client.py         # httpx async client
│   ├── cli.py            # typer CLI
│   └── formatters.py     # Output formatting
└── serena_daemon/        # Daemon architecture
    ├── server.py         # HTTP daemon server
    └── client.py         # Stdlib-only thin client
```
