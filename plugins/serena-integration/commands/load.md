---
description: Restore Serena session context by loading memories from previous sessions
allowed-tools:
  - Bash
  - Read
---

# /serena-load - Restore Session Context

Quick session restoration with folder-organized memory recovery.

## Execute These Steps

### 1. Activate & Check Status
```bash
/home/sebastian/.local/bin/serena status
```

If no project active or wrong project:
```bash
/home/sebastian/.local/bin/serena activate "$(pwd)"
```

### 2. Show Memory Structure
```bash
/home/sebastian/.local/bin/serena memory tree
```

### 3. Load Active Context (in parallel)

Check what's in active folders:
```bash
/home/sebastian/.local/bin/serena memory list active
```

Load session and task memories:
```bash
/home/sebastian/.local/bin/serena memory read active/sessions/current
/home/sebastian/.local/bin/serena memory list active/tasks
```

For each active task, read its memory.

### 4. Load Reference Context (if needed)
```bash
/home/sebastian/.local/bin/serena memory list reference
/home/sebastian/.local/bin/serena memory list learnings
```

### 5. Report Session State

Present a structured summary:

```
## Session Restored

**Project**: [project path]
**Last Active**: [timestamp from active/sessions/current]

### Active Tasks
[List from active/tasks/ folder]

### Previous Session
[Summary from active/sessions/current]

### Key Learnings
[From learnings/ folder if relevant]

### Ready to Continue
[Suggest next actions based on context]
```

## Memory Folder Structure

```
memories/
├── active/
│   ├── sessions/current    # Last session state
│   └── tasks/              # In-progress tasks (HMKG-2064, etc.)
├── reference/              # Architecture, patterns, integrations
├── learnings/              # Mistakes, discoveries, commands
└── archive/                # Completed work (auto-organized by date)
```

## Expected Memory Schemas

**active/sessions/current**:
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

**active/tasks/TICKET**:
```markdown
## Task: [name]
### Status: [in_progress|blocked|done]
### Completed
- [x] Step 1
- [x] Step 2
### Remaining
- [ ] Step 3
### Key Files
- [file paths]
```
