---
name: project-memory
description: Use when starting work on a project, ending a session, or needing to recall past decisions. Triggers - "what did we do before", "continue from last time", "save progress", "remember this", session start/end.
---

# Project Memory Skill

## When to Use

- **First time on project**: Initialize with `pm init`
- **Session start**: Load context with `/pm:load`
- **Session end**: Save progress with `/pm:save`
- **Mid-session**: Search past work with `/pm:search`
- **Learning something**: Save with `pm write "learnings/[topic]" "..."`

## Memory Organization

```
.project-memory/
├── active/
│   ├── session.md           # Current session state (singular)
│   └── tasks/
│       └── TICKET-123.md    # In-progress work
├── archive/
│   ├── sessions/            # Past sessions
│   └── tasks/               # Completed tasks
└── learnings/
    └── [topic].md           # Persistent learnings
```

## Templates

Use templates from `${PLUGIN_ROOT}/templates/` when writing memories:

| Memory Type | Template | Path Pattern |
|-------------|----------|--------------|
| Session | `templates/session.md` | `active/session.md` |
| Task | `templates/task.md` | `active/tasks/*` |
| Learning | `templates/learning.md` | `learnings/**` |

**Datetime format:** `YYYY-MM-DD HH:MM`

Read the template, fill placeholders (`{{datetime}}`, `{{content}}`, etc.), then write.

## Quick Reference

| Action | Command |
|--------|---------|
| Initialize (first time) | `pm init` |
| Save session | `/pm:save` |
| Load context | `/pm:load` |
| Search memories | `/pm:search [term]` |
| View structure | `pm tree` |
| Read specific | `pm read "[name]"` |
| Write learning | Use learning template |

## Best Practices

1. **Save frequently**: Use `/pm:save` before ending sessions
2. **Structure learnings**: Use descriptive paths like `learnings/python/asyncio`
3. **Archive completed work**: Don't delete, archive for reference
4. **Search before asking**: Check memories before asking user to repeat context

## Red Flags

- Starting work without checking existing context -> `/pm:load` first
- Ending session without saving -> `/pm:save` before stopping
- Asking user "what were we working on?" -> Search memories first
