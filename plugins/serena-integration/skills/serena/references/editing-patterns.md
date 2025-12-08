# Symbol Editing Patterns

When to use Serena's symbol-based editing vs. standard Edit tool.

## Decision Matrix

| Scenario | Serena | Standard Edit |
|----------|--------|---------------|
| Replace entire method body | `serena edit replace` | - |
| Add new method to class | `serena edit after` | - |
| Add import statement | `serena edit before` | - |
| Rename method/class | `serena edit rename` | - |
| Change few lines in method | - | Edit tool |
| Fix typo in string | - | Edit tool |
| Modify config files | - | Edit tool |
| Non-PHP files | - | Edit tool |

## Symbol Editing Operations

### serena edit replace

Replaces the entire body of a symbol (method, function, class).

```bash
serena edit replace "Customer/calculateTotal" src/Entity/Customer.php '
    $total = 0;
    foreach ($this->items as $item) {
        $total += $item->getPrice();
    }
    return $total;
'
```

**Best for**: Rewriting methods, updating function logic.

### serena edit after

Inserts code after a symbol. Useful for adding methods.

```bash
serena edit after "Customer/getName" src/Entity/Customer.php '
    public function getFullName(): string
    {
        return $this->firstName . " " . $this->lastName;
    }
'
```

**Best for**: Adding new methods, appending to class.

### serena edit before

Inserts code before a symbol. Useful for imports.

```bash
# Add use statement before class
serena edit before "Customer" src/Entity/Customer.php 'use App\Service\Calculator;'
```

**Best for**: Adding imports, docblocks, annotations.

### serena edit rename

Renames a symbol and updates all references.

```bash
serena edit rename "Customer/getName" src/Entity/Customer.php "getCustomerName"
```

**Best for**: Refactoring, renaming methods/classes.

## Using stdin for Multi-line Code

For complex code blocks, use stdin:

```bash
# Read body from stdin
cat <<'EOF' | serena edit replace "Customer/calculateTotal" src/Entity/Customer.php -
    $total = 0;
    foreach ($this->items as $item) {
        $total += $item->getPrice();
    }
    return $total;
EOF
```

## When NOT to Use Symbol Editing

1. **Small changes within a method**: Use standard Edit
2. **Non-code files**: JSON, YAML, MD - use standard Edit
3. **Config files**: Use standard Edit
4. **When you need line-level precision**: Use standard Edit

## Workflow: Adding a New Feature

```bash
# 1. Find where to add
serena overview src/Entity/Customer.php

# 2. Check existing code
serena find "Customer/getName" --body

# 3. Insert new code
serena edit after "Customer/getName" src/Entity/Customer.php 'public function newMethod() {}'

# 4. Add imports if needed
serena edit before "Customer" src/Entity/Customer.php 'use App\Service\NewService;'

# 5. Check references if needed
serena refs "Customer/getName" src/Entity/Customer.php
```

## Error Handling

Symbol operations fail if:
- Symbol not found (check name_path spelling)
- File not in project (check relative_path)
- Syntax error in body (validate PHP syntax)

Always verify symbol exists before editing:

```bash
# Check symbol exists first
serena find "Customer/getName" --path src/Entity/Customer.php

# Then edit if found
serena edit replace "Customer/getName" src/Entity/Customer.php 'return $this->name;'
```
