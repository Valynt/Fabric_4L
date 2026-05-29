from __future__ import annotations

"""Resilience ports for OSS-0 substitution scaffolding.

The interfaces intentionally separate Fabric-owned tenant fairness from generic
dependency circuit-breaking. Legacy adapters delegate to the current implementations
so defaults remain unchanged.
"""


from collections.abc import Callable
from typing import Any, Protocol, runtime_checkable

from .resilience import CircuitBreaker, TenantRateLimiter


@runtime_checkable
class TenantRateLimitPort(Protocol):
    """Fabric-owned tenant fairness contract."""

    async def check_rate_limit(self, tenant_id: str) -> bool:
        """Return whether the tenant has capacity for another request."""

    async def get_retry_after(self, tenant_id: str) -> float:
        """Return seconds until the tenant can make another request."""

    def get_bucket_state(self, tenant_id: str) -> dict | None:
        """Return the tenant bucket monitoring shape, or ``None`` if unseen."""


@runtime_checkable
class DependencyCircuitBreakerPort(Protocol):
    """Generic dependency-resilience contract for outbound calls."""

    async def call(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute a dependency call through breaker protection."""

    def get_state(self) -> dict[str, Any]:
        """Return the current circuit-breaker monitoring shape."""


class LegacyTenantRateLimitAdapter:
    """TenantRateLimitPort adapter around the current TenantRateLimiter."""

    def __init__(self, limiter: TenantRateLimiter) -> None:
        self._limiter = limiter

    async def check_rate_limit(self, tenant_id: str) -> bool:
        return await self._limiter.check_rate_limit(tenant_id)

    async def get_retry_after(self, tenant_id: str) -> float:
        return await self._limiter.get_retry_after(tenant_id)

    def get_bucket_state(self, tenant_id: str) -> dict | None:
        return self._limiter.get_bucket_state(tenant_id)


class LegacyCircuitBreakerAdapter:
    """DependencyCircuitBreakerPort adapter around the current CircuitBreaker."""

    def __init__(self, breaker: CircuitBreaker) -> None:
        self._breaker = breaker

    async def call(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        return await self._breaker.call(func, *args, **kwargs)

    def get_state(self) -> dict[str, Any]:
        return self._breaker.get_state()


def as_tenant_rate_limit_port(limiter: TenantRateLimiter) -> TenantRateLimitPort:
    """Return the legacy limiter through the tenant-fairness port."""

    return LegacyTenantRateLimitAdapter(limiter)


def as_dependency_circuit_breaker_port(
    breaker: CircuitBreaker,
) -> DependencyCircuitBreakerPort:
    """Return the legacy breaker through the dependency-resilience port."""

    return LegacyCircuitBreakerAdapter(breaker)
