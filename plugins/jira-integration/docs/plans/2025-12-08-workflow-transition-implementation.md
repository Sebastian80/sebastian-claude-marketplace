# Jira Workflow & Transition Overhaul - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix jira-transition.py and add smart multi-step transitions with workflow discovery.

**Architecture:** Core logic in `lib/workflow.py` (WorkflowGraph, WorkflowStore, path finding), thin CLI wrappers in `jira-transition.py` (enhanced) and `jira-workflow.py` (new). Workflows persisted to `references/workflows.json`.

**Tech Stack:** Python 3.10+, Click CLI, atlassian-python-api, PEP 723 inline deps

**Base Path:** `~/.claude/plugins/marketplaces/sebastian-marketplace/plugins/jira-integration/skills/jira-communication`

---

## Phase 1: Core Data Structures

### Task 1.1: Create Transition and WorkflowGraph dataclasses

**Files:**
- Create: `scripts/lib/workflow.py`

**Step 1: Create the workflow module with dataclasses**

```python
#!/usr/bin/env python3
"""Jira workflow graph and transition logic."""

from dataclasses import dataclass, field
from datetime import datetime
from collections import deque
from typing import Optional


@dataclass
class Transition:
    """Single transition from one state to another."""
    id: str
    name: str
    to: str

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "to": self.to}

    @classmethod
    def from_dict(cls, data: dict) -> "Transition":
        return cls(id=data["id"], name=data["name"], to=data["to"])


@dataclass
class WorkflowGraph:
    """Complete workflow graph for an issue type."""
    issue_type: str
    issue_type_id: str
    states: dict[str, list[Transition]] = field(default_factory=dict)
    discovered_from: Optional[str] = None
    discovered_at: Optional[datetime] = None

    def transitions_from(self, state: str) -> list[Transition]:
        """Get available transitions from a state."""
        return self.states.get(state, [])

    def all_states(self) -> set[str]:
        """All known states in this workflow."""
        states = set(self.states.keys())
        for transitions in self.states.values():
            for t in transitions:
                states.add(t.to)
        return states

    def add_state(self, state: str, transitions: list[Transition]) -> None:
        """Add or update state with its transitions."""
        self.states[state] = transitions

    def to_dict(self) -> dict:
        """JSON-serializable dictionary."""
        return {
            "id": self.issue_type_id,
            "discovered_from": self.discovered_from,
            "discovered_at": self.discovered_at.isoformat() if self.discovered_at else None,
            "states": {
                state: [t.to_dict() for t in transitions]
                for state, transitions in self.states.items()
            }
        }

    @classmethod
    def from_dict(cls, issue_type: str, data: dict) -> "WorkflowGraph":
        """Create from dictionary."""
        states = {}
        for state, transitions in data.get("states", {}).items():
            states[state] = [Transition.from_dict(t) for t in transitions]

        discovered_at = None
        if data.get("discovered_at"):
            discovered_at = datetime.fromisoformat(data["discovered_at"])

        return cls(
            issue_type=issue_type,
            issue_type_id=data.get("id", ""),
            states=states,
            discovered_from=data.get("discovered_from"),
            discovered_at=discovered_at
        )
```

**Step 2: Verify module imports**

Run:
```bash
cd ~/.claude/plugins/marketplaces/sebastian-marketplace/plugins/jira-integration/skills/jira-communication
python3 -c "from scripts.lib.workflow import Transition, WorkflowGraph; print('OK')"
```

Expected: `OK`

**Step 3: Commit**

```bash
git add scripts/lib/workflow.py
git commit -m "feat(jira): add Transition and WorkflowGraph dataclasses"
```

---

### Task 1.2: Add path finding to WorkflowGraph

**Files:**
- Modify: `scripts/lib/workflow.py`

**Step 1: Add path_to method with BFS**

Add after `add_state` method:

```python
    def path_to(self, from_state: str, to_state: str) -> list[Transition]:
        """
        Find shortest path between states using BFS.

        Args:
            from_state: Starting state name
            to_state: Target state name (case-insensitive, partial match on transition name)

        Returns:
            List of Transitions to execute in order

        Raises:
            PathNotFoundError: If no path exists
        """
        # Normalize target for matching
        to_lower = to_state.lower()

        # Check if already at target
        if from_state.lower() == to_lower:
            return []

        # BFS
        queue = deque([(from_state, [])])
        visited = {from_state}

        while queue:
            current, path = queue.popleft()

            for transition in self.transitions_from(current):
                # Check if this transition reaches target
                if (transition.to.lower() == to_lower or
                    to_lower in transition.to.lower() or
                    to_lower in transition.name.lower()):
                    return path + [transition]

                # Continue BFS if not visited
                if transition.to not in visited:
                    visited.add(transition.to)
                    queue.append((transition.to, path + [transition]))

        # No path found
        raise PathNotFoundError(
            from_state=from_state,
            to_state=to_state,
            reachable=visited
        )

    def reachable_from(self, state: str) -> set[str]:
        """All states reachable from given state."""
        visited = set()
        queue = deque([state])

        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)

            for transition in self.transitions_from(current):
                if transition.to not in visited:
                    queue.append(transition.to)

        return visited
```

**Step 2: Add exception class at top of file (after imports)**

```python
class WorkflowError(Exception):
    """Base class for workflow errors."""
    pass


class PathNotFoundError(WorkflowError):
    """No path exists between states."""
    def __init__(self, from_state: str, to_state: str, reachable: set[str]):
        self.from_state = from_state
        self.to_state = to_state
        self.reachable = reachable
        super().__init__(
            f"No path from '{from_state}' to '{to_state}'. "
            f"Reachable states: {', '.join(sorted(reachable))}"
        )
```

**Step 3: Test path finding manually**

```bash
python3 << 'EOF'
import sys
sys.path.insert(0, "$HOME/.claude/plugins/marketplaces/sebastian-marketplace/plugins/jira-integration/skills/jira-communication/scripts")
from lib.workflow import Transition, WorkflowGraph, PathNotFoundError

# Create test graph
graph = WorkflowGraph(issue_type="Test", issue_type_id="1")
graph.add_state("Offen", [Transition("21", "Start working", "In Arbeit")])
graph.add_state("In Arbeit", [
    Transition("651", "Send to QA", "Waiting for QA"),
    Transition("41", "Stop working", "Offen")
])
graph.add_state("Waiting for QA", [Transition("721", "Approve", "Done")])

# Test path finding
path = graph.path_to("Offen", "Waiting for QA")
print("Path:", " → ".join([t.to for t in path]))
assert len(path) == 2
assert path[0].to == "In Arbeit"
assert path[1].to == "Waiting for QA"
print("✓ Path finding works")
EOF
```

Expected:
```
Path: In Arbeit → Waiting for QA
✓ Path finding works
```

**Step 4: Commit**

```bash
git add scripts/lib/workflow.py
git commit -m "feat(jira): add BFS path finding to WorkflowGraph"
```

---

### Task 1.3: Add ASCII and table output formats

**Files:**
- Modify: `scripts/lib/workflow.py`

**Step 1: Add formatting methods to WorkflowGraph**

Add after `reachable_from` method:

```python
    def to_ascii(self) -> str:
        """Visual ASCII diagram of workflow."""
        lines = [f"Workflow: {self.issue_type}", "=" * 50]

        for state in sorted(self.states.keys()):
            transitions = self.states[state]
            lines.append(f"\n[{state}]")
            for t in transitions:
                lines.append(f"  --({t.name})--> {t.to}")

        return "\n".join(lines)

    def to_table(self) -> str:
        """Tabular representation."""
        lines = []
        header = f"{'State':<25} {'Transition':<25} {'To State':<25}"
        lines.append(header)
        lines.append("-" * 75)

        for state in sorted(self.states.keys()):
            first = True
            for t in self.states[state]:
                state_col = state if first else ""
                lines.append(f"{state_col:<25} {t.name:<25} {t.to:<25}")
                first = False

        return "\n".join(lines)
```

**Step 2: Test output formats**

```bash
python3 << 'EOF'
import sys
sys.path.insert(0, "$HOME/.claude/plugins/marketplaces/sebastian-marketplace/plugins/jira-integration/skills/jira-communication/scripts")
from lib.workflow import Transition, WorkflowGraph

graph = WorkflowGraph(issue_type="Sub: Task", issue_type_id="5")
graph.add_state("Offen", [Transition("21", "Start working", "In Arbeit")])
graph.add_state("In Arbeit", [
    Transition("651", "Send to QA", "Waiting for QA"),
    Transition("41", "Stop working", "Offen")
])

print(graph.to_ascii())
print("\n")
print(graph.to_table())
EOF
```

**Step 3: Commit**

```bash
git add scripts/lib/workflow.py
git commit -m "feat(jira): add ASCII and table output formats"
```

---

## Phase 2: Workflow Store

### Task 2.1: Implement WorkflowStore

**Files:**
- Modify: `scripts/lib/workflow.py`

**Step 1: Add WorkflowStore class**

Add at end of file:

```python
import json
from pathlib import Path


class WorkflowStore:
    """Persistence layer for workflow graphs."""

    def __init__(self, path: Optional[Path] = None):
        if path is None:
            # Default to references/workflows.json relative to this file
            path = Path(__file__).parent.parent.parent / "references" / "workflows.json"
        self.path = path
        self._data = self._load()

    def _load(self) -> dict:
        """Load workflows from JSON file."""
        if not self.path.exists():
            return {"_meta": {"version": 1, "updated_at": None}, "issue_types": {}}

        with open(self.path, "r") as f:
            return json.load(f)

    def _save(self) -> None:
        """Save workflows to JSON file."""
        self._data["_meta"]["updated_at"] = datetime.now().isoformat()

        # Ensure parent directory exists
        self.path.parent.mkdir(parents=True, exist_ok=True)

        # Write atomically
        tmp_path = self.path.with_suffix(".tmp")
        with open(tmp_path, "w") as f:
            json.dump(self._data, f, indent=2)
        tmp_path.rename(self.path)

    def get(self, issue_type: str) -> Optional[WorkflowGraph]:
        """Load workflow for issue type, or None if not found."""
        if issue_type not in self._data.get("issue_types", {}):
            return None

        return WorkflowGraph.from_dict(
            issue_type,
            self._data["issue_types"][issue_type]
        )

    def save(self, graph: WorkflowGraph) -> None:
        """Save/update workflow graph."""
        if "issue_types" not in self._data:
            self._data["issue_types"] = {}

        self._data["issue_types"][graph.issue_type] = graph.to_dict()
        self._save()

    def list_types(self) -> list[str]:
        """List all known issue types."""
        return list(self._data.get("issue_types", {}).keys())

    def delete(self, issue_type: str) -> bool:
        """Remove workflow mapping."""
        if issue_type in self._data.get("issue_types", {}):
            del self._data["issue_types"][issue_type]
            self._save()
            return True
        return False
```

**Step 2: Test store operations**

```bash
python3 << 'EOF'
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, "$HOME/.claude/plugins/marketplaces/sebastian-marketplace/plugins/jira-integration/skills/jira-communication/scripts")
from lib.workflow import Transition, WorkflowGraph, WorkflowStore

# Use temp file for testing
with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
    test_path = Path(f.name)

store = WorkflowStore(test_path)

# Create and save
graph = WorkflowGraph(issue_type="Sub: Task", issue_type_id="5")
graph.add_state("Offen", [Transition("21", "Start", "In Arbeit")])
store.save(graph)

# Reload and verify
store2 = WorkflowStore(test_path)
loaded = store2.get("Sub: Task")
assert loaded is not None
assert loaded.issue_type == "Sub: Task"
assert len(loaded.transitions_from("Offen")) == 1
print("✓ Store save/load works")

# List types
assert "Sub: Task" in store2.list_types()
print("✓ List types works")

# Cleanup
test_path.unlink()
print("✓ All store tests passed")
EOF
```

**Step 3: Commit**

```bash
git add scripts/lib/workflow.py
git commit -m "feat(jira): add WorkflowStore for persistence"
```

---

### Task 2.2: Create initial workflows.json

**Files:**
- Create: `references/workflows.json`

**Step 1: Create empty workflows file**

```json
{
  "_meta": {
    "version": 1,
    "updated_at": null
  },
  "issue_types": {}
}
```

**Step 2: Commit**

```bash
git add references/workflows.json
git commit -m "feat(jira): add empty workflows.json"
```

---

## Phase 3: Workflow Discovery

### Task 3.1: Add discovery function

**Files:**
- Modify: `scripts/lib/workflow.py`

**Step 1: Add additional exceptions**

Add after `PathNotFoundError`:

```python
class WorkflowNotFoundError(WorkflowError):
    """Issue type not in workflow store."""
    def __init__(self, issue_type: str):
        self.issue_type = issue_type
        super().__init__(f"Workflow for '{issue_type}' not found")


class DiscoveryError(WorkflowError):
    """Workflow discovery failed."""
    def __init__(self, issue_key: str, stuck_at: str, discovered_states: set[str]):
        self.issue_key = issue_key
        self.stuck_at = stuck_at
        self.discovered_states = discovered_states
        super().__init__(
            f"Discovery failed for {issue_key}. Stuck at '{stuck_at}'. "
            f"Discovered {len(discovered_states)} states."
        )


class TransitionFailedError(WorkflowError):
    """Transition execution failed."""
    def __init__(self, issue_key: str, transition: Transition,
                 current_state: str, reason: str):
        self.issue_key = issue_key
        self.transition = transition
        self.current_state = current_state
        self.reason = reason
        super().__init__(
            f"Transition '{transition.name}' failed for {issue_key} "
            f"at state '{current_state}': {reason}"
        )
```

**Step 2: Add discover_workflow function**

Add at end of file (before `if __name__`):

```python
def discover_workflow(client, issue_key: str, verbose: bool = False) -> WorkflowGraph:
    """
    Walk issue through all reachable states to map complete workflow.

    Args:
        client: Jira client instance
        issue_key: Issue to use for discovery
        verbose: Print progress during discovery

    Returns:
        Complete WorkflowGraph for this issue type
    """
    # Get issue info
    issue = client.issue(issue_key, fields="status,issuetype")
    issue_type = issue["fields"]["issuetype"]["name"]
    issue_type_id = issue["fields"]["issuetype"]["id"]
    original_state = issue["fields"]["status"]["name"]

    if verbose:
        print(f"Discovering workflow for '{issue_type}' from {issue_key}")
        print(f"Starting state: {original_state}")

    graph = WorkflowGraph(
        issue_type=issue_type,
        issue_type_id=issue_type_id,
        discovered_from=issue_key,
        discovered_at=datetime.now()
    )

    # BFS through all states
    visited = set()
    queue = deque([original_state])

    while queue:
        current_state = queue.popleft()

        if current_state in visited:
            continue
        visited.add(current_state)

        if verbose:
            print(f"  Mapping state: {current_state}")

        # Get transitions from current state
        # First, we need to BE in this state
        issue = client.issue(issue_key, fields="status")
        actual_state = issue["fields"]["status"]["name"]

        if actual_state != current_state:
            # Try to navigate to this state
            if graph.states:  # Only if we have some transitions mapped
                try:
                    path = graph.path_to(actual_state, current_state)
                    for t in path:
                        client.set_issue_status(issue_key, t.to)
                except PathNotFoundError:
                    if verbose:
                        print(f"    Cannot reach {current_state}, skipping")
                    continue

        # Now get available transitions
        response = client.get(f"/rest/api/2/issue/{issue_key}/transitions")
        transitions = []
        for t in response.get("transitions", []):
            to_state = t.get("to", {})
            if isinstance(to_state, dict):
                to_name = to_state.get("name", "")
            else:
                to_name = str(to_state)

            transitions.append(Transition(
                id=t["id"],
                name=t["name"],
                to=to_name
            ))

            # Queue unvisited states
            if to_name and to_name not in visited:
                queue.append(to_name)

        graph.add_state(current_state, transitions)

        # Move to an unvisited state if possible
        for t in transitions:
            if t.to not in visited:
                try:
                    client.set_issue_status(issue_key, t.to)
                    break
                except Exception:
                    continue

    # Try to return to original state
    if verbose:
        print(f"  Returning to original state: {original_state}")

    try:
        issue = client.issue(issue_key, fields="status")
        current = issue["fields"]["status"]["name"]
        if current != original_state:
            path = graph.path_to(current, original_state)
            for t in path:
                client.set_issue_status(issue_key, t.to)
    except (PathNotFoundError, Exception) as e:
        if verbose:
            print(f"    Warning: Could not return to original state: {e}")

    if verbose:
        print(f"✓ Discovered {len(graph.states)} states")

    return graph
```

**Step 3: Commit**

```bash
git add scripts/lib/workflow.py
git commit -m "feat(jira): add workflow discovery function"
```

---

## Phase 4: Smart Transition

### Task 4.1: Add smart_transition function

**Files:**
- Modify: `scripts/lib/workflow.py`

**Step 1: Add smart_transition function**

Add after `discover_workflow`:

```python
def smart_transition(
    client,
    issue_key: str,
    target_state: str,
    store: WorkflowStore,
    add_comment: bool = False,
    dry_run: bool = False,
    verbose: bool = False
) -> list[Transition]:
    """
    Transition issue to target state, navigating multiple steps if needed.

    Args:
        client: Jira client instance
        issue_key: Issue to transition
        target_state: Target state name (case-insensitive, partial match)
        store: WorkflowStore instance
        add_comment: Add comment trail after transition
        dry_run: Show path without executing
        verbose: Print progress

    Returns:
        List of Transitions that were executed

    Raises:
        WorkflowNotFoundError: Issue type unknown (triggers auto-discover)
        PathNotFoundError: No route to target state
        TransitionFailedError: Execution failed mid-path
    """
    # Get issue info
    issue = client.issue(issue_key, fields="status,issuetype")
    issue_type = issue["fields"]["issuetype"]["name"]
    current_state = issue["fields"]["status"]["name"]

    if verbose:
        print(f"Transitioning {issue_key} ({issue_type})")
        print(f"  Current: {current_state}")
        print(f"  Target: {target_state}")

    # Load workflow
    graph = store.get(issue_type)

    if graph is None:
        if verbose:
            print(f"  Workflow unknown, discovering...")
        graph = discover_workflow(client, issue_key, verbose=verbose)
        store.save(graph)

    # Find path
    path = graph.path_to(current_state, target_state)

    if not path:
        if verbose:
            print(f"  Already at target state")
        return []

    if verbose or dry_run:
        path_str = " → ".join([current_state] + [t.to for t in path])
        print(f"  Path: {path_str} ({len(path)} steps)")

    if dry_run:
        return path

    # Execute transitions
    executed = []
    for i, transition in enumerate(path, 1):
        if verbose:
            print(f"  Step {i}/{len(path)}: {transition.name} → {transition.to}", end=" ")

        try:
            client.set_issue_status(issue_key, transition.to)
            executed.append(transition)
            if verbose:
                print("✓")
        except Exception as e:
            if verbose:
                print("✗")
            raise TransitionFailedError(
                issue_key=issue_key,
                transition=transition,
                current_state=executed[-1].to if executed else current_state,
                reason=str(e)
            )

    # Add comment trail if requested
    if add_comment and executed:
        trail = " → ".join([current_state] + [t.to for t in executed])
        comment = f"Transitioned: {trail}"
        try:
            client.issue_add_comment(issue_key, comment)
        except Exception:
            pass  # Don't fail if comment fails

    return executed
```

**Step 2: Commit**

```bash
git add scripts/lib/workflow.py
git commit -m "feat(jira): add smart_transition function"
```

---

## Phase 5: Enhanced jira-transition.py

### Task 5.1: Fix and enhance jira-transition.py

**Files:**
- Modify: `scripts/workflow/jira-transition.py`

**Step 1: Update imports and add workflow imports**

Replace lines 22-24 with:

```python
import click
from lib.client import get_jira_client
from lib.output import format_output, format_table, success, error, warning
from lib.workflow import (
    WorkflowStore,
    smart_transition,
    PathNotFoundError,
    WorkflowNotFoundError,
    TransitionFailedError
)
```

**Step 2: Update the `do` command**

Replace the entire `do_transition` function (lines 123-215) with:

```python
@cli.command('do')
@click.argument('issue_key')
@click.argument('target_state')
@click.option('--comment', '-c', is_flag=True, help='Add transition trail as comment')
@click.option('--resolution', '-r', help='Resolution name (for closing transitions)')
@click.option('--dry-run', is_flag=True, help='Show path without executing')
@click.pass_context
def do_transition(ctx, issue_key: str, target_state: str,
                  comment: bool, resolution: str | None, dry_run: bool):
    """Transition an issue to a new status (smart multi-step).

    ISSUE_KEY: The Jira issue key (e.g., PROJ-123)

    TARGET_STATE: Target status name (e.g., "In Progress", "Waiting for QA")

    Automatically finds and executes the shortest path to the target state.

    Examples:

      jira-transition do PROJ-123 "In Progress"

      jira-transition do PROJ-123 "Waiting for QA" --dry-run

      jira-transition do PROJ-123 "Done" --comment

      jira-transition do PROJ-123 "Geschlossen" -r Fixed
    """
    client = ctx.obj['client']
    debug = ctx.obj['debug']

    try:
        store = WorkflowStore()

        # Handle resolution for closing transitions
        # TODO: Add resolution support in v2
        if resolution:
            warning("Resolution support coming in v2, ignoring for now")

        executed = smart_transition(
            client=client,
            issue_key=issue_key,
            target_state=target_state,
            store=store,
            add_comment=comment,
            dry_run=dry_run,
            verbose=not ctx.obj['quiet']
        )

        if dry_run:
            if ctx.obj['json']:
                format_output({
                    'issue_key': issue_key,
                    'dry_run': True,
                    'path': [t.to_dict() for t in executed]
                }, as_json=True)
            return

        if ctx.obj['quiet']:
            print(issue_key)
        elif ctx.obj['json']:
            format_output({
                'issue_key': issue_key,
                'transitions': [t.to_dict() for t in executed],
                'final_state': executed[-1].to if executed else target_state
            }, as_json=True)
        else:
            if executed:
                success(f"Transitioned {issue_key} to '{executed[-1].to}'")
            else:
                success(f"{issue_key} already at '{target_state}'")

    except PathNotFoundError as e:
        error(f"No path to '{target_state}'")
        print(f"  Reachable states: {', '.join(sorted(e.reachable))}")
        sys.exit(1)

    except TransitionFailedError as e:
        error(f"Transition failed at '{e.current_state}'")
        print(f"  Failed: {e.transition.name} → {e.transition.to}")
        print(f"  Reason: {e.reason}")
        sys.exit(1)

    except Exception as e:
        if debug:
            raise
        error(f"Failed to transition {issue_key}: {e}")
        sys.exit(1)
```

**Step 3: Commit**

```bash
git add scripts/workflow/jira-transition.py
git commit -m "feat(jira): enhance jira-transition with smart multi-step"
```

---

## Phase 6: New jira-workflow.py

### Task 6.1: Create jira-workflow.py CLI

**Files:**
- Create: `scripts/workflow/jira-workflow.py`

**Step 1: Create the full script**

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "atlassian-python-api>=3.41.0",
#     "click>=8.1.0",
# ]
# ///
"""Jira workflow discovery and visualization."""

import sys
from pathlib import Path

# Shared library import
_script_dir = Path(__file__).parent
_lib_path = _script_dir.parent / "lib"
if _lib_path.exists():
    sys.path.insert(0, str(_lib_path.parent))

import click
from lib.client import get_jira_client
from lib.output import format_output, success, error, warning
from lib.workflow import (
    WorkflowStore,
    WorkflowGraph,
    discover_workflow,
    PathNotFoundError
)


@click.group()
@click.option('--json', 'output_json', is_flag=True, help='Output as JSON')
@click.option('--quiet', '-q', is_flag=True, help='Minimal output')
@click.option('--env-file', type=click.Path(), help='Environment file path')
@click.option('--debug', is_flag=True, help='Show debug information on errors')
@click.pass_context
def cli(ctx, output_json: bool, quiet: bool, env_file: str | None, debug: bool):
    """Jira workflow discovery and visualization.

    Discover, view, and analyze Jira workflows for different issue types.
    """
    ctx.ensure_object(dict)
    ctx.obj['json'] = output_json
    ctx.obj['quiet'] = quiet
    ctx.obj['debug'] = debug
    ctx.obj['env_file'] = env_file


@cli.command('discover')
@click.argument('issue_key')
@click.pass_context
def discover(ctx, issue_key: str):
    """Discover workflow from a sample issue.

    ISSUE_KEY: Issue to use for discovery (e.g., PROJ-123)

    Walks the issue through all reachable states to map the complete workflow.
    Saves the result to the workflow store.

    Example:

      jira-workflow discover PROJ-123
    """
    try:
        client = get_jira_client(ctx.obj['env_file'])
    except Exception as e:
        if ctx.obj['debug']:
            raise
        error(str(e))
        sys.exit(1)

    try:
        store = WorkflowStore()
        graph = discover_workflow(
            client,
            issue_key,
            verbose=not ctx.obj['quiet']
        )
        store.save(graph)

        if ctx.obj['json']:
            format_output(graph.to_dict(), as_json=True)
        elif not ctx.obj['quiet']:
            success(f"Workflow saved for '{graph.issue_type}'")
            print(f"  States: {len(graph.states)}")
            print(f"  Transitions: {sum(len(t) for t in graph.states.values())}")

    except Exception as e:
        if ctx.obj['debug']:
            raise
        error(f"Discovery failed: {e}")
        sys.exit(1)


@cli.command('show')
@click.argument('issue_type')
@click.option('--format', '-f', 'fmt',
              type=click.Choice(['ascii', 'table', 'json']),
              default='table', help='Output format')
@click.pass_context
def show(ctx, issue_type: str, fmt: str):
    """Show workflow for an issue type.

    ISSUE_TYPE: Issue type name (e.g., "Sub: Task")

    Example:

      jira-workflow show "Sub: Task"

      jira-workflow show "Sub: Task" --format ascii
    """
    store = WorkflowStore()
    graph = store.get(issue_type)

    if graph is None:
        error(f"Workflow for '{issue_type}' not found")
        print(f"\nKnown types: {', '.join(store.list_types()) or 'none'}")
        print("\nRun 'jira-workflow discover ISSUE-KEY' to map a workflow")
        sys.exit(1)

    if fmt == 'json' or ctx.obj['json']:
        format_output(graph.to_dict(), as_json=True)
    elif fmt == 'ascii':
        print(graph.to_ascii())
    else:
        print(f"Workflow: {graph.issue_type}")
        if graph.discovered_from:
            print(f"Discovered from: {graph.discovered_from}")
        print()
        print(graph.to_table())


@cli.command('list')
@click.pass_context
def list_workflows(ctx):
    """List all known workflows.

    Example:

      jira-workflow list
    """
    store = WorkflowStore()
    types = store.list_types()

    if ctx.obj['json']:
        format_output({'issue_types': types}, as_json=True)
        return

    if not types:
        print("No workflows discovered yet")
        print("\nRun 'jira-workflow discover ISSUE-KEY' to map a workflow")
        return

    print("Known workflows:")
    for t in sorted(types):
        graph = store.get(t)
        states = len(graph.states) if graph else 0
        source = f" (from {graph.discovered_from})" if graph and graph.discovered_from else ""
        print(f"  {t}: {states} states{source}")


@cli.command('path')
@click.argument('issue_type')
@click.option('--from', '-f', 'from_state', required=True, help='Starting state')
@click.option('--to', '-t', 'to_state', required=True, help='Target state')
@click.pass_context
def show_path(ctx, issue_type: str, from_state: str, to_state: str):
    """Show path between two states.

    ISSUE_TYPE: Issue type name (e.g., "Sub: Task")

    Example:

      jira-workflow path "Sub: Task" --from "Offen" --to "Waiting for QA"
    """
    store = WorkflowStore()
    graph = store.get(issue_type)

    if graph is None:
        error(f"Workflow for '{issue_type}' not found")
        sys.exit(1)

    try:
        path = graph.path_to(from_state, to_state)

        if ctx.obj['json']:
            format_output({
                'from': from_state,
                'to': to_state,
                'path': [t.to_dict() for t in path]
            }, as_json=True)
            return

        if not path:
            print(f"Already at '{to_state}'")
            return

        print(f"Path from '{from_state}' to '{to_state}':")
        current = from_state
        for i, t in enumerate(path, 1):
            print(f"  {i}. {t.name} → {t.to}")
            current = t.to

    except PathNotFoundError as e:
        error(f"No path from '{from_state}' to '{to_state}'")
        print(f"  Reachable: {', '.join(sorted(e.reachable))}")
        sys.exit(1)


@cli.command('validate')
@click.argument('issue_type')
@click.pass_context
def validate(ctx, issue_type: str):
    """Validate workflow for dead ends.

    ISSUE_TYPE: Issue type name (e.g., "Sub: Task")

    Example:

      jira-workflow validate "Sub: Task"
    """
    store = WorkflowStore()
    graph = store.get(issue_type)

    if graph is None:
        error(f"Workflow for '{issue_type}' not found")
        sys.exit(1)

    # Find states with no exit (dead ends)
    dead_ends = []
    done_states = {'Fertig', 'Done', 'Geschlossen', 'Closed'}

    for state in graph.all_states():
        if state in done_states:
            continue

        reachable = graph.reachable_from(state)
        if not reachable.intersection(done_states):
            dead_ends.append(state)

    if ctx.obj['json']:
        format_output({
            'issue_type': issue_type,
            'valid': len(dead_ends) == 0,
            'dead_ends': dead_ends
        }, as_json=True)
        return

    print(f"Validating '{issue_type}' workflow...")

    if dead_ends:
        warning(f"Found {len(dead_ends)} dead-end states:")
        for state in dead_ends:
            print(f"  - {state} (no path to done)")
    else:
        success("All states have exit path to done")


@cli.command('refresh')
@click.argument('issue_type')
@click.option('--issue', '-i', required=True, help='Issue to use for re-discovery')
@click.pass_context
def refresh(ctx, issue_type: str, issue: str):
    """Re-discover workflow for an issue type.

    ISSUE_TYPE: Issue type name to refresh

    Example:

      jira-workflow refresh "Sub: Task" --issue PROJ-123
    """
    try:
        client = get_jira_client(ctx.obj['env_file'])
    except Exception as e:
        error(str(e))
        sys.exit(1)

    store = WorkflowStore()

    # Verify issue is correct type
    issue_data = client.issue(issue, fields="issuetype")
    actual_type = issue_data["fields"]["issuetype"]["name"]

    if actual_type != issue_type:
        error(f"Issue {issue} is '{actual_type}', not '{issue_type}'")
        sys.exit(1)

    if not ctx.obj['quiet']:
        print(f"Re-discovering '{issue_type}' from {issue}...")

    graph = discover_workflow(client, issue, verbose=not ctx.obj['quiet'])
    store.save(graph)

    success(f"Workflow refreshed for '{issue_type}'")


if __name__ == '__main__':
    cli()
```

**Step 2: Make executable**

```bash
chmod +x ~/.claude/plugins/marketplaces/sebastian-marketplace/plugins/jira-integration/skills/jira-communication/scripts/workflow/jira-workflow.py
```

**Step 3: Commit**

```bash
git add scripts/workflow/jira-workflow.py
git commit -m "feat(jira): add jira-workflow.py for discovery and visualization"
```

---

## Phase 7: Documentation & Polish

### Task 7.1: Update SKILL.md

**Files:**
- Modify: `SKILL.md`

**Step 1: Add new commands to documentation**

Add after the existing `jira-transition.py` section (around line 51):

```markdown
#### `scripts/workflow/jira-workflow.py`
**When to use:** Discover, view, and analyze Jira workflows

```bash
# Discover workflow from issue
$JIRA/workflow/jira-workflow.py discover PROJ-123

# Show workflow for issue type
$JIRA/workflow/jira-workflow.py show "Sub: Task"
$JIRA/workflow/jira-workflow.py show "Sub: Task" --format ascii

# List known workflows
$JIRA/workflow/jira-workflow.py list

# Show path between states
$JIRA/workflow/jira-workflow.py path "Sub: Task" --from "Offen" --to "Waiting for QA"

# Validate workflow for dead ends
$JIRA/workflow/jira-workflow.py validate "Sub: Task"
```
```

**Step 2: Update jira-transition.py section**

Update the existing section to mention smart transitions:

```markdown
#### `scripts/workflow/jira-transition.py`
**When to use:** Change issue status (smart multi-step navigation)

```bash
# Simple transition
$JIRA/workflow/jira-transition.py do PROJ-123 "In Progress"

# Smart multi-step (finds path automatically)
$JIRA/workflow/jira-transition.py do PROJ-123 "Waiting for QA"

# With comment trail
$JIRA/workflow/jira-transition.py do PROJ-123 "Waiting for QA" --comment

# Dry-run to see path
$JIRA/workflow/jira-transition.py do PROJ-123 "Done" --dry-run
```
```

**Step 3: Commit**

```bash
git add SKILL.md
git commit -m "docs(jira): update SKILL.md with new workflow commands"
```

---

### Task 7.2: Pre-populate HMKG workflows

**Files:**
- Modify: `references/workflows.json`

**Step 1: Run discovery on HMKG issue types**

```bash
JIRA=~/.claude/plugins/marketplaces/sebastian-marketplace/plugins/jira-integration/skills/jira-communication/scripts

# Discover Sub: Task workflow
$JIRA/workflow/jira-workflow.py discover HMKG-2064

# List what we have
$JIRA/workflow/jira-workflow.py list
```

**Step 2: Commit populated workflows**

```bash
git add references/workflows.json
git commit -m "data(jira): pre-populate HMKG workflow mappings"
```

---

### Task 7.3: Final integration test

**Step 1: Test complete flow**

```bash
JIRA=~/.claude/plugins/marketplaces/sebastian-marketplace/plugins/jira-integration/skills/jira-communication/scripts

# List workflows
$JIRA/workflow/jira-workflow.py list

# Show a workflow
$JIRA/workflow/jira-workflow.py show "Sub: Task" --format ascii

# Test path finding
$JIRA/workflow/jira-workflow.py path "Sub: Task" --from "Offen" --to "Waiting for QA"

# Dry-run a transition
$JIRA/workflow/jira-transition.py do HMKG-2064 "In Arbeit" --dry-run
```

**Step 2: Tag release**

```bash
git tag -a jira-workflow-v1.0.0 -m "Jira workflow discovery and smart transitions"
```

---

## Summary

| Phase | Tasks | Outcome |
|-------|-------|---------|
| 1 | 1.1-1.3 | Core dataclasses with path finding |
| 2 | 2.1-2.2 | Persistent workflow store |
| 3 | 3.1 | Workflow discovery |
| 4 | 4.1 | Smart transition function |
| 5 | 5.1 | Enhanced jira-transition.py |
| 6 | 6.1 | New jira-workflow.py CLI |
| 7 | 7.1-7.3 | Docs, data, integration test |

**Total: 11 tasks, ~2-3 hours implementation time**
