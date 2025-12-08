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
- "Let me glob for files first" → WRONG. `serena-fast find` searches semantically.
- "serena command not found" → WRONG. You must use the FULL PATH. See Setup section.

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
| "Refactor X" / "Rename X" | `$SERENA refs` then `mcp__jetbrains__rename_refactoring` |

## When to Use vs When NOT to Use

| ✅ USE SERENA | ❌ DON'T USE SERENA |
|---------------|---------------------|
| Finding class/method/function definitions | Searching template files (.twig, .html) |
| Tracing who calls a method ("find refs") | Finding text in comments |
| Understanding file/class structure | Searching languages NOT in project.yml |
| Navigating languages configured in `.serena/project.yml` | Finding strings/literals across all files |
| Refactoring by symbol path | Log files, .env files |
| Cross-file symbol references | Hybrid search (code + config) |
| PHP classes, methods, interfaces | **JavaScript files** (use JetBrains/Grep) |
| YAML service definitions | AMD/RequireJS modules |

**Rule:** Serena for CONFIGURED LANGUAGES. Grep for UNCONFIGURED/TEMPLATES/COMMENTS.
**Note:** Run `$SERENA status` to see active languages. Edit `.serena/project.yml` to add more.

## JavaScript Navigation (Special Case)

**Serena does NOT support JavaScript in this project.** The TypeScript LSP is disabled because:
- Oro uses AMD/RequireJS module pattern (`define(function(require) {...})`)
- LSP sees these as single `define() callback` functions, not classes/components
- Symbol search, references, and navigation don't work meaningfully

### JS Navigation Fallback Strategy

Use this **priority order** for JavaScript files:

| Priority | Tool | When to Use | Example |
|----------|------|-------------|---------|
| **1st** | JetBrains MCP | PhpStorm open (better AMD heuristics) | `mcp__jetbrains__search_in_files_by_text` |
| **2nd** | Grep/Glob | JetBrains unavailable or failed | `Grep` with `*.js` glob |
| **3rd** | Read | Need full file with line numbers | `Read` tool |

### JetBrains MCP for JavaScript

```bash
# Search JS files by content
mcp__jetbrains__search_in_files_by_text(searchText="BaseComponent", fileMask="*.js")

# Search with regex
mcp__jetbrains__search_in_files_by_regex(regexPattern="extend\\(", fileMask="*.js")

# Find JS files by name
mcp__jetbrains__find_files_by_name_keyword(nameKeyword="component")

# Get symbol info (may work better than Serena for AMD)
mcp__jetbrains__get_symbol_info(filePath="src/path/to/file.js", line=20, column=15)
```

### Native Tools Fallback for JavaScript

```bash
# Find JS files
Glob pattern="src/**/*.js"

# Search content in JS
Grep pattern="BaseComponent" glob="*.js"

# Read with line numbers (for editing)
Read file_path="/full/path/to/file.js"
```

### Detection: Is JetBrains Available?

**Try JetBrains first.** If the MCP call fails or returns an error, fall back to native tools.
No explicit detection needed - just handle failures gracefully.

```
1. Try: mcp__jetbrains__search_in_files_by_text(...)
2. If success → use result
3. If error/timeout → fall back to Grep/Glob/Read
```

## When to Use JetBrains MCP Instead

JetBrains MCP tools are available automatically (no skill needed). Use them for these tasks:

| Task | Use JetBrains MCP | Why |
|------|-------------------|-----|
| **Get PHPDoc/documentation** | `mcp__jetbrains__get_symbol_info` | Extracts docblocks, Serena only shows basic info |
| **Safe project-wide rename** | `mcp__jetbrains__rename_refactoring` | Handles all references safely |
| **Debug code** | `mcp__jetbrains-debugger__*` | Only option - full debugger |
| **Run tests/builds** | `mcp__jetbrains__execute_run_configuration` | Only option |
| **IDE inspections/errors** | `mcp__jetbrains__get_file_problems` | PHPStan-like analysis |
| **Format code** | `mcp__jetbrains__reformat_file` | Apply IDE formatter |
| **Open in IDE** | `mcp__jetbrains__open_file_in_editor` | Jump to location |

### Serena vs JetBrains Decision Matrix

| Task | Serena | JetBrains | Winner |
|------|--------|-----------|--------|
| Find class/method definition | `find X --kind class` | `search_in_files_by_text` | **Serena** (semantic) |
| Find who calls this | `refs X file.php` | ❌ Not available | **Serena** (only option) |
| Search vendor code | `find X --path vendor/` | ❌ Excluded | **Serena** (only option) |
| Get symbol documentation | Basic output | Rich PHPDoc extraction | **JetBrains** |
| Rename symbol | Manual with `edit rename` | Project-wide safe | **JetBrains** |
| Quick text search in src/ | Slower (LSP overhead) | Instant | **JetBrains** (speed) |

### Quick JetBrains MCP Reference

```bash
# Get symbol documentation (extracts PHPDoc)
mcp__jetbrains__get_symbol_info(filePath="path/file.php", line=20, column=15)

# Safe project-wide rename
mcp__jetbrains__rename_refactoring(pathInProject="path/file.php", symbolName="oldName", newName="newName")

# Check for IDE errors/warnings
mcp__jetbrains__get_file_problems(filePath="path/file.php")

# Run test or build configuration
mcp__jetbrains__execute_run_configuration(configurationName="PHPUnit")

# Quick text search (faster than Serena for simple searches)
mcp__jetbrains__search_in_files_by_text(searchText="pattern", directoryToSearch="src", fileMask="*.php")
```

### Debugging Workflow (JetBrains Only)

For debugging, use JetBrains MCP tools:

```bash
# 1. Set breakpoint
mcp__jetbrains-debugger__set_breakpoint(file_path="path/file.php", line=50)

# 2. Start debug session
mcp__jetbrains-debugger__start_debug_session(configuration_name="PHP Debug")

# 3. Step through code
mcp__jetbrains-debugger__step_over()
mcp__jetbrains-debugger__step_into()

# 4. Inspect variables
mcp__jetbrains-debugger__get_variables()
mcp__jetbrains-debugger__evaluate_expression(expression="$variable")

# 5. Stop session
mcp__jetbrains-debugger__stop_debug_session()
```

### Combined Workflow Example

**Refactoring a method:**

```bash
# 1. Find the method (Serena - semantic accuracy)
$SERENA find calculateTotal --kind method --path src/

# 2. Get documentation (JetBrains - extracts PHPDoc)
mcp__jetbrains__get_symbol_info(filePath="src/Service/OrderService.php", line=45, column=20)

# 3. Find all callers (Serena - only option)
$SERENA refs "OrderService/calculateTotal" src/Service/OrderService.php --all

# 4. Rename safely (JetBrains - project-wide)
mcp__jetbrains__rename_refactoring(pathInProject="src/Service/OrderService.php", symbolName="calculateTotal", newName="computeOrderTotal")

# 5. Verify no errors (JetBrains - IDE inspections)
mcp__jetbrains__get_file_problems(filePath="src/Service/OrderService.php")
```

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

## Setup - CLI Wrapper

**Use the unified CLI wrapper:** `/home/sebastian/.local/bin/serena`

The wrapper automatically routes commands:
- Fast commands (`find`, `refs`, `overview`, `status`, `search`) → serena-fast
- Full commands (`recipe`, `memory`, `edit`, `tools`, `activate`) → full serena

When this document shows `$SERENA`, substitute: `/home/sebastian/.local/bin/serena`

**EXAMPLES:**
```bash
# All commands use the same wrapper:
/home/sebastian/.local/bin/serena find Customer
/home/sebastian/.local/bin/serena refs "Customer/getName" src/Entity/Customer.php
/home/sebastian/.local/bin/serena recipe entities
/home/sebastian/.local/bin/serena memory list
```

## MANDATORY First Action

Before ANY code exploration, run this:

```bash
/home/sebastian/.local/bin/serena status
```

**Did not run this first? STOP. Run it NOW.**

## Quick Reference (Cheat Sheet)

All commands use the same wrapper - it routes automatically.

| Task | Command |
|------|---------|
| Find class/symbol | `serena find Customer` |
| Find with body | `serena find Customer --body` |
| Find only classes | `serena find Customer --kind class` |
| Find only methods | `serena find "get*" --kind method` |
| Who calls this? | `serena refs ClassName file.php` |
| Who calls method? | `serena refs "Class/method" file.php` |
| File structure | `serena overview file.php` |
| Check status | `serena status` |
| Find entities | `serena recipe entities` |
| Find controllers | `serena recipe controllers` |
| Find listeners | `serena recipe listeners` |
| Read memory | `serena memory read name` |
| Write memory | `serena memory write name "content"` |
| Regex search | `serena search "pattern" --glob "src/**/*.php"` |

## Quick Start

```bash
# Check connection
/home/sebastian/.local/bin/serena status

# Find a class
/home/sebastian/.local/bin/serena find Customer --body

# Find who calls a method
/home/sebastian/.local/bin/serena refs "Customer/getName" src/Entity/Customer.php

# Get file structure
/home/sebastian/.local/bin/serena overview src/Entity/Customer.php

# Common recipes
/home/sebastian/.local/bin/serena recipe entities
/home/sebastian/.local/bin/serena recipe controllers
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

### $SERENA_FULL memory - Professional Memory Management

Memories support **folder organization** for better structure:

```
memories/
├── active/           # Current work
│   ├── tasks/        # In-progress tasks (HMKG-2064, etc.)
│   └── sessions/     # Session continuity
├── reference/        # Documentation
│   ├── architecture/ # System design
│   ├── patterns/     # Code patterns
│   ├── integrations/ # External systems
│   └── workflows/    # Dev processes
├── learnings/        # Knowledge base
│   ├── mistakes/     # Errors & solutions
│   ├── discoveries/  # Useful findings
│   └── commands/     # Helpful snippets
├── archive/          # Historical (auto-organized by date)
│   └── 2025-12/
│       └── tasks/
└── .templates/       # Reusable templates
```

#### Basic Operations

```bash
$SERENA_FULL memory list                    # List all memories (recursive)
$SERENA_FULL memory list active/tasks       # List only active tasks
$SERENA_FULL memory read <name>             # Read a memory
$SERENA_FULL memory write <name> <content>  # Write (folders auto-created)
$SERENA_FULL memory delete <name>           # Delete (cleans empty dirs)

Examples:
  $SERENA_FULL memory list
  $SERENA_FULL memory list learnings
  $SERENA_FULL memory read active/tasks/HMKG-2064
  $SERENA_FULL memory write active/tasks/HMKG-2065 "## Task: Fix checkout"
  echo "Multi-line content" | $SERENA_FULL memory write reference/notes -
```

#### Organization Commands

```bash
$SERENA_FULL memory tree                    # Visual tree of all memories
$SERENA_FULL memory tree active             # Tree from subfolder
$SERENA_FULL memory search <pattern>        # Search content (regex)
$SERENA_FULL memory search "Mollie" --folder learnings
$SERENA_FULL memory stats                   # Memory statistics

Examples:
  $SERENA_FULL memory tree
  $SERENA_FULL memory search "checkout"
  $SERENA_FULL memory search "error" --folder learnings/mistakes
  $SERENA_FULL memory stats
```

#### Lifecycle Commands

```bash
$SERENA_FULL memory archive <name>          # Archive with date prefix
$SERENA_FULL memory archive <name> --category tasks
$SERENA_FULL memory mv <src> <dest>         # Move/rename
$SERENA_FULL memory init                    # Create folder structure

Examples:
  # Archive completed task (moves to archive/2025-12/tasks/20251208_HMKG-2064)
  $SERENA_FULL memory archive active/tasks/HMKG-2064 --category tasks

  # Move memory to different folder
  $SERENA_FULL memory mv old_notes learnings/discoveries/old_notes

  # Initialize recommended structure with templates
  $SERENA_FULL memory init
```

#### Memory Lifecycle

```
CREATE: Write to active/tasks/TICKET
  ↓
WORK: Update as you progress
  ↓
COMPLETE: Archive when done
  ↓
LEARNING: Extract insights to learnings/
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

Use the folder structure for organized session continuity:

```bash
# Save task context to active/tasks folder
$SERENA_FULL memory write active/tasks/HMKG-2064 "## Task: HMKG-2064
### Status: in_progress
### Completed
- [x] Found affected classes
- [x] Fixed payment surcharge
### Remaining
- [ ] Write tests
### Key Files
- src/Meyer/Bundle/MollieFixBundle/..."

# Save session state
$SERENA_FULL memory write active/sessions/current "## Session: $(date)
### Worked On
- HMKG-2064 payment fix
### Blockers
- None
### Next Steps
- Run tests"

# Resume in next session
$SERENA_FULL memory tree active
$SERENA_FULL memory read active/tasks/HMKG-2064

# When task is done, archive it
$SERENA_FULL memory archive active/tasks/HMKG-2064 --category tasks
```

**Tip:** Use `/serena:load` and `/serena:save` commands for automated session handoff.

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
