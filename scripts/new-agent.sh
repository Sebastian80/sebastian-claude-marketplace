#!/usr/bin/env bash
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

usage() {
    echo "Usage: $0 <agent-name> --plugin <plugin-name> [--model <model>]"
    echo ""
    echo "Arguments:"
    echo "  agent-name     Name of the agent in kebab-case"
    echo ""
    echo "Options:"
    echo "  --plugin       Plugin to add the agent to (required)"
    echo "  --model        Model to use: sonnet (default), opus, haiku"
    echo ""
    echo "Examples:"
    echo "  $0 code-reviewer --plugin dev-tools"
    echo "  $0 quick-analyzer --plugin utils --model haiku"
    exit 1
}

if [[ $# -lt 1 ]]; then
    usage
fi

AGENT_NAME="$1"
PLUGIN_NAME=""
MODEL="sonnet"

shift
while [[ $# -gt 0 ]]; do
    case $1 in
        --plugin) PLUGIN_NAME="$2"; shift 2 ;;
        --model) MODEL="$2"; shift 2 ;;
        *) echo -e "${RED}Unknown option: $1${NC}"; usage ;;
    esac
done

if [[ -z "$PLUGIN_NAME" ]]; then
    echo -e "${RED}Error: --plugin is required${NC}"
    usage
fi

# Validate names
if [[ ! "$AGENT_NAME" =~ ^[a-z][a-z0-9-]*[a-z0-9]$ ]] && [[ ! "$AGENT_NAME" =~ ^[a-z]$ ]]; then
    echo -e "${RED}Error: Agent name must be in kebab-case${NC}"
    exit 1
fi

PLUGIN_DIR="$ROOT_DIR/plugins/$PLUGIN_NAME"
if [[ ! -d "$PLUGIN_DIR" ]]; then
    echo -e "${RED}Error: Plugin '$PLUGIN_NAME' does not exist${NC}"
    exit 1
fi

AGENTS_DIR="$PLUGIN_DIR/agents"
mkdir -p "$AGENTS_DIR"

AGENT_FILE="$AGENTS_DIR/$AGENT_NAME.md"
if [[ -f "$AGENT_FILE" ]]; then
    echo -e "${RED}Error: Agent '$AGENT_NAME' already exists${NC}"
    exit 1
fi

AGENT_TITLE=$(echo "$AGENT_NAME" | sed -E 's/-/ /g' | sed -E 's/\b(.)/\u\1/g')

echo -e "${GREEN}Creating agent: $AGENT_NAME${NC}"
echo "Location: $AGENT_FILE"

cat > "$AGENT_FILE" << EOF
---
name: $AGENT_NAME
description: |
  TODO: Add description with trigger phrases.
  Use when: (1) First use case, (2) Second use case.
  Keywords: keyword1, keyword2, keyword3
model: $MODEL
tools:
  - Read
  - Glob
  - Grep
  - Bash
---

# $AGENT_TITLE Agent

## Context

You are a specialized agent for TODO: describe purpose.

## Instructions

1. TODO: First instruction
2. TODO: Second instruction
3. TODO: Third instruction

## Output Format

Return your findings in the following format:

\`\`\`
## Summary
[Brief summary]

## Details
[Detailed findings]

## Recommendations
[Action items]
\`\`\`
EOF

echo -e "${GREEN}Agent created successfully!${NC}"
echo ""
echo "Next steps:"
echo "  1. Edit $AGENT_FILE"
echo "  2. Update description with strong trigger phrases"
echo "  3. Add <example> blocks for reliable triggering"
echo "  4. Configure tools list based on agent needs"
