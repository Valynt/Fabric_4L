"""Shared circuit breaker for external service resilience (P1-014).

Extracted from Layer 4's proven implementation and made settings-agnostic
so any service can adopt the same pattern without layer coupling.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


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
    """Async circuit breaker with CLOSED → OPEN → HALF_OPEN lifecycle.

    Usage::

        breaker = CircuitBreaker("downstream-service", failure_threshold=5)
        try:
            result = await breaker.call(http_client.post, url, json=payload)
        except CircuitBreakerOpen:
            # Fallback — circuit is open
            return cached_value
    """

    service_name: str
    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    half_open_max_calls: int = 3

    state: CircuitState = field(default=CircuitState.CLOSED)
    failures: int = field(default=0)
    last_failure_time: float = field(default=0)
    half_open_calls: int = field(default=0)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def call(self, func: Callable, *args, **kwargs):
        """Execute *func* with circuit-breaker protection.

        Raises:
            CircuitBreakerOpen: when the circuit is OPEN or HALF_OPEN quota
                is exhausted.
            Exception: the original exception raised by *func*.
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

        # Execute call outside lock so concurrent attempts are not serialized
        # by the breaker state machine (only state transitions are guarded).
        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
        except Exception:
            await self._on_failure()
            raise

    async def _update_state(self) -> None:
        """Transition OPEN → HALF_OPEN when recovery timeout expires."""
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                self.half_open_calls = 0
                logger.info(
                    "circuit_breaker_half_open",
                    extra={"service": self.service_name},
                )

    async def _on_success(self) -> None:
        """Record successful call and close circuit if in HALF_OPEN."""
        async with self._lock:
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.CLOSED
                self.failures = 0
                self.half_open_calls = 0
                logger.info(
                    "circuit_breaker_closed",
                    extra={"service": self.service_name},
                )
            else:
                self.failures = 0

    async def _on_failure(self) -> None:
        """Record failed call and open circuit if threshold exceeded."""
        async with self._lock:
            self.failures += 1
            self.last_failure_time = time.time()

            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.OPEN
                logger.warning(
                    "circuit_breaker_reopened",
                    extra={"service": self.service_name, "failures": self.failures},
                )
            elif self.failures >= self.failure_threshold:
                self.state = CircuitState.OPEN
                logger.warning(
                    "circuit_breaker_opened",
                    extra={
                        "service": self.service_name,
                        "failures": self.failures,
                        "threshold": self.failure_threshold,
                    },
                )

    def get_state(self) -> dict[str, Any]:
        """Return current circuit state for health probes and metrics."""
        return {
            "service": self.service_name,
            "state": self.state.value,
            "failures": self.failures,
            "failure_threshold": self.failure_threshold,
            "last_failure_time": self.last_failure_time,
            "half_open_calls": self.half_open_calls,
            "half_open_max_calls": self.half_open_max_calls,
        }


class CircuitBreakerRegistry:
    """Registry for named circuit breakers."""

    def __init__(self):
        self._breakers: dict[str, CircuitBreaker] = {}
        self._lock = asyncio.Lock()

    async def get_breaker(self, service_name: str, **kwargs) -> CircuitBreaker:
        """Get or create a circuit breaker for *service_name*."""
        async with self._lock:
            if service_name not in self._breakers:
                self._breakers[service_name] = CircuitBreaker(service_name, **kwargs)
            return self._breakers[service_name]

    async def call(self, service_name: str, func: Callable, *args, **kwargs):
        """Convenience wrapper: call *func* through the named breaker."""
        breaker = await self.get_breaker(service_name)
        return await breaker.call(func, *args, **kwargs)

    def get_all_states(self) -> dict[str, dict[str, Any]]:
        """Return states of all registered breakers."""
        return {
            name: breaker.get_state()
            for name, breaker in self._breakers.items()
        }
