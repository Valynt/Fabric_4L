"""Sync circuit breaker and retry helper for synchronous HTTP clients.

The async :class:`CircuitBreaker` in ``circuit_breaker.py`` serves the async
service-to-service clients. The gateway's ``Layer4OrchestrationClient`` is
synchronous (it projects state into a sync in-memory store), so this module
provides a thread-safe sync equivalent plus a retry-with-exponential-backoff
helper that classifies transient vs. deterministic failures.

Design notes:
- Transient failures (connect errors, 502/503/504) trip the breaker and are
  retried with full jitter exponential backoff.
- Deterministic failures (4xx other than 429) do NOT trip the breaker and are
  not retried — they surface immediately as dependency errors.
- The breaker is process-local: each gateway replica has its own state. For
  cross-repo coordination, the Redis-backed breaker in
  ``redis_circuit_breaker.py`` is the authoritative path (see P2-003).
"""

from __future__ import annotations

import logging
import random
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TypeVar

from ..error_handling import sanitize_log_error

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Status codes that indicate a transient upstream failure worth retrying.
TRANSIENT_STATUS_CODES: frozenset[int] = frozenset({502, 503, 504, 429})


class CircuitBreakerOpen(Exception):
    """Raised when the sync circuit breaker is open."""

    def __init__(self, service: str, retry_after: float) -> None:
        self.service = service
        self.retry_after = retry_after
        super().__init__(
            f"Circuit breaker open for {service}. "
            f"Retry after {retry_after:.1f}s."
        )


class RetryExhausted(Exception):
    """Raised when all retry attempts fail."""


@dataclass
class SyncCircuitBreaker:
    """Thread-safe sync circuit breaker with CLOSED → OPEN → HALF_OPEN.

    Unlike the async breaker, this uses a ``threading.Lock`` so it is safe to
    call from sync code paths that may be invoked from multiple worker
    threads (e.g. a sync FastAPI route offloaded via ``run_in_threadpool``).
    """

    service_name: str
    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    half_open_max_calls: int = 3

    _state: str = "closed"
    _failures: int = 0
    _last_failure_time: float = 0.0
    _half_open_calls: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock)

    @property
    def state(self) -> str:
        return self._state

    def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute *func* with circuit-breaker protection.

        Raises:
            CircuitBreakerOpen: when OPEN or HALF_OPEN quota exhausted.
            Exception: the original exception from *func*.
        """
        with self._lock:
            self._update_state_locked()
            if self._state == "open":
                retry_after = self.recovery_timeout - (
                    time.time() - self._last_failure_time
                )
                raise CircuitBreakerOpen(self.service_name, max(0.0, retry_after))
            if self._state == "half_open":
                if self._half_open_calls >= self.half_open_max_calls:
                    retry_after = self.recovery_timeout - (
                        time.time() - self._last_failure_time
                    )
                    raise CircuitBreakerOpen(self.service_name, max(0.0, retry_after))
                self._half_open_calls += 1

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception:
            self._on_failure()
            raise

    def _update_state_locked(self) -> None:
        if self._state == "open":
            if time.time() - self._last_failure_time >= self.recovery_timeout:
                self._state = "half_open"
                self._half_open_calls = 0
                logger.info(
                    "sync_circuit_breaker_half_open",
                    extra={"service": self.service_name},
                )

    def _on_success(self) -> None:
        with self._lock:
            if self._state == "half_open":
                self._state = "closed"
                self._failures = 0
                self._half_open_calls = 0
                logger.info(
                    "sync_circuit_breaker_closed",
                    extra={"service": self.service_name},
                )
            else:
                self._failures = 0

    def _on_failure(self) -> None:
        with self._lock:
            self._failures += 1
            self._last_failure_time = time.time()
            if self._state == "half_open":
                self._state = "open"
                logger.warning(
                    "sync_circuit_breaker_reopened",
                    extra={"service": self.service_name, "failures": self._failures},
                )
            elif self._failures >= self.failure_threshold:
                self._state = "open"
                logger.warning(
                    "sync_circuit_breaker_opened",
                    extra={
                        "service": self.service_name,
                        "failures": self._failures,
                        "threshold": self.failure_threshold,
                    },
                )

    def get_state(self) -> dict[str, str | int | float]:
        with self._lock:
            return {
                "service": self.service_name,
                "state": self._state,
                "failures": self._failures,
                "failure_threshold": self.failure_threshold,
                "last_failure_time": self._last_failure_time,
                "half_open_calls": self._half_open_calls,
                "half_open_max_calls": self.half_open_max_calls,
            }


def retry_transient(
    func: Callable[..., T],
    *args,
    max_attempts: int = 3,
    base_delay: float = 0.2,
    max_delay: float = 5.0,
    retry_on: Callable[[Exception], bool] | None = None,
    sleep: Callable[[float], None] = time.sleep,
    **kwargs,
) -> T:
    """Retry *func* on transient failures with full-jitter exponential backoff.

    Args:
        max_attempts: total attempts including the first (min 1).
        base_delay: base seconds for backoff schedule.
        max_delay: cap on the randomised sleep.
        retry_on: predicate returning True if the exception is transient. If
            None, only :class:`RetryableError` instances are retried.
        sleep: injection point for tests (defaults to ``time.sleep``).

    Returns:
        The result of the first successful call.

    Raises:
        Exception: the last exception if all attempts fail.
    """
    if max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")

    last_exc: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            last_exc = exc
            is_retryable = (
                retry_on(exc) if retry_on is not None else isinstance(exc, RetryableError)
            )
            if not is_retryable:
                raise
            if attempt >= max_attempts:
                raise
            delay = min(max_delay, base_delay * (2 ** (attempt - 1)))
            jittered = random.uniform(0, delay)
            logger.debug(
                "retry_transient_retry",
                extra={
                    "attempt": attempt,
                    "delay": jittered,
                    "error_code": "RETRY_TRANSIENT",
                    "error": sanitize_log_error(exc),
                },
            )
            sleep(jittered)
    raise RetryExhausted() from last_exc


class RetryableError(Exception):
    """Marker exception: subclasses indicate a retryable failure.

    Concrete clients wrap transient upstream failures in this type so
    :func:`retry_transient` retries them without a custom predicate.
    """


__all__ = [
    "TRANSIENT_STATUS_CODES",
    "CircuitBreakerOpen",
    "RetryExhausted",
    "RetryableError",
    "SyncCircuitBreaker",
    "retry_transient",
]
