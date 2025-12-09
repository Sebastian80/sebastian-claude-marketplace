---
name: serena
description: "Use when grep returns too many matches, you need to find all method callers, or want to understand codebase structure - semantic code navigation via LSP that replaces grep/glob with symbol-aware search across 30+ languages. Finds exact definitions, all references, file structure without text-matching noise. Triggers: where is X defined, who calls this, find all usages, show class structure, find implementations"
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

**Discovery:** Run `serena tools` to see all available MCP tools dynamically.

| Task | Command |
|------|---------|
| Find symbol | `serena find --pattern Customer --kind class` |
| Find with source | `serena find --pattern Customer --body` |
| Who calls this? | `serena refs --symbol "Class/method" --file path.php` |
| File structure | `serena overview --file path.php` |
| Regex search | `serena search --pattern "regex" --path src/` |
| Check status | `serena status` |
| List tools | `serena tools` |

**Nested commands use slash notation:**
```bash
serena memory/list
serena memory/tree
serena edit/replace --symbol X --file Y --body Z
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

## Detailed Reference

For full CLI syntax, see `references/cli-reference.md`.

For symbol kinds, see `references/symbol-kinds.md`.

For editing patterns, see `references/editing-patterns.md`.
