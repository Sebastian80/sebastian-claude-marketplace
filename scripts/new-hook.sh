#!/usr/bin/env bash
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

usage() {
    echo "Usage: $0 <hook-name> --plugin <plugin-name> --event <event-type>"
    echo ""
    echo "Arguments:"
    echo "  hook-name      Name of the hook script in kebab-case"
    echo ""
    echo "Options:"
    echo "  --plugin       Plugin to add the hook to (required)"
    echo "  --event        Hook event type (required):"
    echo "                   PreToolUse, PostToolUse, Stop, SubagentStop,"
    echo "                   SessionStart, SessionEnd, UserPromptSubmit,"
    echo "                   PreCompact, Notification"
    echo "  --type         Hook type: command (default) or prompt"
    echo ""
    echo "Examples:"
    echo "  $0 validate-write --plugin security --event PreToolUse"
    echo "  $0 cleanup --plugin dev-tools --event Stop"
    exit 1
}

if [[ $# -lt 1 ]]; then
    usage
fi

HOOK_NAME="$1"
PLUGIN_NAME=""
EVENT_TYPE=""
HOOK_TYPE="command"

shift
while [[ $# -gt 0 ]]; do
    case $1 in
        --plugin) PLUGIN_NAME="$2"; shift 2 ;;
        --event) EVENT_TYPE="$2"; shift 2 ;;
        --type) HOOK_TYPE="$2"; shift 2 ;;
        *) echo -e "${RED}Unknown option: $1${NC}"; usage ;;
    esac
done

if [[ -z "$PLUGIN_NAME" ]] || [[ -z "$EVENT_TYPE" ]]; then
    echo -e "${RED}Error: --plugin and --event are required${NC}"
    usage
fi

# Validate event type
VALID_EVENTS="PreToolUse PostToolUse Stop SubagentStop SessionStart SessionEnd UserPromptSubmit PreCompact Notification"
if [[ ! " $VALID_EVENTS " =~ " $EVENT_TYPE " ]]; then
    echo -e "${RED}Error: Invalid event type '$EVENT_TYPE'${NC}"
    echo "Valid events: $VALID_EVENTS"
    exit 1
fi

PLUGIN_DIR="$ROOT_DIR/plugins/$PLUGIN_NAME"
if [[ ! -d "$PLUGIN_DIR" ]]; then
    echo -e "${RED}Error: Plugin '$PLUGIN_NAME' does not exist${NC}"
    exit 1
fi

HOOKS_DIR="$PLUGIN_DIR/hooks"
mkdir -p "$HOOKS_DIR"

HOOK_FILE="$HOOKS_DIR/$HOOK_NAME.sh"
if [[ -f "$HOOK_FILE" ]]; then
    echo -e "${RED}Error: Hook '$HOOK_NAME' already exists${NC}"
    exit 1
fi

echo -e "${GREEN}Creating hook: $HOOK_NAME${NC}"
echo "Event: $EVENT_TYPE"
echo "Location: $HOOK_FILE"

# Create hook script
cat > "$HOOK_FILE" << 'EOF'
#!/usr/bin/env bash
set -euo pipefail

# Hook: {{HOOK_NAME}}
# Event: {{EVENT_TYPE}}
# Description: TODO: Add description

# Read input from stdin (JSON format)
INPUT=$(cat)

# Parse input (example for PreToolUse)
# TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty')
# TOOL_INPUT=$(echo "$INPUT" | jq -r '.tool_input // empty')

# Hook logic goes here
# TODO: Implement hook logic

# Output format:
# - For continue: {"action": "allow"}
# - For block: {"action": "block", "reason": "explanation"}
# - For modify: {"action": "allow", "modifiedInput": {...}}

# Default: allow
echo '{"action": "allow"}'
EOF

# Replace placeholders
sed -i "s/{{HOOK_NAME}}/$HOOK_NAME/g" "$HOOK_FILE"
sed -i "s/{{EVENT_TYPE}}/$EVENT_TYPE/g" "$HOOK_FILE"

chmod +x "$HOOK_FILE"

# Update hooks.json
HOOKS_JSON="$HOOKS_DIR/hooks.json"
if [[ ! -f "$HOOKS_JSON" ]]; then
    echo '{"hooks": {}}' > "$HOOKS_JSON"
fi

# Add hook entry (using jq if available, otherwise manual)
if command -v jq &> /dev/null; then
    HOOK_ENTRY=$(cat << JSONEOF
{
  "matcher": "*",
  "hooks": [{
    "type": "$HOOK_TYPE",
    "command": "\${CLAUDE_PLUGIN_ROOT}/hooks/$HOOK_NAME.sh"
  }]
}
JSONEOF
)
    # Check if event exists and append, or create new
    UPDATED=$(jq --arg event "$EVENT_TYPE" --argjson entry "$HOOK_ENTRY" '
      if .hooks[$event] then
        .hooks[$event] += [$entry]
      else
        .hooks[$event] = [$entry]
      end
    ' "$HOOKS_JSON")
    echo "$UPDATED" > "$HOOKS_JSON"
    echo -e "${GREEN}Updated hooks.json${NC}"
else
    echo -e "${YELLOW}Warning: jq not found. Please manually add hook to hooks.json${NC}"
fi

echo -e "${GREEN}Hook created successfully!${NC}"
echo ""
echo "Next steps:"
echo "  1. Edit $HOOK_FILE with your hook logic"
echo "  2. Verify hooks.json configuration"
echo "  3. Test with: echo '{}' | $HOOK_FILE"
