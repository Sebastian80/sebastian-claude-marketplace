"""Tests for circuit breaker logic."""

import time

import pytest

from ai_tool_bridge.connectors.circuit import CircuitBreaker, CircuitState


class TestCircuitBreaker:
    """Test circuit breaker state transitions."""

    def test_initial_state_is_closed(self):
        """Circuit starts in CLOSED state."""
        cb = CircuitBreaker()
        assert cb.state == CircuitState.CLOSED
        assert cb.can_execute()

    def test_stays_closed_on_success(self):
        """Successes keep circuit closed."""
        cb = CircuitBreaker(failure_threshold=3)

        for _ in range(10):
            cb.record_success()

        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0

    def test_opens_after_threshold_failures(self):
        """Circuit opens after failure_threshold failures."""
        cb = CircuitBreaker(failure_threshold=3)

        cb.record_failure()
        assert cb.state == CircuitState.CLOSED

        cb.record_failure()
        assert cb.state == CircuitState.CLOSED

        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        assert not cb.can_execute()

    def test_success_resets_failure_count(self):
        """Success resets the failure counter."""
        cb = CircuitBreaker(failure_threshold=3)

        cb.record_failure()
        cb.record_failure()
        assert cb.failure_count == 2

        cb.record_success()
        assert cb.failure_count == 0
        assert cb.state == CircuitState.CLOSED

    def test_transitions_to_half_open_after_timeout(self):
        """Circuit transitions to HALF_OPEN after reset_timeout."""
        cb = CircuitBreaker(failure_threshold=1, reset_timeout=0.1)

        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        assert not cb.can_execute()

        # Wait for reset timeout
        time.sleep(0.15)

        assert cb.can_execute()
        assert cb.state == CircuitState.HALF_OPEN

    def test_half_open_closes_on_success(self):
        """Success in HALF_OPEN closes the circuit."""
        cb = CircuitBreaker(failure_threshold=1, reset_timeout=0.01)

        cb.record_failure()
        time.sleep(0.02)
        cb.can_execute()  # Triggers transition to HALF_OPEN

        cb.record_success()
        assert cb.state == CircuitState.CLOSED

    def test_half_open_opens_on_failure(self):
        """Failure in HALF_OPEN reopens the circuit."""
        cb = CircuitBreaker(failure_threshold=1, reset_timeout=0.01)

        cb.record_failure()
        time.sleep(0.02)
        cb.can_execute()  # Triggers transition to HALF_OPEN

        cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_reset(self):
        """Reset returns circuit to initial state."""
        cb = CircuitBreaker(failure_threshold=1)

        cb.record_failure()
        assert cb.state == CircuitState.OPEN

        cb.reset()
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0
        assert cb.can_execute()

    def test_status(self):
        """Status returns dict with circuit info."""
        cb = CircuitBreaker(failure_threshold=3)
        cb.record_failure()

        status = cb.status()

        assert status["state"] == "closed"
        assert status["failure_count"] == 1
        assert status["failure_threshold"] == 3
        assert "reset_timeout" in status
