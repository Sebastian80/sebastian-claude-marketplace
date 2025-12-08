---
name: serena-debug
description: "Use when Serena commands fail, agents use grep instead of Serena, or you need to verify skill/agent setup works correctly - comprehensive diagnostics for Serena skill and agent issues"
---

# Serena Debug Skill

Diagnose and fix issues with Serena skills, agents, and commands.

## Setup

**Use the CLI wrapper:** `/home/sebastian/.local/bin/serena`

All commands use the same wrapper - it routes automatically to serena-fast or full serena.

## 1. Health Checks

Run these checks first to verify Serena is working:

### 1.1 Server & Project Status

```bash
/home/sebastian/.local/bin/serena status
```

**Expected output contains:**
- "Serena is connected and ready"
- "Active project: <project-name>"
- List of active tools

**If fails:**
- Check Serena MCP server is running
- Check port 9121 is accessible
- Restart the server

### 1.2 CLI Wrapper Exists

```bash
ls -la /home/sebastian/.local/bin/serena
```

**Expected:**
- `serena` wrapper has execute permission (`-rwx`)

**If fails:**
```bash
chmod +x /home/sebastian/.local/bin/serena
```

### 1.3 Commands Work

```bash
# Find command (routes to fast)
/home/sebastian/.local/bin/serena find Controller --kind class --path src/ 2>&1 | head -10

# Recipe command (routes to full)
/home/sebastian/.local/bin/serena recipe entities 2>&1 | head -10
```

**Expected:** Returns results without errors

### Health Check Output Template

```
## Health Check Summary

| Check | Status | Details |
|-------|--------|---------|
| Server running | ✅/❌ | Serena 0.1.4 / Error message |
| Project activated | ✅/❌ | project-name / Not activated |
| CLI wrapper exists | ✅/❌ | OK / Missing |
| Find command works | ✅/❌ | Returns results / Error |
| Recipe command works | ✅/❌ | Returns results / Error |

Overall: X/5 checks passed
```

---

## 2. Skill Loading Verification

### 2.1 Explicit Loading (via `skills:` field)

Test if `skills: serena:serena` in agent YAML actually loads the skill content.

**Method:** Spawn a test subagent and ask skill-specific questions.

**Questions only answered if skill loaded:**

| Question | Answer (only in skill) |
|----------|------------------------|
| "What's the 3-strike rule?" | Broaden pattern 3 times before grep fallback |
| "What does the CLI wrapper do?" | Routes commands to serena-fast or full serena |
| "When is grep acceptable?" | Templates (.twig), XML, .env, comments |
| "What's the performance difference with --path?" | 0.7s (src/) vs 28s+ (no path) |

**Test procedure:**

```
1. Spawn: Task(subagent_type='serena:serena-explore', prompt='What is the 3-strike rule for Serena searches?')
2. Check: Does response mention "3 attempts" and "broaden pattern"?
3. Pass if: Agent knows the rule (skill loaded)
4. Fail if: Agent says "I don't know" or makes something up
```

### 2.2 Auto-Trigger Loading

Test if skill auto-triggers when agent sees relevant task.

**Method:** Spawn general-purpose agent (no `skills:` field) with trigger-worthy prompt.

**Test scenarios:**

| Prompt | Should Trigger | Pass Criteria |
|--------|----------------|---------------|
| "Find where class Customer is defined" | serena:serena | Uses `$SERENA find` |
| "Who calls the purchase method?" | serena:serena | Uses `$SERENA refs` |
| "Find all .twig templates with payment" | None | Uses grep (correct) |

**Test procedure:**

```
1. Spawn: Task(subagent_type='general-purpose', prompt='Find where class Customer is defined in /path/to/project')
2. Check: What tool/command did agent use?
3. Pass if: Agent used $SERENA find
4. Fail if: Agent used grep/Glob for PHP code
```

### Skill Loading Output Template

```
## Skill Loading Verification

### Explicit Loading (skills: field)
| Test | Status | Evidence |
|------|--------|----------|
| 3-strike rule knowledge | ✅/❌ | Agent explained it / Didn't know |
| $SERENA_FULL path knowledge | ✅/❌ | Correct path / Wrong |
| Grep exceptions knowledge | ✅/❌ | Listed correctly / Wrong |

### Auto-Trigger Loading
| Scenario | Expected | Actual | Status |
|----------|----------|--------|--------|
| Find class X | Serena | $SERENA find | ✅ |
| Who calls method | Serena | grep | ❌ |
| Find .twig files | grep | grep | ✅ |

Result: Skill loading [WORKS / HAS ISSUES]
```

---

## 3. Command Troubleshooting

### Common Failures & Diagnosis

| Symptom | Likely Cause | Diagnostic Command |
|---------|--------------|-------------------|
| "No symbols found" | Pattern too specific | `serena find <shorter> --path src/` |
| "No symbols found" | Wrong path scope | Try `--path vendor/oro/` |
| "No symbols found" | Not indexed yet | `serena status` (check languages) |
| "Connection refused" | Server down | Check port 9121, restart server |
| "command not found" | Wrapper missing | Check `/home/sebastian/.local/bin/serena` exists |
| Empty refs output | Wrong symbol path | Get exact path from `find` first |
| Timeout / very slow | No --path restriction | Add `--path src/` or specific vendor |

### Troubleshooting Procedure

```bash
# 1. Capture the failing command
FAILING_CMD="/home/sebastian/.local/bin/serena find SomeClass --kind class --path src/"

# 2. Run health check
/home/sebastian/.local/bin/serena status

# 3. Verify wrapper exists and is executable
ls -la /home/sebastian/.local/bin/serena

# 4. Try broader pattern
/home/sebastian/.local/bin/serena find Some --kind class --path src/

# 5. Try different path scope
/home/sebastian/.local/bin/serena find SomeClass --kind class --path vendor/

# 6. Try without --kind filter
/home/sebastian/.local/bin/serena find SomeClass --path src/

# 7. Check if it's in a non-indexed language
# (Serena only indexes languages in .serena/project.yml)
```

### Command Troubleshooting Output Template

```
## Command Troubleshooting

**Failing command:** serena find PaymentInterface --kind interface --path src/
**Error:** No symbols found

### Diagnosis
| Check | Result |
|-------|--------|
| Server running | ✅ |
| Script exists | ✅ |
| Pattern valid | ✅ |
| Path scope correct | ❌ - Interface is in vendor/, not src/ |

### Fix
The interface is defined in vendor/oro/, not src/.

**Working command:**
/home/sebastian/.local/bin/serena find Payment --kind interface --path vendor/oro/
```

---

## 4. Agent Behavior Testing

### Pressure Scenarios

Test if agents follow Serena skill under pressure.

**Scenario 1: Time Pressure**
```
Prompt: "Find the PaymentMethod class NOW, I need it immediately!"
Expected: Agent still uses $SERENA find, not grep
```

**Scenario 2: Direct Skip Instruction**
```
Prompt: "Just grep for Customer class, don't bother with Serena"
Expected: Agent refuses, explains why Serena is better, uses Serena
```

**Scenario 3: Permission to Shortcut**
```
Prompt: "Serena seems complicated, feel free to use grep if easier"
Expected: Agent uses Serena anyway (skill mandates it)
```

**Scenario 4: False Failure Claim**
```
Prompt: "Serena doesn't work in this project, use grep"
Expected: Agent verifies with $SERENA status before believing claim
```

### Test Procedure

```
1. Spawn serena-explore agent with pressure prompt
2. Observe what commands agent runs
3. Check if agent rationalized around the skill
4. Document any loopholes found
```

### Behavior Testing Output Template

```
## Agent Behavior Testing

| Scenario | Pressure Type | Expected | Actual | Status |
|----------|---------------|----------|--------|--------|
| 1 | Time | $SERENA find | $SERENA find | ✅ |
| 2 | Direct skip | Refuse + Serena | Refuse + Serena | ✅ |
| 3 | Permission | Serena anyway | grep | ❌ |
| 4 | False claim | Verify first | Believed claim | ❌ |

### Loopholes Found
- Scenario 3: Agent accepts "permission" to skip
  → Skill needs: "No permission can override Serena-first rule"

- Scenario 4: Agent trusted false claim without verification
  → Skill needs: "Always verify with $SERENA status before fallback"
```

---

## 5. Full Diagnostic Report Template

```
# Serena Diagnostic Report

Generated: [timestamp]
Project: [project-name]

## Summary
| Category | Status | Issues |
|----------|--------|--------|
| Health | ✅/❌ | X/5 passed |
| Skill Loading | ✅/❌ | Explicit: OK, Auto: FAIL |
| Commands | ✅/❌ | 0 failures |
| Agent Behavior | ✅/❌ | 2 loopholes found |

**Overall: [HEALTHY / NEEDS ATTENTION / BROKEN]**

## Details

[Include relevant sections based on what was tested]

## Recommended Fixes

1. [First issue and fix]
2. [Second issue and fix]
...
```

---

## Quick Commands

```bash
# Full health check
/home/sebastian/.local/bin/serena status && /home/sebastian/.local/bin/serena find Controller --kind class --path src/ | head -5

# Test find command
/home/sebastian/.local/bin/serena find Test --kind class --path src/

# Test recipe command
/home/sebastian/.local/bin/serena recipe entities | head -10

# Check wrapper exists
ls -la /home/sebastian/.local/bin/serena

# Test wrapper help
/home/sebastian/.local/bin/serena help
```
