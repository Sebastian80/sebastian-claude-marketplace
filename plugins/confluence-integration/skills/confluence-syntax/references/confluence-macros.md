# Confluence Macros Reference

Complete reference for Confluence-specific macros. These macros work in Confluence but NOT in Jira.

## Panel Macros

### Info Panel
Blue panel for informational content.

```
{info}
This is informational content that users should know about.
{info}

{info:title=Important Information}
Panel with a custom title.
{info}

{info:title=Note|icon=false}
Panel without the icon.
{info}
```

### Note Panel
Yellow panel for notes and reminders.

```
{note}
Please remember to backup your data before proceeding.
{note}

{note:title=Remember}
Don't forget to save your changes!
{note}
```

### Warning Panel
Red panel for critical warnings.

```
{warning}
This action cannot be undone!
{warning}

{warning:title=Critical}
Proceeding will delete all data permanently.
{warning}
```

### Tip Panel
Green panel for helpful tips.

```
{tip}
You can use keyboard shortcuts to speed up your workflow.
{tip}

{tip:title=Pro Tip}
Press Ctrl+S to save quickly.
{tip}
```

### Custom Panel
Fully customizable panel with colors and borders.

```
{panel:title=My Custom Panel}
Content inside the panel.
{panel}

{panel:title=Styled Panel|borderStyle=solid|borderColor=#ccc|bgColor=#f5f5f5}
Panel with custom styling.
{panel}

{panel:title=Full Options|borderStyle=dashed|borderColor=#0052CC|borderWidth=2|bgColor=#DEEBFF|titleBGColor=#0052CC|titleColor=#FFFFFF}
Panel with all styling options.
{panel}
```

**Panel Parameters:**
| Parameter | Description | Example |
|-----------|-------------|---------|
| `title` | Panel heading | `title=My Title` |
| `borderStyle` | Border style | `solid`, `dashed`, `none` |
| `borderColor` | Border color | `#ccc`, `red` |
| `borderWidth` | Border thickness | `1`, `2`, `3` |
| `bgColor` | Background color | `#f5f5f5`, `#DEEBFF` |
| `titleBGColor` | Title background | `#0052CC` |
| `titleColor` | Title text color | `#FFFFFF` |

## Navigation Macros

### Table of Contents
Auto-generates table of contents from headings.

```
{toc}

{toc:minLevel=2}

{toc:minLevel=2|maxLevel=4}

{toc:type=flat|separator=pipe}

{toc:outline=true|style=disc}
```

**TOC Parameters:**
| Parameter | Description | Values |
|-----------|-------------|--------|
| `minLevel` | Minimum heading level | 1-6 |
| `maxLevel` | Maximum heading level | 1-6 |
| `type` | List type | `list`, `flat` |
| `separator` | Flat list separator | `pipe`, `comma`, `bracket` |
| `outline` | Show numbering | `true`, `false` |
| `style` | Bullet style | `disc`, `circle`, `square`, `none` |

### Anchor
Create a named anchor for linking.

```
{anchor:section-name}

h2. My Section {anchor:my-section}

[Jump to section|#my-section]
```

### Expand/Collapse
Create collapsible sections.

```
{expand:Click to see details}
Hidden content that appears when expanded.

* Bullet points
* More content
* Even code blocks work here

{code:java}
public class Example {}
{code}
{expand}

{expand:title=Advanced Options}
More complex content here.
{expand}
```

## Status Macros

### Status Lozenge
Colored status badges/lozenges.

```
{status:colour=Green|title=DONE}
{status:colour=Yellow|title=IN PROGRESS}
{status:colour=Red|title=BLOCKED}
{status:colour=Blue|title=NEW}
{status:colour=Grey|title=ON HOLD}
```

**Available Colors:**
- `Green` - Success, done, approved
- `Yellow` - Warning, in progress, pending
- `Red` - Error, blocked, critical
- `Blue` - Info, new, default
- `Grey` - Neutral, on hold, inactive

### Status Examples in Tables

```
||Task||Status||Owner||
|Complete documentation|{status:colour=Green|title=DONE}|[~john]|
|Review code changes|{status:colour=Yellow|title=IN PROGRESS}|[~jane]|
|Deploy to production|{status:colour=Red|title=BLOCKED}|[~admin]|
```

## Layout Macros

### Section and Column
Create multi-column layouts.

```
{section}
{column:width=30%}
Left sidebar content.
{column}
{column:width=70%}
Main content area with more space.
{column}
{section}

{section:border=true}
{column:width=50%}
First column
{column}
{column:width=50%}
Second column
{column}
{section}
```

## Content Inclusion

### Include Page
Embed content from another page.

```
{include:Page Title}

{include:SPACE:Page Title}
```

**Note:** The included page's content appears inline, not as a link.

## Code and Formatting

### Code Block with Syntax Highlighting
```
{code:java}
public class HelloWorld {
    public static void main(String[] args) {
        System.out.println("Hello, World!");
    }
}
{code}

{code:title=Example.py|language=python|linenumbers=true}
def hello():
    print("Hello, World!")
{code}

{code:python|collapse=true|title=Click to expand}
# This code is collapsed by default
import os
print(os.getcwd())
{code}
```

**Code Block Parameters:**
| Parameter | Description | Example |
|-----------|-------------|---------|
| `language` | Syntax highlighting | `java`, `python`, `sql`, `bash` |
| `title` | Block title | `title=Example.java` |
| `linenumbers` | Show line numbers | `true`, `false` |
| `collapse` | Start collapsed | `true`, `false` |
| `firstline` | Starting line number | `firstline=10` |

**Supported Languages:**
`java`, `javascript`, `python`, `sql`, `xml`, `html`, `css`, `bash`, `shell`, `powershell`, `json`, `yaml`, `ruby`, `go`, `rust`, `php`, `typescript`, `c`, `cpp`, `csharp`, `kotlin`, `scala`, `groovy`, and more.

### No Format Block
Preformatted text without syntax highlighting.

```
{noformat}
This text preserves
    whitespace and
        indentation
exactly as written.
{noformat}
```

## Quote Block

```
{quote}
This is a block quote that can span
multiple lines and contain *formatting*.
{quote}

bq. This is a single-line block quote.
```

## Horizontal Rule

```
----
```

Creates a horizontal divider line.

## Common Patterns

### Documentation Page Header
```
{toc:minLevel=2|maxLevel=3}

----

h2. Overview

{info:title=Version}
This document applies to version 2.0 and later.
{info}
```

### Decision Log Entry
```
h3. Decision: Use PostgreSQL for Production

{status:colour=Green|title=APPROVED}

{panel:title=Context|bgColor=#f5f5f5}
We need a reliable database for production workloads.
{panel}

h4. Alternatives Considered
* MySQL - Rejected due to licensing concerns
* MongoDB - Rejected, need relational model

h4. Decision
We will use PostgreSQL 15 for all production databases.

h4. Consequences
* Team needs PostgreSQL training
* Migration from dev MySQL required
```

### Meeting Notes Structure
```
h2. Sprint Planning - 2025-01-15

h3. Attendees
* [~pm] - Product Manager
* [~tech-lead] - Technical Lead
* [~dev1], [~dev2] - Developers

h3. Decisions
||Decision||Owner||Status||
|Prioritize bug fixes|[~tech-lead]|{status:colour=Green|title=APPROVED}|
|Delay feature X|[~pm]|{status:colour=Yellow|title=PENDING}|

h3. Action Items
# [~dev1] - Fix login bug by Friday
# [~dev2] - Update documentation
# [~pm] - Schedule stakeholder review

{expand:Meeting Recording}
[Recording link|https://example.com/recording]
Duration: 45 minutes
{expand}
```

## Macro Compatibility Note

| Macro | Confluence | Jira |
|-------|------------|------|
| `{info}`, `{note}`, `{warning}`, `{tip}` | Yes | No |
| `{toc}` | Yes | No |
| `{expand}` | Yes | No |
| `{status}` | Yes | No |
| `{section}`, `{column}` | Yes | No |
| `{include}` | Yes | No |
| `{panel}` | Yes | Yes |
| `{code}` | Yes | Yes |
| `{quote}` | Yes | Yes |
| `{noformat}` | Yes | Yes |
| `{color}` | Yes | Yes |
| `{anchor}` | Yes | Yes |
