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

- "Let me just grep quickly" → WRONG. `serena find` is faster AND accurate.
- "I'll read the file to find the class" → WRONG. Use `serena find X --body`.
- "Grep will find all usages" → WRONG. Grep finds TEXT. `serena refs` finds CODE REFERENCES.
- "I know the file path already" → WRONG. Still use `serena overview`.
- "This is a simple search" → WRONG. Simple searches benefit MOST from semantic tools.
- "I'll use the Task/Explore agent" → WRONG. Use Serena directly or serena-explore agent.
- "Let me glob for files first" → WRONG. `serena find` searches semantically.

**If a Serena operation exists for your task, you MUST use it.**
</EXTREMELY-IMPORTANT>

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
**Note:** Run `serena status` to see active languages. Edit `.serena/project.yml` to add more.

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

## Setup

Two CLI options available:

| Script | Speed | Use Case |
|--------|-------|----------|
| `serena` | ~200ms | Full-featured Python client, recipes, stdin support |
| `serena-fast` | ~90ms | Ultra-fast bash+jq wrapper, grouped output |

```bash
# Scripts location
SERENA_DIR=~/.claude/plugins/marketplaces/sebastian-marketplace/plugins/serena/skills/serena/scripts

# Fast version (recommended for find/refs/overview)
$SERENA_DIR/serena-fast find Customer

# Full version (for recipes, complex operations)
$SERENA_DIR/serena find Customer

# Create aliases (add to ~/.bashrc or ~/.zshrc)
alias serena='$SERENA_DIR/serena'
alias sf='$SERENA_DIR/serena-fast'  # Quick alias for fast version
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
serena refs <symbol> <file> [--all]

Options:
  --all, -a    Show all references (default: top 10 files)

Examples:
  serena refs "Customer/getName" src/Entity/Customer.php
  serena refs "ShippingMethod" src/Meyer/ShippingBundle/Method/ShippingMethod.php
  serena refs Tool src/tools.py --all   # Show all references
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
| Generic Task/Explore agent | `serena` directly or `serena-explore` agent |

## Performance Best Practices

### Always Use --path for Speed

LSP must search the entire indexed codebase without `--path`. Use path restriction:

| Search | Time | Notes |
|--------|------|-------|
| `find Payment --path src/` | **0.7s** | Custom code only |
| `find Payment --path vendor/mollie/` | **2-3s** | Specific vendor |
| `find Payment --path vendor/oro/` | **5-10s** | Large framework |
| `find Payment` (no path) | **28s+** | All indexed vendors |

```bash
# FAST: Always specify path when you know the scope
serena-fast find Payment --kind class --path src/
serena-fast find Payment --kind class --path vendor/mollie/

# SLOW: Avoid searching entire codebase
serena-fast find Payment --kind class  # Searches everything
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
serena find Payment --path src/         # Custom code first
serena find Payment --kind class        # Only classes
serena find Payment                     # Full search if needed

# BAD: Too specific (may fail during indexing)
serena find PaymentMethodProviderInterface  # Very specific name
serena find Oro\\Bundle\\PaymentBundle      # Namespaces often fail
```

### Good vs Bad Search Patterns

| ❌ BAD | ✅ GOOD |
|--------|---------|
| `find PaymentMethodInterface` | `find Payment --kind interface` |
| `find CustomerEntityListener` | `find Customer --kind class` |
| `find addDeSpecificationsOnPrePersist` | `find addDe --kind method` |

### 3-Strike Rule

Try up to 3 progressively broader patterns before falling back:

```bash
# Strike 1: Specific
serena find PaymentMethodInterface --kind interface
# Exit 1? → broaden

# Strike 2: Shorter
serena find PaymentMethod --kind interface
# Exit 1? → broaden more

# Strike 3: Minimal
serena find Payment --kind interface
# Exit 1? → fall back to grep
```

### Indexing Awareness

LSP indexes `src/` before `vendor/`. During initial indexing:

```bash
# Likely works (local code indexed first):
serena find Customer --path src/Meyer/

# May fail until fully indexed:
serena find Mollie --path vendor/
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

The CLI outputs optimized human-readable format by default, JSON with `-j` flag:

```bash
serena find Customer              # Human-readable (token-efficient)
serena -j find Customer           # JSON for processing
serena -j find Customer | jq '.[] | .name_path'
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
| "No symbols found" | Pattern too specific or project not activated | Broaden pattern (`CustomerEntity` → `Customer`), run `serena status` |
| "No references found" | Wrong symbol path format | Use `serena find X` first to get exact path, then use that in `refs` |
| refs empty but method IS called | Called from config files, not code | Combine: `serena refs` for code + `grep` for YAML/XML configs |
| overview too brief | Shows structure only, not implementation | Use `serena find X --body` instead |
| Connection errors | Server not running | Run `serena status`, check localhost:9121 |
| Project not indexed | First activation needs time | Wait a few seconds after `serena activate`, then retry |

**Key rule for refs:** Always `serena find X` first → copy exact symbol path → use in `serena refs "ExactPath" file.php`

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
serena refs "RatesProvider/getPricesForTypes" src/Meyer/ShippingBundle/Provider/RatesProvider.php

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
