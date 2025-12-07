---
name: confluence-communication
description: >
  Confluence API operations via Python CLI scripts. Use when:
  - Searching Confluence pages (CQL queries)
  - Getting, creating, updating, or deleting pages
  - Managing labels, comments, attachments
  - Listing spaces and page hierarchies
  - Exporting pages to markdown
  - Converting between markdown and wiki markup
  - Rendering Mermaid diagrams and uploading to pages
  - Syncing markdown files to Confluence (Git-to-Confluence workflow)
  - Any request mentioning "Confluence", "wiki", "page", or page IDs
  Supports Confluence Cloud and Server/Data Center with automatic auth detection.
---

# Confluence Communication

Standalone CLI scripts for Confluence operations using `uv run`.

## Instructions

- **Default to `--json` flag** when processing data programmatically
- **Don't read scripts** - use `<script>.py --help` to understand options
- **Validate first**: Run `confluence-validate.py` before other operations
- **Dry-run writes**: Use `--dry-run` for create/update/delete operations
- **Credentials**: Via `~/.env.confluence` file or environment variables (see Authentication)
- **Content formatting**: Use **confluence-syntax** skill for page content (Confluence wiki markup, NOT Markdown)

## Available Scripts

### Core Operations

#### `scripts/core/confluence-validate.py`
**When to use:** Verify Confluence connection and credentials

#### `scripts/core/confluence-search.py`
**When to use:** Search pages with CQL queries
- Subcommands: `query`, `text`

#### `scripts/core/confluence-page.py`
**When to use:** Get, create, update, or delete pages
- Subcommands: `get`, `create`, `update`, `delete`, `get-by-title`

#### `scripts/core/confluence-space.py`
**When to use:** List spaces or get space details
- Subcommands: `list`, `get`, `pages`

### Workflow Operations

#### `scripts/workflow/confluence-label.py`
**When to use:** Manage page labels
- Subcommands: `list`, `add`, `remove`

#### `scripts/workflow/confluence-comment.py`
**When to use:** Add or list page comments
- Subcommands: `list`, `add`

#### `scripts/workflow/confluence-children.py`
**When to use:** Navigate page hierarchy
- Subcommands: `list`, `ancestors`

#### `scripts/workflow/confluence-attachment.py`
**When to use:** Upload, list, or download attachments
- Subcommands: `list`, `upload`, `download`

### Utility Operations

#### `scripts/utility/confluence-export.py`
**When to use:** Export pages to markdown files
- Subcommands: `page`, `space`

#### `scripts/utility/confluence-convert.py`
**When to use:** Convert between markdown and wiki markup
- Subcommands: `to-wiki`, `to-markdown`

#### `scripts/utility/confluence-user.py`
**When to use:** Get user information
- Subcommands: `me`, `search`

#### `scripts/utility/confluence-mermaid.py`
**When to use:** Render Mermaid diagrams and upload to Confluence
- Subcommands: `render`, `to-storage`, `upload`, `check`
- Requires: `mermaid-cli` (mmdc) or uses mermaid.ink API fallback
- Linux users: See [Mermaid CLI Setup](#mermaid-cli-setup-linux) for sandbox fix

#### `scripts/utility/confluence-sync.py`
**When to use:** Sync markdown files to Confluence (documentation-as-code)
- Subcommands: `push`, `push-dir`, `check`, `init-frontmatter`
- Supports: YAML frontmatter, mark CLI integration, native API fallback

## Flag Ordering (Critical)

Global flags **MUST** come **before** the subcommand:

```bash
# Correct
uv run scripts/core/confluence-page.py --json get 12345

# Wrong - fails with "No such option"
uv run scripts/core/confluence-page.py get 12345 --json
```

## Quick Start

All scripts support `--help`, `--json`, `--quiet`, and `--debug`.

```bash
# Validate setup first
uv run scripts/core/confluence-validate.py --verbose

# Search pages
uv run scripts/core/confluence-search.py query "space = DEV AND type = page"

# Get page by ID
uv run scripts/core/confluence-page.py get 12345678

# Create page with dry-run
uv run scripts/core/confluence-page.py create DEV "New Page Title" --body "<p>Content</p>" --dry-run
```

## Common Workflows

### Find pages in a space
```bash
uv run scripts/core/confluence-search.py --json query "space = DEV AND type = page"
```

### Export a page to markdown
```bash
uv run scripts/utility/confluence-export.py page 12345678 -o page.md --include-frontmatter
```

### Add labels to a page
```bash
uv run scripts/workflow/confluence-label.py add 12345678 documentation api-reference
```

### Convert markdown to wiki markup
```bash
uv run scripts/utility/confluence-convert.py to-wiki README.md -o output.wiki
```

### Render and upload a Mermaid diagram
```bash
# Render locally
uv run scripts/utility/confluence-mermaid.py render diagram.mmd -o diagram.svg

# Upload to a page
uv run scripts/utility/confluence-mermaid.py upload 12345678 diagram.mmd --name architecture
```

### Sync markdown docs to Confluence
```bash
# Push single file
uv run scripts/utility/confluence-sync.py push docs/guide.md --space DEV --parent "Documentation"

# Push entire directory
uv run scripts/utility/confluence-sync.py push-dir docs/ --space DEV -r

# Add frontmatter to file
uv run scripts/utility/confluence-sync.py init-frontmatter README.md --space DEV --title "Project Overview"
```

## CQL Quick Reference

CQL (Confluence Query Language) examples:

```
# Pages in a specific space
space = "DEV"

# Pages by title (contains)
title ~ "Architecture"

# Recently modified
lastModified > now("-7d")

# By label
label = "documentation"

# Combine conditions
space = "DEV" AND type = "page" AND text ~ "API"

# Created by user
creator = "john.doe"
```

See `references/cql-quick-reference.md` for complete syntax.

## Authentication

Configuration loaded in priority order:
1. `~/.env.confluence` file (if exists)
2. Environment variables (fallback for missing values)

**Confluence Cloud**: `CONFLUENCE_URL` + `CONFLUENCE_USERNAME` + `CONFLUENCE_API_TOKEN`
**Confluence Server/DC**: `CONFLUENCE_URL` + `CONFLUENCE_PERSONAL_TOKEN`

### Example ~/.env.confluence

**For Cloud:**
```
CONFLUENCE_URL=https://company.atlassian.net
CONFLUENCE_USERNAME=your-email@example.com
CONFLUENCE_API_TOKEN=your-api-token
```

**For Server/DC:**
```
CONFLUENCE_URL=https://confluence.yourcompany.com
CONFLUENCE_PERSONAL_TOKEN=your-personal-access-token
```

Run `confluence-validate.py --verbose` to verify setup.

## Mermaid CLI Setup (Linux)

Install mermaid-cli:
```bash
npm install -g @mermaid-js/mermaid-cli
```

### Chrome Sandbox Fix (Ubuntu 23.10+)

On Ubuntu 23.10+ and other modern Linux distributions, mermaid-cli fails with Chrome sandbox errors due to AppArmor restrictions.

**Solution:** Create a Puppeteer config to use system Chrome:

```bash
mkdir -p ~/.config/mermaid
cat > ~/.config/mermaid/puppeteer-config.json << 'EOF'
{
  "executablePath": "/usr/bin/google-chrome",
  "args": ["--no-sandbox", "--disable-setuid-sandbox", "--disable-gpu"]
}
EOF
```

The `confluence-mermaid.py` script auto-detects this config. For direct mmdc usage:
```bash
mmdc -i diagram.mmd -o out.svg -p ~/.config/mermaid/puppeteer-config.json
```

**Alternative:** If you don't want to configure Puppeteer, the script automatically falls back to the mermaid.ink API (requires internet).

## Related Skills

**confluence-syntax**: Use for formatting page content, templates, and validation. Confluence uses wiki markup, NOT Markdown.
- `*bold*` not `**bold**`
- `h2. Heading` not `## Heading`
- `{code:python}...{code}` not triple backticks
- `{info}...{info}` for info panels

## References

- **CQL syntax**: See [references/cql-quick-reference.md](references/cql-quick-reference.md)
- **Troubleshooting**: See [references/troubleshooting.md](references/troubleshooting.md)
