---
name: serena
description: "MANDATORY for code navigation - use INSTEAD of grep/glob when finding definitions, callers, or code structure. Semantic LSP search across PHP, Python, JS, Go, Rust, Java. Triggers: where is X defined, find class, find method, who calls this, find usages, show methods, find implementations, what calls this, find references, show class structure"
---

<EXTREMELY-IMPORTANT>
# MANDATORY: Code Navigation = Serena First

If you are working with code in a Serena-configured language and think "let me grep for this" or "let me glob for files" - STOP.

**Use Serena FIRST. Always. No exceptions.**

This is not optional. Serena outperforms text-based tools for:
- Finding classes/methods/functions → Semantic, not text matching
- Finding references ("who calls this?") → Actual code references, not grep noise
- Understanding code structure → Symbol tree, not blind file reading

## Rationalizations That Mean You're About To Fail

If you catch yourself thinking ANY of these, STOP:

- "Let me just grep quickly" → WRONG. `serena find` is faster AND accurate.
- "Grep will find all usages" → WRONG. Grep finds TEXT. `serena refs` finds CODE REFERENCES.
- "I'll use the Task/Explore agent" → WRONG. Use Serena directly or serena-explore agent.
- "This is a simple search" → WRONG. Simple searches benefit MOST from semantic tools.

**If a Serena operation exists for your task, you MUST use it.**
</EXTREMELY-IMPORTANT>

## Quick Reference

### Finding Code

| Task | Command | Example |
|------|---------|---------|
| Find class | `serena find --pattern X --kind class` | `serena find --pattern Customer --kind class` |
| Find method | `serena find --pattern X --kind method` | `serena find --pattern getName --kind method` |
| Find with source | `serena find --pattern X --body true` | `serena find --pattern Customer --body true` |
| Find with children | `serena find --pattern X --depth 1` | `serena find --pattern Service --depth 1 --body true` |
| Restrict to path | `serena find --pattern X --path src/` | `serena find --pattern Order --path src/Meyer/` |

### Finding References (Who Calls This?)

```bash
# Step 1: Find the symbol to get exact path
serena find --pattern CustomerService --kind class

# Step 2: Find who uses it
serena refs --symbol "CustomerService" --file "src/Service/CustomerService.php"

# For a method:
serena refs --symbol "CustomerService/getCustomer" --file "src/Service/CustomerService.php"
```

### Search & Discovery

| Task | Command |
|------|---------|
| Regex search | `serena search --pattern "implements.*Interface" --path src/` |
| File structure | `serena overview --file src/Entity/Customer.php` |
| Find entities | `serena recipe --name entities` |
| Find controllers | `serena recipe --name controllers` |
| Check status | `serena status` |

### Memory Commands (Nested with /)

```bash
serena memory/list                    # List all memories
serena memory/tree                    # Visual tree
serena memory/read --name X           # Read memory
serena memory/search --pattern X      # Search memories
```

### Edit Commands (Nested with /)

```bash
serena edit/replace --symbol X --file Y --body "new code"
serena edit/after --symbol X --file Y --code "code to insert"
serena edit/rename --symbol X --file Y --new_name Z
```

### Tool Discovery

If you need a command NOT listed above, run:
```bash
serena tools                          # Lists ALL available MCP tools
serena tools --json                   # JSON format for parsing
```

## Automatic Triggers

| User Request | Command |
|--------------|---------|
| "Find class X" / "Where is X defined" | `serena find --pattern X --body` |
| "Who calls X" / "Find usages of X" | `serena refs --symbol X/method --file file.php` |
| "Find all controllers/entities" | `serena recipe --name controllers` |
| "What methods does X have" | `serena overview --file file.php` |

## When to Use vs NOT Use

| USE SERENA | DON'T USE SERENA |
|------------|------------------|
| Class/method/function definitions | Template files (.twig, .html) |
| Finding references ("who calls this") | Text in comments |
| Understanding file/class structure | Languages NOT in project.yml |
| Languages in `.serena/project.yml` | Log files, .env files |

**Rule:** Serena for CONFIGURED LANGUAGES. Grep for templates/comments/unconfigured.

Run `serena status` to see active languages.

## Symbol Path Convention

- **Class**: `Customer`
- **Method**: `Customer/getName`
- **Constructor**: `Customer/__construct`
- **Property**: `Customer/$name`

## Performance

Always use `--path` to restrict search scope:

```bash
serena find --pattern Payment --path src/      # Fast: ~0.7s
serena find --pattern Payment                   # Slow: ~28s (searches everything)
```

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| "No symbols found" | Broaden pattern: `CustomerEntity` → `Customer` |
| Empty refs | Use `serena find` first to get exact symbol path |
| Very slow | Add `--path src/` to restrict scope |

## Deep Reference (Read Only When Needed)

These files contain detailed documentation. Only read them if the quick reference above doesn't answer your question:

| File | When to Read |
|------|--------------|
| `references/cli-reference.md` | Need exact parameter syntax or all options |
| `references/symbol-kinds.md` | Need to filter by specific symbol type |
| `references/editing-patterns.md` | Doing complex code edits |

**For most tasks, the Quick Reference above is sufficient.**
