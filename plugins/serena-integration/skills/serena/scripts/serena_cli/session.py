"""
Session management for Serena MCP connections.

Handles persistent session storage across CLI invocations, allowing
connection reuse without re-initialization overhead.

The session file stores:
    - Session ID from MCP server
    - Creation timestamp for expiry checking
    - Server URL for validation

Session files are stored per-user in /tmp to survive across invocations
but not across reboots (appropriate for localhost connections).
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

# Session expires after 30 minutes of inactivity
SESSION_TTL_SECONDS = 1800


@dataclass
class Session:
    """Represents an MCP session with metadata."""

    session_id: str
    server_url: str
    created_at: float
    last_used: float

    def is_expired(self, ttl: int = SESSION_TTL_SECONDS) -> bool:
        """Check if session has expired based on last use time."""
        return (time.time() - self.last_used) > ttl

    def touch(self) -> None:
        """Update last_used timestamp."""
        self.last_used = time.time()

    def to_dict(self) -> dict:
        """Serialize session to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> Session:
        """Deserialize session from dictionary."""
        return cls(**data)


class SessionManager:
    """
    Manages persistent MCP sessions across CLI invocations.

    Sessions are stored in a JSON file per user, keyed by server URL.
    This allows multiple Serena servers to maintain separate sessions.

    Attributes:
        session_file: Path to the session storage file.

    Example:
        >>> manager = SessionManager()
        >>> session = manager.get_session("http://localhost:9121/mcp")
        >>> if session and not session.is_expired():
        ...     print(f"Reusing session: {session.session_id}")
    """

    def __init__(self, session_file: Optional[Path] = None):
        """
        Initialize session manager.

        Args:
            session_file: Custom path for session storage.
                         Defaults to /tmp/serena-session-{uid}.json
        """
        if session_file is None:
            uid = os.getuid()
            session_file = Path(f"/tmp/serena-session-{uid}.json")
        self.session_file = session_file

    def get_session(self, server_url: str) -> Optional[Session]:
        """
        Retrieve session for a server URL if it exists and is valid.

        Args:
            server_url: The MCP server URL.

        Returns:
            Session object if valid session exists, None otherwise.
        """
        sessions = self._load_sessions()
        if server_url not in sessions:
            return None

        session = Session.from_dict(sessions[server_url])
        if session.is_expired():
            self.clear_session(server_url)
            return None

        return session

    def save_session(self, session: Session) -> None:
        """
        Save or update a session.

        Args:
            session: The session to save.
        """
        sessions = self._load_sessions()
        session.touch()
        sessions[session.server_url] = session.to_dict()
        self._save_sessions(sessions)

    def clear_session(self, server_url: str) -> None:
        """
        Remove a session for a server URL.

        Args:
            server_url: The MCP server URL.
        """
        sessions = self._load_sessions()
        if server_url in sessions:
            del sessions[server_url]
            self._save_sessions(sessions)

    def clear_all(self) -> None:
        """Remove all stored sessions."""
        if self.session_file.exists():
            self.session_file.unlink()

    def _load_sessions(self) -> dict:
        """Load sessions from file."""
        if not self.session_file.exists():
            return {}
        try:
            with open(self.session_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}

    def _save_sessions(self, sessions: dict) -> None:
        """Save sessions to file with restricted permissions."""
        # Create with restricted permissions (owner read/write only)
        old_umask = os.umask(0o077)
        try:
            with open(self.session_file, "w") as f:
                json.dump(sessions, f, indent=2)
        finally:
            os.umask(old_umask)
