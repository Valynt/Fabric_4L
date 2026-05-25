"""Circuit breaker pattern implementation for external service resilience.

P0-01: Prevents cascading failures by breaking connections to failing services.
Supports HTTPX, Playwright, and Redis clients with configurable thresholds.
"""

import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable

import structlog
from pybreaker import CircuitBreaker, CircuitBreakerError

from ..metrics.prometheus_metrics import get_metrics

logger = structlog.get_logger()


class CircuitBreakerState(str, Enum):
    """Circuit breaker states for monitoring."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Circuit broken, rejecting calls
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker instances."""

    failure_threshold: int = 5  # Failures before opening
    recovery_timeout: int = 30  # Seconds before attempting recovery
    expected_exception: type[Exception] | tuple[type[Exception], ...] = Exception
    name: str = "default"


class CircuitBreakerManager:
    """Manages circuit breakers for external services."""

    def __init__(self):
        self._breakers: dict[str, CircuitBreaker] = {}
        self._configs: dict[str, CircuitBreakerConfig] = {}
        self.metrics = get_metrics()

    def create_breaker(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 30,
        expected_exception: type[Exception] | tuple[type[Exception], ...] = Exception,
    ) -> CircuitBreaker:
        """Create or retrieve a circuit breaker.

        Args:
            name: Unique identifier for the circuit breaker
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            expected_exception: Exception types that count as failures

        Returns:
            CircuitBreaker instance
        """
        if name in self._breakers:
            return self._breakers[name]

        config = CircuitBreakerConfig(
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            expected_exception=expected_exception,
            name=name,
        )
        self._configs[name] = config

        breaker = CircuitBreaker(
            fail_max=failure_threshold,
            reset_timeout=recovery_timeout,
            expected_exception=expected_exception,
        )

        # Add state change monitoring
        breaker.add_listener(_CircuitBreakerListener(name, self.metrics))

        self._breakers[name] = breaker
        logger.info(
            "Circuit breaker created",
            name=name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
        )

        return breaker

    def get_breaker(self, name: str) -> CircuitBreaker | None:
        """Get existing circuit breaker by name."""
        return self._breakers.get(name)

    def get_state(self, name: str) -> CircuitBreakerState:
        """Get current state of a circuit breaker."""
        breaker = self.get_breaker(name)
        if not breaker:
            return CircuitBreakerState.CLOSED

        if breaker.open:
            return CircuitBreakerState.OPEN
        elif breaker.half_open:
            return CircuitBreakerState.HALF_OPEN
        else:
            return CircuitBreakerState.CLOSED

    def reset(self, name: str) -> None:
        """Manually reset a circuit breaker to closed state."""
        breaker = self.get_breaker(name)
        if breaker:
            breaker._state = CircuitBreaker._CLOSED_STATE
            breaker._failure_count = 0
            logger.info("Circuit breaker manually reset", name=name)


class _CircuitBreakerListener:
    """Listener for circuit breaker state changes for metrics."""

    def __init__(self, name: str, metrics: Any):
        self.name = name
        self.metrics = metrics

    def state_change(self, old_state: str, new_state: str) -> None:
        """Handle circuit breaker state changes."""
        logger.info(
            "Circuit breaker state changed",
            name=self.name,
            old_state=old_state,
            new_state=new_state,
        )

        # Emit metric for state change
        if self.metrics and self.metrics.config.enabled:
            # Track circuit breaker opens as failures
            if new_state == "open":
                self.metrics._metrics["circuit_breaker_opens_total"].labels(
                    service=self.name
                ).inc()


# Global circuit breaker manager instance
_circuit_breaker_manager = CircuitBreakerManager()


def get_circuit_breaker_manager() -> CircuitBreakerManager:
    """Get the global circuit breaker manager instance."""
    return _circuit_breaker_manager


def with_circuit_breaker(
    service_name: str,
    failure_threshold: int = 5,
    recovery_timeout: int = 30,
    expected_exception: type[Exception] | tuple[type[Exception], ...] = Exception,
):
    """Decorator to apply circuit breaker to a function.

    Args:
        service_name: Name of the service for circuit breaker identification
        failure_threshold: Number of failures before opening circuit
        recovery_timeout: Seconds to wait before attempting recovery
        expected_exception: Exception types that count as failures

    Example:
        @with_circuit_breaker("httpx_client", failure_threshold=5, recovery_timeout=30)
        async def fetch_url(url: str) -> str:
            return await httpx.get(url).text
    """

    def decorator(func: Callable) -> Callable:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            manager = get_circuit_breaker_manager()
            breaker = manager.create_breaker(
                name=service_name,
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout,
                expected_exception=expected_exception,
            )

            try:
                return breaker.call(func, *args, **kwargs)
            except CircuitBreakerError:
                logger.warning(
                    "Circuit breaker open, call rejected",
                    service=service_name,
                    function=func.__name__,
                )
                raise

        return wrapper

    return decorator
