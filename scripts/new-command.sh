#!/usr/bin/env bash
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

usage() {
    echo "Usage: $0 <command-name> --plugin <plugin-name>"
    echo ""
    echo "Arguments:"
    echo "  command-name   Name of the command in kebab-case"
    echo ""
    echo "Options:"
    echo "  --plugin       Plugin to add the command to (required)"
    echo ""
    echo "Examples:"
    echo "  $0 run-tests --plugin dev-tools"
    echo "  $0 deploy --plugin ci-cd"
    exit 1
}

if [[ $# -lt 1 ]]; then
    usage
fi

COMMAND_NAME="$1"
PLUGIN_NAME=""

shift
while [[ $# -gt 0 ]]; do
    case $1 in
        --plugin) PLUGIN_NAME="$2"; shift 2 ;;
        *) echo -e "${RED}Unknown option: $1${NC}"; usage ;;
    esac
done

if [[ -z "$PLUGIN_NAME" ]]; then
    echo -e "${RED}Error: --plugin is required${NC}"
    usage
fi

PLUGIN_DIR="$ROOT_DIR/plugins/$PLUGIN_NAME"
if [[ ! -d "$PLUGIN_DIR" ]]; then
    echo -e "${RED}Error: Plugin '$PLUGIN_NAME' does not exist${NC}"
    exit 1
fi

COMMANDS_DIR="$PLUGIN_DIR/commands"
mkdir -p "$COMMANDS_DIR"

COMMAND_FILE="$COMMANDS_DIR/$COMMAND_NAME.md"
if [[ -f "$COMMAND_FILE" ]]; then
    echo -e "${RED}Error: Command '$COMMAND_NAME' already exists${NC}"
    exit 1
fi

COMMAND_TITLE=$(echo "$COMMAND_NAME" | sed -E 's/-/ /g' | sed -E 's/\b(.)/\u\1/g')

echo -e "${GREEN}Creating command: $COMMAND_NAME${NC}"
echo "Location: $COMMAND_FILE"

cat > "$COMMAND_FILE" << EOF
---
description: TODO: Brief description of what /$PLUGIN_NAME:$COMMAND_NAME does
argument-hint: "[optional arguments]"
allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash
---

# $COMMAND_TITLE

TODO: Add command instructions here.

## Arguments

- \`arg1\`: TODO: Describe first argument
- \`arg2\`: TODO: Describe second argument

## Examples

\`\`\`bash
/$PLUGIN_NAME:$COMMAND_NAME
/$PLUGIN_NAME:$COMMAND_NAME arg1 arg2
\`\`\`

## Instructions

When this command is invoked:

1. TODO: First step
2. TODO: Second step
3. TODO: Third step
EOF

echo -e "${GREEN}Command created successfully!${NC}"
echo ""
echo "Next steps:"
echo "  1. Edit $COMMAND_FILE"
echo "  2. Update description and argument-hint"
echo "  3. Add command instructions"
echo ""
echo "Usage: /$PLUGIN_NAME:$COMMAND_NAME"
