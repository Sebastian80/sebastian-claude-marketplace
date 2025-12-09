#!/usr/bin/env python3
"""
Extend Explore agent with Serena LSP context.

PreToolUse hook that injects Serena CLI tool instructions into Explore agent's
prompt for semantic code navigation.

Triggers when:
- Tool: Task with subagent_type: Explore

Exit codes:
  0 = allow (with optional JSON output for modifications)
  1 = show stderr to user only
  2 = block and show stderr to Claude
"""
import json
import sys

SERENA_CONTEXT = """
<serena-context>
## Serena LSP Tools (via CLI)

Use `serena <command>` for semantic code navigation:

| Task | Command | Instead of |
|------|---------|------------|
| Find symbol definition | `serena find_symbol "ClassName"` | Grep |
| Find all references/callers | `serena find_referencing_symbols "Class::method"` | Grep |
| Get file/class structure | `serena get_symbols_overview file.php` | Reading file |
| Pattern search in code | `serena search_for_pattern "pattern"` | Grep |
| List directory contents | `serena list_dir path/` | ls |
| Find files by pattern | `serena find_file "*.php"` | Glob |

### When to Use Serena
- Finding class, method, function definitions (any language with LSP)
- Finding who calls a method (references)
- Understanding class/file structure
- Navigating framework code (Symfony, Oro, Doctrine)
- Works in vendor/ directories

### When to Use Grep Instead
- YAML/JSON config values (strings, not symbols)
- Literal text in comments/logs
- Regex across all file types

### Serena Advantages
- Exact file:line locations
- Understands namespaces and inheritance
- Symbol-aware (not text matching)
</serena-context>

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

    # Always inject Serena context for Explore agents
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
