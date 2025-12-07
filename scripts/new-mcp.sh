#!/usr/bin/env bash
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

usage() {
    echo "Usage: $0 <server-name> --plugin <plugin-name> --type <server-type>"
    echo ""
    echo "Arguments:"
    echo "  server-name    Name of the MCP server"
    echo ""
    echo "Options:"
    echo "  --plugin       Plugin to add the MCP server to (required)"
    echo "  --type         Server type: stdio (default), sse, http"
    echo ""
    echo "Examples:"
    echo "  $0 database --plugin data-tools --type stdio"
    echo "  $0 api-gateway --plugin integration --type http"
    exit 1
}

if [[ $# -lt 1 ]]; then
    usage
fi

SERVER_NAME="$1"
PLUGIN_NAME=""
SERVER_TYPE="stdio"

shift
while [[ $# -gt 0 ]]; do
    case $1 in
        --plugin) PLUGIN_NAME="$2"; shift 2 ;;
        --type) SERVER_TYPE="$2"; shift 2 ;;
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

MCP_FILE="$PLUGIN_DIR/.mcp.json"

echo -e "${GREEN}Adding MCP server: $SERVER_NAME${NC}"
echo "Type: $SERVER_TYPE"

# Create or update .mcp.json
if [[ ! -f "$MCP_FILE" ]]; then
    echo '{"mcpServers": {}}' > "$MCP_FILE"
fi

case $SERVER_TYPE in
    stdio)
        SERVER_CONFIG=$(cat << JSONEOF
{
  "command": "\${CLAUDE_PLUGIN_ROOT}/mcp/$SERVER_NAME/server.py",
  "args": [],
  "env": {}
}
JSONEOF
)
        mkdir -p "$PLUGIN_DIR/mcp/$SERVER_NAME"
        cat > "$PLUGIN_DIR/mcp/$SERVER_NAME/server.py" << 'PYEOF'
#!/usr/bin/env python3
"""MCP Server: {{SERVER_NAME}}

A stdio-based MCP server.
"""

import json
import sys

def main():
    # TODO: Implement MCP server logic
    # Read JSON-RPC requests from stdin
    # Write JSON-RPC responses to stdout
    pass

if __name__ == "__main__":
    main()
PYEOF
        sed -i "s/{{SERVER_NAME}}/$SERVER_NAME/g" "$PLUGIN_DIR/mcp/$SERVER_NAME/server.py"
        chmod +x "$PLUGIN_DIR/mcp/$SERVER_NAME/server.py"
        ;;
    sse)
        SERVER_CONFIG=$(cat << JSONEOF
{
  "url": "https://your-server.com/sse",
  "headers": {
    "Authorization": "Bearer \${API_TOKEN}"
  }
}
JSONEOF
)
        ;;
    http)
        SERVER_CONFIG=$(cat << JSONEOF
{
  "url": "https://your-server.com/api",
  "method": "POST",
  "headers": {
    "Authorization": "Bearer \${API_TOKEN}",
    "Content-Type": "application/json"
  }
}
JSONEOF
)
        ;;
esac

if command -v jq &> /dev/null; then
    UPDATED=$(jq --arg name "$SERVER_NAME" --argjson config "$SERVER_CONFIG" '
      .mcpServers[$name] = $config
    ' "$MCP_FILE")
    echo "$UPDATED" > "$MCP_FILE"
else
    echo -e "${RED}Error: jq is required for MCP configuration${NC}"
    exit 1
fi

echo -e "${GREEN}MCP server added successfully!${NC}"
echo ""
echo "Next steps:"
if [[ "$SERVER_TYPE" == "stdio" ]]; then
    echo "  1. Edit $PLUGIN_DIR/mcp/$SERVER_NAME/server.py"
    echo "  2. Implement MCP server logic"
fi
echo "  3. Verify $MCP_FILE configuration"
