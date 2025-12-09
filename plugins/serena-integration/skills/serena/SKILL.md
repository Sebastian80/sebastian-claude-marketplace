---
name: serena
description: "MANDATORY for PHP code navigation - use INSTEAD of grep/glob when finding PHP definitions, callers, or code structure. Semantic LSP search via Intelephense. Triggers: where is X defined, find class, find method, who calls this, find usages, show methods, find implementations, what calls this, find references, show class structure. Use grep for JS/Twig/YAML."
---

<EXTREMELY-IMPORTANT>
# MANDATORY: Code Navigation = Serena First

**Use Serena FIRST. Always. No exceptions.**

## The Iron Law

```
CODE NAVIGATION IN CONFIGURED LANGUAGES = SERENA
```

Using grep/glob when Serena is available? Delete your search. Use Serena.

**No exceptions:**
- Not for "quick" searches
- Not because user asked for grep
- Not under time pressure
- Not for "simple" lookups

## Rationalizations That Mean You're About To Fail

If you catch yourself thinking ANY of these, STOP:

- "Let me just grep quickly" → WRONG. `serena find` is faster AND accurate.
- "Grep will find all usages" → WRONG. Grep finds TEXT. `serena refs` finds CODE REFERENCES.
- "I'll use the Task/Explore agent" → WRONG. Use Serena directly.
- "This is a simple search" → WRONG. Simple searches benefit MOST from semantic tools.
- "I'll search src/ first, then global" → WRONG. For integration classes, this ALWAYS fails.
- "It's probably in our custom code" → WRONG. Custom code extends vendor classes. Search globally.
- "I'm under time pressure" → WRONG. Incomplete results waste MORE time.
- "User explicitly asked for grep" → WRONG. Users want RESULTS, not tools. Use Serena, explain why.
- "I don't want to seem pedantic" → WRONG. Using the right tool is professional, not pedantic.
- "I'll run parallel searches for speed" → WRONG. LSP is sequential. Run one search at a time.
- "Serena timed out, I'll use grep" → WRONG. See "If Serena Times Out" section first.

## MANDATORY: Global Search Decision Gate

**BEFORE adding `--path`, answer:**

```
Pattern contains: Payment, Transaction, Checkout, Order, Invoice,
                 Mollie, Stripe, Provider, Integration, Gateway?

YES/UNSURE → Search globally. NO --path.
NO (and user specified scope) → MAY use --path.
```

30 seconds complete > 0.5s + confusion + 30s retry.
</EXTREMELY-IMPORTANT>

## Red Flags - STOP and Check

- Using grep for PHP class/method lookup → Use Serena
- Using glob to find PHP files → Use Serena
- "Let me search src/ first" → Search globally
- Dispatching Explore agent for code navigation → Use Serena
- Running multiple serena commands in parallel → Run sequentially
- Falling back to grep after one timeout → Follow timeout steps
- Using serena for JavaScript files → Use grep (JS not indexed)
- Using serena for Twig/YAML → Use grep (not indexed)

**Check the "When to Use vs NOT Use" table.**

## Quick Reference

### Finding Code

| Task | Command |
|------|---------|
| Find class | `serena find --pattern X --kind class` |
| Find method | `serena find --pattern X --kind method` |
| Find with source | `serena find --pattern X --kind class --body` |
| Get class methods | `serena find --pattern X --kind class --depth 1` |
| Restrict to path | `serena find --pattern X --path src/` |

### Finding References

```bash
# Step 1: Find symbol to get path
serena find --pattern CustomerService --kind class

# Step 2: Find who uses it
serena refs --symbol "CustomerService" --file "src/Service/CustomerService.php"
```

### Common Commands

| Task | Command |
|------|---------|
| Check status | `serena status` |
| Regex search | `serena search --pattern "regex" --path src/` |
| File structure | `serena overview --file path.php` |
| Pre-built searches | `serena recipe --name entities` |

## Automatic Triggers

| User Says | You Run |
|-----------|---------|
| "Find class X" / "Where is X defined" | `serena find --pattern X --kind class --body` |
| "Who calls X" / "Find usages" | `serena refs --symbol X --file file.php` |
| "Find all controllers/entities" | `serena recipe --name controllers` |
| "What methods does X have" | `serena find --pattern X --kind class --depth 1` |

## When to Use vs NOT Use

| USE SERENA | DON'T USE SERENA |
|------------|------------------|
| PHP class/method/function definitions | Template files (.twig, .html) |
| Finding PHP references | JavaScript files |
| PHP code structure analysis | YAML/XML config files |
| Languages with LSP configured | Text in comments/strings |

**Rule:** Serena = languages in `.serena/project.yml`. Grep for everything else.

**This project:** Only `php` is configured. YAML/JS/Twig use grep.

**Check config:** `cat .serena/project.yml | grep -A5 "languages:"`

## Multi-File-Type Searches

When searching across PHP + JS + templates + config:

| File Type | Tool | Why |
|-----------|------|-----|
| PHP classes/methods | `serena find` | Semantic code navigation |
| JavaScript files | `grep` | JS not indexed by Intelephense |
| Twig/HTML templates | `grep` | Templates not indexed |
| YAML/XML config | `grep` | Config not indexed |

**Workflow:** Search PHP FIRST (Serena), then JS/templates/config (grep).

**Pattern expansion:** If `ShippingCost` returns nothing, try `shipping_cost` (snake_case) or translation keys.

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| "No symbols found" | Broaden pattern: `CustomerEntity` → `Customer` |
| Empty refs | Use `serena find` first to get exact symbol path |
| Incomplete results | Remove `--path` - may be missing vendor code |
| Empty results | Run `serena status` - project not activated |
| Timeout | See "If Serena Times Out" below |

## If Serena Times Out

**DO NOT immediately fall back to grep.** Try in order:

1. Run `serena status` - verify project is activated
2. Broaden pattern: `PaymentMethodProvider` → `PaymentMethod`
3. Add `--path` to reduce scope (only if NOT an integration pattern)
4. Try `serena search` (regex) instead of `serena find` (semantic)
5. Check if LSP server needs restart: `serena activate --project .`

**Only after all above fail:** Use grep WITH documentation that results may be incomplete.

**Never silently switch to grep** - incomplete results cause more problems than waiting.

## Performance Notes

- **No parallel serena commands** - LSP processes sequentially. Run one at a time.
- Global search: ~20-30s (complete results)
- Path-restricted: ~0.5-3s (may miss vendor code)
- Recipes: ~0.5s (pre-optimized)

## Verification Checklist

Before moving on from a code search task:

- [ ] Used `serena find` instead of grep for code lookup
- [ ] Used global search for integration patterns (Payment, Order, Mollie, etc.)
- [ ] Ran `serena status` if results were empty
- [ ] Used `--kind class --depth 1` to get class methods (not just `--depth 1`)

## Project Activation

```bash
serena status                              # Check current project
serena activate --project /path/to/project  # Activate if needed
```

## Deep Reference

Only read if Quick Reference doesn't answer your question:

| File | When to Read |
|------|--------------|
| `references/cli-reference.md` | Need exact parameter syntax |
| `references/symbol-kinds.md` | Filter by symbol type, symbol path format |
| `references/recipes.md` | Framework-specific searches (Oro, Mollie) |
| `references/editing-patterns.md` | Complex code edits |

**For most tasks, the Quick Reference above is sufficient.**
