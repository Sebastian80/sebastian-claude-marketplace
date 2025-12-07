# Serena Skill Changelog

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
