#!/usr/bin/env bash
set -euo pipefail

# Hook: example-hook
# Event: SessionStart
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
