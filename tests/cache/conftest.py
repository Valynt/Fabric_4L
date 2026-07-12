"""Cache test fixtures.

Provides ``make_redis_mock`` / ``mock_redis_client`` with sensible int defaults
for the Redis sorted-set and key/value operations used by
``value_fabric.shared.rate_limiting.tenant_rate_limiter.TenantRateLimiter``.

Without these defaults, ``AsyncMock`` returns unset child mocks for methods like
``zcard``/``zremrangebyscore``, causing ``TypeError: '>=' not supported between
instances of 'AsyncMock' and 'int'`` at ``tenant_rate_limiter.py:324`` and
fail-closed errors elsewhere. See
``reports/TEST_COVERAGE_RUBRIC_AUDIT_2026-05-12.md`` §8 M0-2.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from unittest.mock import AsyncMock

import pytest


def make_redis_mock() -> AsyncMock:
    """Return an ``AsyncMock`` for ``redis.asyncio.Redis`` with int defaults.

    Defaults cover every Redis method touched by the rate limiter and entity
    cache code paths under test. Individual tests may override any attribute
    (e.g. ``mock.zcount = custom_zcount``) before invoking the system under
    test — the override semantics match the prior per-test instantiation.
    """
    mock = AsyncMock()
    # Sorted-set ops used by TenantRateLimiter._check_window
    mock.zremrangebyscore = AsyncMock(return_value=0)
    mock.zcard = AsyncMock(return_value=0)
    mock.zcount = AsyncMock(return_value=0)
    mock.zrange = AsyncMock(return_value=[])
    mock.zadd = AsyncMock(return_value=1)
    # Key/value + admin ops used by reset paths and entity cache
    mock.expire = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=0)
    mock.keys = AsyncMock(return_value=[])
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.setex = AsyncMock(return_value=True)
    mock.exists = AsyncMock(return_value=0)
    mock.ttl = AsyncMock(return_value=-1)
    mock.incr = AsyncMock(return_value=1)
    mock.hset = AsyncMock(return_value=1)
    mock.hget = AsyncMock(return_value=None)
    mock.hdel = AsyncMock(return_value=0)
    return mock


@pytest.fixture
def mock_redis_client() -> AsyncMock:
    """Pytest fixture form of :func:`make_redis_mock`."""
    return make_redis_mock()


class DeterministicFakeRedis:
    """Deterministic async Redis test double with integer counter semantics.

    This adapter mirrors the integer return values from real Redis for counter-
    style operations such as ``INCR`` and sorted-set cardinality checks.
    """

    def __init__(self) -> None:
        self._kv: dict[str, bytes | str] = {}
        self._sorted_sets: dict[str, list[tuple[float, str]]] = defaultdict(list)
        self._counters: dict[str, int] = defaultdict(int)

    async def incr(self, key: str) -> int:
        self._counters[key] += 1
        return self._counters[key]

    async def zremrangebyscore(self, key: str, min: float, max: float) -> int:
        original = self._sorted_sets[key]
        retained = [item for item in original if not (min <= item[0] <= max)]
        self._sorted_sets[key] = retained
        return len(original) - len(retained)

    async def zcard(self, key: str) -> int:
        return len(self._sorted_sets[key])

    async def zrange(self, key: str, start: int, stop: int, withscores: bool = False):
        items = sorted(self._sorted_sets[key], key=lambda item: item[0])
        if stop == -1:
            window = items[start:]
        else:
            window = items[start : stop + 1]
        if withscores:
            return [(member, score) for score, member in window]
        return [member for score, member in window]

    async def zadd(self, key: str, mapping: dict[str, float]) -> int:
        added = 0
        members = {member for _, member in self._sorted_sets[key]}
        for member, score in mapping.items():
            if member not in members:
                added += 1
            self._sorted_sets[key].append((score, member))
        return added

    async def expire(self, key: str, ttl: int) -> bool:  # noqa: ARG002
        return True

    async def get(self, key: str):
        return self._kv.get(key)

    async def set(self, key: str, value, ex=None) -> bool:  # noqa: ANN001, ARG002
        self._kv[key] = value
        return True


@pytest.fixture
def deterministic_fake_redis() -> DeterministicFakeRedis:
    """Fixture providing deterministic Redis behavior for counter tests."""
    return DeterministicFakeRedis()
