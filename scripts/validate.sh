#!/usr/bin/env bash
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

ERRORS=0
WARNINGS=0

log_error() {
    echo -e "${RED}ERROR: $1${NC}"
    ((ERRORS++))
}

log_warning() {
    echo -e "${YELLOW}WARNING: $1${NC}"
    ((WARNINGS++))
}

log_success() {
    echo -e "${GREEN}OK: $1${NC}"
}

echo "Validating marketplace structure..."
echo ""

# Validate skills
echo "=== Validating Skills ==="
for skill_dir in "$ROOT_DIR"/skills/*/; do
    if [[ -d "$skill_dir" ]]; then
        skill_name=$(basename "$skill_dir")
        skill_file="$skill_dir/SKILL.md"

        if [[ ! -f "$skill_file" ]]; then
            log_error "Skill '$skill_name' missing SKILL.md"
            continue
        fi

        # Check frontmatter
        if ! head -1 "$skill_file" | grep -q "^---$"; then
            log_error "Skill '$skill_name' missing YAML frontmatter"
            continue
        fi

        # Check required fields
        if ! grep -q "^name:" "$skill_file"; then
            log_error "Skill '$skill_name' missing 'name' field"
        fi
        if ! grep -q "^description:" "$skill_file"; then
            log_error "Skill '$skill_name' missing 'description' field"
        fi

        # Check name matches directory
        yaml_name=$(grep "^name:" "$skill_file" | sed 's/name:\s*//' | tr -d '\r')
        if [[ "$yaml_name" != "$skill_name" ]]; then
            log_error "Skill '$skill_name' name mismatch: YAML says '$yaml_name'"
        fi

        log_success "Skill '$skill_name' is valid"
    fi
done

echo ""
echo "=== Validating Plugins ==="
for plugin_dir in "$ROOT_DIR"/plugins/*/; do
    if [[ -d "$plugin_dir" ]]; then
        plugin_name=$(basename "$plugin_dir")
        manifest="$plugin_dir/plugin.json"

        if [[ ! -f "$manifest" ]]; then
            log_warning "Plugin '$plugin_name' missing plugin.json (optional)"
        else
            # Validate JSON
            if ! jq empty "$manifest" 2>/dev/null; then
                log_error "Plugin '$plugin_name' has invalid JSON in plugin.json"
            else
                # Check required fields
                if [[ $(jq -r '.name' "$manifest") == "null" ]]; then
                    log_error "Plugin '$plugin_name' missing 'name' in plugin.json"
                fi
            fi
        fi

        # Validate hooks
        hooks_json="$plugin_dir/hooks/hooks.json"
        if [[ -f "$hooks_json" ]]; then
            if ! jq empty "$hooks_json" 2>/dev/null; then
                log_error "Plugin '$plugin_name' has invalid JSON in hooks.json"
            fi
        fi

        # Validate MCP
        mcp_json="$plugin_dir/.mcp.json"
        if [[ -f "$mcp_json" ]]; then
            if ! jq empty "$mcp_json" 2>/dev/null; then
                log_error "Plugin '$plugin_name' has invalid JSON in .mcp.json"
            fi
        fi

        # Validate agents
        for agent_file in "$plugin_dir"/agents/*.md 2>/dev/null; do
            if [[ -f "$agent_file" ]]; then
                agent_name=$(basename "$agent_file" .md)
                if ! head -1 "$agent_file" | grep -q "^---$"; then
                    log_error "Agent '$agent_name' in '$plugin_name' missing frontmatter"
                fi
            fi
        done

        # Validate commands
        for cmd_file in "$plugin_dir"/commands/*.md 2>/dev/null; do
            if [[ -f "$cmd_file" ]]; then
                cmd_name=$(basename "$cmd_file" .md)
                if ! head -1 "$cmd_file" | grep -q "^---$"; then
                    log_error "Command '$cmd_name' in '$plugin_name' missing frontmatter"
                fi
            fi
        done

        log_success "Plugin '$plugin_name' validated"
    fi
done

echo ""
echo "=== Summary ==="
echo "Errors: $ERRORS"
echo "Warnings: $WARNINGS"

if [[ $ERRORS -gt 0 ]]; then
    echo -e "${RED}Validation failed with $ERRORS error(s)${NC}"
    exit 1
else
    echo -e "${GREEN}Validation passed!${NC}"
    exit 0
fi
