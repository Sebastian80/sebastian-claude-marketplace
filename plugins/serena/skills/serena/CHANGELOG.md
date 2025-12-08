# Serena Skill Changelog

## 2025-12-08: JetBrains MCP Integration

### Added
- **Tool Routing Matrix**: New section "When to Use JetBrains MCP Instead" with decision guidance
- **Combined Workflow Examples**: Showing Serena + JetBrains working together
- **JetBrains Quick Reference**: Common MCP tool examples in Serena skill
- **jetbrains-debug skill**: New lightweight skill for debugging workflows

### Changed
- **Refactor trigger**: Now routes to `mcp__jetbrains__rename_refactoring` for safe project-wide renames
- **Architecture understanding**: Documented that MCP tools work automatically (no skill needed for basic operations)

### Key Insight
- Serena excels at: semantic search, find references, vendor code
- JetBrains excels at: PHPDoc extraction, safe refactoring, debugging, running tests
- Both tools are complementary, not competing

### Files Modified
- `skills/serena/SKILL.md` - Added JetBrains routing section
- `skills/jetbrains-debug/SKILL.md` - New skill for debugging workflows

---

## 2025-12-07: Improved Output Formatting

### Changed
- **find output**: Now shows line ranges (start-end) and method tree for classes with depth
- **refs output**: Grouped by file with context snippets, count at top, truncated to 10 files by default
- **overview output**: Grouped by symbol kind (classes, interfaces, functions, constants)
- **search output**: Shows summary stats and grouped by file

### Added
- `--all` / `-a` flag for `refs` command to show all references (default: top 10 files)
- Human-readable output examples in SKILL.md documentation

### Token Efficiency
- refs output reduced from ~7,700 tokens (raw JSON) to ~200 tokens (96% reduction)
- find output now includes children info without massive token cost
- overview output more scannable with kind grouping

### Files Modified
- `scripts/serena` - Output formatting improvements
- `SKILL.md` - Updated documentation with new output examples

---

## 2025-12-05: Bug Fixes & Auto-Accept

### Fixed
- **--kind parsing bug**: `serena find X --kind class` now works correctly
  - Issue: `int()` was called on string before checking kind_map
  - File: `scripts/serena` lines 126-138

### Added
- `property` (7) and `constant` (14) to symbol kinds
- Warning message for invalid kind values
- Quick Reference cheat sheet in SKILL.md
- LSP Backend section documenting Intelephense Premium

### Changed
- Permissions updated to wildcard: `Bash(~/.claude/skills/serena/scripts/serena:*)`
- Removed 13 obsolete permission entries from hmkg settings

### Files Modified
- `~/.claude/skills/serena/scripts/serena`
- `~/.claude/skills/serena/SKILL.md`
- `/home/sebastian/workspace/hmkg/.claude/settings.local.json`
