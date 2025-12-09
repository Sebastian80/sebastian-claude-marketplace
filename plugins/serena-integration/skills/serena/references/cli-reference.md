# Serena CLI Reference

Complete reference for the Serena CLI. For quick overview, see SKILL.md.

## CLI Architecture

```
serena <command> [--options]       # Simple commands
serena <group>/<subcommand>        # Nested commands (memory/list, edit/replace)
```

## Commands

### serena status
Check connection and project configuration.

```bash
serena status
```

Returns: Active project, languages, available tools.

### serena tools
List all available Serena MCP tools (dynamic discovery).

```bash
serena tools
```

Returns: Tool names with descriptions.

### serena find
Find symbols by pattern.

```bash
serena find --pattern <pattern> [options]

Options:
  --pattern    Symbol pattern (required)
  --kind       Filter: class, method, interface, function
  --path       Restrict to directory
  --body       Include source code (flag, no value needed)
  --depth      Traversal depth (0=symbol only, 1=include children)
  --exact      Exact match only (flag)
```

**Examples:**
```bash
serena find --pattern Customer
serena find --pattern Customer --kind class
serena find --pattern "get*" --kind method
serena find --pattern Customer --kind class --body
serena find --pattern Order --path src/Meyer/

# Get class with all methods (IMPORTANT: use --kind class with --depth 1)
serena find --pattern Customer --kind class --depth 1
serena find --pattern Customer --kind class --depth 1 --body
```

**Gotcha:** Without `--kind class`, `--depth 1` returns File children (namespace + class), not class children (methods). Always combine `--kind class` with `--depth 1`.

### serena refs
Find all references to a symbol.

```bash
serena refs --symbol <path> --file <file> [--all]

Options:
  --symbol    Symbol path (required), e.g., "Class/method"
  --file      File containing the symbol (required)
  --all       Show all refs (default: top 10)
```

**Examples:**
```bash
serena refs --symbol "Customer/getName" --file src/Entity/Customer.php
serena refs --symbol ShippingMethod --file src/Method/ShippingMethod.php --all true
```

### serena overview
Get **top-level** file structure (namespace, class names only - NOT methods).

```bash
serena overview --file <path>
```

**Examples:**
```bash
serena overview --file src/Entity/Customer.php
serena overview --file src/Service/PaymentService.php
```

**Note:** To get class methods, use `serena find --pattern ClassName --kind class --depth 1` instead.

### serena search
Regex search in code files.

```bash
serena search --pattern <regex> [--path PATH] [--glob GLOB]

Options:
  --pattern    Regex pattern (required)
  --path       Directory to search
  --glob       File pattern filter
```

**Examples:**
```bash
serena search --pattern "implements.*Interface" --glob "src/**/*.php"
serena search --pattern "#\[ORM\\Entity" --glob "src/**/*.php"
```

### serena recipe
Pre-built search recipes.

```bash
serena recipe --name <recipe>

Recipes:
  list         Show available recipes
  entities     Find entity classes
  controllers  Find controllers
  services     Find services
  interfaces   Find interfaces
  tests        Find test classes
```

**Examples:**
```bash
serena recipe --name list
serena recipe --name entities
serena recipe --name controllers
```

## Memory Commands

Use slash notation for nested commands.

### serena memory/list
List memories.

```bash
serena memory/list [--folder FOLDER]
```

### serena memory/tree
Visual tree of memory structure.

```bash
serena memory/tree [--folder FOLDER]
```

### serena memory/read
Read a memory.

```bash
serena memory/read --name <name>
```

### serena memory/write
Write a memory.

```bash
serena memory/write --name <name> --content <content>
```

### serena memory/search
Search memory contents.

```bash
serena memory/search --pattern <regex> [--folder FOLDER]
```

### serena memory/delete
Delete a memory.

```bash
serena memory/delete --name <name>
```

## Edit Commands

Symbol-based code editing. Use slash notation.

### serena edit/replace
Replace a symbol's body.

```bash
serena edit/replace --symbol <path> --file <file> --body <code>
```

### serena edit/after
Insert code after a symbol.

```bash
serena edit/after --symbol <path> --file <file> --code <code>
```

### serena edit/before
Insert code before a symbol.

```bash
serena edit/before --symbol <path> --file <file> --code <code>
```

### serena edit/rename
Rename a symbol.

```bash
serena edit/rename --symbol <path> --file <file> --new_name <name>
```

## Symbol Path Formats

| Type | Format | Example |
|------|--------|---------|
| Class | `ClassName` | `Customer` |
| Method | `Class/method` | `Customer/getName` |
| Constructor | `Class/__construct` | `Customer/__construct` |
| Property | `Class/$property` | `Customer/$name` |
| Wildcard | `*Pattern` | `*Controller` |

## Output Formats

```bash
serena find --pattern X              # Human-readable (default)
serena --json find --pattern X       # JSON output
```

## Performance Tips

1. **Always use --path** to restrict search scope
2. **Broaden patterns** if no results: `CustomerEntity` → `Customer`
3. **Use recipes** for common searches
4. **Check status** first if commands fail

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "No symbols found" | Broaden pattern, check --path scope |
| Empty refs | Use `serena find` first to get exact path |
| Connection error | Run `serena status`, check daemon |
| Very slow | Add `--path src/` restriction |
| "command not found" | Ensure `~/.local/bin` in PATH |
