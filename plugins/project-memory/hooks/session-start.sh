#!/bin/bash
# Check if pm CLI is available and project has memories

if ! command -v pm &> /dev/null; then
    exit 0
fi

# Check if .project-memory exists in current directory
if [ ! -d ".project-memory" ]; then
    exit 0
fi

# Get memory stats
STATS=$(pm stats 2>/dev/null)
if [ $? -ne 0 ]; then
    exit 0
fi

# Output reminder as JSON for context injection
cat << 'EOF'
{
  "result": "success",
  "additionalContext": "**Project Memory Available**: This project has stored memories. Use `/pm:load` to restore context or `/pm:search` to find specific information."
}
EOF
