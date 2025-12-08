# Serena Integration Plugin

Claude Code integration with Serena LSP for PHP/YAML code navigation.

## Features

- **serena skill**: Core Serena usage with CLI wrapper
- **serena-debug skill**: Troubleshooting Serena issues
- **php-explore hook**: Automatically injects Serena context into Explore agent for PHP projects
- **Slash commands**: `/serena:onboard`, `/serena:load`, `/serena:save`
- **Agents**: serena-explore, serena-debug, framework-explore

## When This Plugin Activates

The explore hook triggers for projects with:
- `composer.json` present (PHP projects)

## Setup

### 1. Enable Plugin

Already enabled via marketplace.

### 2. Create CLI Wrapper

Create `~/.local/bin/serena`:

```bash
#!/bin/bash
# Tiny wrapper - all logic in plugin
exec ~/.claude/plugins/marketplaces/sebastian-marketplace/plugins/serena-integration/bin/serena "$@"
```

Make executable: `chmod +x ~/.local/bin/serena`

### 3. Register Hook in settings.json

Add to `~/.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Task",
        "hooks": [{
          "type": "command",
          "command": "python3 /home/sebastian/.claude/plugins/marketplaces/sebastian-marketplace/plugins/serena-integration/hooks/explore-php-yaml.py"
        }]
      }
    ]
  }
}
```

### 4. Add Permissions

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
serena find Customer --kind class    # Find symbol
serena refs "Customer/getName" file  # Find references
serena overview file.php             # File structure
serena status                        # Check connection
serena memory list                   # List memories
```

## Skills

### serena

Core Serena usage - semantic code navigation via LSP.

### serena-debug

Troubleshooting when Serena commands fail.
