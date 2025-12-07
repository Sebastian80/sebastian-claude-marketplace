---
name: "confluence-syntax"
description: "Confluence wiki markup syntax validation, templates, and formatting guidance. Use when: (1) Writing Confluence page content or comments, (2) Converting Markdown to Confluence wiki markup, (3) Requesting documentation templates, (4) Validating Confluence syntax before submission, (5) Keywords like 'confluence format', 'wiki markup', 'format for confluence', (6) Ensuring content uses h2./h3. headings instead of Markdown ##, (7) Checking macros like {info}, {toc}, {code:lang}, (8) Any task involving Confluence text formatting"
---

# Confluence Syntax Validation Skill

Provides Confluence wiki markup syntax validation, templates, and formatting guidance. For API operations (create/update pages, search, attachments), use the **confluence-communication** skill.

## Quick Syntax Reference

| Confluence Syntax | Purpose | NOT this (Markdown) |
|-------------------|---------|---------------------|
| `h2. Title` | Heading | `## Title` |
| `*bold*` | Bold | `**bold**` |
| `_italic_` | Italic | `*italic*` |
| `{{code}}` | Inline code | `` `code` `` |
| `{code:java}...{code}` | Code block | ``` ```java ``` |
| `[text\|url]` | Link | `[text](url)` |
| `[Page Title]` | Page link | - |
| `[SPACE:Page]` | Cross-space link | - |
| `[~username]` | User mention | `@username` |
| `* item` | Bullet list | `- item` |
| `# item` | Numbered list | `1. item` |
| `\|\|Header\|\|` | Table header | `\|Header\|` |

See `references/confluence-wiki-markup.md` for complete syntax documentation.

## Confluence-Specific Macros

These macros work in Confluence but NOT in Jira:

| Macro | Purpose | Example |
|-------|---------|---------|
| `{info}...{info}` | Blue info panel | Important information |
| `{note}...{note}` | Yellow note panel | Notes and reminders |
| `{warning}...{warning}` | Red warning panel | Critical warnings |
| `{tip}...{tip}` | Green tip panel | Helpful tips |
| `{toc}` | Table of contents | Auto-generated TOC |
| `{expand:title}...{expand}` | Collapsible section | Hide details |
| `{status:colour=Green\|title=DONE}` | Status badge | Colored lozenges |
| `{anchor:name}` | Create anchor | Link targets |

See `references/confluence-macros.md` for complete macro documentation.

## Available Templates

### Documentation Page
**Path**: `templates/documentation-template.md`

Sections: Overview, Prerequisites, Installation, Configuration, Usage, Troubleshooting

### Meeting Notes
**Path**: `templates/meeting-notes-template.md`

Sections: Attendees, Agenda, Discussion, Decisions, Action Items

### Architecture Decision Record (ADR)
**Path**: `templates/adr-template.md`

Sections: Status, Context, Decision, Consequences, Alternatives Considered

### Runbook / Troubleshooting Guide
**Path**: `templates/runbook-template.md`

Sections: Overview, Prerequisites, Symptoms, Diagnosis, Resolution, Prevention

## Syntax Validation

Run before submitting to Confluence:
```bash
scripts/validate-confluence-syntax.sh path/to/content.txt
```

### Validation Checklist
- [ ] Headings: `h2. Title` (space after period)
- [ ] Bold: `*text*` (single asterisk)
- [ ] Code blocks: `{code:language}...{code}`
- [ ] Lists: `*` for bullets, `#` for numbers
- [ ] Links: `[label|url]` or `[Page Title]`
- [ ] Tables: `||Header||` and `|Cell|`
- [ ] Info panels: `{info}...{info}` (not `> note`)
- [ ] TOC: `{toc}` at page top if needed

### Common Mistakes

| Wrong (Markdown) | Correct (Confluence) |
|------------------|----------------------|
| `## Heading` | `h2. Heading` |
| `**bold**` | `*bold*` |
| `` `code` `` | `{{code}}` |
| `[text](url)` | `[text\|url]` |
| `- bullet` | `* bullet` |
| `h2.Title` | `h2. Title` |
| `> quote` | `{quote}...{quote}` |
| ``` ```code``` ``` | `{code}...{code}` |
| `> **Note:** text` | `{note}text{note}` |

## Integration with confluence-communication Skill

**Workflow:**
1. Get template from confluence-syntax
2. Fill content using Confluence wiki markup
3. Validate with `scripts/validate-confluence-syntax.sh`
4. Submit via confluence-communication scripts (e.g., `uv run scripts/core/confluence-page.py create`)

## Atlassian Wiki Markup Note

Confluence and Jira share the same underlying wiki renderer (AtlassianWikiRenderer). The core syntax is ~90% identical. Key differences:
- **Confluence-only macros**: `{info}`, `{note}`, `{warning}`, `{tip}`, `{toc}`, `{expand}`, `{status}`
- **Page links**: `[Page Title]` and `[SPACE:Page]` work only in Confluence
- **Jira issue links**: `[PROJ-123]` works in both

## References

- `references/confluence-wiki-markup.md` - Complete syntax documentation
- `references/confluence-macros.md` - Macro catalog and examples
- `scripts/validate-confluence-syntax.sh` - Automated syntax checker
- [Official Confluence Wiki Markup](https://confluence.atlassian.com/doc/confluence-wiki-markup-251003035.html)
