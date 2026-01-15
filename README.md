# Sebastian's Claude Code Marketplace

Private marketplace for Claude Code plugins.

## Plugins

| Plugin | Description | Version |
|--------|-------------|---------|
| **serena-integration** | Semantic PHP code navigation via Serena LSP | 2.0.0 |
| **jira** | Jira issue management CLI | 2.0.0 |
| **code-nav** | Direct CLI for JetBrains Serena Plugin | 1.0.0 |
| **tmux-cli** | CLI for communicating with other agents in tmux panes | 1.0.0 |
| **agent-browser** | Browser automation for web testing and screenshots | 1.0.0 |
| **cc-docs** | Claude Code documentation expert | 1.0.0 |
| **frontend-test** | Frontend testing with logged-in browser sessions | 1.0.0 |
| **validate-frontmatter** | Validate YAML frontmatter in Claude Code components | 1.0.0 |

## Installation

### 1. Add Marketplace

In Claude Code: `/plugins` → Marketplaces → Add

```
https://github.com/Sebastian80/sebastian-claude-marketplace.git
```

### 2. Install Plugins

`/plugins` → Discover → select plugins to install

## Architecture

Both plugins are **standalone** - no shared daemon or bridge:

```
serena-integration
    bin/serena (MCP client)
        ↓ HTTP/SSE
    Serena MCP server (:9121)
        ↓
    Intelephense LSP

jira
    bin/jira (bash + FastAPI)
        ↓ HTTP
    Self-contained server (:9200)
        ↓
    Jira Cloud/Server API
```

## Plugin Details

### serena-integration

Semantic PHP code navigation via LSP.

**Skills:** `serena`  
**Commands:** `/serena:onboard`, `/serena:load`, `/serena:save`

```bash
serena help                    # List available tools
serena find_symbol --name X    # Find symbol by name
serena get_references --symbol X --file F
```

**Requires:** Serena MCP server running on `:9121`

### jira

Jira issue management with full CLI.

**Skills:** `jira`, `jira-syntax`

```bash
jira help                      # List commands
jira issue PROJ-123            # Get issue
jira search --jql 'assignee = currentUser()'
jira transition PROJ-123 --target "In Progress"
jira comment PROJ-123 --text "Done"
```

**Config:** `~/.env.jira` with `JIRA_URL`, `JIRA_USERNAME`, `JIRA_API_TOKEN`

## Permissions

Add to `~/.claude/settings.local.json`:

```json
{
  "permissions": {
    "allow": [
      "Skill(serena:*)",
      "Skill(jira:*)",
      "Bash(serena:*)",
      "Bash(jira:*)"
    ]
  }
}
```

## License

MIT
