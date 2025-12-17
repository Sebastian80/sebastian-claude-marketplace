---
name: jira
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

Unified `jira` CLI for all Jira operations via AI Tool Bridge daemon.

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
bridge jira <command> [args] [--params]
    ↓ HTTP
AI Tool Bridge daemon (FastAPI on port 9100)
    ↓
Jira API
```

The CLI is thin - all logic is in the daemon. Daemon auto-starts on first use.

## Quick Reference

```bash
# ─── Issues ───────────────────────────────────────────
jira issue PROJ-123                    # Get issue details
jira issue PROJ-123 --fields summary,status  # Specific fields
jira issue PROJ-123 --expand changelog # Include change history
jira create --project PROJ --type Task --summary "New task"

# ─── Search ───────────────────────────────────────────
jira search --jql "assignee = currentUser()"
jira search --jql "project = PROJ" --maxResults 50

# ─── Transitions ─────────────────────────────────────
jira transitions PROJ-123              # List available transitions
jira transition PROJ-123 --target "In Progress"

# ─── Comments ─────────────────────────────────────────
jira comments PROJ-123                 # List comments
jira comment PROJ-123 --text "Done"    # Add comment

# ─── Time Tracking ────────────────────────────────────
jira worklogs PROJ-123                 # List worklogs
jira worklog PROJ-123 --timeSpent 2h   # Log time
jira worklog PROJ-123 12345            # Get specific worklog

# ─── Links ────────────────────────────────────────────
jira links PROJ-123                    # Issue links
jira linktypes                         # Available link types
jira link --from PROJ-1 --to PROJ-2 --type Blocks
jira weblinks PROJ-123                 # Web/remote links
jira weblink PROJ-123 --url "https://..."

# ─── Attachments & Watchers ───────────────────────────
jira attachments PROJ-123              # List attachments
jira watchers PROJ-123                 # List watchers
jira watcher PROJ-123 --username john  # Add watcher

# ─── Project Data ─────────────────────────────────────
jira projects                          # List all projects
jira project PROJ                      # Project details
jira components PROJ                   # Project components
jira versions PROJ                     # Project versions

# ─── Reference Data ───────────────────────────────────
jira priorities                        # Priority levels
jira statuses                          # All statuses
jira fields                            # All fields
jira filters                           # Your saved filters
jira user me                           # Current user

# ─── Health ───────────────────────────────────────────
jira health                            # Check connection
```

## API Self-Discovery

```bash
jira --help                    # List all commands
bridge jira --help             # Same thing
bridge jira issue --help       # Command-specific help
```

Help is generated from daemon's FastAPI metadata - always current.

## Output Formats

```bash
jira issue PROJ-123                     # Default JSON output
jira issue PROJ-123 --format human      # Human-readable tables
jira issue PROJ-123 --format ai         # Structured for AI context
jira issue PROJ-123 --format markdown   # Markdown tables
jira issue PROJ-123 --format json       # Raw JSON (explicit)
```

## Permission Setup

Add to Claude Code settings for auto-approval:
```
Bash(jira:*)
```

## Common Workflows

### Get issue details
```bash
jira issue PROJ-123
```

### Search my open issues
```bash
jira search --jql 'assignee = currentUser() AND status != Done'
```

**Note**: Use single quotes for JQL to avoid bash history expansion with `!`.

### Transition an issue
```bash
jira transition PROJ-123 --target "In Progress"
```

### Add a comment
```bash
jira comment PROJ-123 --text "Work completed"
```

## Localized Jira Instances

If your Jira displays German (or other language) status names, **always use English names in JQL**:

| Display Name | JQL Value |
|--------------|-----------|
| Geschlossen | Closed |
| Offen | Open |
| In Arbeit | In Progress |
| Erledigt | Resolved |
| Zu erledigen | To Do |

Example: Even if the UI shows "Geschlossen", use `status = Closed` in JQL.

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
