#!/usr/bin/env python3
"""
Extend Explore agent with JetBrains MCP context for JS projects.

PreToolUse hook that injects JetBrains MCP tool instructions into Explore agent's
prompt for JavaScript code navigation, especially legacy AMD-style code.

Triggers when:
- Tool: Task with subagent_type: Explore
- Project has: package.json (without composer.json, to avoid conflict with PHP projects)

Exit codes:
  0 = allow (with optional JSON output for modifications)
  1 = show stderr to user only
  2 = block and show stderr to Claude
"""
import json
import sys
import os

JETBRAINS_CONTEXT = """
<jetbrains-js-context>
## JetBrains MCP Tools for JavaScript

This project has JetBrains MCP integration. Use JetBrains for JS code navigation:

| Task | JetBrains MCP Tool | Instead of |
|------|-------------------|------------|
| Find files by name | `mcp__jetbrains__find_files_by_name_keyword` | Glob |
| Search text in files | `mcp__jetbrains__search_in_files_by_text` | Grep |
| Search with regex | `mcp__jetbrains__search_in_files_by_regex` | Grep |
| Get symbol info/docs | `mcp__jetbrains__get_symbol_info` | Reading file |
| Find files by glob | `mcp__jetbrains__find_files_by_glob` | Glob |

### When to Use JetBrains MCP (JavaScript)
- Finding JS/TS files by name
- Searching in JS/TS code
- Understanding legacy AMD-style modules
- Getting symbol documentation
- PhpStorm handles messy JS better than basic LSP

### When to Use Grep Instead
- Simple literal text search
- Searching across all file types
- When you need specific regex features

### JetBrains Advantages
- Understands PhpStorm's indexing
- Better handling of legacy AMD/RequireJS
- Integrated with IDE context
- Faster than manual file reading
</jetbrains-js-context>

"""


def main():
    try:
        hook_input = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    tool_name = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {})

    # Only process Task tool
    if tool_name != "Task":
        sys.exit(0)

    subagent_type = tool_input.get("subagent_type", "")

    # Only extend Explore agent
    if subagent_type != "Explore":
        sys.exit(0)

    # Check if JS project (has package.json)
    # Both hooks can fire for mixed PHP+JS projects
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    has_package = os.path.exists(os.path.join(project_dir, "package.json"))

    if not has_package:
        # Not a JS project
        sys.exit(0)

    # Extend prompt with JetBrains context
    original_prompt = tool_input.get("prompt", "")
    extended_prompt = JETBRAINS_CONTEXT + original_prompt

    # Build updated input
    updated_input = {
        "subagent_type": subagent_type,
        "prompt": extended_prompt,
    }

    # Preserve optional fields
    for field in ["description", "model", "run_in_background"]:
        if field in tool_input:
            updated_input[field] = tool_input[field]

    # Output JSON to modify the tool input
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "permissionDecisionReason": "Extended Explore with JetBrains JS context",
            "updatedInput": updated_input
        }
    }
    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
