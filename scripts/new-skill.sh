#!/usr/bin/env bash
set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

usage() {
    echo "Usage: $0 <skill-name> [--plugin <plugin-name>]"
    echo ""
    echo "Arguments:"
    echo "  skill-name    Name of the skill in kebab-case (e.g., my-awesome-skill)"
    echo ""
    echo "Options:"
    echo "  --plugin      Create skill inside a plugin instead of standalone"
    echo ""
    echo "Examples:"
    echo "  $0 code-review"
    echo "  $0 lint-fixer --plugin dev-tools"
    exit 1
}

if [[ $# -lt 1 ]]; then
    usage
fi

SKILL_NAME="$1"
PLUGIN_NAME=""

# Parse optional arguments
shift
while [[ $# -gt 0 ]]; do
    case $1 in
        --plugin)
            PLUGIN_NAME="$2"
            shift 2
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            usage
            ;;
    esac
done

# Validate skill name (kebab-case)
if [[ ! "$SKILL_NAME" =~ ^[a-z][a-z0-9-]*[a-z0-9]$ ]] && [[ ! "$SKILL_NAME" =~ ^[a-z]$ ]]; then
    echo -e "${RED}Error: Skill name must be in kebab-case (e.g., my-skill)${NC}"
    exit 1
fi

# Determine target directory
if [[ -n "$PLUGIN_NAME" ]]; then
    SKILL_DIR="$ROOT_DIR/plugins/$PLUGIN_NAME/skills/$SKILL_NAME"
else
    SKILL_DIR="$ROOT_DIR/skills/$SKILL_NAME"
fi

# Check if skill already exists
if [[ -d "$SKILL_DIR" ]]; then
    echo -e "${RED}Error: Skill '$SKILL_NAME' already exists at $SKILL_DIR${NC}"
    exit 1
fi

# Convert kebab-case to Title Case
SKILL_TITLE=$(echo "$SKILL_NAME" | sed -E 's/-/ /g' | sed -E 's/\b(.)/\u\1/g')

echo -e "${GREEN}Creating skill: $SKILL_NAME${NC}"
echo "Location: $SKILL_DIR"

# Create skill directory
mkdir -p "$SKILL_DIR"

# Copy and process template
TEMPLATE="$ROOT_DIR/templates/skill/SKILL.md.template"

if [[ -f "$TEMPLATE" ]]; then
    sed -e "s/{{SKILL_NAME}}/$SKILL_NAME/g" \
        -e "s/{{SKILL_TITLE}}/$SKILL_TITLE/g" \
        -e "s/{{SKILL_DESCRIPTION}}/TODO: Add description/g" \
        -e "s/{{SKILL_OVERVIEW}}/TODO: Add overview/g" \
        -e "s/{{USE_CASE_1}}/TODO: First use case/g" \
        -e "s/{{USE_CASE_2}}/TODO: Second use case/g" \
        -e "s/{{INSTRUCTIONS}}/TODO: Add instructions/g" \
        -e "s/{{EXAMPLES}}/TODO: Add examples/g" \
        "$TEMPLATE" > "$SKILL_DIR/SKILL.md"
else
    # Fallback if template doesn't exist
    cat > "$SKILL_DIR/SKILL.md" << EOF
---
name: $SKILL_NAME
description: TODO: Add description
license: MIT
allowed-tools:
  - Read
  - Glob
  - Grep
---

# $SKILL_TITLE

## Overview

TODO: Add overview

## When to Use

Use this skill when:
- TODO: First use case
- TODO: Second use case

## Instructions

TODO: Add instructions

## Examples

TODO: Add examples
EOF
fi

echo -e "${GREEN}Skill created successfully!${NC}"
echo ""
echo "Next steps:"
echo "  1. Edit $SKILL_DIR/SKILL.md"
echo "  2. Fill in the description, instructions, and examples"
echo "  3. Add any additional resources to $SKILL_DIR/"
echo ""
echo -e "${YELLOW}Tip: Use strong trigger phrases in your description for reliable activation${NC}"
