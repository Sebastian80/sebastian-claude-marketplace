---
name: serena
description: "PRIMARY TOOL FOR PHP CODE NAVIGATION. Use BEFORE grep/find for: finding classes, methods, functions, interfaces; understanding file/class structure; finding symbol references ('who calls this?'); navigating OroCommerce/Symfony bundles; editing code by symbol path (safer than line-based edits); persisting context across sessions. If working with PHP code, USE THIS SKILL FIRST."
---

<EXTREMELY-IMPORTANT>
# MANDATORY: PHP Code = Serena First

If you are working with PHP code and think "let me grep for this" or "let me glob for files" - STOP.

**Use Serena FIRST. Always. No exceptions.**

This is not optional. This is not a suggestion. Serena outperforms text-based tools for:
- Finding classes/methods/functions → Semantic, not text matching
- Finding references ("who calls this?") → Actual code references, not grep noise
- Understanding code structure → Symbol tree, not blind file reading
- Editing code → By symbol path, not fragile line numbers

## Rationalizations That Mean You're About To Fail

If you catch yourself thinking ANY of these, STOP:

- "Let me just grep quickly" → WRONG. `serena find` is faster AND accurate.
- "I'll read the file to find the class" → WRONG. Use `serena find X --body`.
- "Grep will find all usages" → WRONG. Grep finds TEXT. `serena refs` finds CODE REFERENCES.
- "I know the file path already" → WRONG. Still use `serena overview`.
- "This is a simple search" → WRONG. Simple searches benefit MOST from semantic tools.
- "I'll use the Task/Explore agent" → WRONG for PHP. Use Serena directly.
- "Let me glob for PHP files first" → WRONG. `serena find` searches ALL PHP files semantically.

**If a Serena operation exists for your task, you MUST use it.**
</EXTREMELY-IMPORTANT>

# Serena CLI - Professional PHP Code Intelligence

## LSP Backend

**Intelephense Premium** - Licensed PHP language server providing:
- Semantic symbol search (not text matching)
- Find implementations of interfaces/abstract classes
- Find all references to symbols
- Type hierarchy navigation
- Accurate code navigation across the entire codebase

## Setup

The CLI is at `~/.claude/skills/serena/scripts/serena`. All commands are auto-accepted.

```bash
# Option 1: Use full path
~/.claude/skills/serena/scripts/serena find Customer

# Option 2: Create alias (add to ~/.bashrc or ~/.zshrc)
alias serena='~/.claude/skills/serena/scripts/serena'

# Option 3: Symlink to PATH
ln -s ~/.claude/skills/serena/scripts/serena ~/bin/serena
```

## Quick Reference (Cheat Sheet)

| Task | Command |
|------|---------|
| Find class/symbol | `serena find Customer` |
| Find with body | `serena find Customer --body` |
| Find only classes | `serena find Customer --kind class` |
| Find only methods | `serena find "get*" --kind method` |
| Who calls this? | `serena refs ClassName file.php` |
| Who calls method? | `serena refs "Class/method" file.php` |
| File structure | `serena overview file.php` |
| Find entities | `serena recipe entities` |
| Find controllers | `serena recipe controllers` |
| Find listeners | `serena recipe listeners` |
| Regex search | `serena search "pattern" --glob "src/**/*.php"` |
| Read memory | `serena memory read name` |
| Write memory | `serena memory write name "content"` |
| Check status | `serena status` |

## Quick Start

```bash
# Check connection
serena status

# Find a class
serena find Customer --body

# Find who calls a method
serena refs "Customer/getName" src/Entity/Customer.php

# Get file structure
serena overview src/Entity/Customer.php

# Common recipes
serena recipe entities
serena recipe controllers
serena recipe listeners
```

## Commands

### serena find - Find Symbols

```bash
serena find <pattern> [options]

Options:
  --body, -b          Include symbol body code
  --path, -p PATH     Restrict to file/directory
  --depth, -d N       Traversal depth (0=symbol, 1=children)
  --kind, -k KIND     Filter: class, method, interface, function
  --exact, -e         Exact match only (no substring)
  --json, -j          Output JSON format

Examples:
  serena find Customer                    # Find anything with "Customer"
  serena find Customer --kind class       # Only classes
  serena find "get*" --kind method        # Methods starting with get
  serena find Customer --body             # Include implementation
  serena find Order --path src/Meyer/     # Restrict to directory
```

### serena refs - Find References

```bash
serena refs <symbol> <file>

Examples:
  serena refs "Customer/getName" src/Entity/Customer.php
  serena refs "ShippingMethod" src/Meyer/ShippingBundle/Method/ShippingMethod.php
```

### serena overview - File Structure

```bash
serena overview <file>

Examples:
  serena overview src/Entity/Customer.php
  serena overview src/Meyer/ShippingBundle/Provider/RatesProvider.php
```

### serena search - Regex Search

```bash
serena search <pattern> [--glob GLOB]

Examples:
  serena search "implements.*Interface" --glob "src/**/*.php"
  serena search "#\[ORM\\Entity" --glob "src/**/*.php"
  serena search "throw new.*Exception"
```

### serena recipe - Pre-built Operations

```bash
serena recipe <name>

Recipes:
  entities      Find all Doctrine entities (#[ORM\Entity])
  controllers   Find all *Controller classes
  services      Find all *Service classes
  interfaces    Find all interfaces
  tests         Find all *Test classes
  listeners     Find all event listeners
  commands      Find all console commands

Examples:
  serena recipe entities
  serena recipe controllers
  serena recipe list          # Show all recipes
```

### serena memory - Persistent Storage

```bash
serena memory list                    # List all memories
serena memory read <name>             # Read a memory
serena memory write <name> <content>  # Write (use - for stdin)
serena memory delete <name>           # Delete

Examples:
  serena memory list
  serena memory read project_overview
  serena memory write task_context "Working on feature X"
  echo "Multi-line content" | serena memory write notes -
```

### serena edit - Symbol-based Editing

```bash
serena edit replace <symbol> <file> <body>   # Replace symbol body
serena edit after <symbol> <file> <code>     # Insert after symbol
serena edit before <symbol> <file> <code>    # Insert before symbol
serena edit rename <symbol> <file> <newname> # Rename symbol

Examples:
  serena edit replace "Customer/getName" src/Entity/Customer.php "return \$this->name;"
  serena edit after "Customer/__construct" src/Entity/Customer.php "public function newMethod() {}"
  serena edit rename "Customer/getName" src/Entity/Customer.php "getFullName"
```

### serena status - Check Connection

```bash
serena status                # Show config and active tools
```

### serena tools - List Serena Tools

```bash
serena tools                 # List all available Serena operations
```

## Automatic Triggers

**Use Serena IMMEDIATELY when user asks ANY of these:**

| User Request Pattern | Serena Command |
|---------------------|----------------|
| "Find class X" / "Where is X defined" | `serena find X --body` |
| "Who calls X" / "Find usages of X" | `serena refs X/method file.php` |
| "How does X work" / "Show me X" | `serena find X --body` |
| "Find all controllers/entities" | `serena recipe controllers` |
| "What methods does X have" | `serena overview file.php` |
| "Refactor X" / "Rename X" | `serena refs` then `serena edit` |

## Autonomous Workflows

### Workflow 1: Find Where X is Defined

```bash
serena find ClassName --body
serena overview path/from/result.php   # If need structure
```

### Workflow 2: Who Calls X

```bash
serena find ClassName/methodName       # Get file path
serena refs "ClassName/methodName" path/to/file.php
```

### Workflow 3: Full Exploration

```bash
serena find MainClass --body           # Find entry point
serena overview path/to/MainClass.php  # Get structure
serena refs MainClass path/to/file.php # Find integration points
serena memory read bundle_architecture # Check existing context
```

### Workflow 4: Safe Refactoring

```bash
serena find X --body                   # Understand the symbol
serena refs X path/to/file.php         # Find ALL affected places
# Review each reference
serena edit replace "X/method" file.php "new body"
# Or for renames:
serena edit rename "X/oldMethod" file.php "newMethod"
```

### Workflow 5: Debug/Trace Issue

```bash
serena find ErrorClass/errorMethod --body   # Find error location
serena refs "ErrorClass/errorMethod" path.php   # Trace callers
# Repeat for each caller until root cause found
serena memory write debug_trace "## Call Chain: ..."
```

## Anti-Patterns (NEVER DO THIS)

| BAD (Text-based) | GOOD (Semantic) |
|------------------|-----------------|
| `grep "class Customer"` | `serena find Customer --kind class` |
| `grep "->getName("` | `serena refs "Class/getName" file.php` |
| `glob "**/*Customer*.php"` | `serena find Customer` |
| Read file to find class | `serena overview file.php` |
| Edit by line number | `serena edit replace Symbol file.php` |
| Task agent for PHP | `serena` directly |

## Fallback Rules

**Only fall back to grep/glob when Serena genuinely can't help:**

1. **Empty results?** Broaden the pattern: `CustomerEntity` → `Customer`
2. **Still empty?** Check: `serena status` (is project activated?)
3. **Truly can't help?** State why: "Serena returned empty, falling back to grep"
4. **Use standard tools for:** non-PHP files, creating new files, reading logs

## Symbol Path Convention

- **Class**: `Customer` or `Meyer\Bundle\Entity\Customer`
- **Method**: `Customer/getName` or `Customer/__construct`
- **Property**: `Customer/$name`
- **Wildcard**: `*Controller`, `Customer/*`

## Symbol Kinds

| Kind | Name | Filter |
|------|------|--------|
| 3 | Namespace | `--kind namespace` |
| 5 | Class | `--kind class` |
| 6 | Method | `--kind method` |
| 7 | Property | `--kind property` |
| 11 | Interface | `--kind interface` |
| 12 | Function | `--kind function` |
| 14 | Constant | `--kind constant` |

Multiple kinds: `--kind class interface` (space-separated)

## Session Persistence

```bash
# Save context before ending
serena memory write task_context "## Current Task
Working on X feature
## Progress
- [x] Found classes
- [ ] Implement changes
## Key Files
- src/Service/X.php"

# Resume in next session
serena memory list
serena memory read task_context
```

## Output Formats

```bash
serena find Customer              # Human-readable
serena find Customer --json       # JSON for processing
serena find Customer -j | jq '.[] | .name_path'
```

## Verification

```bash
serena status              # Check connection, list tools
serena find Controller     # Test semantic search works
```

## Architecture: How Serena Works

```
┌─────────────────────┐      HTTP POST       ┌────────────────────────┐
│ serena CLI          │ ◄──────────────────► │ Serena MCP Server      │
│ ~/.../scripts/serena│   localhost:9121     │ (Centralized)          │
│                     │                      │                        │
│ Python wrapper that │                      │ ┌────────────────────┐ │
│ translates commands │                      │ │ Intelephense LSP   │ │
│ to MCP tool calls   │                      │ │ (Premium License)  │ │
└─────────────────────┘                      │ └────────────────────┘ │
                                             │                        │
                                             │ Semantic PHP analysis: │
                                             │ - Symbol indexing      │
                                             │ - Type inference       │
                                             │ - Reference tracking   │
                                             │ - Project-wide search  │
                                             └────────────────────────┘
```

**Key points:**
- The `serena` CLI is just a thin Python wrapper
- All semantic intelligence comes from the MCP server
- The server runs Intelephense Premium (licensed PHP LSP)
- Session state is managed via HTTP headers (`mcp-session-id`)
- Project activation is required before searching

## Troubleshooting

### "No symbols found" Error

**Causes:**
1. Pattern too specific (e.g., full namespace vs short name)
2. Project not activated
3. Typo in symbol name

**Fixes:**
```bash
# Broaden the pattern
serena find CustomerEntityListener     # Too specific?
serena find CustomerEntity             # Still nothing?
serena find Customer                   # Broader - should find more

# Check project activation
serena status
# If "Active project: None" or wrong project:
serena activate /path/to/project
```

### "No references found" Error

**The #1 cause: Wrong symbol path format.**

The `refs` command requires the EXACT symbol path as returned by `find`.

```bash
# WRONG - guessing the path
serena refs "addDeCert" src/file.php                    # Missing class prefix!
serena refs "CustomerListener/addDeCert" src/file.php   # Wrong class name!

# CORRECT - use find first to get exact path
serena find addDeCert --kind method
# Output: CustomerEntityListener/addDeCert at src/.../CustomerEntityListener.php:68

# Now use the EXACT path from output
serena refs "CustomerEntityListener/addDeCert" src/Meyer/CustomerBundle/EventListener/CustomerEntityListener.php
```

**Other causes:**
- Method is truly never called (check for commented-out code with grep)
- Method is called dynamically (reflection, magic methods)
- References are in non-PHP files (YAML config, XML) - use grep instead

### refs Returns Empty But Method IS Called

**The method might be called from YAML/XML config (not PHP code).**

Serena only understands PHP. Symfony/Oro often wire listeners via YAML:

```bash
# Serena sees: no PHP code calls this
serena refs "CustomerEntityListener/addDeSpecificationsOnPrePersist" src/file.php
# Returns empty!

# But grep finds the YAML binding:
grep -r "addDeSpecificationsOnPrePersist" --include="*.yml" src/
# Output: doctrine.orm.entity_listener config!
```

**Solution: Combine Serena + grep for full picture.**

### serena overview Returns Minimal Info

The `overview` command shows file structure, not implementation details.

```bash
# If overview is too brief:
serena overview src/Entity/Customer.php
# Returns: just Namespace + Class

# Get more detail with find + body:
serena find Customer --body --path src/Entity/Customer.php
```

### Connection Errors

```bash
# Check if server is running
serena status

# If "Cannot connect to Serena":
# 1. Check server is running on localhost:9121
# 2. Check SERENA_URL environment variable
# 3. Restart the Serena server if needed
```

### Project Not Indexed

After first activation, Serena needs time to index:

```bash
serena activate /path/to/project
# Wait a few seconds for indexing

serena find SomeClass  # Should work now
```

## When to Use Grep Instead of Serena

| Scenario | Why Grep |
|----------|----------|
| Search YAML/XML config | Serena only parses PHP |
| Find service definitions | Usually in `services.yml` |
| Find Doctrine listener bindings | In `entity_listener.yml` |
| Search Twig templates | Not PHP |
| Find text in comments | Serena ignores comments |
| Check if something exists ANYWHERE | Grep is file-type agnostic |

**Hybrid workflow example:**

```bash
# 1. Find PHP implementation with Serena
serena find CustomerEntityListener --body

# 2. Find how it's wired with grep
grep -r "CustomerEntityListener" --include="*.yml" --include="*.xml" src/

# 3. Find where it's used in templates
grep -r "customer" --include="*.twig" src/
```

## Common Symbol Path Patterns

| Symbol Type | Path Format | Example |
|-------------|-------------|---------|
| Class | `ClassName` | `CustomerEntityListener` |
| Method | `Class/method` | `CustomerEntityListener/addDeCert` |
| Constructor | `Class/__construct` | `Customer/__construct` |
| Property | `Class/$property` | `Customer/$name` |
| Interface | `InterfaceName` | `EntityConverterInterface` |
| Constant | `Class/CONSTANT` | `CustomerEntityListener/CERT_CODE_ONLY_DE` |

## refs: What It Returns

The refs command returns **symbols that REFERENCE the target**, not lines of code:

```bash
serena refs "RatesProvider/getPricesForTypes" src/Meyer/ShippingBundle/Provider/RatesProvider.php

# Returns:
# [Method] ShippingMethod/calculatePrices     <- This METHOD calls getPricesForTypes
# [Method] ShippingMethodType/calculatePrice  <- This METHOD also calls it

# NOT:
# src/file.php:123: $this->ratesProvider->getPricesForTypes(...)  <- grep would show this
```

This is more useful for understanding code structure, but sometimes you want grep for the exact lines.
