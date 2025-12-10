"""
Structured logging for skills daemon.

Features:
- JSON-formatted log entries for file output
- Log rotation (5MB max, 3 backups)
- Async logging via QueueHandler (non-blocking I/O)
"""

import atexit
import contextvars
import json
import logging
import logging.handlers
import queue
import sys
import uuid
from datetime import datetime, timezone
from typing import Any

from .config import config

# Context variable for request correlation
request_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    'request_id', default=None
)


def get_request_id() -> str | None:
    """Get current request ID from context."""
    return request_id_ctx.get()


def set_request_id(request_id: str) -> contextvars.Token:
    """Set request ID in context."""
    return request_id_ctx.set(request_id)


def generate_request_id() -> str:
    """Generate a new request ID."""
    return str(uuid.uuid4())[:8]  # Short ID for readability


# Log rotation settings
MAX_BYTES = 5 * 1024 * 1024  # 5MB
BACKUP_COUNT = 3


class StructuredFormatter(logging.Formatter):
    """JSON-formatted log entries."""

    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add request_id from context if available
        request_id = request_id_ctx.get()
        if request_id:
            entry["request_id"] = request_id

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
    """Logger for daemon operations with file and console output.

    Features:
    - Console: human-readable format
    - File: JSON format with rotation (5MB, 3 backups)
    - Async: QueueHandler for non-blocking I/O
    """

    def __init__(self, name: str = "skills-daemon"):
        self.logger = logging.getLogger(name)

        # Use log level from config/environment
        log_level = getattr(logging, config.log_level.upper(), logging.INFO)
        self.logger.setLevel(log_level)

        self._queue_listener = None

        # Console handler (human-readable, direct)
        console = logging.StreamHandler(sys.stdout)
        console.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%H:%M:%S"
        ))
        self.logger.addHandler(console)

        # File handler with rotation + async queue
        try:
            # Ensure log directory exists
            config.log_file.parent.mkdir(parents=True, exist_ok=True)

            # Create rotating file handler
            file_handler = logging.handlers.RotatingFileHandler(
                str(config.log_file),
                maxBytes=MAX_BYTES,
                backupCount=BACKUP_COUNT,
            )
            file_handler.setFormatter(StructuredFormatter())

            # Wrap in QueueHandler for async logging
            log_queue = queue.Queue(-1)  # Unlimited queue
            queue_handler = logging.handlers.QueueHandler(log_queue)
            self.logger.addHandler(queue_handler)

            # Start listener thread to process queue
            self._queue_listener = logging.handlers.QueueListener(
                log_queue, file_handler, respect_handler_level=True
            )
            self._queue_listener.start()

            # Ensure cleanup on exit
            atexit.register(self._shutdown)

        except (OSError, PermissionError):
            pass  # Skip file logging if not writable

    def _shutdown(self) -> None:
        """Stop the queue listener on shutdown."""
        if self._queue_listener:
            self._queue_listener.stop()

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
