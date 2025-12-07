# Confluence Wiki Markup Reference

Quick reference for Confluence wiki markup syntax.

## Text Formatting

| Markup | Result | Notes |
|--------|--------|-------|
| `*bold*` | **bold** | Single asterisks |
| `_italic_` | *italic* | Single underscores |
| `-strikethrough-` | ~~strikethrough~~ | Hyphens |
| `+underline+` | underline | Plus signs |
| `^superscript^` | superscript | Carets |
| `~subscript~` | subscript | Tildes |
| `{{monospace}}` | `monospace` | Double braces |

## Headings

```
h1. Heading 1
h2. Heading 2
h3. Heading 3
h4. Heading 4
h5. Heading 5
h6. Heading 6
```

**Note:** Space after the period is required!

## Lists

### Unordered Lists
```
* Item 1
* Item 2
** Nested item
** Another nested
* Item 3
```

### Ordered Lists
```
# First item
# Second item
## Nested numbered
## Another nested
# Third item
```

### Mixed Lists
```
* Bullet
*# Numbered under bullet
*# Another numbered
* Another bullet
```

## Links

| Markup | Description |
|--------|-------------|
| `[Link text\|http://example.com]` | External link |
| `[Page Title]` | Link to page in same space |
| `[SPACE:Page Title]` | Link to page in different space |
| `[Link text\|Page Title]` | Link with custom text |
| `[~username]` | Link to user profile |
| `[PROJ-123]` | Link to Jira issue |
| `[^attachment.pdf]` | Link to attachment |

## Images

```
!image.png!                      # Attached image
!image.png|width=300!            # With width
!image.png|thumbnail!            # Thumbnail
!http://example.com/image.png!   # External image
```

## Tables

```
||Header 1||Header 2||Header 3||
|Cell 1|Cell 2|Cell 3|
|Cell 4|Cell 5|Cell 6|
```

### Table with Formatting
```
||*Bold Header*||_Italic Header_||
|Normal cell|{{code}}|
```

## Code

### Inline Code
```
{{inline code here}}
```

### Code Block
```
{code:java}
public class Hello {
    public static void main(String[] args) {
        System.out.println("Hello World");
    }
}
{code}
```

### Supported Languages
`java`, `javascript`, `python`, `ruby`, `sql`, `xml`, `html`, `css`, `bash`, `powershell`, `json`, `yaml`, and more.

### Code Block with Title
```
{code:title=Example.java|language=java}
// Code here
{code}
```

## Panels and Macros

### Info Panel
```
{info}
This is an informational message.
{info}
```

### Note Panel
```
{note}
This is a note.
{note}
```

### Warning Panel
```
{warning}
This is a warning!
{warning}
```

### Tip Panel
```
{tip}
This is a helpful tip.
{tip}
```

### Quote
```
{quote}
This is a quoted block of text.
{quote}
```

### Expand/Collapse
```
{expand:Click to expand}
Hidden content goes here.
{expand}
```

### Table of Contents
```
{toc}
{toc:minLevel=2|maxLevel=4}
```

### Panel with Title
```
{panel:title=My Panel|borderStyle=solid}
Panel content here.
{panel}
```

## Colors

```
{color:red}Red text{color}
{color:#0000FF}Blue text (hex){color}
```

## Horizontal Rule

```
----
```

## Line Break

```
Text before\\
Text after (forced line break)
```

## Escaping

Use backslash to escape special characters:

```
\*not bold\*
\{not a macro\}
```

## Anchors

### Create Anchor
```
{anchor:myanchor}
```

### Link to Anchor
```
[Jump to section|#myanchor]
```

## Status Macros

```
{status:colour=Green|title=DONE}
{status:colour=Yellow|title=IN PROGRESS}
{status:colour=Red|title=BLOCKED}
```

## Common Mistakes

| Wrong (Markdown) | Correct (Wiki) |
|------------------|----------------|
| `## Heading` | `h2. Heading` |
| `**bold**` | `*bold*` |
| `` `code` `` | `{{code}}` |
| `[text](url)` | `[text\|url]` |
| `- bullet` | `* bullet` |
| `1. numbered` | `# numbered` |
| `> quote` | `{quote}...{quote}` |
| ` ```code``` ` | `{code}...{code}` |
