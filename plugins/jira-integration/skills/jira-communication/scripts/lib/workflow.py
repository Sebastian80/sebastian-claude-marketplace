#!/usr/bin/env python3
"""Jira workflow graph and transition logic."""

import json
from dataclasses import dataclass, field
from datetime import datetime
from collections import deque
from pathlib import Path
from typing import Optional


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
    def __init__(self, issue_key: str, transition: "Transition",
                 current_state: str, reason: str):
        self.issue_key = issue_key
        self.transition = transition
        self.current_state = current_state
        self.reason = reason
        super().__init__(
            f"Transition '{transition.name}' failed for {issue_key} "
            f"at state '{current_state}': {reason}"
        )


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


def smart_transition(
    client,
    issue_key: str,
    target_state: str,
    store: WorkflowStore = None,  # Kept for backward compat, now ignored
    add_comment: bool = False,
    dry_run: bool = False,
    verbose: bool = False,
    max_steps: int = 5,
) -> list[Transition]:
    """
    Transition issue to target state using runtime path-finding.

    NO CACHING - discovers path at runtime by querying available transitions.
    This works reliably across all projects and workflow configurations.

    Algorithm:
    1. Check if already at target → done
    2. Get available transitions from current state
    3. If target directly available → execute
    4. Otherwise, try each transition and recursively search (greedy BFS)
    5. Stop at max_steps to prevent infinite loops

    Args:
        client: Jira client instance
        issue_key: Issue to transition
        target_state: Target state name (case-insensitive match)
        store: IGNORED - kept for backward compatibility
        add_comment: Add comment trail after transition
        dry_run: Show path without executing
        verbose: Print progress
        max_steps: Maximum transitions to execute (default 5)

    Returns:
        List of Transitions that were executed

    Raises:
        PathNotFoundError: No route to target state
        TransitionFailedError: Execution failed mid-path
    """
    target_lower = target_state.lower()
    executed = []
    visited_states = set()
    start_state = None

    for step in range(max_steps):
        # Get current state
        issue = client.issue(issue_key, fields="status")
        current_state = issue["fields"]["status"]["name"]

        if start_state is None:
            start_state = current_state

        if verbose:
            print(f"  Step {step}: at '{current_state}'")

        # Check if already at target (case-insensitive)
        if current_state.lower() == target_lower:
            if verbose:
                print(f"  ✓ Reached target '{target_state}'")
            break

        # Detect loops
        if current_state in visited_states:
            raise PathNotFoundError(
                from_state=start_state,
                to_state=target_state,
                reachable=visited_states
            )
        visited_states.add(current_state)

        # Get available transitions
        transitions_raw = client.get_issue_transitions(issue_key)
        transitions = []
        for t in transitions_raw:
            to_state = t.get("to", {})
            to_name = to_state.get("name", "") if isinstance(to_state, dict) else str(to_state)
            transitions.append(Transition(
                id=str(t["id"]),
                name=t["name"],
                to=to_name
            ))

        if verbose:
            available = [t.to for t in transitions]
            print(f"    Available: {available}")

        if not transitions:
            raise PathNotFoundError(
                from_state=start_state,
                to_state=target_state,
                reachable=visited_states
            )

        # Look for direct transition to target
        direct = None
        for t in transitions:
            if t.to.lower() == target_lower:
                direct = t
                break

        if direct:
            if verbose:
                print(f"    → Direct transition: {direct.name}")
            if not dry_run:
                try:
                    client.set_issue_status(issue_key, direct.to)
                except Exception as e:
                    raise TransitionFailedError(
                        issue_key=issue_key,
                        transition=direct,
                        current_state=current_state,
                        reason=str(e)
                    )
            executed.append(direct)
            break

        # No direct path - pick transition to unvisited state
        next_transition = None
        for t in transitions:
            if t.to not in visited_states:
                next_transition = t
                break

        if next_transition is None:
            # All transitions lead to visited states - stuck
            raise PathNotFoundError(
                from_state=start_state,
                to_state=target_state,
                reachable=visited_states
            )

        if verbose:
            print(f"    → Intermediate: {next_transition.name} → {next_transition.to}")

        if not dry_run:
            try:
                client.set_issue_status(issue_key, next_transition.to)
            except Exception as e:
                raise TransitionFailedError(
                    issue_key=issue_key,
                    transition=next_transition,
                    current_state=current_state,
                    reason=str(e)
                )
        executed.append(next_transition)

    else:
        # Loop exhausted without reaching target
        raise WorkflowError(
            f"Could not reach '{target_state}' within {max_steps} steps. "
            f"Visited: {', '.join(sorted(visited_states))}"
        )

    # Add comment trail if requested
    if add_comment and executed and not dry_run:
        trail = " → ".join([start_state] + [t.to for t in executed])
        comment = f"Transitioned: {trail}"
        try:
            client.issue_add_comment(issue_key, comment)
        except Exception:
            pass  # Don't fail if comment fails

    return executed
