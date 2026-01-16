---
description: Search project memories for specific topics or patterns
allowed-tools:
  - Bash
---

# /pm:search - Search Memories

## Usage

User provides search term. Execute:

```bash
pm search "[user's search term]"
```

## Steps

### 1. Execute Search

```bash
pm search "[term]"
```

### 2. For Each Match, Show Context

If matches found, read full content of top 3 results:

```bash
pm read "[matched-memory-name]"
```

### 3. Report Results

```
## Search Results for "[term]"

**Found N matches:**

### [memory-name-1]
[relevant excerpt]

### [memory-name-2]
[relevant excerpt]

---
Use `/pm:load` to restore full session context.
```

If no matches:
```
No memories found matching "[term]".

**Suggestions:**
- Try broader terms
- Check `pm tree` for available memories
- Use `pm list` to see all memory names
```
