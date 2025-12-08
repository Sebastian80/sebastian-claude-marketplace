# JetBrains Integration Plugin

Claude Code integration with JetBrains MCP for JavaScript code navigation.

## Features

- **js-explore hook**: Automatically injects JetBrains MCP context into Explore agent for JS projects
- **jetbrains-debug skill**: Interactive debugging with PhpStorm

## When This Plugin Activates

The explore hook triggers for projects with:
- `package.json` present
- No `composer.json` (PHP projects use Serena instead)

## Setup

### 1. Enable Plugin

Already enabled via marketplace.

### 2. Register Hook in settings.json

Add to `~/.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Task",
        "hooks": [{
          "type": "command",
          "command": "python3 /home/sebastian/.claude/plugins/marketplaces/sebastian-marketplace/plugins/jetbrains-integration/hooks/explore-js.py"
        }]
      }
    ]
  }
}
```

## JetBrains MCP Tools

| Tool | Purpose |
|------|---------|
| `mcp__jetbrains__find_files_by_name_keyword` | Find files by name |
| `mcp__jetbrains__search_in_files_by_text` | Text search in files |
| `mcp__jetbrains__search_in_files_by_regex` | Regex search |
| `mcp__jetbrains__get_symbol_info` | Get symbol documentation |

## Skills

### jetbrains-debug

Interactive debugging with PhpStorm. Use for:
- Setting breakpoints
- Stepping through code
- Inspecting variables
- Evaluating expressions
