"""
Circuit Breaker - Prevents hammering dead services.

States:
- CLOSED: Normal operation, requests pass through, failures counted
- OPEN: Service is down, reject requests immediately
- HALF_OPEN: Testing recovery, allow one request through

Transitions:
- CLOSED → OPEN: After failure_threshold consecutive failures
- OPEN → HALF_OPEN: After reset_timeout seconds
- HALF_OPEN → CLOSED: On successful request
- HALF_OPEN → OPEN: On failed request
"""

import time
from dataclasses import dataclass, field
from enum import Enum


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreaker:
    """Circuit breaker prevents cascade failures.

    Example:
        circuit = CircuitBreaker(failure_threshold=5, reset_timeout=30.0)

        if circuit.can_execute():
            try:
                response = await make_request()
                circuit.record_success()
            except Exception:
                circuit.record_failure()
        else:
            raise ServiceUnavailable("Circuit open")
    """

    failure_threshold: int = 5
    reset_timeout: float = 30.0

    state: CircuitState = field(default=CircuitState.CLOSED)
    failure_count: int = field(default=0)
    success_count: int = field(default=0)
    last_failure_time: float = field(default=0.0)
    last_state_change: float = field(default_factory=time.monotonic)

    def record_success(self) -> None:
        """Record successful request. Resets failure count."""
        self.failure_count = 0
        self.success_count += 1

        if self.state == CircuitState.HALF_OPEN:
            self._transition_to(CircuitState.CLOSED)

    def record_failure(self) -> None:
        """Record failed request. May open circuit."""
        self.failure_count += 1
        self.last_failure_time = time.monotonic()

        if self.state == CircuitState.HALF_OPEN:
            self._transition_to(CircuitState.OPEN)
        elif self.failure_count >= self.failure_threshold:
            self._transition_to(CircuitState.OPEN)

    def can_execute(self) -> bool:
        """Check if request should proceed.

        Returns:
            True if request can proceed, False if circuit is open
        """
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            # Check if reset timeout has elapsed
            elapsed = time.monotonic() - self.last_failure_time
            if elapsed >= self.reset_timeout:
                self._transition_to(CircuitState.HALF_OPEN)
                return True
            return False

        # HALF_OPEN: allow one test request
        return True

    def reset(self) -> None:
        """Manually reset circuit to closed state."""
        self.failure_count = 0
        self._transition_to(CircuitState.CLOSED)

    def _transition_to(self, new_state: CircuitState) -> None:
        """Transition to new state."""
        if self.state != new_state:
            self.state = new_state
            self.last_state_change = time.monotonic()

    def status(self) -> dict:
        """Current circuit status."""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "failure_threshold": self.failure_threshold,
            "reset_timeout": self.reset_timeout,
            "time_in_state": time.monotonic() - self.last_state_change,
        }
