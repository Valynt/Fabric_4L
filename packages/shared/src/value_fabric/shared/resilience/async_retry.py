"""Async retry helper with full-jitter exponential backoff.

Companion to :func:`sync_circuit_breaker.retry_transient` for async call
sites (e.g. the gateway delegation router, which uses ``httpx.AsyncClient``).
Mirrors the sync helper's classification: retry only when ``retry_on`` says so,
raise the last exception when attempts are exhausted.
"""

from __future__ import annotations

import asyncio
import logging
import random
from collections.abc import Awaitable, Callable
from typing import TypeVar

from ..error_handling import sanitize_log_error
from .sync_circuit_breaker import RetryableError

logger = logging.getLogger(__name__)

T = TypeVar("T")


async def retry_transient_async(
    func: Callable[..., Awaitable[T]],
    *args,
    max_attempts: int = 3,
    base_delay: float = 0.2,
    max_delay: float = 5.0,
    retry_on: Callable[[Exception], bool] | None = None,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    **kwargs,
) -> T:
    """Retry *func* on transient failures with full-jitter exponential backoff.

    Args:
        max_attempts: total attempts including the first (min 1).
        base_delay: base seconds for backoff schedule.
        max_delay: cap on the randomised sleep.
        retry_on: predicate returning True if the exception is transient. If
            None, only :class:`RetryableError` instances are retried.
        sleep: async sleep injection point for tests.

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
            return await func(*args, **kwargs)
        except Exception as exc:
            last_exc = exc
            is_retryable = retry_on(exc) if retry_on is not None else isinstance(exc, RetryableError)
            if not is_retryable:
                raise
            if attempt >= max_attempts:
                raise
            delay = min(max_delay, base_delay * (2 ** (attempt - 1)))
            jittered = random.uniform(0, delay)
            logger.debug(
                "retry_transient_async_retry",
                extra={
                    "attempt": attempt,
                    "delay": jittered,
                    "error_code": "RETRY_TRANSIENT_ASYNC",
                    "error": sanitize_log_error(exc),
                },
            )
            await sleep(jittered)
    raise RuntimeError("retry_transient_async exhausted without exception") from last_exc


__all__ = ["retry_transient_async"]
