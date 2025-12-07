---
description: Restore Serena session context by loading memories from previous sessions
allowed-tools:
  - Bash
  - Read
---

# /serena-load - Restore Session Context

Quick session restoration with full context recovery.

## Execute These Steps

### 1. Activate & Check Status
```bash
~/.claude/skills/serena/scripts/serena status
```

If no project active or wrong project:
```bash
~/.claude/skills/serena/scripts/serena activate "$(pwd)"
```

### 2. List Available Memories
```bash
~/.claude/skills/serena/scripts/serena memory list
```

### 3. Load Core Memories (in parallel)
```bash
~/.claude/skills/serena/scripts/serena memory read session_context
~/.claude/skills/serena/scripts/serena memory read task_progress
~/.claude/skills/serena/scripts/serena memory read learnings
~/.claude/skills/serena/scripts/serena memory read project_overview
```

Read any memory that exists from the list.

### 4. Report Session State

Present a structured summary:

```
## Session Restored

**Project**: [project path]
**Last Active**: [timestamp from session_context]

### Previous Progress
[Summary from task_progress memory]

### Open Tasks
[Any incomplete items]

### Key Learnings
[From learnings memory]

### Ready to Continue
[Suggest next actions based on context]
```

## Memory Schema Expected

**session_context**:
```markdown
## Session: [date]
### What I Worked On
- [task 1]
- [task 2]

### Current State
[where things are at]

### Blockers/Issues
[any problems encountered]
```

**task_progress**:
```markdown
## Task: [name]
### Status: [in_progress|blocked|done]
### Completed
- [x] Step 1
- [x] Step 2
### Remaining
- [ ] Step 3
```
