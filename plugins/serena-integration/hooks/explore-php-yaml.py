#!/usr/bin/env python3
"""
Extend Explore agent with Serena context for PHP/YAML projects.

PreToolUse hook that injects Serena tool instructions into Explore agent's
prompt for PHP and YAML code navigation.

Triggers when:
- Tool: Task with subagent_type: Explore
- Project has: composer.json

Exit codes:
  0 = allow (with optional JSON output for modifications)
  1 = show stderr to user only
  2 = block and show stderr to Claude
"""
import json
import sys
import os

SERENA_CONTEXT = """
<serena-php-context>
## Serena LSP Tools for PHP/YAML

This project has Serena (Intelephense LSP). Use Serena for PHP code navigation:

| Task | Serena Tool | Instead of |
|------|-------------|------------|
| Find class/method definition | `serena find "ClassName"` | Grep |
| Find all callers/usages | `serena refs "Class/method" file.php` | Grep |
| Get file structure | `serena overview file.php` | Reading entire file |
| Pattern search in code | `serena search "pattern"` | Grep |

### When to Use Serena (PHP/YAML)
- Finding PHP class, method, function definitions
- Finding who calls a method (references)
- Understanding class structure
- Navigating Symfony/Oro services and entities
- Works on vendor code (Oro, Symfony, Doctrine)

### When to Use Grep Instead
- Searching YAML config values (strings, not symbols)
- Searching non-PHP files (md, json, xml)
- Literal text search in logs/comments
- When you need regex across all file types

### Serena Advantages
- Exact file:line locations
- Understands PHP namespaces and inheritance
- Works in vendor/ directories
- Symbol-aware (not text matching)
</serena-php-context>

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

    # Check if PHP project (composer.json is the indicator)
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    has_composer = os.path.exists(os.path.join(project_dir, "composer.json"))

    if not has_composer:
        # Not a PHP project - don't inject Serena context
        sys.exit(0)

    # Extend prompt with Serena context
    original_prompt = tool_input.get("prompt", "")
    extended_prompt = SERENA_CONTEXT + original_prompt

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
            "permissionDecisionReason": "Extended Explore with Serena PHP context",
            "updatedInput": updated_input
        }
    }
    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
