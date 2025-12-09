"""
Structured logging for skills daemon.
"""

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import LOG_FILE


class StructuredFormatter(logging.Formatter):
    """JSON-formatted log entries."""

    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add extra fields
        if hasattr(record, "event"):
            entry["event"] = record.event
        if hasattr(record, "context"):
            entry.update(record.context)

        # Add exception info if present
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(entry)


class DaemonLogger:
    """Logger for daemon operations with file and console output."""

    def __init__(self, name: str = "skills-daemon"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)

        # Console handler (human-readable)
        console = logging.StreamHandler(sys.stdout)
        console.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%H:%M:%S"
        ))
        self.logger.addHandler(console)

        # File handler (JSON)
        try:
            file_handler = logging.FileHandler(LOG_FILE)
            file_handler.setFormatter(StructuredFormatter())
            self.logger.addHandler(file_handler)
        except (OSError, PermissionError):
            pass  # Skip file logging if not writable

    def log(self, level: str, event: str, **context: Any) -> None:
        """Log with structured context."""
        record = self.logger.makeRecord(
            self.logger.name,
            getattr(logging, level.upper()),
            "", 0, event, (), None
        )
        record.event = event
        record.context = context
        self.logger.handle(record)

    def info(self, message: str, **context: Any) -> None:
        self.log("INFO", message, **context)

    def warning(self, message: str, **context: Any) -> None:
        self.log("WARNING", message, **context)

    def error(self, message: str, **context: Any) -> None:
        self.log("ERROR", message, **context)

    def debug(self, message: str, **context: Any) -> None:
        self.log("DEBUG", message, **context)


# Global logger instance
logger = DaemonLogger()
