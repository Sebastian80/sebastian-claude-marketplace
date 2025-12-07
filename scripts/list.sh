#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== Sebastian's Claude Code Marketplace ==="
echo ""

echo "## Standalone Skills"
for skill_dir in "$ROOT_DIR"/skills/*/; do
    if [[ -d "$skill_dir" ]]; then
        skill_name=$(basename "$skill_dir")
        skill_file="$skill_dir/SKILL.md"
        if [[ -f "$skill_file" ]]; then
            desc=$(grep "^description:" "$skill_file" | sed 's/description:\s*//' | head -c 60)
            echo "  - $skill_name: $desc"
        fi
    fi
done

echo ""
echo "## Plugins"
for plugin_dir in "$ROOT_DIR"/plugins/*/; do
    if [[ -d "$plugin_dir" ]]; then
        plugin_name=$(basename "$plugin_dir")
        echo "  - $plugin_name"

        # Count components
        cmd_count=$(find "$plugin_dir/commands" -name "*.md" 2>/dev/null | wc -l)
        agent_count=$(find "$plugin_dir/agents" -name "*.md" 2>/dev/null | wc -l)
        skill_count=$(find "$plugin_dir/skills" -maxdepth 1 -type d 2>/dev/null | wc -l)
        ((skill_count--)) || true

        [[ $cmd_count -gt 0 ]] && echo "      Commands: $cmd_count"
        [[ $agent_count -gt 0 ]] && echo "      Agents: $agent_count"
        [[ $skill_count -gt 0 ]] && echo "      Skills: $skill_count"
        [[ -f "$plugin_dir/hooks/hooks.json" ]] && echo "      Hooks: yes"
        [[ -f "$plugin_dir/.mcp.json" ]] && echo "      MCP: yes"
    fi
done

echo ""
echo "## Quick Commands"
echo "  ./scripts/new-skill.sh <name>                   Create standalone skill"
echo "  ./scripts/new-plugin.sh <name> [--full]         Create plugin"
echo "  ./scripts/new-agent.sh <name> --plugin <p>      Add agent to plugin"
echo "  ./scripts/new-command.sh <name> --plugin <p>    Add command to plugin"
echo "  ./scripts/new-hook.sh <name> --plugin <p> -e <event>  Add hook"
echo "  ./scripts/new-mcp.sh <name> --plugin <p>        Add MCP server"
echo "  ./scripts/validate.sh                           Validate all components"
