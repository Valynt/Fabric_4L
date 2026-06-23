from __future__ import annotations

"""Resilience patterns for Layer 4 Agents.

P1-15: Token bucket rate limiting per tenant
P1-18: Circuit breaker for external service calls
"""


import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from value_fabric.shared.models.typed_dict import TypedDictModel

from .config.settings import get_settings


class CircuitBreakerRegistry_get_all_statesResult(TypedDictModel):
    pass


class TenantRateLimiter_get_bucket_stateResult(TypedDictModel):
    capacity: Any
    refill_rate: Any
    tokens: Any

class CircuitBreaker_get_stateResult(TypedDictModel):
    failure_threshold: Any
    failures: Any
    half_open_calls: Any
    half_open_max_calls: Any
    last_failure_time: Any
    service: Any
    state: Any

# ============================================================================
# P1-15: Token Bucket Rate Limiter
# ============================================================================


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded for a tenant."""

    def __init__(self, tenant_id: str, retry_after_seconds: float):
        self.tenant_id = tenant_id
        self.retry_after_seconds = retry_after_seconds
        super().__init__(
            f"Rate limit exceeded for tenant {tenant_id}. "
            f"Retry after {retry_after_seconds:.1f} seconds."
        )


@dataclass
class TokenBucket:
    """Token bucket for rate limiting.

    Attributes:
        capacity: Maximum tokens in bucket (burst size)
        refill_rate: Tokens added per second (requests per minute / 60)
        tokens: Current available tokens
        last_refill: Last timestamp tokens were refilled
    """

    capacity: int
    refill_rate: float
    tokens: float = field(default=0)
    last_refill: float = field(default_factory=time.time)

    def _refill(self) -> None:
        """Add tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(
            self.capacity,
            self.tokens + elapsed * self.refill_rate
        )
        self.last_refill = now

    def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens from bucket.

        Returns:
            True if tokens consumed, False if insufficient tokens
        """
        self._refill()
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    def time_until_available(self, tokens: int = 1) -> float:
        """Calculate time until requested tokens are available."""
        self._refill()
        if self.tokens >= tokens:
            return 0.0
        needed = tokens - self.tokens
        return needed / self.refill_rate


class TenantRateLimiter:
    """P1-15: Per-tenant rate limiter using token buckets.

    Configured via settings:
        - rate_limit_requests_per_minute: 100 default
        - rate_limit_burst_size: 20 default

    Usage:
        limiter = TenantRateLimiter()
        if not limiter.check_rate_limit(tenant_id):
            raise RateLimitExceeded(tenant_id, limiter.get_retry_after(tenant_id))
    """

    def __init__(self):
        self._buckets: dict[str, TokenBucket] = {}
        self._lock = asyncio.Lock()
        self._capacity = get_settings().rate_limit_burst_size
        self._refill_rate = get_settings().rate_limit_requests_per_minute / 60.0

    async def check_rate_limit(self, tenant_id: str) -> bool:
        """Check if request is within rate limit for tenant.

        Returns:
            True if request allowed, False if rate limited
        """
        async with self._lock:
            bucket = self._buckets.get(tenant_id)
            if bucket is None:
                bucket = TokenBucket(
                    capacity=self._capacity,
                    refill_rate=self._refill_rate,
                    tokens=self._capacity  # Start with full bucket
                )
                self._buckets[tenant_id] = bucket
            return bucket.consume(1)

    async def get_retry_after(self, tenant_id: str) -> float:
        """Get seconds until next request is allowed."""
        async with self._lock:
            bucket = self._buckets.get(tenant_id)
            if bucket is None:
                return 0.0
            return bucket.time_until_available(1)

    def get_bucket_state(self, tenant_id: str) -> dict | None:
        """Get current bucket state for monitoring."""
        bucket = self._buckets.get(tenant_id)
        if bucket is None:
            return None
        return TenantRateLimiter_get_bucket_stateResult.model_validate({
            "tokens": bucket.tokens,
            "capacity": bucket.capacity,
            "refill_rate": bucket.refill_rate,
        })


# ============================================================================
# P1-18: Circuit Breaker
# ============================================================================


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject calls
    HALF_OPEN = "half_open"  # Testing if recovered


class CircuitBreakerOpen(Exception):
    """Raised when circuit breaker is open."""

    def __init__(self, service: str, retry_after: float):
        self.service = service
        self.retry_after = retry_after
        super().__init__(
            f"Circuit breaker open for {service}. "
            f"Retry after {retry_after:.1f} seconds."
        )


@dataclass
class CircuitBreaker:
    """P1-18: Circuit breaker for external service resilience.

    Configured via settings:
        - circuit_breaker_failure_threshold: 5 failures to open
        - circuit_breaker_recovery_timeout_seconds: 60s before half-open
        - circuit_breaker_half_open_max_calls: 3 test calls

    Usage:
        breaker = CircuitBreaker("openai")
        try:
            result = await breaker.call(openai_client.complete, prompt)
        except CircuitBreakerOpen:
            # Use fallback
    """

    service_name: str
    failure_threshold: int = field(default_factory=lambda: get_settings().circuit_breaker_failure_threshold)
    recovery_timeout: float = field(default_factory=lambda: get_settings().circuit_breaker_recovery_timeout_seconds)
    half_open_max_calls: int = field(default_factory=lambda: get_settings().circuit_breaker_half_open_max_calls)

    state: CircuitState = field(default=CircuitState.CLOSED)
    failures: int = field(default=0)
    last_failure_time: float = field(default=0)
    half_open_calls: int = field(default=0)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection.

        Args:
            func: Async function to call
            *args, **kwargs: Arguments to pass to function

        Returns:
            Function result

        Raises:
            CircuitBreakerOpen: If circuit is open
            Exception: Original exception if call fails
        """
        async with self._lock:
            await self._update_state()

            if self.state == CircuitState.OPEN:
                retry_after = self.recovery_timeout - (time.time() - self.last_failure_time)
                raise CircuitBreakerOpen(self.service_name, max(0, retry_after))

            if self.state == CircuitState.HALF_OPEN:
                if self.half_open_calls >= self.half_open_max_calls:
                    retry_after = self.recovery_timeout - (time.time() - self.last_failure_time)
                    raise CircuitBreakerOpen(self.service_name, max(0, retry_after))
                self.half_open_calls += 1

        # Execute call outside lock
        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
        except asyncio.CancelledError:
            raise
        except Exception:
            await self._on_failure()
            raise

    async def _update_state(self) -> None:
        """Update circuit state based on time and failures."""
        if self.state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                self.half_open_calls = 0

    async def _on_success(self) -> None:
        """Record successful call."""
        async with self._lock:
            if self.state == CircuitState.HALF_OPEN:
                # Success in half-open closes the circuit
                self.state = CircuitState.CLOSED
                self.failures = 0
                self.half_open_calls = 0
            else:
                # Reset failures on success in closed state
                self.failures = 0

    async def _on_failure(self) -> None:
        """Record failed call."""
        async with self._lock:
            self.failures += 1
            self.last_failure_time = time.time()

            if self.state == CircuitState.HALF_OPEN:
                # Failure in half-open reopens circuit
                self.state = CircuitState.OPEN
            elif self.failures >= self.failure_threshold:
                # Exceeded threshold, open circuit
                self.state = CircuitState.OPEN

    def get_state(self) -> dict:
        """Get current circuit state for monitoring."""
        return CircuitBreaker_get_stateResult.model_validate({
            "service": self.service_name,
            "state": self.state.value,
            "failures": self.failures,
            "failure_threshold": self.failure_threshold,
            "last_failure_time": self.last_failure_time,
            "half_open_calls": self.half_open_calls,
            "half_open_max_calls": self.half_open_max_calls,
        })


class CircuitBreakerRegistry:
    """Registry for circuit breakers by service."""

    def __init__(self):
        self._breakers: dict[str, CircuitBreaker] = {}
        self._lock = asyncio.Lock()

    async def get_breaker(self, service_name: str) -> CircuitBreaker:
        """Get or create circuit breaker for service."""
        async with self._lock:
            if service_name not in self._breakers:
                self._breakers[service_name] = CircuitBreaker(service_name)
            return self._breakers[service_name]

    async def call(self, service_name: str, func: Callable, *args, **kwargs):
        """Call function with circuit breaker for service."""
        breaker = await self.get_breaker(service_name)
        return await breaker.call(func, *args, **kwargs)

    def get_all_states(self) -> dict[str, dict]:
        """Get states of all circuit breakers."""
        return CircuitBreakerRegistry_get_all_statesResult.model_validate({
            name: breaker.get_state()
            for name, breaker in self._breakers.items()
        })


# Global instances
tenant_rate_limiter = TenantRateLimiter()
circuit_breaker_registry = CircuitBreakerRegistry()
