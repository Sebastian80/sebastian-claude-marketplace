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

Unified `jira` CLI wrapper for all Jira operations.

## The Iron Law

```
TICKET KEY MENTIONED = FETCH IT. NO EXCEPTIONS.
```

If a ticket key (PROJ-123, HMKG-2064) appears anywhere in conversation:
- User's message
- File contents you read
- Git branch name
- Error output

**You MUST fetch it using `jira issue get`.**

Not "might be useful to fetch" - MUST fetch. Not "if relevant" - ALWAYS.

Fetching takes 2 seconds. Guessing wastes the user's time when you're wrong.

## Trigger Patterns

**Immediate fetch required:**
- `PROJ-123`, `HMKG-2064` - any UPPERCASE-NUMBER pattern
- "ticket", "issue", "Jira" + identifier
- "look up", "check", "status of", "what's" + ticket reference
- Branch names like `HMKG-2064-fix-something`

**No judgment. No "is it relevant?". See pattern -> fetch.**

## Common Rationalizations

| Excuse | Reality |
|--------|---------|
| "Quick lookup, faster to describe" | Fetching takes 2 seconds. Your "quick description" is a guess. |
| "I remember the ticket from earlier" | Memory is unreliable. Tickets change. Fetch the current state. |
| "User didn't ask me to fetch it" | User mentioned it. That's implicit permission. Fetch it. |
| "I'll just say I don't have access" | You DO have access. Use the `jira` command. |
| "It would interrupt my flow" | Fetching is part of the flow. 2 seconds isn't interruption. |
| "I can infer from context" | Inference != facts. Fetch the facts. |
| "The ticket isn't relevant to the task" | If it was mentioned, it's relevant. Fetch it. |

## Red Flags - STOP and Fetch

If you catch yourself thinking:
- "I don't need to look that up"
- "I can answer from context"
- "Let me just describe what I know"
- "The user can check Jira themselves"
- "I'll mention I don't have access to Jira"
- "Fetching would slow things down"
- "It's probably still in the same status"

**STOP. You are rationalizing. Fetch the ticket.**

If you've already responded without fetching: Acknowledge the mistake, fetch now.

---

## Instructions

- **Use the `jira` wrapper** - not the underlying Python scripts directly
- **Default to `--format json`** when processing data programmatically
- **Credentials**: Via `~/.env.jira` file or environment variables (see Authentication)
- **Content formatting**: Use **jira-syntax** skill for descriptions/comments (Jira wiki markup, NOT Markdown)

## API Self-Discovery

Use `--help` to discover available commands and their parameters dynamically:

```bash
jira --help              # List all commands
jira search --help       # Get search command parameters
jira issue --help        # Get issue command parameters
```

The help is generated from the daemon's FastAPI metadata - always up-to-date with the actual API.

## Permission Setup

Add to your Claude Code settings for auto-approval:
```
Bash(/path/to/jira:*)
```

Example: `Bash(/home/user/.local/bin/jira:*)`

## Available Commands

### Core Operations

#### `jira issue`
**When to use:** Get or update issue details
```bash
jira issue get PROJ-123
jira issue --json get PROJ-123
jira issue get PROJ-123 --full
```

#### `jira search`
**When to use:** Search issues with JQL queries
```bash
jira search query "project = PROJ AND status = Open"
jira search --json query "assignee = currentUser()"
```

#### `jira validate`
**When to use:** Verify Jira connection and credentials
```bash
jira validate
jira validate --verbose
```

#### `jira worklog`
**When to use:** Add or list time tracking entries
```bash
jira worklog add PROJ-123 2h --comment "Implemented feature X"
jira worklog list PROJ-123
```

### Workflow Operations

#### `jira create`
**When to use:** Create new issues (use **jira-syntax** skill for description content)
```bash
jira create issue PROJ "Fix login bug" --type Bug
jira create issue PROJ "New feature" --type Story --dry-run
```

#### `jira transition`
**When to use:** Change issue status with smart multi-step navigation
```bash
# Simple transition
jira transition do PROJ-123 "In Progress"

# Smart multi-step (finds path automatically)
jira transition do PROJ-123 "Waiting for QA"

# With comment trail
jira transition do PROJ-123 "Waiting for QA" --comment

# Dry-run to see path
jira transition do PROJ-123 "Done" --dry-run
```

#### `jira workflow`
**When to use:** Discover, view, and analyze Jira workflows
```bash
# Discover workflow from issue
jira workflow discover PROJ-123

# Show workflow for issue type
jira workflow show "Sub: Task"
jira workflow show "Sub: Task" --format ascii

# List known workflows
jira workflow list

# Show path between states
jira workflow path "Sub: Task" --from "Offen" --to "Waiting for QA"

# Validate workflow for dead ends
jira workflow validate "Sub: Task"
```

#### `jira comment`
**When to use:** Add comments to issues (use **jira-syntax** skill for formatting)
```bash
jira comment add PROJ-123 "Work completed"
```

#### `jira sprint`
**When to use:** List sprints or sprint issues
```bash
jira sprint list
jira sprint issues 123
```

#### `jira board`
**When to use:** List boards or board issues
```bash
jira board list
jira board issues 456
```

### Utility Operations

#### `jira user`
**When to use:** Get user profile information
```bash
jira user me
```

#### `jira fields`
**When to use:** Search available Jira fields
```bash
jira fields search "sprint"
```

#### `jira link`
**When to use:** Create or list issue links
```bash
jira link list PROJ-123
jira link create PROJ-123 PROJ-456 "blocks"
```

## Flag Ordering

Global flags go **after** the subcommand:

```bash
# Correct
jira issue --json get PROJ-123

# Wrong - wrapper won't recognize command
jira --json issue get PROJ-123
```

## Quick Start

All commands support `--help`, `--json`, `--quiet`, and `--debug`.

```bash
# Validate setup first
jira validate --verbose

# Search issues
jira search query "project = PROJ AND status = Open"

# Get issue details
jira issue get PROJ-123

# Transition with dry-run
jira transition do PROJ-123 "In Progress" --dry-run
```

## Common Workflows

### Find my open issues and get details
```bash
jira search --json query "assignee = currentUser() AND status != Done"
```

### Log 2 hours of work
```bash
jira worklog add PROJ-123 2h --comment "Implemented feature X"
```

### Create and transition an issue
```bash
jira create issue PROJ "Fix login bug" --type Bug
jira transition do PROJ-124 "In Progress"
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

Configuration loaded in priority order:
1. `~/.env.jira` file (if exists)
2. Environment variables (fallback for missing values)

**Jira Cloud**: `JIRA_URL` + `JIRA_USERNAME` + `JIRA_API_TOKEN`
**Jira Server/DC**: `JIRA_URL` + `JIRA_PERSONAL_TOKEN`

Run `jira validate --verbose` to verify setup. See [references/troubleshooting.md](references/troubleshooting.md) for detailed setup.
