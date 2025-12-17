# Sebastian's Claude Code Marketplace

Private marketplace for Claude Code plugins, agents, and tooling.

## Quick Start

```bash
# Add marketplace
/plugin marketplace add sebastian/sebastian-claude-marketplace

# Install plugins
/plugin install serena-integration@sebastian-marketplace
/plugin install skills-daemon@sebastian-marketplace
```

---

## Terminology

This documentation uses precise terminology to avoid confusion:

| Term | Meaning | Example |
|------|---------|---------|
| **Plugin** | Claude Code marketplace package with skills, commands, agents | `serena-integration`, `jira` |
| **Bridge Plugin** | FastAPI router exposing HTTP endpoints for CLI tools | `scripts/plugin.py` |
| **Skill** | Markdown file with instructions Claude follows | `serena/SKILL.md` |
| **CLI** | Command-line wrapper calling the AI Tool Bridge | `serena`, `jira` |

**Architecture:**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Claude Code Plugin (marketplace package)                                    │
│   ├── skills/skill-name/                                                    │
│   │   ├── manifest.json  → Bridge plugin config (entry_point: scripts:X)    │
│   │   ├── SKILL.md       → Instructions for Claude                          │
│   │   └── scripts/       → Bridge plugin code (FastAPI router)              │
│   ├── commands/          → Slash commands (/onboard)                        │
│   └── agents/            → Subagent definitions                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Ecosystem Overview

| Marketplace | Source | Purpose |
|-------------|--------|---------|
| **sebastian-marketplace** | `Sebastian80/sebastian-claude-marketplace` | Custom plugins |
| **superpowers-dev** | `obra/superpowers` | Core skills (TDD, debugging) |
| **episodic-memory-dev** | `obra/episodic-memory` | Conversation memory |
| **claude-code-plugins** | `anthropics/claude-code` | Official Anthropic |
| **anthropic-agent-skills** | `anthropics/skills` | Official skills |

---

## Plugins

### serena-integration

**Semantic code navigation** for 30+ languages via LSP.

| Component | Details |
|-----------|---------|
| Skills | `serena` - PHP code navigation |
| Commands | `/serena:onboard`, `/serena:load`, `/serena:save` |
| Agents | `framework-explore`, `serena-explore` |
| Backend | `SerenaBackend` (via skills-daemon) |
| CLI | `serena` |

### skills-daemon

**Central FastAPI daemon** unifying all CLI backends.

| Feature | Details |
|---------|---------|
| Port | 9100 |
| Auto-start | On first CLI use |
| Auto-stop | 30min idle |
| API Docs | http://127.0.0.1:9100/docs |

### jira-integration

**Jira issue management** with comprehensive CLI.

| Component | Details |
|-----------|---------|
| Skills | `jira-communication`, `jira-syntax` |
| CLI | `jira` |

### jetbrains-integration

**PhpStorm/IntelliJ IDE integration** via MCP.

| Component | Details |
|-----------|---------|
| Skills | `jetbrains-ide`, `jetbrains-debug` |
| CLI | `jetbrains` (64342), `jetbrains-debug` (63342) |

---

## Creating a Plugin with CLI Backend

This guide shows how to create a plugin that exposes CLI endpoints through the AI Tool Bridge.

### Architecture Overview

```
~/.local/bin/mytool                    # CLI wrapper (bash)
        ↓ calls
bridge mytool <command>                 # Bridge CLI router
        ↓ HTTP :9100
AI Tool Bridge (FastAPI)                # Central daemon
        ↓ routes to
MyToolPlugin                            # Your plugin (FastAPI router)
        ↓ calls
External Service                        # Your backend service (API, MCP, etc.)
```

### Step 1: Create Plugin Structure

```
plugins/my-tool-integration/
├── skills/
│   └── my-tool/
│       ├── manifest.json        # Bridge plugin config
│       ├── SKILL.md             # Instructions for Claude
│       └── scripts/             # Bridge plugin code
│           ├── __init__.py      # Exports MyToolPlugin
│           ├── plugin.py        # Plugin class
│           ├── connector.py     # API connector
│           └── routes/          # FastAPI routes
├── commands/                    # Slash commands (optional)
├── agents/                      # Subagents (optional)
├── bin/                         # CLI wrapper
│   └── my-tool
└── README.md
```

### Step 2: Create Plugin Metadata

**`.claude-plugin/plugin.json`**:
```json
{
  "name": "my-tool-integration",
  "version": "1.0.0",
  "description": "My Tool integration for Claude Code",
  "author": { "name": "Your Name" },
  "license": "MIT"
}
```

### Step 3: Create the Bridge Plugin

The bridge plugin is a FastAPI router that handles HTTP requests from the CLI.

**`skills/my-tool/manifest.json`**:
```json
{
  "name": "my-tool",
  "version": "1.0.0",
  "description": "My Tool integration",
  "entry_point": "scripts:MyToolPlugin",
  "dependencies": [],
  "cli": {
    "command": "mytool"
  }
}
```

**`skills/my-tool/scripts/__init__.py`**:
```python
from .plugin import MyToolPlugin
__all__ = ["MyToolPlugin"]
```

**`skills/my-tool/scripts/plugin.py`**:

```python
"""
My Tool backend for skills daemon.
"""

import sys
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

# Import SkillPlugin base class from skills-daemon
SKILLS_DAEMON = Path(__file__).parent.parent.parent.parent.parent.parent / "skills-daemon"
if str(SKILLS_DAEMON) not in sys.path:
    sys.path.insert(0, str(SKILLS_DAEMON))

from skills_daemon.plugins import SkillPlugin


def success(data: Any) -> dict:
    """Standard success response."""
    return {"success": True, "data": data}


def error(message: str, hint: Optional[str] = None) -> JSONResponse:
    """Standard error response."""
    content = {"success": False, "error": message}
    if hint:
        content["hint"] = hint
    return JSONResponse(status_code=400, content=content)


class MyToolBackend(SkillPlugin):
    """My Tool backend - exposes HTTP endpoints for CLI."""

    @property
    def name(self) -> str:
        return "mytool"  # URL prefix: /mytool/*

    @property
    def description(self) -> str:
        return "My Tool description for /plugins endpoint"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def router(self) -> APIRouter:
        router = APIRouter()

        @router.get("/status")
        async def status():
            """Get current status."""
            return success({"status": "ready", "version": "1.0.0"})

        @router.get("/search")
        async def search(
            query: str,
            limit: int = Query(10),
            include_body: bool = Query(False),
        ):
            """Search for items."""
            # Your implementation here
            results = do_search(query, limit, include_body)
            return success(results)

        @router.post("/create")
        async def create(
            name: str,
            content: str,
        ):
            """Create a new item."""
            # Your implementation here
            result = do_create(name, content)
            return success(result)

        @router.get("/item")
        async def get_item(id: str):
            """Get item by ID."""
            item = fetch_item(id)
            if not item:
                return error(f"Item not found: {id}", "Check the ID and try again")
            return success(item)

        return router

    async def startup(self) -> None:
        """Called when daemon starts. Initialize connections here."""
        # Example: connect to external service
        pass

    async def shutdown(self) -> None:
        """Called when daemon stops. Cleanup here."""
        # Example: close connections
        pass

    def health_check(self) -> dict[str, Any]:
        """Return health status for /health endpoint."""
        return {"status": "ok", "connected": True}
```

### Step 4: Create CLI Wrapper

**`bin/my-tool`**:

```bash
#!/bin/bash
# My Tool CLI - wrapper for skills-daemon
# Usage: my-tool <command> [options]

if [[ "$1" == "--help" || "$1" == "-h" || -z "$1" ]]; then
    cat << 'EOF'
My Tool - Description

Usage:
    my-tool <command> [options]

Commands:
    status              Show current status
    search              Search for items
    create              Create new item
    item                Get item by ID

Options:
    --query X           Search query
    --limit N           Limit results (default: 10)
    --include-body      Include item body in results
    --name X            Item name (for create)
    --content X         Item content (for create)
    --id X              Item ID (for item command)

Examples:
    my-tool status
    my-tool search --query "test" --limit 5
    my-tool create --name "foo" --content "bar"
    my-tool item --id "abc123"
EOF
    exit 0
fi

exec skills-client mytool "$@"
```

Make executable:
```bash
chmod +x plugins/my-tool-integration/bin/my-tool
```

### Step 5: Create Symlink

```bash
ln -sf ~/.claude/plugins/marketplaces/sebastian-marketplace/plugins/my-tool-integration/bin/my-tool ~/.local/bin/my-tool
```

### Step 6: Add Permissions

**`~/.claude/settings.json`**:
```json
{
  "permissions": {
    "allow": [
      "Skill(my-tool-integration:*)",
      "Bash(my-tool:*)"
    ]
  }
}
```

### Step 7: Create Skill (Optional)

If Claude should use your tool directly:

**`skills/my-tool/SKILL.md`**:

```markdown
---
name: my-tool
description: "Use when user needs to interact with My Tool"
---

# My Tool Skill

## Quick Reference

| Task | Command |
|------|---------|
| Check status | `my-tool status` |
| Search items | `my-tool search --query X` |
| Create item | `my-tool create --name X --content Y` |

## When to Use

Use this tool when:
- User asks about My Tool items
- User wants to search or create items
```

### Step 8: Test

```bash
# Check daemon discovers your backend
skills-client plugins

# Test your endpoints
my-tool status
my-tool search --query "test"
```

### Response Format Convention

All backends should return responses in this format:

```python
# Success
{"success": True, "data": <result>}

# Error
{"success": False, "error": "message", "hint": "optional hint"}
```

The CLI client formats these automatically for terminal display.

### HTTP Methods

| Use Case | Method | Trigger |
|----------|--------|---------|
| Read data | GET | Default |
| Write data | POST | Params: `content`, `code`, `new_name` |
| Specific commands | POST | Commands: `create`, `write`, `delete`, `rename` |

### Plugin Discovery

The AI Tool Bridge auto-discovers plugins from:

1. `~/.claude/plugins/marketplaces/**/manifest.json`
2. `~/.claude/plugins/local/**/manifest.json`

Your `manifest.json` must define `entry_point: "scripts:YourPlugin"` pointing to a class implementing `PluginProtocol`.

---

## Directory Structure

```
sebastian-marketplace/
├── plugins/
│   ├── ai-tool-bridge/              # Central daemon
│   │   ├── src/ai_tool_bridge/      # FastAPI app
│   │   └── bin/bridge               # CLI
│   │
│   ├── serena-integration/
│   │   ├── skills/serena/
│   │   │   ├── manifest.json        # entry_point: scripts:SerenaPlugin
│   │   │   ├── SKILL.md
│   │   │   └── scripts/             # Bridge plugin code
│   │   ├── commands/
│   │   ├── agents/
│   │   └── bin/serena
│   │
│   ├── jira/
│   │   ├── skills/jira/
│   │   │   ├── manifest.json        # entry_point: scripts:JiraPlugin
│   │   │   ├── SKILL.md
│   │   │   └── scripts/             # Bridge plugin code
│   │   └── skills/jira-syntax/
│   │
│   └── jetbrains-integration/
│       ├── skills/
│       ├── bin/
│       └── scripts/                 # MCP clients
│
└── docs/
```

---

## CLI Reference

### serena

```bash
serena status                           # Project status
serena activate --project PATH          # Activate project
serena find --pattern X --kind class    # Find symbols
serena refs --symbol X --file F         # Find references
serena search --pattern X               # Regex search
serena overview --file F                # File structure
serena recipe --name X                  # Pre-built searches
serena memory/list                      # List memories
serena memory/read --name X             # Read memory
serena memory/write --name X --content Y
```

### jira

```bash
jira issue get HMKG-123
jira search query 'assignee = currentUser()'
jira transition do HMKG-123 'In Progress'
jira comment add HMKG-123 "message"
jira create --project HMKG --type Bug
jira sprint list
```

### jetbrains

```bash
jetbrains files <keyword>
jetbrains search <text>
jetbrains problems <file>
jetbrains reformat <file>
```

### jetbrains-debug

```bash
jetbrains-debug bp set <file> <line>
jetbrains-debug start <config>
jetbrains-debug step over|into|out
jetbrains-debug vars
jetbrains-debug eval <expr>
```

---

## Ports Reference

| Port | Service | Protocol |
|------|---------|----------|
| 9100 | Skills Daemon | HTTP/REST |
| 9121 | Serena MCP Server | MCP |
| 64342 | JetBrains IDE MCP | HTTP/SSE |
| 63342 | JetBrains Debugger MCP | HTTP/SSE |

---

## Installation

### 1. Add marketplace

```bash
/plugin marketplace add sebastian/sebastian-claude-marketplace
```

### 2. Install plugins

```bash
/plugin install serena-integration@sebastian-marketplace
/plugin install skills-daemon@sebastian-marketplace
```

### 3. Create CLI symlinks

```bash
ln -sf ~/.claude/plugins/marketplaces/sebastian-marketplace/plugins/serena-integration/bin/serena ~/.local/bin/serena
ln -sf ~/.claude/plugins/marketplaces/sebastian-marketplace/plugins/jetbrains-integration/bin/jetbrains ~/.local/bin/jetbrains
ln -sf ~/.claude/plugins/marketplaces/sebastian-marketplace/plugins/jetbrains-integration/bin/jetbrains-debug ~/.local/bin/jetbrains-debug
```

### 4. Configure permissions

```json
{
  "permissions": {
    "allow": [
      "Skill(serena:*)",
      "Skill(jira-integration:*)",
      "Skill(jetbrains-integration:*)",
      "Bash(serena:*)",
      "Bash(jira:*)",
      "Bash(jetbrains:*)",
      "Bash(jetbrains-debug:*)"
    ]
  },
  "enabledPlugins": {
    "serena-integration@sebastian-marketplace": true,
    "skills-daemon@sebastian-marketplace": true
  }
}
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Connection refused" | Run `skills-daemon start` |
| Backend not found | Check `skills-client plugins` |
| Empty results | Run `serena status` - verify project active |
| JetBrains failed | PhpStorm running? MCP enabled? |

### Logs

```bash
skills-daemon logs                      # Tail logs
tail -f /tmp/skills-daemon.log          # Direct
cat /tmp/skills-daemon.log | jq .       # Parse JSON
```

---

## Creating Components

```bash
./scripts/new-plugin.sh my-plugin       # Full plugin
./scripts/new-skill.sh my-skill         # Skill only
./scripts/new-agent.sh my-agent         # Agent only
./scripts/new-command.sh my-command     # Command only
```

---

## License

MIT
