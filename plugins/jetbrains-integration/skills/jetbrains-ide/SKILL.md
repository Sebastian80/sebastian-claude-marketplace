---
name: jetbrains-ide
description: "Use for PhpStorm IDE operations - find files, search code, check problems, refactor, open files. Triggers: find file, search in files, check errors, refactor, rename symbol, open in IDE"
---

# JetBrains IDE Skill

Access PhpStorm/IntelliJ IDE tools via CLI.

## Quick Reference

| Task | Command |
|------|---------|
| Find files by name | `jetbrains files <keyword>` |
| Find files by glob | `jetbrains glob <pattern>` |
| Search in files | `jetbrains search <text>` |
| Regex search | `jetbrains regex <pattern>` |
| Directory tree | `jetbrains tree <dir>` |
| Read file | `jetbrains read <file>` |
| Create file | `jetbrains create <file>` |
| Check problems | `jetbrains problems <file>` |
| Get symbol info | `jetbrains symbol <file> <line> <col>` |
| Open in editor | `jetbrains open <file>` |
| List open files | `jetbrains open-files` |
| Reformat file | `jetbrains reformat <file>` |
| Replace text | `jetbrains replace <file> <old> <new>` |
| Rename symbol | `jetbrains rename <file> <sym> <new>` |
| Run config | `jetbrains run <config>` |
| List configs | `jetbrains configs` |
| List dependencies | `jetbrains deps` |
| List modules | `jetbrains modules` |
| List repos | `jetbrains repos` |
| Terminal command | `jetbrains terminal <cmd>` |

## Common Workflows

### Find and Open Files

```bash
# Find files by keyword
jetbrains files Customer

# Find by glob pattern
jetbrains glob "src/**/*Service.php"

# Open in editor
jetbrains open src/Service/CustomerService.php
```

### Search Code

```bash
# Text search
jetbrains search "processPayment" --mask "*.php" --dir "src"

# Regex search
jetbrains regex "function\s+process\w+" --mask "*.php"
```

### Check Code Quality

```bash
# Get errors and warnings
jetbrains problems src/Service/PaymentService.php

# Errors only
jetbrains problems src/Service/PaymentService.php --errors-only
```

### Get Symbol Information

```bash
# Get documentation for symbol at position
jetbrains symbol src/Service/PaymentService.php 45 20
```

### Refactoring

```bash
# Rename symbol across project (safe refactoring)
jetbrains rename src/Entity/Customer.php getName getFullName

# Simple text replace in file
jetbrains replace src/Service/MyService.php "oldMethod" "newMethod" --all
```

### Project Structure

```bash
# Show directory tree
jetbrains tree src/Meyer/CustomerBundle --depth 3

# List project modules
jetbrains modules

# List dependencies
jetbrains deps

# List VCS repositories
jetbrains repos
```

### Run Configurations

```bash
# List available configs
jetbrains configs

# Run a configuration
jetbrains run "PHPUnit"
```

## Options Reference

### Search Options

| Option | Description |
|--------|-------------|
| `--dir DIR` | Limit search to directory |
| `--mask MASK` | File mask (e.g., `*.php`) |
| `--case-sensitive` | Case-sensitive search (regex) |

### File Options

| Option | Description |
|--------|-------------|
| `--limit N` | Limit results (files command) |
| `--lines N` | Limit lines (read command) |
| `--depth N` | Tree depth (tree command) |
| `--overwrite` | Overwrite existing (create command) |
| `--all` | Replace all occurrences |

## When to Use JetBrains vs Serena

| Task | Use |
|------|-----|
| PHP class/method definitions | Serena (`serena find`) |
| PHP references/callers | Serena (`serena refs`) |
| JS/AMD module navigation | JetBrains (`jetbrains search`) |
| File problems/errors | JetBrains (`jetbrains problems`) |
| Refactoring (rename) | JetBrains (`jetbrains rename`) |
| Open file in IDE | JetBrains (`jetbrains open`) |

## Integration with Debugging

Use `jetbrains` for navigation, `jetbrains-debug` for debugging:

```bash
# 1. Find the file
jetbrains files PaymentService

# 2. Check for problems
jetbrains problems src/Service/PaymentService.php

# 3. Get symbol info
jetbrains symbol src/Service/PaymentService.php 50 10

# 4. Set breakpoint and debug
jetbrains-debug bp set src/Service/PaymentService.php 50
jetbrains-debug start "PHP Debug"
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Connection failed | Ensure PhpStorm is running with MCP enabled |
| Empty results | Check correct project is open in PhpStorm |
| File not found | Use project-relative paths |
