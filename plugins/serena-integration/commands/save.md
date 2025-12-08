---
description: Save current session state to Serena memories for cross-session continuity
allowed-tools:
  - Bash
---

# /serena-save - Persist Session Context

Save current session state for cross-session continuity.

## Execute These Steps

### 1. Gather Session Context

Before saving, analyze the current session:
- What tasks were worked on?
- What was accomplished?
- What's still in progress?
- What was learned (errors, patterns, insights)?
- What should happen next?

### 2. Save Session Context
```bash
/home/sebastian/.local/bin/serena memory write session_context "## Session: $(date '+%Y-%m-%d')

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
/home/sebastian/.local/bin/serena memory write task_progress "## Task: [task name]

### Status: [in_progress|blocked|review|done]

### Completed
- [x] [completed step 1]
- [x] [completed step 2]

### Remaining
- [ ] [next step]
- [ ] [future step]

### Notes
[any important context for resuming]
"
```

### 4. Save Learnings (if discovered something useful)
```bash
/home/sebastian/.local/bin/serena memory write learnings "## Learnings

### Patterns Discovered
- [useful pattern or approach]

### Mistakes to Avoid
- [error made] → [correct approach]

### Useful Commands/Snippets
\`\`\`bash
[command that was helpful]
\`\`\`
"
```

### 5. Confirm Save
```bash
/home/sebastian/.local/bin/serena memory list
```

Report what was saved:
```
## Session Saved

**Memories Updated:**
- session_context (current state)
- task_progress (task status)
- learnings (if applicable)

**Timestamp**: [auto-added by CLI]

Ready for session handoff.
```

## Smart Save Triggers

Save automatically when:
- User says "save session", "save progress", "I'm done for now"
- Before switching to a different project
- After completing a major task
- When encountering a blocker that needs external input

## Memory Naming Convention

| Memory | Purpose | When to Update |
|--------|---------|----------------|
| `session_context` | Current session state | Every /serena-save |
| `task_progress` | Specific task tracking | When working on defined task |
| `learnings` | Accumulated insights | When discovering patterns/mistakes |
| `project_overview` | Project structure | Rarely, after major changes |
| `[feature]_context` | Feature-specific | For complex multi-session features |
