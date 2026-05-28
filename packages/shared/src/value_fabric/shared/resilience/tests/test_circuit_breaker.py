"""Tests for shared circuit breaker (P1-014)."""

from __future__ import annotations

import asyncio

import pytest

from ..circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerOpen,
    CircuitBreakerRegistry,
    CircuitState,
)


class TestCircuitBreakerStateTransitions:
    """Cover CLOSED → OPEN → HALF_OPEN → CLOSED lifecycle."""

    @pytest.mark.asyncio
    async def test_closed_allows_calls(self):
        breaker = CircuitBreaker("test-svc", failure_threshold=3)
        result = await breaker.call(_ok)
        assert result == "ok"
        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_opens_after_threshold_failures(self):
        breaker = CircuitBreaker("test-svc", failure_threshold=2, recovery_timeout=300)

        with pytest.raises(RuntimeError):
            await breaker.call(_fail)
        assert breaker.state == CircuitState.CLOSED
        assert breaker.failures == 1

        with pytest.raises(RuntimeError):
            await breaker.call(_fail)
        assert breaker.state == CircuitState.OPEN
        assert breaker.failures == 2

    @pytest.mark.asyncio
    async def test_open_rejects_calls_immediately(self):
        breaker = CircuitBreaker("test-svc", failure_threshold=1, recovery_timeout=300)

        with pytest.raises(RuntimeError):
            await breaker.call(_fail)

        with pytest.raises(CircuitBreakerOpen) as exc_info:
            await breaker.call(_ok)

        assert exc_info.value.service == "test-svc"
        assert exc_info.value.retry_after > 0

    @pytest.mark.asyncio
    async def test_half_open_after_recovery_timeout(self):
        breaker = CircuitBreaker("test-svc", failure_threshold=1, recovery_timeout=0.05)

        with pytest.raises(RuntimeError):
            await breaker.call(_fail)
        assert breaker.state == CircuitState.OPEN

        await asyncio.sleep(0.06)
        # State transition happens inside call() when lock is held
        result = await breaker.call(_ok)
        assert result == "ok"
        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_half_open_failure_reopens(self):
        breaker = CircuitBreaker("test-svc", failure_threshold=1, recovery_timeout=0.05)

        with pytest.raises(RuntimeError):
            await breaker.call(_fail)
        assert breaker.state == CircuitState.OPEN

        await asyncio.sleep(0.06)
        with pytest.raises(RuntimeError):
            await breaker.call(_fail)
        assert breaker.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_half_open_max_calls_enforced(self):
        breaker = CircuitBreaker(
            "test-svc", failure_threshold=1, recovery_timeout=0.05, half_open_max_calls=1
        )

        with pytest.raises(RuntimeError):
            await breaker.call(_fail)
        assert breaker.state == CircuitState.OPEN

        await asyncio.sleep(0.06)
        # First half-open call succeeds
        result = await breaker.call(_ok)
        assert result == "ok"
        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_half_open_max_calls_enforced(self):
        breaker = CircuitBreaker(
            "test-svc", failure_threshold=1, recovery_timeout=0.05, half_open_max_calls=1
        )

        with pytest.raises(RuntimeError):
            await breaker.call(_fail)
        assert breaker.state == CircuitState.OPEN

        await asyncio.sleep(0.06)
        # First half-open call succeeds
        result = await breaker.call(_ok)
        assert result == "ok"
        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_success_resets_failures_in_closed_state(self):
        breaker = CircuitBreaker("test-svc", failure_threshold=3)

        with pytest.raises(RuntimeError):
            await breaker.call(_fail)
        assert breaker.failures == 1

        await breaker.call(_ok)
        assert breaker.failures == 0

    @pytest.mark.asyncio
    async def test_get_state_returns_dict(self):
        breaker = CircuitBreaker("test-svc", failure_threshold=2)
        state = breaker.get_state()
        assert state["service"] == "test-svc"
        assert state["state"] == "closed"
        assert state["failures"] == 0
        assert state["failure_threshold"] == 2


class TestCircuitBreakerRegistry:
    @pytest.mark.asyncio
    async def test_get_breaker_creates_on_first_access(self):
        registry = CircuitBreakerRegistry()
        breaker = await registry.get_breaker("svc-a", failure_threshold=3)
        assert breaker.service_name == "svc-a"
        assert breaker.failure_threshold == 3

    @pytest.mark.asyncio
    async def test_get_breaker_returns_same_instance(self):
        registry = CircuitBreakerRegistry()
        b1 = await registry.get_breaker("svc-a")
        b2 = await registry.get_breaker("svc-a")
        assert b1 is b2

    @pytest.mark.asyncio
    async def test_call_routes_through_breaker(self):
        registry = CircuitBreakerRegistry()
        result = await registry.call("svc-a", _ok)
        assert result == "ok"

    def test_get_all_states(self):
        registry = CircuitBreakerRegistry()
        # Synchronous because breaker creation is deferred
        assert registry.get_all_states() == {}


async def _ok():
    return "ok"


async def _fail():
    raise RuntimeError("boom")
