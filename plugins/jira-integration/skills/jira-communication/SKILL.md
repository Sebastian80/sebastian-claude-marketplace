---
name: jira-communication
description: >
  MANDATORY when any ticket key appears (PROJ-123, HMKG-2064, etc.) - fetch it immediately.
  Use for: (1) Any ticket/issue key mentioned anywhere - in conversation, files, git branches, errors,
  (2) "look up", "get", "read", "check", "what's the status of" + ticket reference,
  (3) Searching issues (JQL, "find tickets", "open bugs"),
  (4) Creating, updating, or transitioning tickets,
  (5) Adding comments or logging work time,
  (6) Any mention of "Jira", "ticket", "issue".
  Supports Jira Cloud and Server/Data Center.
---

# Jira Communication

Unified `jira` CLI for all Jira operations via skills-daemon.

## The Iron Law

```
TICKET KEY MENTIONED = FETCH IT. NO EXCEPTIONS.
```

If a ticket key (PROJ-123, HMKG-2064) appears anywhere in conversation:
- User's message
- File contents you read
- Git branch name
- Error output

**You MUST fetch it using `jira issue KEY`.**

Not "might be useful to fetch" - MUST fetch. Not "if relevant" - ALWAYS.

Fetching takes 2 seconds. Guessing wastes the user's time when you're wrong.

## Architecture

```
jira <command> [args] [--params]
    ↓
skills-client jira <command> [args] [--params]
    ↓ HTTP
skills-daemon (FastAPI on port 9100)
    ↓
Jira API
```

The CLI is thin - all logic is in the daemon. Daemon auto-starts on first use.

## Quick Reference

```bash
# Get issue
jira issue PROJ-123

# Search
jira search --jql "assignee = currentUser()"

# Current user
jira user me

# Transitions
jira transitions PROJ-123           # List available
jira transition PROJ-123 --target "In Progress"

# Comments
jira comments PROJ-123              # List
jira comment PROJ-123 --text "Done"

# Create issue
jira create --project PROJ --type Task --summary "New task"

# Workflows
jira workflows                      # List cached
jira workflow discover PROJ-123     # Discover from issue
```

## API Self-Discovery

```bash
jira --help                    # List all commands
skills-client jira --help      # Same thing
skills-client jira issue --help  # Command-specific help
```

Help is generated from daemon's FastAPI metadata - always current.

## Output Formats

```bash
jira issue PROJ-123              # Default compact output
jira --json issue PROJ-123       # Raw JSON for programmatic use
```

## Permission Setup

Add to Claude Code settings for auto-approval:
```
Bash(/home/user/.local/bin/jira:*)
```

## Common Workflows

### Get issue details
```bash
jira issue PROJ-123
```

### Search my open issues
```bash
jira search --jql "assignee = currentUser() AND status != Done"
```

### Transition an issue
```bash
jira transition PROJ-123 --target "In Progress"
```

### Add a comment
```bash
jira comment PROJ-123 --text "Work completed"
```

## Related Skills

**jira-syntax**: Use for formatting descriptions and comments. Jira uses wiki markup, NOT Markdown.
- `*bold*` not `**bold**`
- `h2. Heading` not `## Heading`
- `{code:python}...{code}` not triple backticks

## References

- **JQL syntax**: See [references/jql-quick-reference.md](references/jql-quick-reference.md)
- **Troubleshooting**: See [references/troubleshooting.md](references/troubleshooting.md)

## Authentication

Configuration loaded from `~/.env.jira`:

**Jira Cloud**:
```bash
JIRA_URL=https://yourcompany.atlassian.net
JIRA_USERNAME=your-email@example.com
JIRA_API_TOKEN=your-api-token-here
```

**Jira Server/DC**:
```bash
JIRA_URL=https://jira.yourcompany.com
JIRA_PERSONAL_TOKEN=your-personal-access-token
```

Verify with: `jira user me`
