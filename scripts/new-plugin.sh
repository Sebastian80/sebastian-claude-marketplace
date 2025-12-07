#!/usr/bin/env bash
set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

usage() {
    echo "Usage: $0 <plugin-name> [options]"
    echo ""
    echo "Arguments:"
    echo "  plugin-name    Name of the plugin in kebab-case"
    echo ""
    echo "Options:"
    echo "  --with-commands    Include commands/ directory"
    echo "  --with-agents      Include agents/ directory"
    echo "  --with-skills      Include skills/ directory"
    echo "  --with-hooks       Include hooks/ directory with template"
    echo "  --with-mcp         Include MCP server configuration"
    echo "  --full             Include all component directories"
    echo ""
    echo "Examples:"
    echo "  $0 my-plugin"
    echo "  $0 dev-tools --with-commands --with-hooks"
    echo "  $0 full-plugin --full"
    exit 1
}

if [[ $# -lt 1 ]]; then
    usage
fi

PLUGIN_NAME="$1"
WITH_COMMANDS=false
WITH_AGENTS=false
WITH_SKILLS=false
WITH_HOOKS=false
WITH_MCP=false

shift
while [[ $# -gt 0 ]]; do
    case $1 in
        --with-commands) WITH_COMMANDS=true; shift ;;
        --with-agents) WITH_AGENTS=true; shift ;;
        --with-skills) WITH_SKILLS=true; shift ;;
        --with-hooks) WITH_HOOKS=true; shift ;;
        --with-mcp) WITH_MCP=true; shift ;;
        --full)
            WITH_COMMANDS=true
            WITH_AGENTS=true
            WITH_SKILLS=true
            WITH_HOOKS=true
            WITH_MCP=true
            shift
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            usage
            ;;
    esac
done

# Validate plugin name
if [[ ! "$PLUGIN_NAME" =~ ^[a-z][a-z0-9-]*[a-z0-9]$ ]] && [[ ! "$PLUGIN_NAME" =~ ^[a-z]$ ]]; then
    echo -e "${RED}Error: Plugin name must be in kebab-case${NC}"
    exit 1
fi

PLUGIN_DIR="$ROOT_DIR/plugins/$PLUGIN_NAME"

if [[ -d "$PLUGIN_DIR" ]]; then
    echo -e "${RED}Error: Plugin '$PLUGIN_NAME' already exists${NC}"
    exit 1
fi

PLUGIN_TITLE=$(echo "$PLUGIN_NAME" | sed -E 's/-/ /g' | sed -E 's/\b(.)/\u\1/g')

echo -e "${GREEN}Creating plugin: $PLUGIN_NAME${NC}"
echo "Location: $PLUGIN_DIR"

# Create plugin directory
mkdir -p "$PLUGIN_DIR"

# Create plugin.json
cat > "$PLUGIN_DIR/plugin.json" << EOF
{
  "name": "$PLUGIN_NAME",
  "version": "1.0.0",
  "description": "TODO: Add plugin description",
  "author": "Sebastian",
  "license": "MIT"
}
EOF

# Create README.md
cat > "$PLUGIN_DIR/README.md" << EOF
# $PLUGIN_TITLE

TODO: Add plugin description

## Installation

\`\`\`bash
/plugin install $PLUGIN_NAME@sebastian-marketplace
\`\`\`

## Components

EOF

# Create optional directories
if [[ "$WITH_COMMANDS" == true ]]; then
    mkdir -p "$PLUGIN_DIR/commands"
    echo "- **Commands**: See \`commands/\` directory" >> "$PLUGIN_DIR/README.md"
fi

if [[ "$WITH_AGENTS" == true ]]; then
    mkdir -p "$PLUGIN_DIR/agents"
    echo "- **Agents**: See \`agents/\` directory" >> "$PLUGIN_DIR/README.md"
fi

if [[ "$WITH_SKILLS" == true ]]; then
    mkdir -p "$PLUGIN_DIR/skills"
    echo "- **Skills**: See \`skills/\` directory" >> "$PLUGIN_DIR/README.md"
fi

if [[ "$WITH_HOOKS" == true ]]; then
    mkdir -p "$PLUGIN_DIR/hooks"
    cat > "$PLUGIN_DIR/hooks/hooks.json" << 'HOOKEOF'
{
  "hooks": {}
}
HOOKEOF
    echo "- **Hooks**: See \`hooks/\` directory" >> "$PLUGIN_DIR/README.md"
fi

if [[ "$WITH_MCP" == true ]]; then
    cat > "$PLUGIN_DIR/.mcp.json" << 'MCPEOF'
{
  "mcpServers": {}
}
MCPEOF
    echo "- **MCP Servers**: See \`.mcp.json\`" >> "$PLUGIN_DIR/README.md"
fi

# Add usage section
cat >> "$PLUGIN_DIR/README.md" << EOF

## Usage

TODO: Add usage examples
EOF

echo -e "${GREEN}Plugin created successfully!${NC}"
echo ""
echo "Structure:"
find "$PLUGIN_DIR" -type f | sed "s|$PLUGIN_DIR/|  |g"
echo ""
echo "Next steps:"
echo "  1. Edit $PLUGIN_DIR/plugin.json with proper description"
echo "  2. Add components using generator scripts:"
if [[ "$WITH_COMMANDS" == true ]]; then
    echo "     ./scripts/new-command.sh command-name --plugin $PLUGIN_NAME"
fi
if [[ "$WITH_AGENTS" == true ]]; then
    echo "     ./scripts/new-agent.sh agent-name --plugin $PLUGIN_NAME"
fi
if [[ "$WITH_SKILLS" == true ]]; then
    echo "     ./scripts/new-skill.sh skill-name --plugin $PLUGIN_NAME"
fi
