---
name: onboard
description: Activate project in Serena, run onboarding, and load existing memories for session handoff
allowed-tools:
  - Bash
  - Read
---

# Serena Project Onboarding

Perform complete Serena project setup and session initialization.

## Steps to Execute

### 1. Activate Project & Check Status

```bash
~/.claude/skills/serena/scripts/serena status
```

If no project is active, activate it:

```bash
~/.claude/skills/serena/scripts/serena activate "$(pwd)"
```

### 2. List Available Memories

```bash
~/.claude/skills/serena/scripts/serena memory list
```

### 3. Read Key Memories

```bash
# Project overview
~/.claude/skills/serena/scripts/serena memory read project_overview

# Any task context from previous session
~/.claude/skills/serena/scripts/serena memory read task_context
```

## Output

After completing all steps, summarize:

1. **Project Status**: Activated and onboarded?
2. **Available Memories**: List of memory names
3. **Key Context**: Summary of project_overview and task_context
4. **Ready for Work**: Confirm Serena is ready

## Example Summary

```
## Serena Onboarding Complete

**Project**: /home/sebastian/workspace/hmkg
**Status**: Activated and onboarded

### Available Memories
- project_overview
- code_conventions
- bundle_architecture
- task_context

### Project Context
[Summary from project_overview memory]

### Previous Task
[Summary from task_context memory, if exists]

Serena is ready. 23 tools available.
```
