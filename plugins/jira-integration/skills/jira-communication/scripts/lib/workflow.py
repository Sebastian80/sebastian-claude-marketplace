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
