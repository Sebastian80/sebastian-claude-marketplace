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
- "I'll read the file to find the class" → WRONG. Use `serena find --pattern X --body`.
- "Grep will find all usages" → WRONG. Grep finds TEXT. `serena refs` finds CODE REFERENCES.
- "I know the file path already" → WRONG. Still use `serena overview`.
- "This is a simple search" → WRONG. Simple searches benefit MOST from semantic tools.
- "I'll use the Task/Explore agent" → WRONG. Use Serena directly or serena-explore agent.
- "Let me glob for files first" → WRONG. `serena find` searches semantically.
- "serena command not found" → WRONG. Check your PATH includes `~/.local/bin`.

**If a Serena operation exists for your task, you MUST use it.**
</EXTREMELY-IMPORTANT>

## Automatic Triggers

**Use Serena IMMEDIATELY when user asks ANY of these:**

| User Request Pattern | Serena Command |
|---------------------|----------------|
| "Find class X" / "Where is X defined" | `serena find --pattern X --body` |
| "Who calls X" / "Find usages of X" | `serena refs --symbol X/method --file file.php` |
| "How does X work" / "Show me X" | `serena find --pattern X --body` |
| "Find all controllers/entities" | `serena recipe --name controllers` |
| "What methods does X have" | `serena overview --file file.php` |
| "Refactor X" / "Rename X" | `serena refs` then `mcp__jetbrains__rename_refactoring` |

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
**Note:** Run `serena status` to see active languages. Edit `.serena/project.yml` to add more.

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
| Find class/method definition | `find --pattern X --kind class` | `search_in_files_by_text` | **Serena** (semantic) |
| Find who calls this | `refs --symbol X --file f.php` | ❌ Not available | **Serena** (only option) |
| Search vendor code | `find --pattern X --path vendor/` | ❌ Excluded | **Serena** (only option) |
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
serena find --pattern calculateTotal --kind method --path src/

# 2. Get documentation (JetBrains - extracts PHPDoc)
mcp__jetbrains__get_symbol_info(filePath="src/Service/OrderService.php", line=45, column=20)

# 3. Find all callers (Serena - only option)
serena refs --symbol "OrderService/calculateTotal" --file src/Service/OrderService.php --all true

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

**Use the unified CLI:** `serena` (in PATH at `~/.local/bin/serena`)

The CLI uses a central skills-daemon architecture:
- FastAPI daemon with concurrent request handling
- Auto-generated API docs at `http://127.0.0.1:9100/docs`
- Thin stdlib-only client minimizes startup overhead
- Daemon auto-starts on first use, auto-stops after 30min idle

**API Documentation:** `curl http://127.0.0.1:9100/docs` or `curl http://127.0.0.1:9100/openapi.json`

**Daemon commands:**
```bash
skills-daemon status    # Check if daemon is running
skills-daemon start     # Start daemon manually
skills-daemon stop      # Stop daemon
skills-daemon restart   # Restart daemon
```

**All commands use named arguments:**
```bash
serena find --pattern Customer
serena refs --symbol "Customer/getName" --file src/Entity/Customer.php
serena recipe --name entities
serena status
```

## MANDATORY First Action

Before ANY code exploration, run this:

```bash
serena status
```

**Did not run this first? STOP. Run it NOW.**

## Quick Reference (Cheat Sheet)

**Full API docs:** `http://127.0.0.1:9100/docs`

| Task | Command |
|------|---------|
| Find class/symbol | `serena find --pattern Customer` |
| Find with body | `serena find --pattern Customer --body` |
| Find only classes | `serena find --pattern Customer --kind class` |
| Find only methods | `serena find --pattern "get*" --kind method` |
| Who calls this? | `serena refs --symbol ClassName --file file.php` |
| Who calls method? | `serena refs --symbol "Class/method" --file file.php` |
| File structure | `serena overview --file file.php` |
| Check status | `serena status` |
| Find entities | `serena recipe --name entities` |
| Find controllers | `serena recipe --name controllers` |
| Read memory | `serena memory/read --name memname` |
| Write memory | `serena memory/write --name memname --content "text"` |
| Regex search | `serena search --pattern "regex" --glob "src/**/*.php"` |

## Quick Start

```bash
# Check connection
serena status

# Find a class
serena find --pattern Customer --body

# Find who calls a method
serena refs --symbol "Customer/getName" --file src/Entity/Customer.php

# Get file structure
serena overview --file src/Entity/Customer.php

# Common recipes
serena recipe --name entities
serena recipe --name controllers
```

## Commands

**Full API documentation with all parameters:** `http://127.0.0.1:9100/docs`

### serena find - Find Symbols

```bash
serena find --pattern <pattern> [options]

Options:
  --pattern       Symbol pattern to find (required)
  --body          Include symbol body code (bool)
  --path          Restrict to file/directory
  --depth         Traversal depth (0=symbol, 1=children)
  --kind          Filter: class, method, interface, function
  --exact         Exact match only (bool)

Examples:
  serena find --pattern Customer
  serena find --pattern Customer --kind class
  serena find --pattern "get*" --kind method
  serena find --pattern Customer --body
  serena find --pattern Order --path src/Meyer/
```

### serena refs - Find References

```bash
serena refs --symbol <symbol> --file <file> [--all]

Options:
  --symbol    Symbol path (required)
  --file      File containing symbol (required)
  --all       Show all references (bool, default: top 10)

Examples:
  serena refs --symbol "Customer/getName" --file src/Entity/Customer.php
  serena refs --symbol "ShippingMethod" --file src/Meyer/ShippingBundle/Method/ShippingMethod.php
  serena refs --symbol Tool --file src/tools.py --all true
```

### serena overview - File Structure

```bash
serena overview --file <file>

Examples:
  serena overview --file src/Entity/Customer.php
  serena overview --file src/Meyer/ShippingBundle/Provider/RatesProvider.php
```

### serena search - Regex Search

```bash
serena search --pattern <regex> [--glob GLOB] [--path PATH]

Examples:
  serena search --pattern "implements.*Interface" --glob "src/**/*.php"
  serena search --pattern "#\[ORM\\Entity" --glob "src/**/*.php"
  serena search --pattern "throw new.*Exception"
```

### serena recipe - Pre-built Operations

```bash
serena recipe --name <recipe>

Recipes: entities, controllers, services, interfaces, tests

Examples:
  serena recipe --name entities
  serena recipe --name controllers
  serena recipe --name list    # Show all recipes
```

### serena memory - Professional Memory Management

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
serena memory list                    # List all memories (recursive)
serena memory list active/tasks       # List only active tasks
serena memory read <name>             # Read a memory
serena memory write <name> <content>  # Write (folders auto-created)
serena memory delete <name>           # Delete (cleans empty dirs)

Examples:
  serena memory list
  serena memory list learnings
  serena memory read active/tasks/HMKG-2064
  serena memory write active/tasks/HMKG-2065 "## Task: Fix checkout"
  echo "Multi-line content" | serena memory write reference/notes -
```

#### Organization Commands

```bash
serena memory tree                    # Visual tree of all memories
serena memory tree active             # Tree from subfolder
serena memory search <pattern>        # Search content (regex)
serena memory search "Mollie" --folder learnings
serena memory stats                   # Memory statistics

Examples:
  serena memory tree
  serena memory search "checkout"
  serena memory search "error" --folder learnings/mistakes
  serena memory stats
```

#### Lifecycle Commands

```bash
serena memory archive <name>          # Archive with date prefix
serena memory archive <name> --category tasks
serena memory mv <src> <dest>         # Move/rename
serena memory init                    # Create folder structure

Examples:
  # Archive completed task (moves to archive/2025-12/tasks/20251208_HMKG-2064)
  serena memory archive active/tasks/HMKG-2064 --category tasks

  # Move memory to different folder
  serena memory mv old_notes learnings/discoveries/old_notes

  # Initialize recommended structure with templates
  serena memory init
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
serena find --pattern ClassName --body
serena overview --file path/from/result.php   # If need structure
```

### Workflow 2: Who Calls X

```bash
serena find --pattern ClassName/methodName    # Get file path
serena refs --symbol "ClassName/methodName" --file path/to/file.php
```

### Workflow 3: Full Exploration

```bash
serena find --pattern MainClass --body        # Find entry point
serena overview --file path/to/MainClass.php  # Get structure
serena refs --symbol MainClass --file path/to/file.php  # Find integration points
serena memory/read --name bundle_architecture # Check existing context
```

### Workflow 4: Safe Refactoring

```bash
serena find --pattern X --body                # Understand the symbol
serena refs --symbol X --file path/to/file.php  # Find ALL affected places
# Review each reference
serena edit/replace --symbol "X/method" --file file.php --body "new body"
# Or for renames:
serena edit/rename --symbol "X/oldMethod" --file file.php --new_name "newMethod"
```

### Workflow 5: Debug/Trace Issue

```bash
serena find --pattern ErrorClass/errorMethod --body   # Find error location
serena refs --symbol "ErrorClass/errorMethod" --file path.php  # Trace callers
# Repeat for each caller until root cause found
serena memory/write --name debug_trace --content "## Call Chain: ..."
```

## Anti-Patterns (NEVER DO THIS)

| BAD (Text-based) | GOOD (Semantic) |
|------------------|-----------------|
| `grep "class Customer"` | `serena find --pattern Customer --kind class` |
| `grep "->getName("` | `serena refs --symbol "Class/getName" --file file.php` |
| `glob "**/*Customer*.php"` | `serena find --pattern Customer` |
| Read file to find class | `serena overview --file file.php` |
| Edit by line number | `serena edit/replace --symbol Symbol --file file.php` |
| Generic Task/Explore agent | `serena` directly or `serena-explore` agent |

## Performance Best Practices

### Always Use --path for Speed

LSP must search the entire indexed codebase without `--path`. Use path restriction:

| Search | Time | Notes |
|--------|------|-------|
| `serena find --pattern Payment --path src/` | **0.7s** | Custom code only |
| `serena find --pattern Payment --path vendor/mollie/` | **2-3s** | Specific vendor |
| `serena find --pattern Payment --path vendor/oro/` | **5-10s** | Large framework |
| `serena find --pattern Payment` (no path) | **28s+** | All indexed vendors |

```bash
# FAST: Always specify path when you know the scope
serena find --pattern Payment --kind class --path src/
serena find --pattern Payment --kind class --path vendor/mollie/

# SLOW: Avoid searching entire codebase
serena find --pattern Payment --kind class  # Searches everything
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

### Grouped Output

The CLI groups results by src/vendor and bundle:

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
serena find --pattern Payment --path src/         # Custom code first
serena find --pattern Payment --kind class        # Only classes
serena find --pattern Payment                     # Full search if needed

# BAD: Too specific (may fail during indexing)
serena find --pattern PaymentMethodProviderInterface  # Very specific name
serena find --pattern "Oro\\Bundle\\PaymentBundle"    # Namespaces often fail
```

### Good vs Bad Search Patterns

| ❌ BAD | ✅ GOOD |
|--------|---------|
| `serena find --pattern PaymentMethodInterface` | `serena find --pattern Payment --kind interface` |
| `serena find --pattern CustomerEntityListener` | `serena find --pattern Customer --kind class` |
| `serena find --pattern addDeSpecificationsOnPrePersist` | `serena find --pattern addDe --kind method` |

### 3-Strike Rule

Try up to 3 progressively broader patterns before falling back:

```bash
# Strike 1: Specific
serena find --pattern PaymentMethodInterface --kind interface
# Exit 1? → broaden

# Strike 2: Shorter
serena find --pattern PaymentMethod --kind interface
# Exit 1? → broaden more

# Strike 3: Minimal
serena find --pattern Payment --kind interface
# Exit 1? → fall back to grep
```

### Indexing Awareness

LSP indexes `src/` before `vendor/`. During initial indexing:

```bash
# Likely works (local code indexed first):
serena find --pattern Customer --path src/Meyer/

# May fail until fully indexed:
serena find --pattern Mollie --path vendor/
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
serena memory write active/tasks/HMKG-2064 "## Task: HMKG-2064
### Status: in_progress
### Completed
- [x] Found affected classes
- [x] Fixed payment surcharge
### Remaining
- [ ] Write tests
### Key Files
- src/Meyer/Bundle/MollieFixBundle/..."

# Save session state
serena memory write active/sessions/current "## Session: $(date)
### Worked On
- HMKG-2064 payment fix
### Blockers
- None
### Next Steps
- Run tests"

# Resume in next session
serena memory tree active
serena memory read active/tasks/HMKG-2064

# When task is done, archive it
serena memory archive active/tasks/HMKG-2064 --category tasks
```

**Tip:** Use `/serena:load` and `/serena:save` commands for automated session handoff.

## Output Formats

The CLI outputs optimized human-readable format by default, JSON with `-j` flag:

```bash
serena find --pattern Customer              # Human-readable (token-efficient)
serena --json find --pattern Customer       # JSON for processing
serena --json find --pattern Customer | jq '.[] | .name_path'
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
serena status                            # Check connection, list tools
serena find --pattern Controller         # Test semantic search works
```

## Architecture: How Serena Works

```
┌─────────────────────┐    HTTP     ┌─────────────────────┐    HTTP     ┌────────────────────────┐
│ serena CLI          │ ◄─────────► │ Skills Daemon       │ ◄─────────► │ Serena MCP Server      │
│ ~/.local/bin/serena │  :9100      │ (FastAPI + plugins) │  :9121      │ (Centralized)          │
│                     │             │                     │             │                        │
│ routes to           │             │ skills-daemon/      │             │ ┌────────────────────┐ │
│ skills-client       │             │ ├─ SerenaPlugin     │             │ │ Language Servers   │ │
│ (stdlib, ~10ms)     │             │ ├─ JiraPlugin       │             │ │ (30+ LSP backends) │ │
└─────────────────────┘             │ └─ ...future        │             │ └────────────────────┘ │
                                    └─────────────────────┘             │                        │
                                                                        │ Semantic code analysis:│
                                                                        │ - Symbol indexing      │
                                                                        │ - Type inference       │
                                                                        │ - Reference tracking   │
                                                                        │ - Project-wide search  │
                                                                        └────────────────────────┘
```

**Key points:**
- **3-tier architecture:** thin client → skills-daemon (plugin) → MCP server
- **Central daemon:** Port 9100 hosts multiple skill plugins (Serena, Jira, etc.)
- **Performance:** ~120ms per command with daemon hot
- The daemon keeps Python interpreter and httpx connections warm
- Auto-starts on first use, auto-stops after 30min idle
- Auto-generated API docs at http://127.0.0.1:9100/docs
- Session state managed via HTTP headers (`mcp-session-id`)
- Project activation required before searching
- Languages configured in `.serena/project.yml`

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| "No symbols found" | Pattern too specific or project not activated | Broaden pattern (`CustomerEntity` → `Customer`), run `serena status` |
| "No references found" | Wrong symbol path format | Use `serena find --pattern X` first to get exact path, then use that in `refs` |
| refs empty but method IS called | Called from config files, not code | Combine: `serena refs` for code + `grep` for YAML/XML configs |
| overview too brief | Shows structure only, not implementation | Use `serena find --pattern X --body` instead |
| Connection errors | Server not running | Run `serena status`, check localhost:9121 |
| Project not indexed | First activation needs time | Wait a few seconds after `serena activate`, then retry |
| "command not found" | `serena` not in PATH | Ensure `~/.local/bin` is in your PATH |

**Key rule for refs:** Always `serena find --pattern X` first → copy exact symbol path → use in `serena refs --symbol "ExactPath" --file file.php`

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
