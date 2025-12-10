# Skills Daemon Installation & Lifecycle Design

**Date:** 2025-12-10
**Status:** ✅ Implemented
**Author:** Sebastian + Claude

## Overview

This document describes the architecture for:
1. Automated dependency installation when plugins register
2. Prevention of stale daemon processes
3. Proper installation flow for the daemon
4. CLI help generation from single source of truth
5. Zero-sudo, fully user-space operation

## Design Principles

| Principle | Implementation |
|-----------|----------------|
| **Single source of truth** | FastAPI defines API + generates CLI help |
| **Everything through daemon** | All CLI commands route through daemon |
| **Self-healing** | Client detects stale daemon, auto-recovers |
| **Lazy setup** | First use triggers installation, no explicit install step |
| **Zero sudo** | All files in user home directory |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         ARCHITECTURE                                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ~/.local/bin/jira  (trivial wrapper)                               │
│        │                                                             │
│        ▼                                                             │
│  skills-client                                                       │
│        │                                                             │
│        ├── --help?  → GET /jira/help (generated from FastAPI)       │
│        ├── ensure_runtime()                                         │
│        ├── ensure_deps()                                            │
│        ├── ensure_daemon()                                          │
│        └── request()                                                │
│        │                                                             │
│        ▼                                                             │
│  DAEMON (:9100)                                                      │
│        │                                                             │
│        ├── GET  /health         → Status + validity checks          │
│        ├── GET  /plugins        → List plugins                      │
│        ├── GET  /{plugin}/help  → Generated CLI help                │
│        ├── GET  /{plugin}/commands → List commands                  │
│        ├── *    /{plugin}/*     → Plugin endpoints                  │
│        └── GET  /docs           → Swagger UI                        │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Directory Structure

```
~/.local/share/skills-daemon/          # Stable runtime (survives updates)
├── venv/                              # Python virtual environment
├── logs/                              # Log files (rotated)
│   └── daemon.log
└── state/
    ├── daemon.pid                     # PID file
    └── plugins.json                   # Registered plugins cache

~/.local/bin/                          # CLI entry points
├── skills-daemon                      # Daemon control
├── skills-client                      # Generic client
├── jira                               # Plugin CLI (trivial wrapper)
└── serena                             # Plugin CLI (trivial wrapper)

~/.config/skills-daemon/               # Configuration (optional)
└── config.toml

~/.claude/plugins/.../skills-daemon/   # Source code only (never run from here)
~/.claude/plugins/.../jira-integration/
└── skills/jira-communication/scripts/skills_plugin/
    ├── __init__.py                    # Plugin implementation
    └── manifest.json                  # Dependencies + metadata
```

---

## Documentation Separation

| Document | Audience | Purpose | Location |
|----------|----------|---------|----------|
| **SKILL.md** | Claude (AI) | Behavioral instructions, rules, examples | Plugin skill dir |
| **manifest.json** | Daemon/Tooling | Dependencies, version, metadata | skills_plugin/ |
| **FastAPI endpoints** | Everyone | API definition (source of truth) | Plugin code |
| **`/help` endpoint** | CLI users | Generated from FastAPI | Daemon |
| **`/docs` endpoint** | Developers | Swagger UI | Daemon |

**Key insight:** CLI help is NOT in SKILL.md (that's for AI). CLI help is generated from FastAPI metadata.

---

## Plugin manifest.json Schema

```json
{
  "name": "jira",
  "version": "1.0.0",
  "description": "Jira issue tracking integration",
  "dependencies": [
    "atlassian-python-api>=4.0",
    "httpx>=0.25"
  ],
  "daemon_version": ">=1.0.0",
  "cli": {
    "examples": [
      "jira search \"assignee = currentUser()\"",
      "jira issue get PROJ-123"
    ]
  }
}
```

**Fields:**
- `name` - Plugin identifier (required)
- `version` - Semver version (required)
- `description` - Short description (required)
- `dependencies` - Python packages to install (optional)
- `daemon_version` - Compatible daemon versions (optional)
- `cli.examples` - Example commands for help output (optional)

---

## CLI Help Generation

### Source: FastAPI Metadata

```python
class JiraPlugin(SkillPlugin):
    name = "jira"
    description = "Jira issue tracking integration"

    @router.get("/search", summary="Search issues", description="Search for issues using JQL query language")
    async def search(
        query: str = Query(..., description="JQL query string"),
        max_results: int = Query(50, description="Maximum results to return"),
    ):
        """Search for Jira issues using JQL.

        Supports full JQL syntax including functions like currentUser().
        """
        ...
```

### Generated Output

```
$ jira --help

jira - Jira issue tracking integration

Commands:
  search      Search for issues using JQL
  issue       Get or update issue details
  create      Create new issue
  transition  Change issue status
  comment     Add comment to issue
  worklog     Log time on issue

Examples:
  jira search "assignee = currentUser()"
  jira issue get PROJ-123

Run 'jira <command> --help' for command details.
```

```
$ jira search --help

jira search - Search for issues using JQL

Search for Jira issues using JQL. Supports full JQL syntax
including functions like currentUser().

Options:
  --query        JQL query string (required)
  --max-results  Maximum results to return (default: 50)

Example:
  jira search --query "project = PROJ AND status = Open"
```

### Implementation: /help Endpoint

```python
@app.get("/{plugin}/help")
async def plugin_help(plugin: str, command: str | None = None) -> dict:
    """Generate CLI help from FastAPI metadata."""
    plugin_obj = registry.get(plugin)
    if not plugin_obj:
        return {"error": f"Unknown plugin: {plugin}"}

    if command:
        return generate_command_help(plugin_obj, command)
    else:
        return generate_plugin_help(plugin_obj)


def generate_plugin_help(plugin: SkillPlugin) -> dict:
    """Generate help for entire plugin."""
    commands = []
    for route in plugin.router.routes:
        if hasattr(route, 'summary'):
            commands.append({
                "name": route.path.strip('/'),
                "summary": route.summary or route.name,
            })

    # Load examples from manifest if available
    manifest = load_manifest(plugin.name)
    examples = manifest.get("cli", {}).get("examples", [])

    return {
        "name": plugin.name,
        "description": plugin.description,
        "commands": commands,
        "examples": examples,
    }
```

---

## CLI Wrapper Pattern

### Trivial Wrapper (Recommended)

```bash
#!/bin/bash
# ~/.local/bin/jira
exec skills-client jira "$@"
```

### skills-client Help Handling

```python
def main():
    args = sys.argv[1:]

    # Handle --help at any position
    if "--help" in args or "-h" in args:
        plugin = args[0] if args and not args[0].startswith("-") else None
        command = args[1] if len(args) > 1 and not args[1].startswith("-") else None

        if plugin:
            show_help(plugin, command)
        else:
            show_client_help()
        return

    # Normal flow
    ensure_daemon()
    # ... rest of request handling


def show_help(plugin: str, command: str | None):
    """Fetch and display help from daemon."""
    ensure_daemon()

    if command:
        result = request(f"{plugin}/help", {"command": command})
    else:
        result = request(f"{plugin}/help", {})

    print(format_help(result))
```

---

## Self-Healing Architecture

### Prevention: Stable Runtime Location

```
BEFORE (fragile):
~/.claude/plugins/.../skills-daemon/.venv/  ← deleted on update

AFTER (stable):
~/.local/share/skills-daemon/venv/          ← survives updates
```

### Detection: Enhanced Health Check

```python
@app.get("/health")
async def health() -> dict:
    return {
        "status": "running",
        "version": __version__,
        "cwd_valid": check_cwd_valid(),
        "venv_valid": check_venv_valid(),
        "uptime_seconds": get_uptime(),
        "plugins": registry.names(),
        "plugin_health": get_plugin_health(),
    }


def check_cwd_valid() -> bool:
    """Check if working directory still exists."""
    try:
        cwd = Path.cwd()
        # Check for (deleted) marker in /proc
        proc_cwd = Path("/proc/self/cwd").resolve()
        return cwd.exists() and "(deleted)" not in str(proc_cwd)
    except:
        return False


def check_venv_valid() -> bool:
    """Check if venv is intact."""
    venv = Path.home() / ".local/share/skills-daemon/venv"
    return (venv / "bin/python").exists()
```

### Recovery: Client-Side Auto-Heal

```python
# In skills-client
def ensure_daemon() -> bool:
    """Ensure daemon is running and healthy."""

    # Quick health check
    try:
        health = request_raw("/health", timeout=1)
        if health.get("cwd_valid") == False or health.get("venv_valid") == False:
            print("Daemon unhealthy, recovering...", file=sys.stderr)
            recover_daemon()
            return ensure_daemon()  # Retry
        return True
    except:
        pass

    # Daemon not running - start it
    return start_daemon()


def recover_daemon():
    """Kill stale daemon and clean up."""
    # Graceful shutdown attempt
    try:
        request_raw("/shutdown", method="POST", timeout=2)
        time.sleep(1)
    except:
        pass

    # Force kill if still running
    subprocess.run(["pkill", "-f", "skills_daemon.main"], capture_output=True)
    time.sleep(0.5)
```

---

## Dependency Management

### Startup Flow

```python
async def lifespan(app: FastAPI):
    """Application lifecycle."""

    # 1. Ensure runtime directory exists
    ensure_runtime_dirs()

    # 2. Sync plugin dependencies
    await sync_plugin_dependencies()

    # 3. Normal startup
    lifecycle.write_pid_file()
    lifecycle.setup_signal_handlers()

    # 4. Start plugins
    for plugin in registry.all():
        await plugin.startup()

    yield  # App runs

    # Shutdown...
```

### Dependency Sync

```python
async def sync_plugin_dependencies():
    """Install missing dependencies from plugin manifests."""

    all_deps = set()

    # Collect dependencies from all manifests
    for manifest_path in discover_manifests():
        manifest = json.loads(manifest_path.read_text())
        deps = manifest.get("dependencies", [])
        all_deps.update(deps)

    if not all_deps:
        return

    # Check what's already installed
    installed = get_installed_packages()
    missing = [d for d in all_deps if not is_satisfied(d, installed)]

    if missing:
        logger.info(f"Installing dependencies: {missing}")
        result = subprocess.run(
            ["uv", "pip", "install", *missing],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            logger.error(f"Dependency install failed: {result.stderr}")
```

---

## Logging

### Configuration

- **Library:** structlog
- **Location:** `~/.local/share/skills-daemon/logs/daemon.log`
- **Rotation:** 5MB max, 3 backups
- **Format:** JSON (file), human-readable (console)

### Implementation

```python
import structlog

def setup_logging():
    """Configure structlog for daemon."""

    log_dir = Path.home() / ".local/share/skills-daemon/logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
    )

    # File handler with rotation
    handler = RotatingFileHandler(
        log_dir / "daemon.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
    )

    logging.basicConfig(
        handlers=[handler],
        level=logging.INFO,
    )
```

---

## Lazy Installation Flow

No explicit install command needed. First use triggers setup:

```
User runs: jira search "project = PROJ"
                │
                ▼
        skills-client jira search ...
                │
                ▼
        ensure_runtime()
        ┌───────────────────────────────────┐
        │ ~/.local/share/skills-daemon/     │
        │ exists?                           │
        │   No → Create dirs                │
        └───────────────────────────────────┘
                │
                ▼
        ensure_venv()
        ┌───────────────────────────────────┐
        │ venv exists and valid?            │
        │   No → uv venv + install deps     │
        └───────────────────────────────────┘
                │
                ▼
        ensure_daemon()
        ┌───────────────────────────────────┐
        │ Daemon running and healthy?       │
        │   No → Start daemon               │
        │   Unhealthy → Recover + restart   │
        └───────────────────────────────────┘
                │
                ▼
        HTTP request to daemon
                │
                ▼
        Return result to user
```

---

## Implementation Checklist

### Phase 1: Runtime Infrastructure
- [ ] Create `~/.local/share/skills-daemon/` structure
- [ ] Move venv to stable location
- [ ] Add structlog logging
- [ ] Add `cwd_valid` / `venv_valid` to /health

### Phase 2: Dependency Management
- [ ] Create manifest.json schema
- [ ] Add manifest.json to jira plugin
- [ ] Add manifest.json to serena plugin
- [ ] Implement `sync_plugin_dependencies()`
- [ ] Test dependency installation on startup

### Phase 3: CLI Help Generation
- [ ] Add `GET /{plugin}/help` endpoint
- [ ] Add `GET /{plugin}/commands` endpoint
- [ ] Implement help text formatter
- [ ] Update skills-client to handle --help
- [ ] Test help generation

### Phase 4: Self-Healing
- [ ] Implement `check_cwd_valid()`
- [ ] Implement `check_venv_valid()`
- [ ] Add recovery logic to skills-client
- [ ] Test recovery from stale state

### Phase 5: CLI Wrappers
- [ ] Simplify jira wrapper (delegate to skills-client)
- [ ] Simplify serena wrapper (delegate to skills-client)
- [ ] Update skills-daemon wrapper
- [ ] Test all CLI entry points

### Phase 6: Documentation
- [ ] Update README with new architecture
- [ ] Document manifest.json format
- [ ] Add troubleshooting guide

---

## Summary

| Component | Decision |
|-----------|----------|
| **Dependency declaration** | manifest.json in skills_plugin/ |
| **CLI help source** | Generated from FastAPI (single source of truth) |
| **SKILL.md purpose** | AI instructions for Claude (unchanged) |
| **Installation flow** | Lazy setup on first use |
| **Runtime location** | ~/.local/share/skills-daemon/ |
| **Logging** | structlog to ~/.local/share/skills-daemon/logs/ |
| **Self-healing** | Client-side detection + recovery |
| **CLI wrappers** | Trivial, delegate to skills-client |
| **Daemon hooks** | Not needed (YAGNI) |
