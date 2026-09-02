from __future__ import annotations

"""Tests for resilience patterns: token-bucket rate limiter and circuit breaker.

Covers:
- P1-15: Per-tenant rate limiting via TokenBucket / TenantRateLimiter
- P1-18: Circuit breaker for external service calls
"""


import time
from unittest.mock import patch

import pytest

from layer4_agents.resilience import (
    CircuitBreaker,
    CircuitBreakerOpen,
    CircuitBreakerRegistry,
    CircuitState,
    RateLimitExceeded,
    TenantRateLimiter,
    TokenBucket,
)

# ============================================================================
# TokenBucket
# ============================================================================


class TestTokenBucket:
    """Unit tests for the TokenBucket implementation."""

    @pytest.mark.unit
    def test_initial_state(self):
        """Bucket starts with specified token count."""
        bucket = TokenBucket(capacity=10, refill_rate=1.0, tokens=10.0)
        assert bucket.tokens == 10.0
        assert bucket.capacity == 10
        assert bucket.refill_rate == 1.0

    @pytest.mark.unit
    def test_consume_succeeds_when_tokens_available(self, monkeypatch):
        """consume() returns True and decrements tokens exactly when there are enough."""
        clock = {"now": 1_000.0}
        monkeypatch.setattr(time, "time", lambda: clock["now"])

        bucket = TokenBucket(capacity=10, refill_rate=1.0, tokens=5.0)
        # The bucket is created before monkeypatching the time source in this test,
        # so the initial last_refill can be stale relative to the patched clock.
        # Resetting it to the frozen now keeps the elapsed delta consistent with the
        # virtual-time setup and avoids a misleading refill calculation.
        bucket.last_refill = clock["now"]
        result = bucket.consume(1)
        assert result is True
        # The clock is frozen, so no refill can occur between creation and consume;
        # the 5.0-token bucket must hold exactly 4.0 after consuming 1.
        assert bucket.tokens == pytest.approx(4.0)

    @pytest.mark.unit
    def test_consume_fails_when_insufficient_tokens(self):
        """consume() returns False when bucket is empty."""
        bucket = TokenBucket(capacity=10, refill_rate=0.0, tokens=0.0)
        result = bucket.consume(1)
        assert result is False
        assert bucket.tokens == 0.0

    @pytest.mark.unit
    def test_consume_exact_tokens(self):
        """consume() succeeds when exactly the required tokens are available."""
        bucket = TokenBucket(capacity=5, refill_rate=0.0, tokens=3.0)
        assert bucket.consume(3) is True
        assert bucket.tokens == pytest.approx(0.0)

    @pytest.mark.unit
    def test_consume_more_than_available_fails(self):
        """consume() fails when requesting more tokens than available."""
        bucket = TokenBucket(capacity=10, refill_rate=0.0, tokens=2.0)
        assert bucket.consume(5) is False
        assert bucket.tokens == pytest.approx(2.0)

    @pytest.mark.unit
    def test_refill_adds_tokens_over_time(self, monkeypatch):
        """_refill() adds tokens proportional to elapsed time."""
        clock = {"now": 1_000.0}
        monkeypatch.setattr(time, "time", lambda: clock["now"])

        bucket = TokenBucket(capacity=10, refill_rate=10.0, tokens=0.0)
        # Simulate 1 second passing on the virtual clock.
        bucket.last_refill = clock["now"]
        clock["now"] += 1.0
        bucket._refill()
        assert bucket.tokens == pytest.approx(10.0)  # 10 tokens/sec × 1 sec, capped at capacity

    @pytest.mark.unit
    def test_refill_does_not_exceed_capacity(self, monkeypatch):
        """_refill() never exceeds bucket capacity."""
        clock = {"now": 1_000.0}
        monkeypatch.setattr(time, "time", lambda: clock["now"])

        bucket = TokenBucket(capacity=5, refill_rate=100.0, tokens=0.0)
        bucket.last_refill = clock["now"]
        clock["now"] += 10.0  # 10 seconds elapsed on the virtual clock
        bucket._refill()
        assert bucket.tokens == pytest.approx(5.0)

    @pytest.mark.unit
    def test_time_until_available_zero_when_tokens_present(self):
        """time_until_available() returns 0 when sufficient tokens exist."""
        bucket = TokenBucket(capacity=10, refill_rate=1.0, tokens=5.0)
        result = bucket.time_until_available(1)
        assert result == 0.0

    @pytest.mark.unit
    def test_time_until_available_calculates_wait(self):
        """time_until_available() returns correct wait time when bucket is empty."""
        bucket = TokenBucket(capacity=10, refill_rate=2.0, tokens=0.0)
        # Need 1 token at 2 tokens/sec → 0.5 sec
        result = bucket.time_until_available(1)
        assert result == pytest.approx(0.5, rel=0.1)

    @pytest.mark.unit
    def test_sequential_consumes_deplete_bucket(self):
        """Multiple consume() calls eventually exhaust the bucket."""
        bucket = TokenBucket(capacity=3, refill_rate=0.0, tokens=3.0)
        assert bucket.consume(1) is True
        assert bucket.consume(1) is True
        assert bucket.consume(1) is True
        assert bucket.consume(1) is False


# ============================================================================
# TenantRateLimiter
# ============================================================================


class TestTenantRateLimiter:
    """Unit tests for TenantRateLimiter."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_first_request_creates_full_bucket(self):
        """First request for an unknown tenant creates a full bucket and succeeds."""
        limiter = TenantRateLimiter()
        allowed = await limiter.check_rate_limit("tenant-new")
        assert allowed is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_different_tenants_are_isolated(self):
        """Each tenant gets its own independent bucket."""
        limiter = TenantRateLimiter()
        # Exhaust tenant-a's bucket
        with patch.object(limiter, "_capacity", 1), patch.object(limiter, "_refill_rate", 0.0):
            await limiter.check_rate_limit("tenant-a")
            await limiter.check_rate_limit("tenant-a")  # now empty
            # tenant-b should still have a full bucket
            allowed = await limiter.check_rate_limit("tenant-b")
        assert allowed is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_retry_after_unknown_tenant_returns_zero(self):
        """get_retry_after() returns 0 for a tenant with no bucket."""
        limiter = TenantRateLimiter()
        retry_after = await limiter.get_retry_after("unknown-tenant")
        assert retry_after == 0.0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_retry_after_depleted_tenant(self):
        """get_retry_after() returns positive wait time for a depleted bucket."""
        limiter = TenantRateLimiter()
        limiter._capacity = 1
        limiter._refill_rate = 1.0  # 1 token/sec
        # Exhaust the bucket
        await limiter.check_rate_limit("tenant-depleted")
        await limiter.check_rate_limit("tenant-depleted")
        retry_after = await limiter.get_retry_after("tenant-depleted")
        # Should be slightly less than 1 second (already consumed 1 at full rate)
        assert retry_after >= 0.0

    @pytest.mark.unit
    def test_get_bucket_state_unknown_tenant_returns_none(self):
        """get_bucket_state() returns None for tenants with no bucket yet."""
        limiter = TenantRateLimiter()
        assert limiter.get_bucket_state("nonexistent") is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_bucket_state_known_tenant(self):
        """get_bucket_state() returns correct state after first request."""
        limiter = TenantRateLimiter()
        await limiter.check_rate_limit("tenant-state")
        state = limiter.get_bucket_state("tenant-state")
        assert state is not None
        assert "tokens" in state
        assert "capacity" in state
        assert "refill_rate" in state
        assert state["capacity"] == limiter._capacity


# ============================================================================
# CircuitBreaker
# ============================================================================


class TestCircuitBreaker:
    """Unit tests for the CircuitBreaker."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_closed_circuit_allows_calls(self):
        """CLOSED circuit passes calls through normally."""
        breaker = CircuitBreaker(
            service_name="test-service",
            failure_threshold=3,
            recovery_timeout=60.0,
            half_open_max_calls=2,
        )

        async def success_func():
            return "ok"

        result = await breaker.call(success_func)
        assert result == "ok"
        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_failure_increments_counter(self):
        """Failed call increments failure counter."""
        breaker = CircuitBreaker(
            service_name="test-service",
            failure_threshold=5,
            recovery_timeout=60.0,
            half_open_max_calls=2,
        )

        async def failing_func():
            raise ValueError("service error")

        with pytest.raises(ValueError):
            await breaker.call(failing_func)

        assert breaker.failures == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_circuit_opens_after_threshold(self):
        """Circuit opens after hitting failure_threshold."""
        breaker = CircuitBreaker(
            service_name="test-service",
            failure_threshold=2,
            recovery_timeout=60.0,
            half_open_max_calls=2,
        )

        async def failing_func():
            raise RuntimeError("down")

        for _ in range(2):
            with pytest.raises(RuntimeError):
                await breaker.call(failing_func)

        assert breaker.state == CircuitState.OPEN

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_open_circuit_rejects_calls(self):
        """OPEN circuit raises CircuitBreakerOpen without calling the function."""
        breaker = CircuitBreaker(
            service_name="test-service",
            failure_threshold=1,
            recovery_timeout=60.0,
            half_open_max_calls=2,
        )

        async def failing_func():
            raise RuntimeError("down")

        # Trip the breaker
        with pytest.raises(RuntimeError):
            await breaker.call(failing_func)

        assert breaker.state == CircuitState.OPEN

        # Now it should reject calls
        called = []

        async def should_not_be_called():
            called.append(True)
            return "result"

        with pytest.raises(CircuitBreakerOpen):
            await breaker.call(should_not_be_called)

        assert not called

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_circuit_transitions_to_half_open_after_timeout(self, monkeypatch):
        """Circuit transitions to HALF_OPEN after recovery_timeout elapses."""
        clock = {"now": 1_000.0}
        monkeypatch.setattr(time, "time", lambda: clock["now"])

        breaker = CircuitBreaker(
            service_name="test-service",
            failure_threshold=1,
            recovery_timeout=0.01,  # 10 ms
            half_open_max_calls=2,
        )

        async def failing_func():
            raise RuntimeError("down")

        with pytest.raises(RuntimeError):
            await breaker.call(failing_func)

        assert breaker.state == CircuitState.OPEN

        # Advance past the recovery timeout on the virtual clock.
        clock["now"] += 1.0

        # Force state update via the public refresh seam.
        await breaker.refresh_state()

        assert breaker.state == CircuitState.HALF_OPEN

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_half_open_success_closes_circuit(self, monkeypatch):
        """A successful call in HALF_OPEN state closes the circuit."""
        clock = {"now": 1_000.0}
        monkeypatch.setattr(time, "time", lambda: clock["now"])

        breaker = CircuitBreaker(
            service_name="test-service",
            failure_threshold=1,
            recovery_timeout=0.01,
            half_open_max_calls=3,
        )

        async def failing_func():
            raise RuntimeError("down")

        async def success_func():
            return "recovered"

        # Trip breaker
        with pytest.raises(RuntimeError):
            await breaker.call(failing_func)

        # Advance past the recovery timeout on the virtual clock.
        clock["now"] += 1.0
        await breaker.refresh_state()
        assert breaker.state == CircuitState.HALF_OPEN

        # Call succeeds in half-open, closes circuit
        result = await breaker.call(success_func)
        assert result == "recovered"
        assert breaker.state == CircuitState.CLOSED
        assert breaker.failures == 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_half_open_failure_reopens_circuit(self, monkeypatch):
        """A failure in HALF_OPEN state re-opens the circuit."""
        clock = {"now": 1_000.0}
        monkeypatch.setattr(time, "time", lambda: clock["now"])

        breaker = CircuitBreaker(
            service_name="test-service",
            failure_threshold=1,
            recovery_timeout=0.01,
            half_open_max_calls=3,
        )

        async def failing_func():
            raise RuntimeError("still down")

        # Trip the breaker
        with pytest.raises(RuntimeError):
            await breaker.call(failing_func)

        # Advance past the recovery timeout on the virtual clock.
        clock["now"] += 1.0
        await breaker.refresh_state()
        assert breaker.state == CircuitState.HALF_OPEN

        # Fail again in half-open
        with pytest.raises(RuntimeError):
            await breaker.call(failing_func)

        assert breaker.state == CircuitState.OPEN

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_success_in_closed_resets_failure_count(self):
        """Successful call in CLOSED state resets failure counter."""
        breaker = CircuitBreaker(
            service_name="test-service",
            failure_threshold=5,
            recovery_timeout=60.0,
            half_open_max_calls=2,
        )

        async def failing_func():
            raise RuntimeError("fail")

        async def success_func():
            return "ok"

        # Fail twice
        for _ in range(2):
            with pytest.raises(RuntimeError):
                await breaker.call(failing_func)

        assert breaker.failures == 2

        # Succeed once — failures should reset
        await breaker.call(success_func)
        assert breaker.failures == 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_state_returns_correct_dict(self):
        """get_state() returns a dict with all expected keys."""
        breaker = CircuitBreaker(
            service_name="my-service",
            failure_threshold=3,
            recovery_timeout=30.0,
            half_open_max_calls=2,
        )
        state = breaker.get_state()
        assert state["service"] == "my-service"
        assert state["state"] == CircuitState.CLOSED.value
        assert state["failures"] == 0
        assert state["failure_threshold"] == 3
        assert state["half_open_max_calls"] == 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_circuit_breaker_open_exception_carries_metadata(self):
        """CircuitBreakerOpen exception contains service name and retry_after."""
        exc = CircuitBreakerOpen("my-service", 42.0)
        assert exc.service == "my-service"
        assert exc.retry_after == 42.0
        assert "my-service" in str(exc)
        assert "42" in str(exc)


# ============================================================================
# CircuitBreakerRegistry
# ============================================================================


class TestCircuitBreakerRegistry:
    """Unit tests for CircuitBreakerRegistry."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_breaker_creates_new_breaker(self):
        """get_breaker() creates a new CircuitBreaker for an unknown service."""
        registry = CircuitBreakerRegistry()
        breaker = await registry.get_breaker("openai")
        assert isinstance(breaker, CircuitBreaker)
        assert breaker.service_name == "openai"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_breaker_returns_same_instance(self):
        """get_breaker() returns the same instance on repeated calls."""
        registry = CircuitBreakerRegistry()
        breaker1 = await registry.get_breaker("openai")
        breaker2 = await registry.get_breaker("openai")
        assert breaker1 is breaker2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_breaker_isolates_services(self):
        """Different services get different CircuitBreaker instances."""
        registry = CircuitBreakerRegistry()
        breaker_a = await registry.get_breaker("service-a")
        breaker_b = await registry.get_breaker("service-b")
        assert breaker_a is not breaker_b

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_call_delegates_to_breaker(self):
        """registry.call() passes through to the underlying circuit breaker."""
        registry = CircuitBreakerRegistry()

        async def my_func():
            return "result"

        result = await registry.call("my-service", my_func)
        assert result == "result"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_all_states_returns_empty_initially(self):
        """get_all_states() returns an empty mapping when no breakers exist."""
        registry = CircuitBreakerRegistry()
        states = registry.get_all_states()
        # The return type is a TypedDictModel; verify it has no entries
        assert len(states) == 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_all_states_after_breakers_created(self):
        """get_all_states() includes all registered breakers."""
        registry = CircuitBreakerRegistry()
        await registry.get_breaker("svc-alpha")
        await registry.get_breaker("svc-beta")

        states = registry.get_all_states()
        assert "svc-alpha" in states
        assert "svc-beta" in states
        assert states["svc-alpha"]["state"] == CircuitState.CLOSED.value
        assert states["svc-beta"]["state"] == CircuitState.CLOSED.value

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_rate_limit_exceeded_exception_metadata(self):
        """RateLimitExceeded stores tenant_id and retry_after."""
        exc = RateLimitExceeded("tenant-xyz", 5.3)
        assert exc.tenant_id == "tenant-xyz"
        assert exc.retry_after_seconds == 5.3
        assert "tenant-xyz" in str(exc)
