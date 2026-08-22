"""Tests for retry_transient_async."""

from __future__ import annotations

import pytest

from value_fabric.shared.resilience import (
    RetryableError,
    retry_transient_async,
)


class _Transient(RetryableError):
    pass


async def _sleep_zero(_: float) -> None:
    return None


@pytest.mark.asyncio
async def test_returns_on_first_success() -> None:
    calls = 0

    async def func() -> str:
        nonlocal calls
        calls += 1
        return "ok"

    result = await retry_transient_async(func, sleep=_sleep_zero)
    assert result == "ok"
    assert calls == 1


@pytest.mark.asyncio
async def test_retries_on_transient_then_succeeds() -> None:
    calls = 0

    async def func() -> str:
        nonlocal calls
        calls += 1
        if calls < 3:
            raise _Transient("boom")
        return "ok"

    def retry_on(exc: Exception) -> bool:
        return isinstance(exc, _Transient)

    result = await retry_transient_async(func, max_attempts=5, retry_on=retry_on, sleep=_sleep_zero)
    assert result == "ok"
    assert calls == 3


@pytest.mark.asyncio
async def test_raises_last_when_exhausted() -> None:
    calls = 0

    async def func() -> str:
        nonlocal calls
        calls += 1
        raise _Transient("boom")

    def retry_on(exc: Exception) -> bool:
        return isinstance(exc, _Transient)

    with pytest.raises(_Transient):
        await retry_transient_async(func, max_attempts=2, retry_on=retry_on, sleep=_sleep_zero)
    assert calls == 2


@pytest.mark.asyncio
async def test_non_transient_not_retried() -> None:
    calls = 0

    async def func() -> str:
        nonlocal calls
        calls += 1
        raise ValueError("nope")

    def retry_on(exc: Exception) -> bool:
        return isinstance(exc, _Transient)

    with pytest.raises(ValueError):
        await retry_transient_async(func, max_attempts=3, retry_on=retry_on, sleep=_sleep_zero)
    assert calls == 1


@pytest.mark.asyncio
async def test_invalid_max_attempts() -> None:
    async def func() -> str:
        return "ok"

    with pytest.raises(ValueError):
        await retry_transient_async(func, max_attempts=0)


@pytest.mark.asyncio
async def test_default_predicate_retries_retryable_error() -> None:
    calls = 0

    async def func() -> str:
        nonlocal calls
        calls += 1
        if calls < 2:
            raise RetryableError("boom")
        return "ok"

    result = await retry_transient_async(func, max_attempts=3, sleep=_sleep_zero)
    assert result == "ok"
    assert calls == 2
