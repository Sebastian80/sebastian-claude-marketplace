---
description: Save current session state to project memory for cross-session continuity
allowed-tools:
  - Bash
  - Read
---

# /pm:save - Persist Session Context

## Steps

### 1. Check Initialized

```bash
pm tree
```

If not initialized, run `pm init` first.

### 2. Analyze Current Session

Before saving, identify:
- What tasks were worked on?
- What was accomplished?
- What's still in progress?

### 3. Save Session State

Read template from `${PLUGIN_ROOT}/templates/session.md`, fill placeholders:
- `{{datetime}}` - current datetime (YYYY-MM-DD HH:MM)
- `{{project}}` - project/repo name
- `{{tasks}}` - active task IDs as list (e.g., `- OROSPD-589\n- OROSPD-655`)
- `{{working_on}}` - brief summary of current focus
- `{{progress}}` - what was accomplished
- `{{decisions}}` - key decisions made (or "None")
- `{{blockers}}` - blockers or pending questions (or "None")
- `{{next}}` - what's remaining

Write to `active/session`.

### 4. Save/Update Task Progress (if applicable)

Read template from `${PLUGIN_ROOT}/templates/task.md`, fill placeholders:
- `{{ticket}}` - ticket ID (e.g., PROJ-123)
- `{{title}}` - brief description
- `{{status}}` - in_progress, blocked, review
- `{{done}}` - completed items (use `- [x]` format)
- `{{next}}` - remaining items (use `- [ ]` format)
- `{{files}}` - key file paths
- `{{datetime}}` - current datetime

Write to `active/tasks/TICKET-ID`.

### 5. Archive Completed Tasks (if any)

```bash
pm archive "active/tasks/TICKET-ID" --category completed
```

### 6. Save Learnings (if any discoveries)

Read template from `${PLUGIN_ROOT}/templates/learning.md`, fill placeholders:
- `{{title}}` - topic name
- `{{content}}` - what you learned
- `{{when_useful}}` - when to apply this knowledge
- `{{datetime}}` - current datetime

Write to `learnings/[topic]`.

### 7. Confirm

```bash
pm tree
pm stats
```

Report:
```
## Session Saved

**Updated:**
- active/session
- active/tasks/[ticket]

**Learnings:**
- learnings/[topic]

**Archived:**
- [completed tickets]

Ready for handoff.
```
