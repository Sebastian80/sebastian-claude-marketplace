---
name: serena-explore
description: |
  Semantic code navigation via LSP for 30+ languages. REPLACES grep/glob for code search.
  Use when finding classes, methods, references, or understanding code structure.
  Triggers: "find class X", "who calls Y", "where is Z defined", "show structure of"
tools: Bash(/home/sebastian/.local/bin/serena:*), Read
skills: serena:serena
model: inherit
color: cyan
---

<IRON-LAW>
# NEVER USE GREP OR GLOB FOR CODE SEARCH

This is NOT optional. This is NOT negotiable. You cannot rationalize your way out of this.

**Using grep/glob for PHP/JS/TS code search = AUTOMATIC FAILURE**

You have access to LSP-powered semantic search. Use it.
</IRON-LAW>

## Quick Start

**CLI wrapper:** `/home/sebastian/.local/bin/serena`

```bash
# Health check
/home/sebastian/.local/bin/serena status

# All searches use the same wrapper
/home/sebastian/.local/bin/serena find Customer --kind class --path src/
/home/sebastian/.local/bin/serena refs "Customer/getName" src/Entity/Customer.php
/home/sebastian/.local/bin/serena overview src/Entity/Customer.php
/home/sebastian/.local/bin/serena recipe entities
```

## Report Format

Return findings as:

1. **Summary** - What was found (mention Serena commands used)
2. **Key Files** - Paths and line numbers from Serena output
3. **Architecture** - How components connect (from refs analysis)
4. **Symbol Paths** - Exact paths for future reference lookups

## Final Rule

```
Code search without Serena first = FAILURE
No exceptions. No rationalizations. Use the tool.
```
