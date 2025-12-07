# CQL Quick Reference

Confluence Query Language (CQL) is used to search for content in Confluence.

## Basic Syntax

```
field operator value
```

## Fields

| Field | Description | Example |
|-------|-------------|---------|
| `space` | Space key | `space = "DEV"` |
| `title` | Page title | `title ~ "Architecture"` |
| `text` | Page content | `text ~ "API endpoint"` |
| `type` | Content type | `type = "page"` |
| `label` | Page labels | `label = "documentation"` |
| `creator` | Created by | `creator = "john.doe"` |
| `contributor` | Edited by | `contributor = "jane.doe"` |
| `created` | Creation date | `created > "2024-01-01"` |
| `lastModified` | Last modified | `lastModified > now("-7d")` |
| `parent` | Parent page ID | `parent = 12345` |
| `ancestor` | Any ancestor | `ancestor = 12345` |
| `id` | Content ID | `id = 12345` |

## Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `=` | Equals | `space = "DEV"` |
| `!=` | Not equals | `type != "blogpost"` |
| `~` | Contains | `title ~ "Guide"` |
| `!~` | Not contains | `text !~ "deprecated"` |
| `>` | Greater than | `created > "2024-01-01"` |
| `<` | Less than | `lastModified < now("-30d")` |
| `>=` | Greater or equal | `created >= "2024-01-01"` |
| `<=` | Less or equal | `lastModified <= now()` |
| `IN` | In list | `space IN ("DEV", "DOCS")` |
| `NOT IN` | Not in list | `label NOT IN ("draft", "wip")` |

## Logical Operators

| Operator | Description |
|----------|-------------|
| `AND` | Both conditions must match |
| `OR` | Either condition must match |
| `NOT` | Negate condition |
| `()` | Group conditions |

## Date Functions

| Function | Description |
|----------|-------------|
| `now()` | Current date/time |
| `now("-7d")` | 7 days ago |
| `now("-1w")` | 1 week ago |
| `now("-1M")` | 1 month ago |
| `now("-1y")` | 1 year ago |
| `startOfDay()` | Start of today |
| `startOfWeek()` | Start of current week |
| `startOfMonth()` | Start of current month |
| `startOfYear()` | Start of current year |

## Content Types

| Type | Description |
|------|-------------|
| `page` | Regular pages |
| `blogpost` | Blog posts |
| `attachment` | Attachments |
| `comment` | Comments |

## Examples

### Find pages in a space
```
space = "DEV" AND type = "page"
```

### Find recently modified documentation
```
label = "documentation" AND lastModified > now("-7d")
```

### Search for specific content
```
space = "DOCS" AND text ~ "authentication"
```

### Find pages by creator
```
creator = "john.doe" AND created > "2024-01-01"
```

### Complex query with grouping
```
space IN ("DEV", "DOCS") AND (label = "api" OR label = "guide") AND type = "page"
```

### Find child pages
```
parent = 12345 AND type = "page"
```

### Find pages without a label
```
space = "DEV" AND label IS EMPTY
```

## Order By

```
space = "DEV" ORDER BY lastModified DESC
space = "DEV" ORDER BY title ASC
```

## Escaping

- Use double quotes for values with spaces: `title ~ "User Guide"`
- Escape special characters with backslash: `text ~ "version 1\.0"`
