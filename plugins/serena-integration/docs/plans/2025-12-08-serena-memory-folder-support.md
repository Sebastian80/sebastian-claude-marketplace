# Serena Memory Folder Support Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add folder organization, archive command, and configuration support to Serena CLI memory management.

**Architecture:** CLI-side enhancements only. The MCP server already accepts paths with `/` - we add mkdir, recursive listing, and file organization commands in the Python CLI wrapper. Config loaded from project.yml at runtime.

**Tech Stack:** Python 3.8+ stdlib (os, os.path, pathlib, yaml)

---

## Prerequisites

- Working Serena installation at `~/.claude/plugins/marketplaces/sebastian-marketplace/plugins/serena/`
- Active project with `.serena/memories/` directory
- Python 3.8+ available

## Files Overview

| File | Action | Purpose |
|------|--------|---------|
| `scripts/serena` | Modify | Main CLI - add folder support |
| `scripts/serena_client.py` | No change | HTTP client unchanged |
| `skills/serena/SKILL.md` | Modify | Document new commands |

---

## Task 1: Add Helper Functions for Memory Paths

**Files:**
- Modify: `~/.claude/plugins/marketplaces/sebastian-marketplace/plugins/serena/skills/serena/scripts/serena:54-62`

**Step 1: Read current imports section**

Verify imports at lines 54-62 include what we need (os, json, sys already present).

**Step 2: Add helper functions after imports**

Insert after line 62 (after the `from serena_client import...` line):

```python
# =============================================================================
# Memory Path Helpers
# =============================================================================

def get_project_memories_dir() -> str:
    """Get memories directory for current project from Serena config."""
    try:
        result = call("get_current_config")
        if isinstance(result, str):
            for line in result.split('\n'):
                if line.startswith("Active project:"):
                    project_path = line.split(":", 1)[1].strip()
                    return os.path.join(project_path, ".serena", "memories")
    except Exception:
        pass
    # Fallback to current directory
    return os.path.join(os.getcwd(), ".serena", "memories")


def ensure_memory_parent_dir(memory_name: str) -> None:
    """Create parent directories for a memory path if needed."""
    if "/" not in memory_name:
        return
    memories_dir = get_project_memories_dir()
    full_path = os.path.join(memories_dir, memory_name)
    parent_dir = os.path.dirname(full_path)
    if not os.path.exists(parent_dir):
        os.makedirs(parent_dir, exist_ok=True)


def list_memories_recursive(base_dir: str = None) -> list:
    """List all memories including those in subdirectories."""
    memories_dir = base_dir or get_project_memories_dir()
    memories = []

    if not os.path.exists(memories_dir):
        return memories

    for root, dirs, files in os.walk(memories_dir):
        # Skip hidden directories
        dirs[:] = [d for d in dirs if not d.startswith('.')]

        for file in files:
            if file.endswith('.md') and not file.startswith('.'):
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, memories_dir)
                # Remove .md extension for display
                memory_name = rel_path[:-3] if rel_path.endswith('.md') else rel_path
                memories.append(memory_name)

    return sorted(memories)
```

**Step 3: Run syntax check**

Run: `python3 -m py_compile ~/.claude/plugins/marketplaces/sebastian-marketplace/plugins/serena/skills/serena/scripts/serena`
Expected: No output (success)

**Step 4: Commit**

```bash
cd ~/.claude/plugins/marketplaces/sebastian-marketplace/plugins/serena
git add skills/serena/scripts/serena
git commit -m "feat(memory): add helper functions for folder support"
```

---

## Task 2: Enhance Memory List Command (Recursive)

**Files:**
- Modify: `~/.claude/plugins/marketplaces/sebastian-marketplace/plugins/serena/skills/serena/scripts/serena:385-391`

**Step 1: Locate cmd_memory function**

The function is at lines 385-413. The `list` subcommand is at lines 387-391.

**Step 2: Replace list command implementation**

Replace lines 387-391:

```python
    if args.memory_cmd == "list":
        # Use recursive local listing for folder support
        memories = list_memories_recursive()
        if out.json_mode:
            out.success(memories)
        else:
            if not memories:
                print("No memories found.")
            else:
                print(f"Memories ({len(memories)}):")
                current_folder = None
                for mem in memories:
                    folder = os.path.dirname(mem) if "/" in mem else None
                    if folder != current_folder:
                        if folder:
                            print(f"\n  {folder}/")
                        current_folder = folder
                    name = os.path.basename(mem) if "/" in mem else mem
                    prefix = "    " if folder else "  "
                    print(f"{prefix}{name}")
```

**Step 3: Run syntax check**

Run: `python3 -m py_compile ~/.claude/plugins/marketplaces/sebastian-marketplace/plugins/serena/skills/serena/scripts/serena`
Expected: No output (success)

**Step 4: Test list command**

Run: `~/.local/bin/serena memory list`
Expected: Shows memories grouped by folder

**Step 5: Commit**

```bash
cd ~/.claude/plugins/marketplaces/sebastian-marketplace/plugins/serena
git add skills/serena/scripts/serena
git commit -m "feat(memory): recursive listing with folder grouping"
```

---

## Task 3: Enhance Memory Write Command (Auto-mkdir)

**Files:**
- Modify: `~/.claude/plugins/marketplaces/sebastian-marketplace/plugins/serena/skills/serena/scripts/serena:397-408`

**Step 1: Locate write subcommand**

The write implementation is at lines 397-408.

**Step 2: Add ensure_memory_parent_dir call**

Replace lines 397-408 with:

```python
    elif args.memory_cmd == "write":
        content = args.content
        if content == "-":
            content = sys.stdin.read()
        # Auto-add timestamp unless --no-timestamp flag is set
        if not getattr(args, 'no_timestamp', False):
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # Append timestamp as HTML comment at the end (invisible in rendered markdown)
            content = f"{content}\n\n<!-- Updated: {timestamp} -->"

        # Create parent directories if memory name contains /
        ensure_memory_parent_dir(args.name)

        result = call("write_memory", memory_file_name=args.name, content=content)
        out.info(f"Memory '{args.name}' written successfully")
        out.success(result)
```

**Step 3: Run syntax check**

Run: `python3 -m py_compile ~/.claude/plugins/marketplaces/sebastian-marketplace/plugins/serena/skills/serena/scripts/serena`
Expected: No output (success)

**Step 4: Test write to subfolder**

Run: `~/.local/bin/serena memory write "test/subfolder_test" "# Test content"`
Expected: Success, file created at `.serena/memories/test/subfolder_test.md`

**Step 5: Verify file exists**

Run: `ls -la .serena/memories/test/`
Expected: `subfolder_test.md` exists

**Step 6: Clean up test**

Run: `rm -rf .serena/memories/test/`

**Step 7: Commit**

```bash
cd ~/.claude/plugins/marketplaces/sebastian-marketplace/plugins/serena
git add skills/serena/scripts/serena
git commit -m "feat(memory): auto-create parent directories on write"
```

---

## Task 4: Add Archive Command

**Files:**
- Modify: `~/.claude/plugins/marketplaces/sebastian-marketplace/plugins/serena/skills/serena/scripts/serena:410-413` (add after delete)

**Step 1: Locate end of cmd_memory function**

After the delete subcommand (lines 410-413), add the archive command.

**Step 2: Add archive subcommand implementation**

Add after line 413 (before the function ends):

```python
    elif args.memory_cmd == "archive":
        # Archive moves a memory to archive/ subfolder with date prefix
        memories_dir = get_project_memories_dir()
        src_path = os.path.join(memories_dir, f"{args.name}.md")

        if not os.path.exists(src_path):
            out.error(f"Memory '{args.name}' not found")

        # Create archive directory
        archive_dir = os.path.join(memories_dir, "archive")
        os.makedirs(archive_dir, exist_ok=True)

        # Generate archive name with date
        date_prefix = datetime.now().strftime("%Y%m%d")
        base_name = os.path.basename(args.name)
        archive_name = f"{date_prefix}_{base_name}"
        dst_path = os.path.join(archive_dir, f"{archive_name}.md")

        # Handle duplicates
        counter = 1
        while os.path.exists(dst_path):
            archive_name = f"{date_prefix}_{base_name}_{counter}"
            dst_path = os.path.join(archive_dir, f"{archive_name}.md")
            counter += 1

        os.rename(src_path, dst_path)
        out.info(f"Archived '{args.name}' → 'archive/{archive_name}'")
```

**Step 3: Add archive subparser to argument parser**

Find the memory subparser section (around line 758-768) and add:

```python
    p_mem_archive = mem_sub.add_parser("archive", help="Archive a memory (move to archive/)")
    p_mem_archive.add_argument("name", help="Memory name to archive")
```

**Step 4: Run syntax check**

Run: `python3 -m py_compile ~/.claude/plugins/marketplaces/sebastian-marketplace/plugins/serena/skills/serena/scripts/serena`
Expected: No output (success)

**Step 5: Test archive command**

Run:
```bash
~/.local/bin/serena memory write "test_archive" "# Test"
~/.local/bin/serena memory archive test_archive
ls .serena/memories/archive/
```
Expected: `20251208_test_archive.md` exists in archive/

**Step 6: Clean up**

Run: `rm -rf .serena/memories/archive/`

**Step 7: Commit**

```bash
cd ~/.claude/plugins/marketplaces/sebastian-marketplace/plugins/serena
git add skills/serena/scripts/serena
git commit -m "feat(memory): add archive command"
```

---

## Task 5: Add Move Command

**Files:**
- Modify: `~/.claude/plugins/marketplaces/sebastian-marketplace/plugins/serena/skills/serena/scripts/serena`

**Step 1: Add mv subcommand implementation**

Add after the archive block:

```python
    elif args.memory_cmd == "mv":
        # Move/rename a memory
        memories_dir = get_project_memories_dir()
        src_path = os.path.join(memories_dir, f"{args.source}.md")

        if not os.path.exists(src_path):
            out.error(f"Memory '{args.source}' not found")

        # Ensure destination parent exists
        ensure_memory_parent_dir(args.dest)
        dst_path = os.path.join(memories_dir, f"{args.dest}.md")

        if os.path.exists(dst_path):
            out.error(f"Destination '{args.dest}' already exists")

        os.rename(src_path, dst_path)
        out.info(f"Moved '{args.source}' → '{args.dest}'")
```

**Step 2: Add mv subparser**

Add to the memory subparser section:

```python
    p_mem_mv = mem_sub.add_parser("mv", help="Move/rename a memory")
    p_mem_mv.add_argument("source", help="Source memory name")
    p_mem_mv.add_argument("dest", help="Destination memory name")
```

**Step 3: Run syntax check**

Run: `python3 -m py_compile ~/.claude/plugins/marketplaces/sebastian-marketplace/plugins/serena/skills/serena/scripts/serena`
Expected: No output (success)

**Step 4: Test move command**

Run:
```bash
~/.local/bin/serena memory write "move_test" "# Test"
~/.local/bin/serena memory mv move_test "completed/move_test"
ls .serena/memories/completed/
```
Expected: `move_test.md` in `completed/` folder

**Step 5: Clean up**

Run: `rm -rf .serena/memories/completed/`

**Step 6: Commit**

```bash
cd ~/.claude/plugins/marketplaces/sebastian-marketplace/plugins/serena
git add skills/serena/scripts/serena
git commit -m "feat(memory): add mv (move/rename) command"
```

---

## Task 6: Add Tree Command

**Files:**
- Modify: `~/.claude/plugins/marketplaces/sebastian-marketplace/plugins/serena/skills/serena/scripts/serena`

**Step 1: Add tree subcommand implementation**

Add after the mv block:

```python
    elif args.memory_cmd == "tree":
        # Display memory structure as tree
        memories_dir = get_project_memories_dir()

        if not os.path.exists(memories_dir):
            out.error("No memories directory found")

        def print_tree(dir_path, prefix=""):
            entries = sorted(os.listdir(dir_path))
            dirs = [e for e in entries if os.path.isdir(os.path.join(dir_path, e)) and not e.startswith('.')]
            files = [e for e in entries if e.endswith('.md') and not e.startswith('.')]

            for i, file in enumerate(files):
                is_last = (i == len(files) - 1) and not dirs
                connector = "└── " if is_last else "├── "
                name = file[:-3]  # Remove .md
                print(f"{prefix}{connector}{name}")

            for i, d in enumerate(dirs):
                is_last = (i == len(dirs) - 1)
                connector = "└── " if is_last else "├── "
                print(f"{prefix}{connector}{d}/")
                new_prefix = prefix + ("    " if is_last else "│   ")
                print_tree(os.path.join(dir_path, d), new_prefix)

        print("memories/")
        print_tree(memories_dir)
```

**Step 2: Add tree subparser**

Add to the memory subparser section:

```python
    mem_sub.add_parser("tree", help="Display memory structure as tree")
```

**Step 3: Run syntax check**

Run: `python3 -m py_compile ~/.claude/plugins/marketplaces/sebastian-marketplace/plugins/serena/skills/serena/scripts/serena`
Expected: No output (success)

**Step 4: Test tree command**

Run: `~/.local/bin/serena memory tree`
Expected: Tree output showing memories structure

**Step 5: Commit**

```bash
cd ~/.claude/plugins/marketplaces/sebastian-marketplace/plugins/serena
git add skills/serena/scripts/serena
git commit -m "feat(memory): add tree command for visual structure"
```

---

## Task 7: Update CLI Help and Documentation

**Files:**
- Modify: `~/.claude/plugins/marketplaces/sebastian-marketplace/plugins/serena/skills/serena/scripts/serena:1-52`

**Step 1: Update docstring**

Replace lines 15-16 in the docstring:

```python
    memory      Memory operations (list, read, write, delete, archive, mv, tree)
```

**Step 2: Update CLI epilog**

In the main() function's argparse epilog (around line 720), add:

```python
Memory Operations:
  serena memory list                   List all memories (recursive)
  serena memory tree                   Show folder structure
  serena memory write "folder/name" "content"  Write to subfolder
  serena memory archive task_progress  Archive completed task
  serena memory mv old_name new_name   Move/rename memory
```

**Step 3: Run syntax check**

Run: `python3 -m py_compile ~/.claude/plugins/marketplaces/sebastian-marketplace/plugins/serena/skills/serena/scripts/serena`
Expected: No output (success)

**Step 4: Verify help**

Run: `~/.local/bin/serena memory --help`
Expected: Shows all subcommands including archive, mv, tree

**Step 5: Commit**

```bash
cd ~/.claude/plugins/marketplaces/sebastian-marketplace/plugins/serena
git add skills/serena/scripts/serena
git commit -m "docs: update memory help with new commands"
```

---

## Task 8: Update Serena Skill Documentation

**Files:**
- Modify: `~/.claude/plugins/marketplaces/sebastian-marketplace/plugins/serena/skills/serena/SKILL.md`

**Step 1: Find memory section in SKILL.md**

Search for the memory operations section.

**Step 2: Update memory commands section**

Add/update the memory section:

```markdown
### Memory Management (with Folder Support)

```bash
# List all memories (recursive, grouped by folder)
serena memory list

# Show folder structure as tree
serena memory tree

# Write to subfolder (auto-creates directories)
serena memory write "active/current_task" "## Current Task..."
serena memory write "context/project_overview" "## Project..."

# Archive completed work (moves to archive/ with date prefix)
serena memory archive task_progress
# Result: archive/20251208_task_progress

# Move/rename memories
serena memory mv old_name new_folder/new_name

# Read from any path
serena memory read "archive/20251208_task_progress"
```

**Recommended Folder Structure:**
```
memories/
├── active/           # Current work in progress
├── context/          # Long-lived project context
├── archive/          # Completed/old memories (auto-dated)
└── *.md              # Root-level quick access
```
```

**Step 3: Commit**

```bash
cd ~/.claude/plugins/marketplaces/sebastian-marketplace/plugins/serena
git add skills/serena/SKILL.md
git commit -m "docs: document memory folder support in skill"
```

---

## Task 9: Integration Testing

**Step 1: Run full workflow test**

```bash
# Create test memories in different locations
~/.local/bin/serena memory write "test_root" "# Root memory"
~/.local/bin/serena memory write "active/current" "# Active task"
~/.local/bin/serena memory write "context/overview" "# Project overview"

# List should show hierarchy
~/.local/bin/serena memory list

# Tree should show structure
~/.local/bin/serena memory tree

# Archive root memory
~/.local/bin/serena memory archive test_root

# Move active to completed
~/.local/bin/serena memory mv "active/current" "archive/current_done"

# List should reflect changes
~/.local/bin/serena memory list
```

Expected output structure:
```
Memories (4):
  context_overview

  active/
    (empty after move)

  archive/
    20251208_test_root
    current_done

  context/
    overview
```

**Step 2: Clean up test data**

```bash
rm -rf .serena/memories/active .serena/memories/archive .serena/memories/context
```

**Step 3: Final commit**

```bash
cd ~/.claude/plugins/marketplaces/sebastian-marketplace/plugins/serena
git add -A
git commit -m "feat(memory): complete folder support implementation"
```

---

## Summary of Changes

| Component | Change |
|-----------|--------|
| `cmd_memory()` | Enhanced list (recursive), write (auto-mkdir), added archive/mv/tree |
| Helper functions | `get_project_memories_dir()`, `ensure_memory_parent_dir()`, `list_memories_recursive()` |
| Argument parser | Added archive, mv, tree subparsers |
| Documentation | Updated docstring, epilog, and SKILL.md |

**Total: ~150 lines added, 9 commits**
