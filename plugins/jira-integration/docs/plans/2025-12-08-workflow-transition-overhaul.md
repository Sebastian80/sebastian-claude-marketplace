# Jira Workflow & Transition Overhaul

**Status:** Approved
**Date:** 2025-12-08
**Author:** Claude + Sebastian

## Problem Statement

The current `jira-transition.py` script has several deficiencies:

1. **Broken API usage** - Uses `client.issue_transition()` which doesn't support `fields` or `comment` parameters. The correct method is `client.set_issue_status()`.

2. **No workflow awareness** - Cannot navigate multi-step transitions. User must manually determine path from state A to state B.

3. **No workflow discovery** - Different issue types have different workflows (e.g., "Sub: Task" vs "Sub: Technical task"). No way to visualize or understand these workflows.

4. **Broken workflows go undetected** - Some issue types (Sub: Bug, Sub: Improvement) have circular workflows with no exit from "In Arbeit". Users discover this painfully.

## Goals

- Fix transition API to work reliably
- Enable smart multi-step transitions ("take me to Waiting for QA")
- Provide workflow discovery and visualization
- Support multiple projects and issue types
- Create reusable, publishable tool

## Non-Goals

- Workflow caching with TTL (always query live for current state)
- Admin-level workflow modification
- Support for transition screens with required fields (v2)

---

## Architecture

```
jira-communication/
├── scripts/
│   ├── lib/
│   │   ├── __init__.py
│   │   ├── client.py           # Existing
│   │   ├── output.py           # Existing
│   │   ├── config.py           # Existing
│   │   └── workflow.py         # NEW - Core workflow logic
│   └── workflow/
│       ├── jira-transition.py  # ENHANCED
│       └── jira-workflow.py    # NEW
├── references/
│   ├── jql-quick-reference.md
│   ├── troubleshooting.md
│   └── workflows.json          # NEW - Persisted workflow maps
└── SKILL.md                    # Update with new commands
```

### Design Principles

1. **Thin CLI, fat lib** - Scripts handle argument parsing only. All logic lives in `lib/workflow.py`.

2. **Single responsibility** - Workflow mapping, path finding, and transition execution are separate concerns.

3. **Explicit over implicit** - Prefer explicit `discover` command, fall back to auto-discover.

4. **Fail clearly** - On error, report exactly what state the issue is in and why it failed.

---

## Data Model

### `references/workflows.json`

```json
{
  "_meta": {
    "version": 1,
    "updated_at": "2025-12-08T15:30:00Z"
  },
  "issue_types": {
    "Sub: Task": {
      "id": "5",
      "discovered_from": "HMKG-2064",
      "discovered_at": "2025-12-08T15:30:00Z",
      "states": {
        "Offen": [
          {"id": "21", "name": "Start working", "to": "In Arbeit"},
          {"id": "11", "name": "Require feedback", "to": "Waiting"}
        ],
        "In Arbeit": [
          {"id": "651", "name": "Send to QA", "to": "Waiting for QA"},
          {"id": "621", "name": "Complete", "to": "Fertig"},
          {"id": "41", "name": "Stop working", "to": "Offen"}
        ],
        "Waiting for QA": [
          {"id": "721", "name": "Start QA", "to": "QA / Revision"}
        ],
        "QA / Revision": [
          {"id": "791", "name": "Done", "to": "Fertig"},
          {"id": "751", "name": "Require deployment", "to": "Ready for deployment"},
          {"id": "671", "name": "Return for revision", "to": "Neueröffnet"}
        ]
      }
    }
  }
}
```

### `lib/workflow.py` Classes

```python
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime

@dataclass
class Transition:
    """Single transition from one state to another."""
    id: str
    name: str
    to: str

@dataclass
class WorkflowGraph:
    """Complete workflow graph for an issue type."""
    issue_type: str
    issue_type_id: str
    states: dict[str, list[Transition]] = field(default_factory=dict)
    discovered_from: str | None = None
    discovered_at: datetime | None = None

    def transitions_from(self, state: str) -> list[Transition]:
        """Get available transitions from a state."""
        return self.states.get(state, [])

    def path_to(self, from_state: str, to_state: str) -> list[Transition]:
        """BFS shortest path between states. Raises PathNotFoundError."""
        ...

    def reachable_from(self, state: str) -> set[str]:
        """All states reachable from given state."""
        ...

    def all_states(self) -> set[str]:
        """All known states in this workflow."""
        ...

    def has_exit_from(self, state: str) -> bool:
        """Check if state has path to a 'done' category state."""
        ...

    def to_ascii(self) -> str:
        """Visual ASCII diagram of workflow."""
        ...

    def to_table(self) -> str:
        """Tabular representation."""
        ...

    def to_dict(self) -> dict:
        """JSON-serializable dictionary."""
        ...

class WorkflowStore:
    """Persistence layer for workflow graphs."""

    def __init__(self, path: Path):
        self.path = path
        self._data = self._load()

    def get(self, issue_type: str) -> WorkflowGraph | None:
        """Load workflow for issue type, or None if not found."""
        ...

    def save(self, graph: WorkflowGraph) -> None:
        """Save/update workflow graph."""
        ...

    def list_types(self) -> list[str]:
        """List all known issue types."""
        ...

    def delete(self, issue_type: str) -> bool:
        """Remove workflow mapping."""
        ...
```

---

## Core Functions

### Discovery

```python
def discover_workflow(client, issue_key: str, store: WorkflowStore) -> WorkflowGraph:
    """
    Walk issue through all reachable states to map complete workflow.

    Algorithm:
    1. Get issue's current state and type
    2. Record original state for return journey
    3. BFS through all states:
       - At each state, record all available transitions
       - Execute transition to unvisited state
       - Repeat until all reachable states visited
    4. Attempt to return to original state
    5. Save workflow to store

    Returns:
        Complete WorkflowGraph for this issue type

    Raises:
        DiscoveryError: If discovery fails or issue gets stuck
    """
```

### Path Finding

```python
def find_path(graph: WorkflowGraph, from_state: str, to_state: str) -> list[Transition]:
    """
    Find shortest path between two states using BFS.

    Matching:
    - Exact state name match (case-insensitive)
    - Partial match on transition name (e.g., "QA" matches "Waiting for QA")

    Returns:
        List of Transitions to execute in order

    Raises:
        PathNotFoundError: If no path exists
        AmbiguousTargetError: If multiple states match target
    """
```

### Smart Transition

```python
def smart_transition(
    client,
    issue_key: str,
    target_state: str,
    store: WorkflowStore,
    add_comment: bool = False,
    dry_run: bool = False
) -> list[Transition]:
    """
    Transition issue to target state, navigating multiple steps if needed.

    Algorithm:
    1. Fetch issue current state and type
    2. Load workflow from store
       - If not found, trigger auto-discovery
    3. Find path from current to target
    4. If dry_run, return path without executing
    5. Execute each transition in sequence
       - Verify success after each step
       - On failure, stop and report
    6. If add_comment, add trail comment

    Returns:
        List of Transitions that were executed

    Raises:
        WorkflowNotFoundError: Issue type unknown (triggers auto-discover)
        PathNotFoundError: No route to target state
        TransitionFailedError: Execution failed mid-path
    """
```

---

## CLI Commands

### `jira-transition.py` (Enhanced)

```bash
# List available transitions (unchanged)
jira-transition.py list PROJ-123

# Single-step transition (fixed to use set_issue_status)
jira-transition.py do PROJ-123 "In Arbeit"

# Smart multi-step transition (NEW)
jira-transition.py do PROJ-123 "Waiting for QA"
# Output:
# Transitioning PROJ-123 to 'Waiting for QA'
#   Step 1/2: Start working → In Arbeit ✓
#   Step 2/2: Send to QA → Waiting for QA ✓
# ✓ PROJ-123 now at 'Waiting for QA'

# With comment trail (NEW)
jira-transition.py do PROJ-123 "Waiting for QA" --comment
# Adds comment: "Transitioned: Offen → In Arbeit → Waiting for QA"

# Dry-run (NEW)
jira-transition.py do PROJ-123 "Waiting for QA" --dry-run
# Output:
# DRY RUN - Would transition PROJ-123:
#   Current: Offen
#   Target: Waiting for QA
#   Path: Offen → In Arbeit → Waiting for QA (2 steps)

# With resolution for closing (fixed)
jira-transition.py do PROJ-123 "Geschlossen" --resolution Fixed
```

### `jira-workflow.py` (New)

```bash
# Discover workflow from sample issue
jira-workflow.py discover PROJ-123
# Output:
# Discovering workflow for 'Sub: Task' from PROJ-123...
#   Found 10 states, 24 transitions
#   Original state: In Arbeit
#   Returning to original state... ✓
# ✓ Workflow saved for 'Sub: Task'

# Show workflow (multiple formats)
jira-workflow.py show "Sub: Task"
jira-workflow.py show "Sub: Task" --format table
jira-workflow.py show "Sub: Task" --format ascii
jira-workflow.py show "Sub: Task" --format json

# List all known workflows
jira-workflow.py list
# Output:
# Known workflows:
#   Sub: Task (10 states) - discovered from HMKG-2064
#   Sub: Technical task (12 states) - discovered from HMKG-2064
#   Sub: Investigation (10 states) - discovered from HMKG-2047

# Show path between states
jira-workflow.py path "Sub: Task" --from "Offen" --to "Waiting for QA"
# Output:
# Path from 'Offen' to 'Waiting for QA':
#   1. Start working → In Arbeit
#   2. Send to QA → Waiting for QA

# Validate workflow (check for dead ends)
jira-workflow.py validate "Sub: Task"
# Output:
# Validating 'Sub: Task' workflow...
# ✓ All states have exit path to done
# ✓ No orphan states

# Re-discover/refresh
jira-workflow.py refresh "Sub: Task" --issue PROJ-456
```

---

## Error Handling

### Error Types

```python
class WorkflowError(Exception):
    """Base class for workflow errors."""

class WorkflowNotFoundError(WorkflowError):
    """Issue type not in workflow store."""
    issue_type: str

class PathNotFoundError(WorkflowError):
    """No path exists between states."""
    from_state: str
    to_state: str
    reachable: set[str]  # States that ARE reachable

class TransitionFailedError(WorkflowError):
    """Transition execution failed."""
    issue_key: str
    transition: Transition
    current_state: str
    target_state: str
    reason: str

class DiscoveryError(WorkflowError):
    """Workflow discovery failed."""
    issue_key: str
    stuck_at: str
    discovered_states: set[str]
```

### Error Messages

```
# PathNotFoundError
Error: No path from 'In Arbeit' to 'Deployed'
  Reachable states: Offen, Waiting, Waiting for QA, QA / Revision, Fertig
  Hint: 'Deployed' may not exist in this workflow

# TransitionFailedError
Error: Transition failed at step 2/3
  Issue: PROJ-123
  Current state: In Arbeit
  Failed transition: Send to QA → Waiting for QA
  Reason: Transition requires 'QA Assignee' field

# WorkflowNotFoundError (triggers auto-discover)
Warning: Workflow for 'Sub: Bug' not found
  Discovering from PROJ-123...
```

---

## Implementation Plan

### Phase 1: Core Library (`lib/workflow.py`)

1. Implement `Transition` and `WorkflowGraph` dataclasses
2. Implement `WorkflowStore` (load/save JSON)
3. Implement `find_path()` with BFS
4. Implement `discover_workflow()` with state walking
5. Implement `smart_transition()`
6. Unit tests for path finding and graph operations

### Phase 2: Enhanced `jira-transition.py`

1. Fix API call to use `set_issue_status()`
2. Integrate `smart_transition()` for multi-step
3. Add `--comment` flag for trail
4. Add `--dry-run` with path preview
5. Add auto-discover fallback
6. Integration tests

### Phase 3: New `jira-workflow.py`

1. Implement `discover` command
2. Implement `show` command with formats (table, ascii, json)
3. Implement `list` command
4. Implement `path` command
5. Implement `validate` command
6. Implement `refresh` command

### Phase 4: Documentation & Polish

1. Update `SKILL.md` with new commands
2. Add `references/workflow-guide.md`
3. Pre-populate `workflows.json` with HMKG workflows
4. Test across multiple projects

---

## Testing Strategy

### Unit Tests (`test_workflow.py`)

- `WorkflowGraph.path_to()` - Various graph shapes, cycles, unreachable
- `WorkflowGraph.to_ascii()` - Output format
- `WorkflowStore` - Load, save, missing file
- `find_path()` - Shortest path, no path, ambiguous target

### Integration Tests

- `discover_workflow()` - Mock client, verify state walking
- `smart_transition()` - Multi-step execution
- CLI commands - End-to-end with real Jira (manual)

---

## Open Questions

1. **Required fields** - Some transitions require fields (e.g., resolution). Handle in v2?
2. **Parallel workflows** - Some projects have parallel paths. BFS finds one, may not be preferred.
3. **State aliases** - "Done" vs "Fertig" vs "Geschlossen" - normalize?

---

## Appendix: Discovered Workflows (HMKG)

### Working Workflows (have QA + Done)

| Issue Type | QA State | Done State |
|------------|----------|------------|
| Sub: Task | UAT Stage | Fertig |
| Sub: Investigation | UAT Stage | Fertig |
| Sub: Technical task | Waiting for QA | Fertig |
| Sub: Estimation | UAT Stage | Fertig |
| Sub: Documentation | UAT Stage | Fertig |

### Broken Workflows (circular, no exit from In Arbeit)

| Issue Type | Issue |
|------------|-------|
| Sub: Bug | No transitions to done from In Arbeit |
| Sub: Improvement | No transitions to done from In Arbeit |
| Sub: Change Request | No transitions to done from In Arbeit |

These should be reported to Jira admin for fixing.
