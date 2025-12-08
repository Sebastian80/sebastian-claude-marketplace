# JetBrains Integration Plugin

Claude Code plugin for PhpStorm/IntelliJ IDE integration via MCP (Model Context Protocol).

## Features

| Component | Description |
|-----------|-------------|
| `jetbrains` CLI | 20 IDE tools (files, search, problems, refactoring) |
| `jetbrains-debug` CLI | 22 debugger tools (breakpoints, stepping, variables) |
| `jetbrains-ide` skill | IDE tools usage guide |
| `jetbrains-debug` skill | Debugging workflow guide |
| `explore-js.py` hook | Explore agent context for JS projects |

## Requirements

### PhpStorm Setup

#### 1. IDE Version

- **PhpStorm 2025.2+** (or IntelliJ IDEA with PHP plugin)
- MCP support is built into recent versions

#### 2. Install Required Plugins

1. `Settings → Plugins → Marketplace`
2. Install these plugins:
   - **[Debugger MCP Server](https://plugins.jetbrains.com/plugin/29233-debugger-mcp-server)** - Required for `jetbrains-debug` CLI (port 63342)
3. Restart IDE after installation

**Note:** The IDE MCP server (port 64342) is built-in since PhpStorm 2025.2 - no plugin needed.

#### 3. Enable MCP Server

1. `Settings → Tools → MCP Server`
2. Click **"Enable MCP Server"**
3. The IDE tools server runs on port `64342`
4. The debugger server (from plugin) runs on port `63342`

#### 4. Xdebug Setup (for debugging)

Install Xdebug in your PHP environment:

```bash
# Docker example
pecl install xdebug
docker-php-ext-enable xdebug
```

Configure `php.ini`:

```ini
[xdebug]
xdebug.mode=debug
xdebug.client_host=host.docker.internal  # or 172.17.0.1 for Linux
xdebug.client_port=9003
xdebug.start_with_request=trigger
xdebug.idekey=PHPSTORM
```

#### 5. Debug Configuration in PhpStorm

1. `Run → Edit Configurations`
2. Click `+` → **PHP Remote Debug**
3. Name: `PHP Debug`
4. IDE key: `PHPSTORM`
5. Configure server:
   - `...` next to Servers
   - Add server with path mappings (local → container paths)

#### 6. PHP Interpreter (optional but recommended)

1. `Settings → PHP`
2. Configure CLI Interpreter (Docker/Remote)
3. Enables better code analysis

### Verify Setup

```bash
# Check IDE MCP server (port 64342)
curl -s http://127.0.0.1:64342/sse -H "Accept: text/event-stream" | head -2
# Should show: event: endpoint / data: /message?sessionId=...

# Check Debugger MCP server (port 63342)
curl -s http://127.0.0.1:63342/debugger-mcp/sse -H "Accept: text/event-stream" | head -2
# Should show: event: endpoint / data: /debugger-mcp?sessionId=...

# Test CLI
jetbrains tools
jetbrains-debug tools
```

## Installation

### 1. Create symlinks

```bash
ln -sf ~/.claude/plugins/marketplaces/sebastian-marketplace/plugins/jetbrains-integration/bin/jetbrains ~/.local/bin/jetbrains
ln -sf ~/.claude/plugins/marketplaces/sebastian-marketplace/plugins/jetbrains-integration/bin/jetbrains-debug ~/.local/bin/jetbrains-debug
```

### 2. Add permissions to `~/.claude/settings.json`

```json
{
  "permissions": {
    "allow": [
      "Bash(/home/USER/.local/bin/jetbrains:*)",
      "Bash(jetbrains:*)",
      "Bash(/home/USER/.local/bin/jetbrains-debug:*)",
      "Bash(jetbrains-debug:*)"
    ]
  }
}
```

### 3. Enable plugin

```json
{
  "enabledPlugins": {
    "jetbrains-integration@sebastian-marketplace": true
  }
}
```

### 4. Register hook (optional)

```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "Task",
      "hooks": [{
        "type": "command",
        "command": "python3 ~/.claude/plugins/marketplaces/sebastian-marketplace/plugins/jetbrains-integration/hooks/explore-js.py"
      }]
    }]
  }
}
```

## CLI Commands

### `jetbrains` - IDE Tools

```bash
jetbrains files <keyword>           # Find files by name
jetbrains glob <pattern>            # Find by glob pattern
jetbrains search <text>             # Search in files
jetbrains regex <pattern>           # Regex search
jetbrains tree <dir>                # Directory tree
jetbrains read <file>               # Read file contents
jetbrains create <file>             # Create new file
jetbrains problems <file>           # Get errors/warnings
jetbrains symbol <file> <ln> <col>  # Symbol info
jetbrains open <file>               # Open in editor
jetbrains open-files                # List open files
jetbrains reformat <file>           # Reformat file
jetbrains replace <f> <old> <new>   # Replace text
jetbrains rename <f> <sym> <new>    # Rename symbol
jetbrains configs                   # List run configs
jetbrains run <config>              # Run config
jetbrains deps                      # Dependencies
jetbrains modules                   # Project modules
jetbrains repos                     # VCS repositories
jetbrains terminal <cmd>            # IDE terminal
```

### `jetbrains-debug` - Debugger

```bash
# Breakpoints
jetbrains-debug bp set <file> <line>   # Set breakpoint
jetbrains-debug bp list                # List breakpoints
jetbrains-debug bp remove <id>         # Remove breakpoint
jetbrains-debug bp clear               # Clear all

# Session
jetbrains-debug configs                # Debug configurations
jetbrains-debug start <config>         # Start session
jetbrains-debug stop                   # Stop session
jetbrains-debug sessions               # Active sessions
jetbrains-debug status                 # Current status

# Execution
jetbrains-debug step over              # Step over
jetbrains-debug step into              # Step into
jetbrains-debug step out               # Step out
jetbrains-debug continue               # Continue
jetbrains-debug pause                  # Pause
jetbrains-debug run-to <file> <line>   # Run to line

# Inspection
jetbrains-debug vars                   # Variables
jetbrains-debug eval <expr>            # Evaluate
jetbrains-debug set <var> <val>        # Set variable
jetbrains-debug stack                  # Stack trace
jetbrains-debug frame <idx>            # Select frame
jetbrains-debug threads                # List threads
jetbrains-debug source                 # Source context
```

## Skills

### `jetbrains-ide`

IDE tools guide. Invoke with:
```
skill: jetbrains-ide
```

### `jetbrains-debug`

Debugging workflow guide. Invoke with:
```
skill: jetbrains-debug
```

## Architecture

```
┌─────────────────┐     HTTP/SSE      ┌──────────────────┐
│  jetbrains CLI  │ ◄───────────────► │  PhpStorm MCP    │
│  (port 64342)   │                   │  (20 IDE tools)  │
└─────────────────┘                   └──────────────────┘

┌─────────────────┐     HTTP/SSE      ┌──────────────────┐
│ jetbrains-debug │ ◄───────────────► │  PhpStorm MCP    │
│  (port 63342)   │                   │  (22 dbg tools)  │
└─────────────────┘                   └──────────────────┘
```

## File Structure

```
jetbrains-integration/
├── bin/
│   ├── jetbrains              # IDE CLI wrapper
│   └── jetbrains-debug        # Debug CLI wrapper
├── scripts/
│   ├── jetbrains_mcp.py       # IDE MCP client
│   ├── jetbrains-cli          # IDE CLI (20 commands)
│   ├── jetbrains_debugger_mcp.py  # Debug MCP client
│   └── jetbrains-debug-cli    # Debug CLI (22 commands)
├── hooks/
│   └── explore-js.py          # Explore agent hook
├── skills/
│   ├── jetbrains-ide/
│   │   └── SKILL.md           # IDE tools skill
│   └── jetbrains-debug/
│       └── SKILL.md           # Debugging skill
└── README.md
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Connection failed | PhpStorm running? MCP enabled? |
| Empty results | Correct project open in IDE? |
| Breakpoint not hit | Xdebug configured? Path mapping correct? |
| No debug configs | Create PHP Remote Debug config |

## Related

- **serena-integration** - PHP/YAML semantic navigation (LSP)
- **jira-integration** - Jira issue management
