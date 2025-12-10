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

### 1. Check Status & Activate Project

```bash
/home/sebastian/.local/bin/serena status
```

If no project is active or wrong project is active, activate it using `--project` flag:

```bash
/home/sebastian/.local/bin/serena activate --project "$(pwd)"
```

**Note**: The `--project` flag is required. Positional arguments are ignored by skills-client.

If activation times out (common for large codebases like Magento), run `serena status` to verify - the project may have activated despite the timeout.

### 2. List Available Memories

```bash
/home/sebastian/.local/bin/serena memory/list
```

### 3. Read Key Memories

```bash
# Project overview
/home/sebastian/.local/bin/serena memory/read --name project_overview

# Any task context from previous session
/home/sebastian/.local/bin/serena memory/read --name task_context
```

**Note**: Memory commands use `/` separator (e.g., `memory/list`, `memory/read`).

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
