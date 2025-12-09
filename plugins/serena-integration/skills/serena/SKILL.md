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

## Critical: Project Activation

**Before using any Serena commands, ensure the project is activated:**

```bash
serena status                                    # Check current project
serena activate --project /path/to/project       # Activate if needed
```

If commands return empty results or timeout, the project is likely not activated.

## Quick Reference

### Finding Code

| Task | Command | Example |
|------|---------|---------|
| Find class | `serena find --pattern X --kind class` | `serena find --pattern Customer --kind class` |
| Find method | `serena find --pattern X --kind method` | `serena find --pattern getName --kind method` |
| Find with source | `serena find --pattern X --body` | `serena find --pattern Customer --kind class --body` |
| **Get class methods** | `serena find --pattern X --kind class --depth 1` | `serena find --pattern Service --kind class --depth 1` |
| Find with children + source | `serena find --pattern X --kind class --depth 1 --body` | `serena find --pattern Service --kind class --depth 1 --body` |
| Restrict to path | `serena find --pattern X --path src/` | `serena find --pattern Order --path src/Meyer/` |

**Important:** Always use `--kind class` with `--depth 1` to get class methods. Without it, you'll get File children (namespace + class) instead of class children (methods, properties).

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
| File structure (top-level only) | `serena overview --file src/Entity/Customer.php` |
| Find entities | `serena recipe --name entities` |
| Find controllers | `serena recipe --name controllers` |
| Check status | `serena status` |

### Framework & Vendor Search

| Task | Command |
|------|---------|
| List all recipes | `serena recipe --name list` |
| **Oro Framework** | |
| Oro payment classes | `serena recipe --name oro-payment` |
| Oro checkout classes | `serena recipe --name oro-checkout` |
| Oro order classes | `serena recipe --name oro-order` |
| **Third-Party** | |
| Mollie payment classes | `serena recipe --name mollie` |
| Netresearch payment | `serena recipe --name netresearch-payment` |
| **All Vendors** | |
| Payment methods | `serena recipe --name payment-methods` |
| Payment providers | `serena recipe --name payment-providers` |
| Payment factories | `serena recipe --name payment-factories` |

**Direct vendor search:**
```bash
serena find --pattern PaymentMethod --kind class --path vendor/       # All vendors
serena find --pattern PaymentMethod --kind class --path vendor/oro    # Oro only
serena find --pattern Mollie --kind class --path vendor/mollie        # Mollie only
```

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
| "Find class X" / "Where is X defined" | `serena find --pattern X --kind class --body` |
| "Who calls X" / "Find usages of X" | `serena refs --symbol X/method --file file.php` |
| "Find all controllers/entities" | `serena recipe --name controllers` |
| "What methods does X have" | `serena find --pattern X --kind class --depth 1` |
| "Show me class X with all its code" | `serena find --pattern X --kind class --depth 1 --body` |

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

**Always use `--path` to restrict search scope:**

| Scope | Files | Speed |
|-------|-------|-------|
| `--path src/` | ~350 | Fast (~0.5s) |
| `--path vendor/oro` | ~5,000 | Medium (~3s) |
| No path (all) | ~60,000 | Slow (~30s) |

```bash
serena find --pattern Payment --path src/        # Fast: your code only
serena find --pattern Payment --path vendor/oro  # Medium: Oro framework
serena find --pattern Payment                    # Slow: searches 60k files
```

**Avoid parallel searches** - The LSP server processes requests sequentially. Running multiple serena commands simultaneously degrades performance. Run searches one at a time.

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| "No symbols found" | Broaden pattern: `CustomerEntity` → `Customer` |
| Empty refs | Use `serena find` first to get exact symbol path |
| Very slow | Add `--path src/` to restrict scope |
| Empty results | Run `serena status` - project may not be activated |
| Overview doesn't show methods | Use `serena find --kind class --depth 1` instead |
| refs returns nothing | Requires `--file` param with path to containing file |

## Deep Reference (Read Only When Needed)

These files contain detailed documentation. Only read them if the quick reference above doesn't answer your question:

| File | When to Read |
|------|--------------|
| `references/cli-reference.md` | Need exact parameter syntax or all options |
| `references/symbol-kinds.md` | Need to filter by specific symbol type |
| `references/editing-patterns.md` | Doing complex code edits |

**For most tasks, the Quick Reference above is sufficient.**
