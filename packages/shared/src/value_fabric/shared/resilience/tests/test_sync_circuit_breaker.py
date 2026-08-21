"""Tests for the sync circuit breaker and retry helper."""

from __future__ import annotations

import pytest

from ..sync_circuit_breaker import (
    TRANSIENT_STATUS_CODES,
    CircuitBreakerOpen,
    RetryableError,
    RetryExhausted,
    SyncCircuitBreaker,
    retry_transient,
)


def _ok() -> str:
    return "ok"


def _fail() -> str:
    raise RuntimeError("boom")


class TestSyncCircuitBreaker:
    def test_closed_allows_calls(self) -> None:
        breaker = SyncCircuitBreaker("svc", failure_threshold=3)
        assert breaker.call(_ok) == "ok"
        assert breaker.state == "closed"

    def test_opens_after_threshold_failures(self) -> None:
        breaker = SyncCircuitBreaker("svc", failure_threshold=2, recovery_timeout=300)
        with pytest.raises(RuntimeError):
            breaker.call(_fail)
        assert breaker.state == "closed"
        with pytest.raises(RuntimeError):
            breaker.call(_fail)
        assert breaker.state == "open"

    def test_open_rejects_immediately(self) -> None:
        breaker = SyncCircuitBreaker("svc", failure_threshold=1, recovery_timeout=300)
        with pytest.raises(RuntimeError):
            breaker.call(_fail)
        with pytest.raises(CircuitBreakerOpen) as exc_info:
            breaker.call(_ok)
        assert exc_info.value.service == "svc"
        assert exc_info.value.retry_after >= 0

    def test_half_open_after_recovery_timeout(self) -> None:
        breaker = SyncCircuitBreaker(
            "svc", failure_threshold=1, recovery_timeout=0.05
        )
        with pytest.raises(RuntimeError):
            breaker.call(_fail)
        assert breaker.state == "open"
        import time

        time.sleep(0.06)
        assert breaker.call(_ok) == "ok"
        assert breaker.state == "closed"

    def test_half_open_failure_reopens(self) -> None:
        breaker = SyncCircuitBreaker(
            "svc", failure_threshold=1, recovery_timeout=0.05
        )
        with pytest.raises(RuntimeError):
            breaker.call(_fail)
        assert breaker.state == "open"
        import time

        time.sleep(0.06)
        with pytest.raises(RuntimeError):
            breaker.call(_fail)
        assert breaker.state == "open"

    def test_success_resets_failures_in_closed_state(self) -> None:
        breaker = SyncCircuitBreaker("svc", failure_threshold=3)
        with pytest.raises(RuntimeError):
            breaker.call(_fail)
        breaker.call(_ok)
        assert breaker.get_state()["failures"] == 0

    def test_get_state_returns_dict(self) -> None:
        breaker = SyncCircuitBreaker("svc", failure_threshold=2)
        state = breaker.get_state()
        assert state["service"] == "svc"
        assert state["state"] == "closed"
        assert state["failures"] == 0
        assert state["failure_threshold"] == 2


class TestRetryTransient:
    def test_succeeds_first_try(self) -> None:
        calls: list[int] = []

        def func() -> str:
            calls.append(1)
            return "ok"

        result = retry_transient(func, max_attempts=3, sleep=lambda _: None)
        assert result == "ok"
        assert len(calls) == 1

    def test_retries_on_retryable_then_succeeds(self) -> None:
        calls: list[int] = []

        def func() -> str:
            calls.append(1)
            if len(calls) < 3:
                raise RetryableError("transient")
            return "ok"

        def retry_on(exc: Exception) -> bool:
            return isinstance(exc, RetryableError)

        result = retry_transient(
            func, max_attempts=3, sleep=lambda _: None, retry_on=retry_on
        )
        assert result == "ok"
        assert len(calls) == 3

    def test_non_retryable_raises_immediately(self) -> None:
        calls: list[int] = []

        def func() -> str:
            calls.append(1)
            raise ValueError("not retryable")

        def retry_on(exc: Exception) -> bool:
            return isinstance(exc, RetryableError)

        with pytest.raises(ValueError):
            retry_transient(
                func, max_attempts=3, sleep=lambda _: None, retry_on=retry_on
            )
        assert len(calls) == 1

    def test_exhausts_attempts_then_raises(self) -> None:
        calls: list[int] = []

        def func() -> str:
            calls.append(1)
            raise RetryableError("always transient")

        def retry_on(exc: Exception) -> bool:
            return isinstance(exc, RetryableError)

        with pytest.raises(RetryableError):
            retry_transient(
                func, max_attempts=3, sleep=lambda _: None, retry_on=retry_on
            )
        assert len(calls) == 3

    def test_sleep_called_with_backoff(self) -> None:
        sleeps: list[float] = []
        attempts: list[int] = []

        def func() -> str:
            attempts.append(1)
            if len(attempts) < 3:
                raise RetryableError("transient")
            return "ok"

        def retry_on(exc: Exception) -> bool:
            return isinstance(exc, RetryableError)

        retry_transient(
            func,
            max_attempts=3,
            base_delay=0.2,
            max_delay=5.0,
            sleep=lambda d: sleeps.append(d),
            retry_on=retry_on,
        )
        assert len(sleeps) == 2
        # Full jitter: each delay must be within [0, expected_max]
        assert 0 <= sleeps[0] <= 0.2
        assert 0 <= sleeps[1] <= 0.4


def test_transient_status_codes_contract() -> None:
    assert TRANSIENT_STATUS_CODES == frozenset({502, 503, 504, 429})
