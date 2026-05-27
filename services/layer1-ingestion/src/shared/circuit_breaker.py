"""Circuit breaker pattern implementation for external service resilience.

P0-01: Prevents cascading failures by breaking connections to failing services.
Supports HTTPX, Playwright, and Redis clients with configurable thresholds.
"""

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

import structlog

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
    success_threshold: int = 2  # Successes in half-open to close circuit


@dataclass
class CircuitBreakerStateData:
    """Internal state for circuit breaker."""

    failure_count: int = 0
    last_failure_time: float = 0.0
    state: CircuitBreakerState = CircuitBreakerState.CLOSED
    success_count: int = 0  # Successes in half-open state


class AsyncCircuitBreaker:
    """Async-compatible circuit breaker implementation."""

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 30,
        expected_exception: type[Exception] | tuple[type[Exception], ...] = Exception,
        success_threshold: int = 2,
    ):
        self.name = name
        self.config = CircuitBreakerConfig(
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            expected_exception=expected_exception,
            name=name,
            success_threshold=success_threshold,
        )
        self._state = CircuitBreakerStateData()
        self._lock = asyncio.Lock()
        self.metrics = get_metrics()

    async def call(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        """Execute function with circuit breaker protection.

        Args:
            func: Async function to call
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerError: If circuit is open
            Exception: If function raises an exception
        """
        # Hold lock for entire operation to prevent race conditions
        async with self._lock:
            # Check if circuit is open and recovery timeout has passed
            if self._state.state == CircuitBreakerState.OPEN:
                if time.time() - self._state.last_failure_time > self.config.recovery_timeout:
                    logger.info("Circuit breaker transitioning to half-open", name=self.name)
                    self._state.state = CircuitBreakerState.HALF_OPEN
                    self._state.success_count = 0
                else:
                    raise CircuitBreakerError(
                        f"Circuit breaker '{self.name}' is open, rejecting call"
                    )

            # Call function while holding lock to prevent concurrent state transitions
            try:
                result = await func(*args, **kwargs)
                
                # Handle success path
                if self._state.state == CircuitBreakerState.HALF_OPEN:
                    self._state.success_count += 1
                    if self._state.success_count >= self.config.success_threshold:
                        logger.info("Circuit breaker closing after successful recovery", name=self.name)
                        self._state.state = CircuitBreakerState.CLOSED
                        self._state.failure_count = 0
                elif self._state.state == CircuitBreakerState.CLOSED:
                    self._state.failure_count = 0  # Reset on success
                
                return result

            except self.config.expected_exception as e:
                self._state.failure_count += 1
                self._state.last_failure_time = time.time()

                if self._state.failure_count >= self.config.failure_threshold:
                    if self._state.state != CircuitBreakerState.OPEN:
                        logger.warning(
                            "Circuit breaker opening",
                            name=self.name,
                            failure_count=self._state.failure_count,
                            threshold=self.config.failure_threshold,
                        )
                        self._state.state = CircuitBreakerState.OPEN
                        if self.metrics and self.metrics.config.enabled:
                            self.metrics._metrics["circuit_breaker_opens_total"].labels(
                                service=self.name
                            ).inc()
                elif self._state.state == CircuitBreakerState.HALF_OPEN:
                    # Failed in half-open, reopen immediately
                    logger.warning("Circuit breaker reopening after half-open failure", name=self.name)
                    self._state.state = CircuitBreakerState.OPEN

                raise

    def get_state(self) -> CircuitBreakerState:
        """Get current circuit breaker state."""
        return self._state.state

    def reset(self) -> None:
        """Manually reset circuit breaker to closed state."""
        self._state = CircuitBreakerStateData()
        logger.info("Circuit breaker manually reset", name=self.name)


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open and rejects a call."""
    pass


class CircuitBreakerManager:
    """Manages circuit breakers for external services."""

    def __init__(self):
        self._breakers: dict[str, AsyncCircuitBreaker] = {}

    def create_breaker(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 30,
        expected_exception: type[Exception] | tuple[type[Exception], ...] = Exception,
        success_threshold: int = 2,
    ) -> AsyncCircuitBreaker:
        """Create or retrieve a circuit breaker.

        Args:
            name: Unique identifier for the circuit breaker
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            expected_exception: Exception types that count as failures
            success_threshold: Successes in half-open state to close circuit

        Returns:
            AsyncCircuitBreaker instance
        """
        if name in self._breakers:
            return self._breakers[name]

        breaker = AsyncCircuitBreaker(
            name=name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            expected_exception=expected_exception,
            success_threshold=success_threshold,
        )

        self._breakers[name] = breaker
        logger.info(
            "Circuit breaker created",
            name=name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            success_threshold=success_threshold,
        )

        return breaker

    def get_breaker(self, name: str) -> AsyncCircuitBreaker | None:
        """Get existing circuit breaker by name."""
        return self._breakers.get(name)

    def get_state(self, name: str) -> CircuitBreakerState:
        """Get current state of a circuit breaker."""
        breaker = self.get_breaker(name)
        if not breaker:
            return CircuitBreakerState.CLOSED
        return breaker.get_state()

    def reset(self, name: str) -> None:
        """Manually reset a circuit breaker to closed state."""
        breaker = self.get_breaker(name)
        if breaker:
            breaker.reset()


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
    success_threshold: int = 2,
):
    """Decorator to apply circuit breaker to an async function.

    Args:
        service_name: Name of the service for circuit breaker identification
        failure_threshold: Number of failures before opening circuit
        recovery_timeout: Seconds to wait before attempting recovery
        expected_exception: Exception types that count as failures
        success_threshold: Successes in half-open state to close circuit

    Example:
        @with_circuit_breaker("httpx_client", failure_threshold=5, recovery_timeout=30)
        async def fetch_url(url: str) -> str:
            return await httpx.get(url).text
    """

    def decorator(func: Callable) -> Callable:
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            manager = get_circuit_breaker_manager()
            breaker = manager.create_breaker(
                name=service_name,
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout,
                expected_exception=expected_exception,
                success_threshold=success_threshold,
            )

            try:
                return await breaker.call(func, *args, **kwargs)
            except CircuitBreakerError:
                logger.warning(
                    "Circuit breaker open, call rejected",
                    service=service_name,
                    function=func.__name__,
                )
                raise

        return wrapper

    return decorator

