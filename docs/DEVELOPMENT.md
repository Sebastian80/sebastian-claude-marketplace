# Development Guide

## Creating Components

### Skills

Skills are reusable instruction sets that Claude loads when triggered.

```bash
# Standalone skill
./scripts/new-skill.sh my-skill

# Skill within a plugin
./scripts/new-skill.sh my-skill --plugin my-plugin
```

Key elements:
- `SKILL.md` with YAML frontmatter
- Strong trigger phrases in description
- Clear instructions with examples

### Plugins

Plugins bundle multiple components together.

```bash
# Minimal plugin
./scripts/new-plugin.sh my-plugin

# Full plugin with all component types
./scripts/new-plugin.sh my-plugin --full
```

### Agents

Agents are autonomous sub-processes for specific tasks.

```bash
./scripts/new-agent.sh my-agent --plugin my-plugin
```

Key elements:
- Description with trigger phrases
- System prompt with clear instructions
- Appropriate tools list

### Commands

Slash commands for direct user invocation.

```bash
./scripts/new-command.sh my-command --plugin my-plugin
```

### Hooks

Event-driven automation scripts.

```bash
./scripts/new-hook.sh my-hook --plugin my-plugin --event PreToolUse
```

Events: PreToolUse, PostToolUse, Stop, SubagentStop, SessionStart, SessionEnd, UserPromptSubmit, PreCompact, Notification

### MCP Servers

Model Context Protocol servers for external integrations.

```bash
./scripts/new-mcp.sh my-server --plugin my-plugin --type stdio
```

Types: stdio, sse, http

## Validation

Always validate before committing:

```bash
./scripts/validate.sh
```

## Publishing

```bash
git add .
git commit -m "feat: description"
git push
```

Claude Code will pull updates when:
- `/plugin update` is run
- A new session starts (with stale cache)
