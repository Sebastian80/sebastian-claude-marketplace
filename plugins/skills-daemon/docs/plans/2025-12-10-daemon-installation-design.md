# Skills Daemon Installation & Lifecycle Design

**Date:** 2025-12-10
**Status:** Draft
**Author:** Sebastian + Claude

## Overview

This document describes the architecture for:
1. Automated dependency installation when plugins register
2. Prevention of stale daemon processes
3. Proper installation flow for the daemon
4. Zero-sudo, fully user-space operation

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Dependency scope | Shared daemon venv + plugin deps | Simple, plugins extend shared venv |
| Dep installation timing | Startup scan + hot-install | Fast startup, runtime flexibility |
| Dependency declaration | `manifest.json` in skills_plugin/ | Readable before import (critical) |
| Stale process handling | Client-side recovery | No watchdog complexity, transparent |
| Runtime location | `~/.local/share/skills-daemon/` | Survives plugin updates |
| Installation method | Marketplace wrapper script | Works without modifying Claude Code |

---

## Architecture

### Directory Structure

```
~/.local/share/skills-daemon/          # Stable runtime (survives updates)
├── venv/                              # Python virtual environment
├── plugins.json                       # Registered plugins + their deps
└── daemon.pid                         # PID file

~/.local/bin/                          # CLI entry points
├── skills-daemon                      # Daemon control
├── skills-client                      # Generic client
├── jira                               # Plugin-specific CLI
└── serena                             # Plugin-specific CLI

~/.config/skills-daemon/               # Configuration
└── config.toml                        # User settings (optional)

~/.claude/plugins/.../skills-daemon/   # Source code only
└── (never run from here)
```

### Component Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Installation Flow                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  User: sebastian-marketplace install skills-daemon                   │
│                          │                                           │
│                          ▼                                           │
│  ┌──────────────────────────────────────┐                           │
│  │  Marketplace install.sh               │                           │
│  │  1. claude plugins install X          │                           │
│  │  2. Read plugin.json (postInstall)    │                           │
│  │  3. Run setup script                  │                           │
│  │  4. Create CLI entry points           │                           │
│  └──────────────────────────────────────┘                           │
│                          │                                           │
│                          ▼                                           │
│  ┌──────────────────────────────────────┐                           │
│  │  setup.sh                             │                           │
│  │  1. Create ~/.local/share/skills-daemon│                          │
│  │  2. Create venv with uv               │                           │
│  │  3. Install core deps                 │                           │
│  │  4. Scan plugin manifests             │                           │
│  │  5. Install plugin deps               │                           │
│  └──────────────────────────────────────┘                           │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                         Runtime Flow                                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  User: jira search "assignee = currentUser()"                        │
│                          │                                           │
│                          ▼                                           │
│  ┌──────────────────────────────────────┐                           │
│  │  ~/.local/bin/jira (wrapper)          │                           │
│  │  1. Check daemon health               │                           │
│  │  2. If stale → recover (kill+restart) │                           │
│  │  3. Forward request to daemon         │                           │
│  └──────────────────────────────────────┘                           │
│                          │                                           │
│                          ▼                                           │
│  ┌──────────────────────────────────────┐                           │
│  │  Skills Daemon (FastAPI)              │                           │
│  │  - Runs from stable venv              │                           │
│  │  - Plugins loaded dynamically         │                           │
│  │  - Auto-shutdown on 30min idle        │                           │
│  └──────────────────────────────────────┘                           │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Plugin Dependency Declaration

### manifest.json Schema

Each plugin that registers with the daemon should have a `manifest.json`:

```
~/.claude/plugins/.../jira-integration/
└── skills/jira-communication/scripts/skills_plugin/
    ├── __init__.py
    └── manifest.json    ← NEW
```

**manifest.json format:**

```json
{
  "name": "jira",
  "version": "1.0.0",
  "description": "Jira integration for skills daemon",
  "dependencies": [
    "atlassian-python-api>=4.0",
    "httpx>=0.25"
  ],
  "daemon_version": ">=1.0.0"
}
```

### Dependency Resolution

On daemon startup:
1. Scan all `skills_plugin/manifest.json` files
2. Collect all dependencies
3. Compare with installed packages in venv
4. Install missing packages via `uv pip install`
5. Log results

```python
# Pseudo-code
def ensure_plugin_dependencies():
    manifests = glob("~/.claude/plugins/**/skills_plugin/manifest.json")
    required = set()
    for m in manifests:
        data = json.load(m)
        required.update(data.get("dependencies", []))

    installed = get_installed_packages()
    missing = required - installed

    if missing:
        logger.info(f"Installing plugin dependencies: {missing}")
        subprocess.run(["uv", "pip", "install", *missing])
```

---

## Stale Process Prevention & Recovery

### Root Cause

Staleness occurs when:
1. Plugin directory is deleted/replaced during update
2. Daemon's working directory becomes invalid
3. Venv is inside the deleted directory

### Prevention: Stable Runtime Location

```
BEFORE (fragile):
~/.claude/plugins/.../skills-daemon/
├── .venv/              ← deleted on update!
└── skills_daemon/

AFTER (stable):
~/.local/share/skills-daemon/
├── venv/               ← survives updates
└── (runtime state)

~/.claude/plugins/.../skills-daemon/
└── skills_daemon/      ← source only
```

### Detection: Health Check Enhancement

**Enhanced /health response:**

```json
{
  "status": "running",
  "version": "1.0.0",
  "cwd_valid": true,
  "venv_valid": true,
  "uptime_seconds": 3600,
  "plugins": ["jira", "serena"]
}
```

**cwd_valid check:**
```python
def check_cwd_valid() -> bool:
    try:
        cwd = Path("/proc/self/cwd").resolve()
        return cwd.exists() and "(deleted)" not in str(cwd)
    except:
        return False
```

### Recovery: Client-Side Auto-Heal

**CLI wrapper flow:**

```bash
#!/bin/bash
# ~/.local/bin/jira

DAEMON_URL="http://127.0.0.1:9100"
RUNTIME="$HOME/.local/share/skills-daemon"

# Health check with validation
health=$(curl -s --max-time 2 "$DAEMON_URL/health" 2>/dev/null)
status=$?

# Check if daemon is healthy
if [ $status -ne 0 ] || [ "$(echo "$health" | jq -r '.cwd_valid')" = "false" ]; then
    echo "Recovering daemon..." >&2

    # Graceful shutdown attempt
    curl -s -X POST "$DAEMON_URL/shutdown" 2>/dev/null
    sleep 1

    # Force kill if still running
    pkill -f "skills_daemon.main" 2>/dev/null
    sleep 1

    # Start fresh
    "$RUNTIME/venv/bin/python" -m skills_daemon.main &

    # Wait for healthy
    for i in {1..30}; do
        sleep 0.1
        curl -s "$DAEMON_URL/health" >/dev/null 2>&1 && break
    done
fi

# Execute command
exec skills-client jira "$@"
```

---

## Installation Flow

### Extended plugin.json Schema

```json
{
  "name": "skills-daemon",
  "version": "1.0.0",
  "description": "Central daemon for Claude Code skills",
  "author": { "name": "Sebastian" },
  "license": "MIT",

  "postInstall": "scripts/setup.sh",
  "postUpdate": "scripts/upgrade.sh",

  "cliEntryPoints": {
    "skills-daemon": {
      "script": "cli/daemon_ctl.py",
      "description": "Daemon control (start/stop/status)"
    },
    "skills-client": {
      "script": "cli/skills_client.py",
      "description": "Generic skills client"
    }
  }
}
```

### Marketplace install.sh

```bash
#!/bin/bash
# ~/.claude/plugins/marketplaces/sebastian-marketplace/scripts/install.sh

set -e

PLUGIN="$1"
MARKETPLACE_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PLUGIN_DIR="$MARKETPLACE_ROOT/plugins/$PLUGIN"
PLUGIN_JSON="$PLUGIN_DIR/.claude-plugin/plugin.json"

# Colors
GREEN='\033[32m'
YELLOW='\033[33m'
RED='\033[31m'
DIM='\033[2m'
RESET='\033[0m'

echo -e "${DIM}Installing $PLUGIN...${RESET}"

# 1. Call Claude Code's native install
if command -v claude &>/dev/null; then
    claude plugins install "$PLUGIN" 2>/dev/null || true
fi

# 2. Check for plugin.json
if [ ! -f "$PLUGIN_JSON" ]; then
    echo -e "${RED}Error: Plugin not found: $PLUGIN${RESET}"
    exit 1
fi

# 3. Read postInstall script
POST_INSTALL=$(jq -r '.postInstall // empty' "$PLUGIN_JSON")

if [ -n "$POST_INSTALL" ]; then
    echo -e "${DIM}Running post-install...${RESET}"
    SCRIPT_PATH="$PLUGIN_DIR/$POST_INSTALL"

    if [ -x "$SCRIPT_PATH" ]; then
        if "$SCRIPT_PATH"; then
            echo -e "${GREEN}✓ Post-install completed${RESET}"
        else
            echo -e "${RED}✗ Post-install failed${RESET}"
            exit 1
        fi
    else
        echo -e "${YELLOW}Warning: Post-install script not executable: $SCRIPT_PATH${RESET}"
    fi
fi

# 4. Create CLI entry points
CLI_ENTRIES=$(jq -r '.cliEntryPoints // empty | keys[]' "$PLUGIN_JSON" 2>/dev/null)

if [ -n "$CLI_ENTRIES" ]; then
    mkdir -p "$HOME/.local/bin"

    for cmd in $CLI_ENTRIES; do
        SCRIPT=$(jq -r ".cliEntryPoints[\"$cmd\"].script // .cliEntryPoints[\"$cmd\"]" "$PLUGIN_JSON")
        WRAPPER="$HOME/.local/bin/$cmd"

        # Determine the runtime location
        RUNTIME="$HOME/.local/share/skills-daemon"

        cat > "$WRAPPER" << EOF
#!/bin/bash
exec "$RUNTIME/venv/bin/python" "$PLUGIN_DIR/$SCRIPT" "\$@"
EOF
        chmod +x "$WRAPPER"
        echo -e "${GREEN}✓ Created CLI: $cmd${RESET}"
    done
fi

echo -e "${GREEN}✓ $PLUGIN installed successfully${RESET}"
```

### Plugin setup.sh (skills-daemon)

```bash
#!/bin/bash
# skills-daemon/scripts/setup.sh

set -e

RUNTIME="$HOME/.local/share/skills-daemon"
PLUGIN_DIR="$(cd "$(dirname "$0")/.." && pwd)"

GREEN='\033[32m'
DIM='\033[2m'
RESET='\033[0m'

echo -e "${DIM}Setting up skills daemon runtime...${RESET}"

# 1. Create runtime directory
mkdir -p "$RUNTIME"

# 2. Create venv if not exists
if [ ! -d "$RUNTIME/venv" ]; then
    echo -e "${DIM}Creating virtual environment...${RESET}"
    uv venv "$RUNTIME/venv"
fi

# 3. Install core dependencies
echo -e "${DIM}Installing dependencies...${RESET}"
"$RUNTIME/venv/bin/pip" install -q \
    fastapi \
    uvicorn[standard] \
    httpx \
    pyyaml \
    python-dotenv

# 4. Install daemon package in editable mode
"$RUNTIME/venv/bin/pip" install -q -e "$PLUGIN_DIR"

# 5. Scan and install plugin dependencies
echo -e "${DIM}Checking plugin dependencies...${RESET}"

for manifest in "$HOME/.claude/plugins"/**/skills_plugin/manifest.json; do
    if [ -f "$manifest" ]; then
        deps=$(jq -r '.dependencies[]? // empty' "$manifest" 2>/dev/null)
        if [ -n "$deps" ]; then
            echo "$deps" | while read dep; do
                "$RUNTIME/venv/bin/pip" install -q "$dep" 2>/dev/null || true
            done
        fi
    fi
done

echo -e "${GREEN}✓ Skills daemon setup complete${RESET}"
echo -e "${DIM}Runtime: $RUNTIME${RESET}"
```

---

## Hot Plugin Installation

### POST /install-plugin Endpoint

For runtime plugin installation without daemon restart:

```python
@app.post("/install-plugin")
async def install_plugin(manifest_path: str) -> dict:
    """Install plugin dependencies and load plugin at runtime."""

    # 1. Read manifest
    manifest = json.loads(Path(manifest_path).read_text())

    # 2. Install dependencies
    deps = manifest.get("dependencies", [])
    if deps:
        result = subprocess.run(
            ["pip", "install", *deps],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            return {"success": False, "error": result.stderr}

    # 3. Load plugin
    plugin_dir = Path(manifest_path).parent
    load_plugin_from_path(plugin_dir / "__init__.py")

    # 4. Mount router
    plugin = registry.get(manifest["name"])
    if plugin:
        app.include_router(plugin.router, prefix=f"/{plugin.name}")
        await plugin.startup()

    return {
        "success": True,
        "plugin": manifest["name"],
        "dependencies_installed": deps
    }
```

---

## CLI Wrapper Template

**Generic wrapper with auto-recovery:**

```bash
#!/bin/bash
# Template for ~/.local/bin/<command>

PLUGIN_NAME="jira"
DAEMON_URL="http://127.0.0.1:9100"
RUNTIME="$HOME/.local/share/skills-daemon"

ensure_daemon() {
    # Quick health check
    if curl -s --max-time 1 "$DAEMON_URL/health" | jq -e '.cwd_valid != false' >/dev/null 2>&1; then
        return 0
    fi

    echo "Starting skills daemon..." >&2

    # Kill stale process
    pkill -f "skills_daemon.main" 2>/dev/null || true
    sleep 0.5

    # Start daemon
    nohup "$RUNTIME/venv/bin/python" -m skills_daemon.main \
        > /tmp/skills-daemon.log 2>&1 &

    # Wait for ready
    for i in {1..50}; do
        sleep 0.1
        curl -s "$DAEMON_URL/health" >/dev/null 2>&1 && return 0
    done

    echo "Failed to start daemon. Check /tmp/skills-daemon.log" >&2
    return 1
}

ensure_daemon || exit 1
exec "$RUNTIME/venv/bin/python" -m cli.skills_client "$PLUGIN_NAME" "$@"
```

---

## Summary

### What Gets Created

| Component | Location | Purpose |
|-----------|----------|---------|
| Runtime venv | `~/.local/share/skills-daemon/venv/` | Stable Python environment |
| CLI wrappers | `~/.local/bin/*` | User commands |
| Plugin manifests | `skills_plugin/manifest.json` | Dependency declarations |
| Install wrapper | `marketplace/scripts/install.sh` | Post-install hook runner |

### User Experience

**First install:**
```bash
$ sebastian-marketplace install skills-daemon
Installing skills-daemon...
Running post-install...
Creating virtual environment...
Installing dependencies...
✓ Post-install completed
✓ Created CLI: skills-daemon
✓ Created CLI: skills-client
✓ skills-daemon installed successfully
```

**First use (auto-starts daemon):**
```bash
$ jira search "assignee = currentUser()"
Starting skills daemon...
PROJ-123  Open    Fix login bug
PROJ-456  Done    Update docs
```

**After plugin update (auto-recovers):**
```bash
$ jira search "project = PROJ"
Recovering daemon...
PROJ-123  Open    Fix login bug
```

---

## Implementation Checklist

- [ ] Create `~/.local/share/skills-daemon/` structure
- [ ] Move venv to stable location
- [ ] Add `manifest.json` schema for plugins
- [ ] Create `manifest.json` for jira plugin
- [ ] Create `manifest.json` for serena plugin
- [ ] Add `cwd_valid` to /health endpoint
- [ ] Create marketplace `install.sh` wrapper
- [ ] Create `scripts/setup.sh` for skills-daemon
- [ ] Update `plugin.json` with new fields
- [ ] Create CLI wrapper template
- [ ] Update existing CLI wrappers with auto-recovery
- [ ] Test full install flow
- [ ] Test recovery from stale state
- [ ] Document for users
