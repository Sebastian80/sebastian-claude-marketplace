# Plan: Serena Auto-Activation on Skill Load

**Date:** 2025-12-09
**Status:** Proposed

## Problem

The `serena:serena` skill assumes project is already active, but:
- User must manually run `/serena:onboard` first (easy to forget)
- Session handoff requires manual memory loading
- No automatic project context verification

Official Serena uses `--project "$(pwd)"` at server start, auto-activating the project. Our centralized server architecture requires manual activation.

## Solution

Add auto-activation block at the **start** of the skill that:
1. Checks if correct project is active
2. Activates if needed
3. Verifies onboarding status
4. Loads session context

## Implementation

### Task 1: Add Auto-Activation Section to Skill

**File:** `skills/serena/SKILL.md`

**Location:** After the `<EXTREMELY-IMPORTANT>` block, before "Automatic Triggers"

**New Section:**

```markdown
## Auto-Activation (Run First)

Before using any Serena commands, ensure project is active:

### Step 1: Check Status
```bash
serena status
```

**Expected output shows:**
- `Active project: <project-name>` (not empty)
- Active tools listed

### Step 2: Activate if Needed

If no project active or wrong project:
```bash
serena activate "$(pwd)"
```

### Step 3: Verify Onboarding (Optional)

For full semantic indexing:
```bash
# Check if onboarded
serena check_onboarding_performed

# If not, run onboarding (takes time on large codebases)
serena onboarding
```

### Step 4: Load Session Context (Optional)

If memories exist from previous session:
```bash
serena memory tree active
serena memory read active/sessions/current
```

**Note:** Steps 3-4 are optional but recommended for best results.
```

---

### Task 2: Update Slash Commands to Use Simple `serena`

**Files to update:**
- `commands/onboard.md`
- `commands/load.md`
- `commands/save.md`

**Change:** Replace all `/home/sebastian/.local/bin/serena` with `serena`

**Example (onboard.md):**
```markdown
### 1. Activate Project & Check Status

```bash
serena status
```

If no project is active, activate it:

```bash
serena activate "$(pwd)"
```
```

---

### Task 3: Update Agents to Use Simple `serena`

**Files to update:**
- `agents/serena-explore.md`
- `agents/serena-debug.md`
- `agents/framework-explore.md`

**Change:** Replace all full paths with `serena`

---

### Task 4: Add Pre-Flight Check to Skill Header

**File:** `skills/serena/SKILL.md`

**Location:** Very top, in frontmatter or immediately after

**Add warning banner:**

```markdown
> **Pre-flight Check Required**
>
> Run `serena status` first. If no project active, run `serena activate "$(pwd)"`.
> Skip this if you just ran `/serena:onboard`.
```

---

### Task 5: Create Quick-Start Section

**File:** `skills/serena/SKILL.md`

**New section after Auto-Activation:**

```markdown
## Quick Start (Copy-Paste)

```bash
# 1. Check & activate (run once per session)
serena status || serena activate "$(pwd)"

# 2. Verify tools available
serena tools | head -5

# 3. Test semantic search
serena find Controller --kind class --path src/
```
```

---

### Task 6: Sync Changes to Cache

After editing source files, sync to cache:

```bash
# Sync skill
cp plugins/marketplaces/sebastian-marketplace/plugins/serena-integration/skills/serena/SKILL.md \
   plugins/cache/sebastian-marketplace/serena-integration/1.0.0/skills/serena/SKILL.md

# Sync commands
for cmd in onboard load save; do
  cp plugins/marketplaces/sebastian-marketplace/plugins/serena-integration/commands/${cmd}.md \
     plugins/cache/sebastian-marketplace/serena-integration/1.0.0/commands/${cmd}.md
done

# Sync agents
for agent in serena-explore serena-debug framework-explore; do
  cp plugins/marketplaces/sebastian-marketplace/plugins/serena-integration/agents/${agent}.md \
     plugins/cache/sebastian-marketplace/serena-integration/1.0.0/agents/${agent}.md
done
```

---

## Files Changed

| File | Change |
|------|--------|
| `skills/serena/SKILL.md` | Add auto-activation section, quick-start |
| `commands/onboard.md` | Use `serena` instead of full path |
| `commands/load.md` | Use `serena` instead of full path |
| `commands/save.md` | Use `serena` instead of full path |
| `agents/serena-explore.md` | Use `serena` instead of full path |
| `agents/serena-debug.md` | Use `serena` instead of full path |
| `agents/framework-explore.md` | Use `serena` instead of full path |

## Testing

1. Restart Claude Code
2. Load skill: `Skill(serena:serena)`
3. Verify auto-activation section appears
4. Test `/serena:onboard` uses simple `serena` commands
5. Test agents use simple `serena` commands

## Alternative: SessionStart Hook (Future)

For fully automatic activation, could add a SessionStart hook:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [{
          "type": "command",
          "command": "serena status >/dev/null 2>&1 || serena activate \"$(pwd)\" 2>/dev/null || true"
        }]
      }
    ]
  }
}
```

**Pros:** Fully automatic
**Cons:** Runs on every session, even non-code tasks

## Decision

Implement Tasks 1-6 (skill-based approach) first. SessionStart hook can be added later if needed.
