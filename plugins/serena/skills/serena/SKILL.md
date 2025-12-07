---
name: serena
description: "Use when grep returns too many matches, you need to find all method callers, or want to understand codebase structure - semantic code navigation via LSP that replaces grep/glob with symbol-aware search across 30+ languages. Finds exact definitions, all references, file structure without text-matching noise. Triggers: where is X defined, who calls this, find all usages, show class structure, find implementations"
---

<EXTREMELY-IMPORTANT>
# MANDATORY: Code Navigation = Serena First

If you are working with code in a Serena-configured language and think "let me grep for this" or "let me glob for files" - STOP.

**Use Serena FIRST. Always. No exceptions.**

This is not optional. This is not a suggestion. Serena outperforms text-based tools for:
- Finding classes/methods/functions → Semantic, not text matching
- Finding references ("who calls this?") → Actual code references, not grep noise
- Understanding code structure → Symbol tree, not blind file reading
- Editing code → By symbol path, not fragile line numbers

## Rationalizations That Mean You're About To Fail

If you catch yourself thinking ANY of these, STOP:

- "Let me just grep quickly" → WRONG. `$SERENA find` is faster AND accurate.
- "I'll read the file to find the class" → WRONG. Use `$SERENA find X --body`.
- "Grep will find all usages" → WRONG. Grep finds TEXT. `$SERENA refs` finds CODE REFERENCES.
- "I know the file path already" → WRONG. Still use `$SERENA overview`.
- "This is a simple search" → WRONG. Simple searches benefit MOST from semantic tools.
- "I'll use the Task/Explore agent" → WRONG. Use Serena directly or serena-explore agent.
- "Let me glob for files first" → WRONG. `$SERENA find` searches semantically.
- "serena command not found" → WRONG. You forgot to set `$SERENA` variable. See Setup section.

**If a Serena operation exists for your task, you MUST use it.**
</EXTREMELY-IMPORTANT>

## Automatic Triggers

**Use Serena IMMEDIATELY when user asks ANY of these:**

| User Request Pattern | Serena Command |
|---------------------|----------------|
| "Find class X" / "Where is X defined" | `$SERENA find X --body` |
| "Who calls X" / "Find usages of X" | `$SERENA refs X/method file.php` |
| "How does X work" / "Show me X" | `$SERENA find X --body` |
| "Find all controllers/entities" | `$SERENA_FULL recipe controllers` |
| "What methods does X have" | `$SERENA overview file.php` |
| "Refactor X" / "Rename X" | `$SERENA refs` then `$SERENA_FULL edit` |

## When to Use vs When NOT to Use

| ✅ USE SERENA | ❌ USE GREP INSTEAD |
|---------------|---------------------|
| Finding class/method/function definitions | Searching template files (.twig, .html) |
| Tracing who calls a method ("find refs") | Finding text in comments |
| Understanding file/class structure | Searching languages NOT in project.yml |
| Navigating languages configured in `.serena/project.yml` | Finding strings/literals across all files |
| Refactoring by symbol path | Log files, .env files |
| Cross-file symbol references | Hybrid search (code + config) |

**Rule:** Serena for CONFIGURED LANGUAGES. Grep for UNCONFIGURED/TEMPLATES/COMMENTS.
**Note:** Run `$SERENA status` to see active languages. Edit `.serena/project.yml` to add more.

# Serena CLI - Semantic Code Intelligence (30+ Languages)

## LSP Backend

**Language Server Protocol** - Multiple language servers providing:
- Semantic symbol search (not text matching)
- Find implementations of interfaces/abstract classes
- Find all references to symbols
- Type hierarchy navigation
- Accurate code navigation across the entire codebase

**Supported Languages:** AL, Bash, C++, C#, Clojure, Dart, Elixir, Elm, Erlang, Fortran, Go, Haskell, Java, JavaScript, Julia, Kotlin, Lua, Markdown, Nix, Perl, PHP, Python, R, Rego, Ruby, Rust, Scala, Swift, Terraform, TypeScript, YAML, Zig

**Note:** Check `.serena/project.yml` for which languages are configured in your project.

## Setup - CRITICAL

**You MUST use the full path. Bare `serena` commands will NOT work.**

Two CLI options available:

| Script | Speed | Use Case |
|--------|-------|----------|
| `$SERENA` | ~90ms | Fast bash+jq wrapper (recommended) |
| `$SERENA_FULL` | ~200ms | Full Python client, recipes, stdin |

```bash
# MANDATORY: Define these variables before ANY Serena command
SERENA=~/.claude/plugins/marketplaces/sebastian-marketplace/plugins/serena/skills/serena/scripts/serena-fast
SERENA_FULL=~/.claude/plugins/marketplaces/sebastian-marketplace/plugins/serena/skills/serena/scripts/serena

# Then use $SERENA for all commands:
$SERENA find Customer
$SERENA refs "Customer/getName" src/Entity/Customer.php
$SERENA overview src/Entity/Customer.php

# Use $SERENA_FULL for recipes:
$SERENA_FULL recipe entities
```

## MANDATORY First Action

Before ANY code exploration, run this:

```bash
SERENA=~/.claude/plugins/marketplaces/sebastian-marketplace/plugins/serena/skills/serena/scripts/serena-fast
$SERENA status
```

**Did not run this first? STOP. Run it NOW.**

## Quick Reference (Cheat Sheet)

| Task | Command |
|------|---------|
| Find class/symbol | `$SERENA find Customer` |
| Find with body | `$SERENA find Customer --body` |
| Find only classes | `$SERENA find Customer --kind class` |
| Find only methods | `$SERENA find "get*" --kind method` |
| Who calls this? | `$SERENA refs ClassName file.php` |
| Who calls method? | `$SERENA refs "Class/method" file.php` |
| File structure | `$SERENA overview file.php` |
| Find entities | `$SERENA_FULL recipe entities` |
| Find controllers | `$SERENA_FULL recipe controllers` |
| Find listeners | `$SERENA_FULL recipe listeners` |
| Regex search | `$SERENA search "pattern" --glob "src/**/*.php"` |
| Read memory | `$SERENA_FULL memory read name` |
| Write memory | `$SERENA_FULL memory write name "content"` |
| Check status | `$SERENA status` |

## Quick Start

```bash
# FIRST: Set up the path variable
SERENA=~/.claude/plugins/marketplaces/sebastian-marketplace/plugins/serena/skills/serena/scripts/serena-fast
SERENA_FULL=~/.claude/plugins/marketplaces/sebastian-marketplace/plugins/serena/skills/serena/scripts/serena

# Check connection
$SERENA status

# Find a class
$SERENA find Customer --body

# Find who calls a method
$SERENA refs "Customer/getName" src/Entity/Customer.php

# Get file structure
$SERENA overview src/Entity/Customer.php

# Common recipes (need full version)
$SERENA_FULL recipe entities
$SERENA_FULL recipe controllers
$SERENA_FULL recipe listeners
```

## Commands

### $SERENA find - Find Symbols

```bash
$SERENA find <pattern> [options]

Options:
  --body, -b          Include symbol body code
  --path, -p PATH     Restrict to file/directory
  --depth, -d N       Traversal depth (0=symbol, 1=children)
  --kind, -k KIND     Filter: class, method, interface, function
  --exact, -e         Exact match only (no substring)
  --json, -j          Output JSON format

Examples:
  $SERENA find Customer                    # Find anything with "Customer"
  $SERENA find Customer --kind class       # Only classes
  $SERENA find "get*" --kind method        # Methods starting with get
  $SERENA find Customer --body             # Include implementation
  $SERENA find Order --path src/Meyer/     # Restrict to directory
```

### $SERENA refs - Find References

```bash
$SERENA refs <symbol> <file> [--all]

Options:
  --all, -a    Show all references (default: top 10 files)

Examples:
  $SERENA refs "Customer/getName" src/Entity/Customer.php
  $SERENA refs "ShippingMethod" src/Meyer/ShippingBundle/Method/ShippingMethod.php
  $SERENA refs Tool src/tools.py --all   # Show all references
```

### $SERENA overview - File Structure

```bash
$SERENA overview <file>

Examples:
  $SERENA overview src/Entity/Customer.php
  $SERENA overview src/Meyer/ShippingBundle/Provider/RatesProvider.php
```

### $SERENA search - Regex Search

```bash
$SERENA search <pattern> [--glob GLOB]

Examples:
  $SERENA search "implements.*Interface" --glob "src/**/*.php"
  $SERENA search "#\[ORM\\Entity" --glob "src/**/*.php"
  $SERENA search "throw new.*Exception"
```

### $SERENA_FULL recipe - Pre-built Operations

```bash
$SERENA_FULL recipe <name>

Recipes:
  entities      Find all Doctrine entities (#[ORM\Entity])
  controllers   Find all *Controller classes
  services      Find all *Service classes
  interfaces    Find all interfaces
  tests         Find all *Test classes
  listeners     Find all event listeners
  commands      Find all console commands

Examples:
  $SERENA_FULL recipe entities
  $SERENA_FULL recipe controllers
  $SERENA_FULL recipe list          # Show all recipes
```

### $SERENA_FULL memory - Persistent Storage

```bash
$SERENA_FULL memory list                    # List all memories
$SERENA_FULL memory read <name>             # Read a memory
$SERENA_FULL memory write <name> <content>  # Write (use - for stdin)
$SERENA_FULL memory delete <name>           # Delete

Examples:
  $SERENA_FULL memory list
  $SERENA_FULL memory read project_overview
  $SERENA_FULL memory write task_context "Working on feature X"
  echo "Multi-line content" | $SERENA_FULL memory write notes -
```

### $SERENA_FULL edit - Symbol-based Editing

```bash
$SERENA_FULL edit replace <symbol> <file> <body>   # Replace symbol body
$SERENA_FULL edit after <symbol> <file> <code>     # Insert after symbol
$SERENA_FULL edit before <symbol> <file> <code>    # Insert before symbol
$SERENA_FULL edit rename <symbol> <file> <newname> # Rename symbol

Examples:
  $SERENA_FULL edit replace "Customer/getName" src/Entity/Customer.php "return \$this->name;"
  $SERENA_FULL edit after "Customer/__construct" src/Entity/Customer.php "public function newMethod() {}"
  $SERENA_FULL edit rename "Customer/getName" src/Entity/Customer.php "getFullName"
```

### $SERENA status - Check Connection

```bash
$SERENA status                # Show config and active tools
```

### $SERENA_FULL tools - List Serena Tools

```bash
$SERENA_FULL tools                 # List all available Serena operations
```

## Autonomous Workflows

### Workflow 1: Find Where X is Defined

```bash
$SERENA find ClassName --body
$SERENA overview path/from/result.php   # If need structure
```

### Workflow 2: Who Calls X

```bash
$SERENA find ClassName/methodName       # Get file path
$SERENA refs "ClassName/methodName" path/to/file.php
```

### Workflow 3: Full Exploration

```bash
$SERENA find MainClass --body           # Find entry point
$SERENA overview path/to/MainClass.php  # Get structure
$SERENA refs MainClass path/to/file.php # Find integration points
$SERENA_FULL memory read bundle_architecture # Check existing context
```

### Workflow 4: Safe Refactoring

```bash
$SERENA find X --body                   # Understand the symbol
$SERENA refs X path/to/file.php         # Find ALL affected places
# Review each reference
$SERENA_FULL edit replace "X/method" file.php "new body"
# Or for renames:
$SERENA_FULL edit rename "X/oldMethod" file.php "newMethod"
```

### Workflow 5: Debug/Trace Issue

```bash
$SERENA find ErrorClass/errorMethod --body   # Find error location
$SERENA refs "ErrorClass/errorMethod" path.php   # Trace callers
# Repeat for each caller until root cause found
$SERENA_FULL memory write debug_trace "## Call Chain: ..."
```

## Anti-Patterns (NEVER DO THIS)

| BAD (Text-based) | GOOD (Semantic) |
|------------------|-----------------|
| `grep "class Customer"` | `$SERENA find Customer --kind class` |
| `grep "->getName("` | `$SERENA refs "Class/getName" file.php` |
| `glob "**/*Customer*.php"` | `$SERENA find Customer` |
| Read file to find class | `$SERENA overview file.php` |
| Edit by line number | `$SERENA_FULL edit replace Symbol file.php` |
| Generic Task/Explore agent | `$SERENA` directly or `serena-explore` agent |

## Performance Best Practices

### Always Use --path for Speed

LSP must search the entire indexed codebase without `--path`. Use path restriction:

| Search | Time | Notes |
|--------|------|-------|
| `$SERENA find Payment --path src/` | **0.7s** | Custom code only |
| `$SERENA find Payment --path vendor/mollie/` | **2-3s** | Specific vendor |
| `$SERENA find Payment --path vendor/oro/` | **5-10s** | Large framework |
| `$SERENA find Payment` (no path) | **28s+** | All indexed vendors |

```bash
# FAST: Always specify path when you know the scope
$SERENA find Payment --kind class --path src/
$SERENA find Payment --kind class --path vendor/mollie/

# SLOW: Avoid searching entire codebase
$SERENA find Payment --kind class  # Searches everything
```

### Vendor Exclusions

Configure `.serena/project.yml` to exclude unneeded vendors:

```yaml
ignored_paths:
  - "vendor/fakerphp"      # Test data generators
  - "vendor/phpunit"       # Test framework
  - "vendor/symfony"       # Use Oro's extensions instead
  - "vendor/**/Tests"      # Test directories
```

Keep only what you need: `oro/*`, `mollie/*`, `meyer/*`, `netresearch/*`

### serena-fast Grouped Output

The fast CLI groups results by src/vendor and bundle:

```
=== src ===
Meyer/PaymentBundle/
  Class  PaymentController     Controller/:15
  Class  PaymentService        Service/:20

=== vendor ===
mollie/orocommerce/
  Class  MolliePayment         PaymentMethod/:12
```

## Smart Search Strategy

### Progressive Search (Broad → Narrow)

Start with broad patterns, narrow only if too many results:

```bash
# GOOD: Start broad with path restriction
$SERENA find Payment --path src/         # Custom code first
$SERENA find Payment --kind class        # Only classes
$SERENA find Payment                     # Full search if needed

# BAD: Too specific (may fail during indexing)
$SERENA find PaymentMethodProviderInterface  # Very specific name
$SERENA find Oro\\Bundle\\PaymentBundle      # Namespaces often fail
```

### Good vs Bad Search Patterns

| ❌ BAD | ✅ GOOD |
|--------|---------|
| `$SERENA find PaymentMethodInterface` | `$SERENA find Payment --kind interface` |
| `$SERENA find CustomerEntityListener` | `$SERENA find Customer --kind class` |
| `$SERENA find addDeSpecificationsOnPrePersist` | `$SERENA find addDe --kind method` |

### 3-Strike Rule

Try up to 3 progressively broader patterns before falling back:

```bash
# Strike 1: Specific
$SERENA find PaymentMethodInterface --kind interface
# Exit 1? → broaden

# Strike 2: Shorter
$SERENA find PaymentMethod --kind interface
# Exit 1? → broaden more

# Strike 3: Minimal
$SERENA find Payment --kind interface
# Exit 1? → fall back to grep
```

### Indexing Awareness

LSP indexes `src/` before `vendor/`. During initial indexing:

```bash
# Likely works (local code indexed first):
$SERENA find Customer --path src/Meyer/

# May fail until fully indexed:
$SERENA find Mollie --path vendor/
```

**State what's happening:** "Serena can't find X in vendor/ yet (still indexing), using grep"

## Fallback Rules

**Only fall back to grep/glob when Serena genuinely can't help:**

1. **Empty results?** Broaden the pattern: `CustomerEntity` → `Customer`
2. **Still empty?** Try `--path src/` (indexed faster than vendor/)
3. **3 strikes and out?** Fall back to grep, state why
4. **Use grep/glob for:** templates (.twig), XML configs, .env files, comments/strings

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
$SERENA_FULL memory write task_context "## Current Task
Working on X feature
## Progress
- [x] Found classes
- [ ] Implement changes
## Key Files
- src/Service/X.php"

# Resume in next session
$SERENA_FULL memory list
$SERENA_FULL memory read task_context
```

## Output Formats

The CLI outputs optimized human-readable format by default, JSON with `-j` flag:

```bash
$SERENA find Customer              # Human-readable (token-efficient)
$SERENA -j find Customer           # JSON for processing
$SERENA -j find Customer | jq '.[] | .name_path'
```

### Human-Readable Output Examples

**find with depth (shows methods):**
```
Tool (class) src/serena/tools/tools_base.py:107-300
  ├─ get_name_from_cls() :118-125
  ├─ get_name() :127-128
  ├─ can_edit() :136-143
  └─ apply_ex() :222-296
     ... +10 more methods
```

**refs (grouped by file with context):**
```
77 references to 'Tool'

  src/serena/agent.py:
    :26  from serena.tools import Tool, ToolRegistry
    :49  def __init__(self, tools: list[Tool]):
    ... +8 more in this file
  src/serena/mcp.py:
    :168  def make_mcp_tool(tool: Tool, ...) -> MCPTool:
  ... +10 more files (use --all to show all)
```

**overview (grouped by kind):**
```
src/serena/tools/tools_base.py (15 symbols)

  CLASSES:
    Component:30-65
    Tool:107-300
    ToolRegistry:359-430
  CONSTANTS: T, SUCCESS_RESULT
  VARIABLES: log
```

**search (with summary):**
```
Pattern: 'class.*Tool' in src/**/*.py
Found 12 matches in 5 files

  src/serena/tools/tools_base.py:
    107: class Tool(Component):
    358: class ToolRegistry:
```

## Verification

```bash
$SERENA status              # Check connection, list tools
$SERENA find Controller     # Test semantic search works
```

## Architecture: How Serena Works

```
┌─────────────────────┐      HTTP POST       ┌────────────────────────┐
│ serena CLI          │ ◄──────────────────► │ Serena MCP Server      │
│ ~/.../scripts/serena│   localhost:9121     │ (Centralized)          │
│                     │                      │                        │
│ Python wrapper that │                      │ ┌────────────────────┐ │
│ translates commands │                      │ │ Language Servers   │ │
│ to MCP tool calls   │                      │ │ (30+ LSP backends) │ │
└─────────────────────┘                      │ └────────────────────┘ │
                                             │                        │
                                             │ Semantic code analysis:│
                                             │ - Symbol indexing      │
                                             │ - Type inference       │
                                             │ - Reference tracking   │
                                             │ - Project-wide search  │
                                             └────────────────────────┘
```

**Key points:**
- The `serena` CLI is just a thin Python wrapper
- All semantic intelligence comes from the MCP server
- The server runs language-specific LSP backends (30+ languages supported)
- Session state is managed via HTTP headers (`mcp-session-id`)
- Project activation is required before searching
- Languages configured in `.serena/project.yml`

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| "No symbols found" | Pattern too specific or project not activated | Broaden pattern (`CustomerEntity` → `Customer`), run `$SERENA status` |
| "No references found" | Wrong symbol path format | Use `$SERENA find X` first to get exact path, then use that in `refs` |
| refs empty but method IS called | Called from config files, not code | Combine: `$SERENA refs` for code + `grep` for YAML/XML configs |
| overview too brief | Shows structure only, not implementation | Use `$SERENA find X --body` instead |
| Connection errors | Server not running | Run `$SERENA status`, check localhost:9121 |
| Project not indexed | First activation needs time | Wait a few seconds after `$SERENA_FULL activate`, then retry |
| "command not found" | Using bare `serena` without path | **ALWAYS use `$SERENA` variable with full path** |

**Key rule for refs:** Always `$SERENA find X` first → copy exact symbol path → use in `$SERENA refs "ExactPath" file.php`

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

The refs command shows **files and context where the symbol is referenced**, grouped by file:

```bash
$SERENA refs "RatesProvider/getPricesForTypes" src/Meyer/ShippingBundle/Provider/RatesProvider.php

# Returns:
# 12 references to 'RatesProvider/getPricesForTypes'
#
#   src/Meyer/ShippingBundle/Method/ShippingMethod.php:
#     :145  $prices = $this->ratesProvider->getPricesForTypes($types);
#     :203  return $this->ratesProvider->getPricesForTypes($filtered);
#   src/Meyer/ShippingBundle/Service/PriceCalculator.php:
#     :78   $rates = $provider->getPricesForTypes($items);
#   ... +3 more files (use --all to show all)
```

This shows:
- Total count at the top for quick impact assessment
- Grouped by file for easy navigation
- Context snippets showing how the symbol is used
- Truncated by default (use `--all` to see everything)

For large refactoring, use `--all` to see every reference.
