---
description: Save current session state to Serena memories for cross-session continuity
allowed-tools:
  - Bash
---

# /serena-save - Persist Session Context

Save current session state using folder-organized memories.

## Execute These Steps

### 1. Gather Session Context

Before saving, analyze the current session:
- What tasks were worked on?
- What was accomplished?
- What's still in progress?
- What was learned (errors, patterns, insights)?
- What should happen next?

### 2. Save Session State
```bash
/home/sebastian/.local/bin/serena memory write active/sessions/current "## Session: $(date '+%Y-%m-%d')

### What I Worked On
- [list main tasks/topics from this session]

### Current State
[describe where things are at - what's working, what's not]

### Blockers/Issues
[any problems encountered, errors, or decisions needed]

### Key Files Modified
- [file1.php]
- [file2.ts]
"
```

### 3. Save Task Progress (if working on specific task)
```bash
/home/sebastian/.local/bin/serena memory write active/tasks/HMKG-XXXX "## Task: [task name]

### Status: [in_progress|blocked|review|done]

### Completed
- [x] [completed step 1]
- [x] [completed step 2]

### Remaining
- [ ] [next step]
- [ ] [future step]

### Key Files
- [affected file paths]

### Notes
[any important context for resuming]
"
```

### 4. Save Learnings (if discovered something useful)

For mistakes/errors:
```bash
/home/sebastian/.local/bin/serena memory write learnings/mistakes/[topic] "## [Error description]

### What Went Wrong
[description]

### Root Cause
[why it happened]

### Solution
[how to fix/avoid]
"
```

For discoveries:
```bash
/home/sebastian/.local/bin/serena memory write learnings/discoveries/[topic] "## [Discovery]

### Context
[when you might need this]

### Details
[what you learned]

### Example
\`\`\`
[code or commands]
\`\`\`
"
```

### 5. Archive Completed Tasks (if any task is done)
```bash
# Archive completed tasks to preserve history
/home/sebastian/.local/bin/serena memory archive active/tasks/HMKG-XXXX --category tasks
```

### 6. Confirm Save
```bash
/home/sebastian/.local/bin/serena memory tree active
/home/sebastian/.local/bin/serena memory stats
```

Report what was saved:
```
## Session Saved

**Active Memories:**
- active/sessions/current (session state)
- active/tasks/[ticket] (task progress)

**Learnings Added:**
- learnings/[category]/[topic]

**Archived:**
- [any completed tasks]

Ready for session handoff.
```

## Smart Save Triggers

Save automatically when:
- User says "save session", "save progress", "I'm done for now"
- Before switching to a different project
- After completing a major task
- When encountering a blocker that needs external input

## Memory Folder Conventions

| Folder | Purpose | When to Use |
|--------|---------|-------------|
| `active/sessions/current` | Current session state | Every /serena-save |
| `active/tasks/TICKET` | Task-specific progress | One per active task |
| `learnings/mistakes/` | Errors & solutions | After debugging issues |
| `learnings/discoveries/` | Useful findings | When learning something new |
| `learnings/commands/` | Helpful snippets | Useful CLI commands |
| `reference/architecture/` | System design notes | After major exploration |
| `reference/patterns/` | Code patterns | When documenting approaches |

## Lifecycle

```
CREATE → active/tasks/TICKET
  ↓
UPDATE → As work progresses
  ↓
COMPLETE → archive with: serena memory archive active/tasks/TICKET --category tasks
  ↓
LEARNING → Extract insights to learnings/
```
