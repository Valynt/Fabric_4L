"""Shared resilience patterns for Fabric_4L services.

P1-014: Circuit breaker standardization.
"""

from .circuit_breaker import CircuitBreaker, CircuitBreakerOpen, CircuitBreakerRegistry, CircuitState
from .sync_circuit_breaker import (
    TRANSIENT_STATUS_CODES,
    RetryableError,
    RetryExhausted,
    SyncCircuitBreaker,
    retry_transient,
)

# Alias so callers using the sync breaker can import a distinctly-named
# exception. The sync breaker raises this class; it is intentionally a
# separate type from the async ``CircuitBreakerOpen`` in
# ``circuit_breaker.py`` so callers know which breaker they are catching.
from .sync_circuit_breaker import CircuitBreakerOpen as SyncCircuitBreakerOpen
from .async_retry import retry_transient_async

__all__ = [
    "CircuitBreaker",
    "CircuitBreakerOpen",
    "CircuitBreakerRegistry",
    "CircuitState",
    "RetryExhausted",
    "RetryableError",
    "SyncCircuitBreaker",
    "SyncCircuitBreakerOpen",
    "TRANSIENT_STATUS_CODES",
    "retry_transient",
    "retry_transient_async",
]
