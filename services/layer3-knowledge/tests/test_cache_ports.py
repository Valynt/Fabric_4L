from __future__ import annotations

"""OSS-0 tests for the L3 cache port and legacy adapter."""


from typing import Any

import pytest

from value_fabric.layer3.cache.ports import CachePort, LegacyCacheAdapter, as_cache_port


class SpyCache:
    """Small spy that exposes the RedisCache public methods used by the adapter."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[Any, ...]]] = []

    async def get(self, key: str) -> Any | None:
        self.calls.append(("get", (key,)))
        return {"key": key}

    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        self.calls.append(("set", (key, value, ttl)))
        return True

    async def delete(self, key: str) -> bool:
        self.calls.append(("delete", (key,)))
        return True

    async def clear_pattern(self, pattern: str) -> int:
        self.calls.append(("clear_pattern", (pattern,)))
        return 2

    async def exists(self, key: str) -> bool:
        self.calls.append(("exists", (key,)))
        return True

    async def increment(self, key: str, amount: int = 1, ttl: int | None = None) -> int:
        self.calls.append(("increment", (key, amount, ttl)))
        return 7

    async def get_stats(self) -> dict[str, Any]:
        self.calls.append(("get_stats", ()))
        return {"connected_clients": 1}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_legacy_cache_adapter_delegates_current_cache_contract() -> None:
    spy = SpyCache()
    adapter = LegacyCacheAdapter(spy)  # type: ignore[arg-type]

    assert isinstance(adapter, CachePort)
    assert await adapter.get("a") == {"key": "a"}
    assert await adapter.set("a", {"value": 1}, ttl=30) is True
    assert await adapter.delete("a") is True
    assert await adapter.clear_pattern("tenant:*") == 2
    assert await adapter.exists("b") is True
    assert await adapter.increment("count", amount=3, ttl=60) == 7
    assert await adapter.get_stats() == {"connected_clients": 1}

    assert spy.calls == [
        ("get", ("a",)),
        ("set", ("a", {"value": 1}, 30)),
        ("delete", ("a",)),
        ("clear_pattern", ("tenant:*",)),
        ("exists", ("b",)),
        ("increment", ("count", 3, 60)),
        ("get_stats", ()),
    ]


@pytest.mark.unit
def test_as_cache_port_returns_legacy_adapter() -> None:
    adapter = as_cache_port(SpyCache())  # type: ignore[arg-type]

    assert isinstance(adapter, LegacyCacheAdapter)
    assert isinstance(adapter, CachePort)
