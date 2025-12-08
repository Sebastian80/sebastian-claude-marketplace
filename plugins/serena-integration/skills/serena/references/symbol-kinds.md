# Symbol Kinds Reference

LSP Symbol Kinds used by Serena/Intelephense.

## Common Kinds

| Kind | Name | Description | Example |
|------|------|-------------|---------|
| 1 | File | Source file | `Customer.php` |
| 2 | Module | Module/Package | - |
| 3 | Namespace | PHP Namespace | `Meyer\Bundle\ImportBundle` |
| 4 | Package | Package | - |
| 5 | Class | PHP Class | `Customer`, `OrderService` |
| 6 | Method | Class method | `getName`, `__construct` |
| 7 | Property | Class property | `$name`, `$id` |
| 8 | Field | Field | - |
| 9 | Constructor | Constructor | `__construct` |
| 10 | Enum | Enumeration | `OrderStatus` |
| 11 | Interface | PHP Interface | `CustomerInterface` |
| 12 | Function | Standalone function | `helper_function` |
| 13 | Variable | Variable | `$customer` |
| 14 | Constant | Constant | `MAX_ITEMS` |
| 15 | String | String literal | - |
| 16 | Number | Number literal | - |
| 17 | Boolean | Boolean | - |
| 18 | Array | Array | - |

## Filtering by Kind

Use `--kind` flag to filter results:

```bash
# Find only classes
serena find Customer --kind class

# Find only methods
serena find get --kind method

# Find only interfaces
serena find Interface --kind interface
```

## Kind Filter Options

| Filter | Kind Number | Matches |
|--------|-------------|---------|
| `--kind class` | 5 | Classes, traits, abstract classes |
| `--kind method` | 6 | Methods, static methods, magic methods |
| `--kind interface` | 11 | Interfaces |
| `--kind function` | 12 | Standalone functions |
| `--kind namespace` | 3 | Namespaces |

## PHP-Specific Notes

- **Traits**: Kind 5 (Class)
- **Abstract classes**: Kind 5 (Class)
- **Static methods**: Kind 6 (Method)
- **Magic methods**: Kind 6 (Method) - `__construct`, `__toString`, etc.

## Common Patterns

```bash
# Find all classes containing "Service"
serena find Service --kind class

# Find all methods starting with "get"
serena find "get*" --kind method

# Find all interfaces
serena find Interface --kind interface

# Use recipes for common patterns
serena recipe controllers    # All *Controller classes
serena recipe interfaces     # All interfaces
serena recipe entities       # All Doctrine entities
```

## JSON Output for Scripting

```bash
# Get raw kind numbers in JSON
serena find Customer --json | jq '.[].kind'

# Filter by kind number in jq
serena find Customer --json | jq '[.[] | select(.kind == 5)]'
```
