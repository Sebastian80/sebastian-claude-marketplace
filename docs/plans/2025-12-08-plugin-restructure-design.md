# Plugin Restructure: serena-integration & jetbrains-integration

## Problem

The current Explore agent hook injects Serena context for all code navigation, but:
- Serena LSP (Intelephense) excels at PHP/YAML
- JetBrains MCP handles JS better, especially legacy AMD-style
- Need separate, focused contexts for each tool

## Solution

Rename `serena` plugin to `serena-integration`, create new `jetbrains-integration` plugin.
Each plugin is self-contained with hooks that inject the right context based on file types.

## Final Structure

### serena-integration (renamed from serena)

```
serena-integration/
├── bin/
│   └── serena                     # Full CLI wrapper
├── hooks/
│   └── explore-php-yaml.py        # Explore enhancement for PHP/YAML
├── skills/
│   ├── serena/                    # Core Serena usage (existing)
│   ├── serena-debug/              # Debug skill (existing)
│   └── php-explore/               # NEW: When to use Serena for exploration
├── agents/
│   ├── framework-explore.md       # existing
│   ├── serena-debug.md            # existing
│   └── serena-explore.md          # existing
├── commands/
│   ├── load.md                    # existing
│   ├── onboard.md                 # existing
│   └── save.md                    # existing
├── docs/
└── README.md                      # Setup instructions
```

### jetbrains-integration (new)

```
jetbrains-integration/
├── bin/
│   └── jetbrains                  # CLI wrapper (if needed)
├── hooks/
│   └── explore-js.py              # Explore enhancement for JS
├── skills/
│   ├── jetbrains-debug/           # Moved from serena (existing)
│   └── js-explore/                # NEW: When to use JetBrains for exploration
├── docs/
└── README.md                      # Setup instructions
```

## Hook Logic

### explore-php-yaml.py (serena-integration)

Triggers when:
- Tool: Task, subagent_type: Explore
- Project has: composer.json OR *.php files OR *.yaml files

Injects context about:
- `find_symbol` for class/method lookup
- `find_referencing_symbols` for callers
- `get_symbols_overview` for file structure
- When to use Serena vs grep

### explore-js.py (jetbrains-integration)

Triggers when:
- Tool: Task, subagent_type: Explore
- Project has: package.json OR *.js files (without modern TS setup)

Injects context about:
- `mcp__jetbrains__search_in_files_by_text` for text search
- `mcp__jetbrains__get_symbol_info` for symbol documentation
- `mcp__jetbrains__find_files_by_name_keyword` for file lookup
- When to use JetBrains MCP vs grep

## External Configuration

### ~/.local/bin/serena (tiny wrapper)

```bash
#!/bin/bash
exec ~/.claude/plugins/marketplaces/sebastian-marketplace/plugins/serena-integration/bin/serena "$@"
```

### ~/.local/bin/jetbrains (tiny wrapper, if needed)

```bash
#!/bin/bash
exec ~/.claude/plugins/marketplaces/sebastian-marketplace/plugins/jetbrains-integration/bin/jetbrains "$@"
```

### ~/.claude/settings.json hooks

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
      },
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

### Permissions

```json
{
  "allow": [
    "Bash(/home/sebastian/.local/bin/serena:*)",
    "Bash(serena:*)",
    "Skill(serena-integration:*)",
    "Skill(jetbrains-integration:*)"
  ]
}
```

## Migration Steps

1. Rename `plugins/serena/` → `plugins/serena-integration/`
2. Create `plugins/serena-integration/bin/` with full CLI wrapper
3. Create `plugins/serena-integration/hooks/explore-php-yaml.py`
4. Move `jetbrains-debug` skill to new `plugins/jetbrains-integration/`
5. Create `plugins/jetbrains-integration/hooks/explore-js.py`
6. Update `~/.local/bin/serena` to point to new location
7. Update `~/.claude/settings.json` hook paths
8. Remove old `~/.claude/hooks/extend-explore.py`
9. Update `~/.claude/settings.json` enabled plugins

## One-Time Setup (README)

After cloning/updating the marketplace:

```bash
# Update serena wrapper (already exists, just update path)
cat > ~/.local/bin/serena << 'EOF'
#!/bin/bash
exec ~/.claude/plugins/marketplaces/sebastian-marketplace/plugins/serena-integration/bin/serena "$@"
EOF
chmod +x ~/.local/bin/serena

# Hooks and permissions are in settings.json (update paths if needed)
```
