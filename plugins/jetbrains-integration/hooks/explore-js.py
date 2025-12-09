#!/usr/bin/env python3
"""
Extend Explore agent with JetBrains IDE context.

PreToolUse hook that injects JetBrains CLI tool instructions into Explore agent's
prompt for IDE-powered code navigation.

Triggers when:
- Tool: Task with subagent_type: Explore

Exit codes:
  0 = allow (with optional JSON output for modifications)
  1 = show stderr to user only
  2 = block and show stderr to Claude
"""
import json
import sys

JETBRAINS_CONTEXT = """
<jetbrains-context>
## JetBrains IDE Tools (via CLI)

Use `jetbrains <command>` for IDE-powered code navigation:

| Task | Command | Instead of |
|------|---------|------------|
| Find files by name | `jetbrains files "keyword"` | Glob |
| Find files by glob | `jetbrains glob "**/*.js"` | Glob |
| Search text in files | `jetbrains search "text"` | Grep |
| Search with regex | `jetbrains regex "pattern"` | Grep |
| Get symbol info | `jetbrains symbol file.js:line:col` | Reading file |
| Get file problems | `jetbrains problems file.js` | Manual check |
| Directory tree | `jetbrains tree path/` | tree |
| Read file | `jetbrains read file.js` | cat |

### When to Use JetBrains CLI
- Searching JS/TS code
- Understanding legacy AMD/RequireJS modules
- Getting IDE-detected problems/errors
- Symbol information with documentation
- PhpStorm handles messy JS better than basic LSP

### When to Use Grep Instead
- Simple literal text search
- Searching non-indexed file types
- When IDE is not running

### JetBrains Advantages
- Uses PhpStorm's indexing
- Better handling of legacy AMD/RequireJS
- Integrated with IDE context
- Shows IDE-detected errors
</jetbrains-context>

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

    # Always inject JetBrains context for Explore agents
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
