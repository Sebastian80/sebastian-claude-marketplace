---
description: Load project memories to restore context from previous sessions
allowed-tools:
  - Bash
---

# /pm:load - Restore Session Context

## Steps

### 1. Check Memory Exists

```bash
pm tree
```

If not initialized, run `pm init` and report "Initialized project memory" then stop.
If empty (initialized but no memories), report "No memories found for this project" and stop.

### 2. Load Current Session

```bash
pm read "active/session"
```

### 3. Load Active Tasks

```bash
pm list
```

For each item starting with `active/tasks/`:
```bash
pm read "active/tasks/[task-name]"
```

### 4. Search Recent Learnings (optional)

```bash
pm search "[relevant keyword]"
```

### 5. Report Context Loaded

```
## Context Restored

**Current Session:**
[summary from active/session]

**Active Tasks:**
- [task list with status]

**Relevant Learnings:**
- [any matching learnings]

Ready to continue.
```
