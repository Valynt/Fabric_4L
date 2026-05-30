from __future__ import annotations

"""OSS-1 parity tests for the non-default aiocache CachePort pilot."""


import asyncio
import fnmatch
import json
import time
from typing import Any

import pytest

from cache import (
    AiocacheCacheAdapter,
    CacheConfig,
    CachePort,
    CacheProviderName,
    LegacyCacheAdapter,
    ShadowCacheComparator,
    build_cache_port,
)


class InMemoryLegacyCache:
    """RedisCache-shaped in-memory double preserving legacy CachePort semantics."""

    def __init__(self, config: CacheConfig | None = None) -> None:
        self.config = config or CacheConfig()
        self.store: dict[str, str] = {}
        self.expires_at: dict[str, float] = {}
        self.hits = 0
        self.misses = 0
        self.commands = 0

    def _make_key(self, key: str) -> str:
        return f"{self.config.key_prefix}{key}"

    def _ttl(self, ttl: int | None = None) -> int:
        cache_ttl = ttl or self.config.default_ttl
        return min(cache_ttl, self.config.max_ttl)

    def _serialize(self, value: Any) -> str:
        if self.config.serializer == "pickle":
            raise ValueError("pickle serializer is disabled for security — use json or msgpack")
        return json.dumps(value, default=str)

    def _deserialize(self, value: str) -> Any:
        if self.config.serializer == "pickle":
            raise ValueError("pickle serializer is disabled for security — use json or msgpack")
        return json.loads(value)

    def _purge_if_expired(self, prefixed_key: str) -> None:
        deadline = self.expires_at.get(prefixed_key)
        if deadline is not None and deadline <= time.monotonic():
            self.store.pop(prefixed_key, None)
            self.expires_at.pop(prefixed_key, None)

    async def get(self, key: str) -> Any | None:
        self.commands += 1
        try:
            prefixed_key = self._make_key(key)
            self._purge_if_expired(prefixed_key)
            if prefixed_key not in self.store:
                self.misses += 1
                return None
            self.hits += 1
            return self._deserialize(self.store[prefixed_key])
        except Exception:
            self.misses += 1
            return None

    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        self.commands += 1
        try:
            prefixed_key = self._make_key(key)
            self.store[prefixed_key] = self._serialize(value)
            self.expires_at[prefixed_key] = time.monotonic() + self._ttl(ttl)
            return True
        except Exception:
            return False

    async def delete(self, key: str) -> bool:
        self.commands += 1
        prefixed_key = self._make_key(key)
        self._purge_if_expired(prefixed_key)
        existed = prefixed_key in self.store
        self.store.pop(prefixed_key, None)
        self.expires_at.pop(prefixed_key, None)
        return existed

    async def clear_pattern(self, pattern: str) -> int:
        self.commands += 1
        prefixed_pattern = self._make_key(pattern)
        keys = list(self.store.keys())
        deleted = 0
        for prefixed_key in keys:
            self._purge_if_expired(prefixed_key)
            if prefixed_key in self.store and fnmatch.fnmatch(prefixed_key, prefixed_pattern):
                self.store.pop(prefixed_key, None)
                self.expires_at.pop(prefixed_key, None)
                deleted += 1
        return deleted

    async def exists(self, key: str) -> bool:
        self.commands += 1
        prefixed_key = self._make_key(key)
        self._purge_if_expired(prefixed_key)
        return prefixed_key in self.store

    async def increment(self, key: str, amount: int = 1, ttl: int | None = None) -> int:
        self.commands += 1
        prefixed_key = self._make_key(key)
        self._purge_if_expired(prefixed_key)
        current = self._deserialize(self.store[prefixed_key]) if prefixed_key in self.store else 0
        next_value = int(current or 0) + amount
        self.store[prefixed_key] = self._serialize(next_value)
        self.expires_at[prefixed_key] = time.monotonic() + self._ttl(ttl)
        return next_value

    async def get_stats(self) -> dict[str, Any]:
        self.commands += 1
        return {
            "connected_clients": 1,
            "used_memory": 0,
            "used_memory_human": "0B",
            "keyspace_hits": self.hits,
            "keyspace_misses": self.misses,
            "total_commands_processed": self.commands,
        }


def _build_adapter(kind: str, config: CacheConfig | None = None) -> CachePort:
    if kind == "legacy":
        return LegacyCacheAdapter(InMemoryLegacyCache(config=config))  # type: ignore[arg-type]
    if kind == "aiocache":
        return AiocacheCacheAdapter(config=config, allow_memory_fallback=True)
    raise AssertionError(f"unknown adapter kind: {kind}")


async def _close_if_supported(adapter: CachePort) -> None:
    close = getattr(adapter, "close", None)
    if close is not None:
        await close()


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize("adapter_kind", ["legacy", "aiocache"])
async def test_cache_port_contract_hit_miss_json_round_trip_and_stats(adapter_kind: str) -> None:
    adapter = _build_adapter(
        adapter_kind,
        CacheConfig(default_ttl=30, max_ttl=30, key_prefix=f"oss1:{adapter_kind}:tenant-a:"),
    )
    try:
        assert isinstance(adapter, CachePort)
        value = {"tenant": "a", "items": [1, 2, 3], "nested": {"ok": True}}

        assert await adapter.get("missing") is None
        assert await adapter.set("document:1", value, ttl=30) is True
        assert await adapter.get("document:1") == value

        stats = await adapter.get_stats()
        assert stats["keyspace_hits"] == 1
        assert stats["keyspace_misses"] == 1
        assert stats["total_commands_processed"] >= 4
    finally:
        await _close_if_supported(adapter)


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize("adapter_kind", ["legacy", "aiocache"])
async def test_cache_port_contract_delete_exists_clear_pattern_and_increment(adapter_kind: str) -> None:
    adapter = _build_adapter(
        adapter_kind,
        CacheConfig(default_ttl=30, max_ttl=30, key_prefix=f"oss1:{adapter_kind}:tenant-b:"),
    )
    try:
        assert await adapter.set("group:1", {"value": 1}) is True
        assert await adapter.set("group:2", {"value": 2}) is True
        assert await adapter.set("other:1", {"value": 3}) is True

        assert await adapter.exists("group:1") is True
        assert await adapter.delete("group:1") is True
        assert await adapter.exists("group:1") is False

        assert await adapter.increment("counter", amount=3, ttl=30) == 3
        assert await adapter.increment("counter", amount=4, ttl=30) == 7
        assert await adapter.get("counter") == 7

        assert await adapter.clear_pattern("group:*") == 1
        assert await adapter.exists("group:2") is False
        assert await adapter.exists("other:1") is True
    finally:
        await _close_if_supported(adapter)


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize("adapter_kind", ["legacy", "aiocache"])
async def test_cache_port_contract_ttl_is_enforced_and_capped(adapter_kind: str) -> None:
    adapter = _build_adapter(
        adapter_kind,
        CacheConfig(default_ttl=1, max_ttl=1, key_prefix=f"oss1:{adapter_kind}:ttl:"),
    )
    try:
        assert await adapter.set("short", {"expires": True}, ttl=3600) is True
        assert await adapter.get("short") == {"expires": True}
        await asyncio.sleep(1.1)
        assert await adapter.get("short") is None
    finally:
        await _close_if_supported(adapter)


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize("adapter_kind", ["legacy", "aiocache"])
async def test_cache_port_contract_tenant_key_prefix_is_preserved(adapter_kind: str) -> None:
    prefix = f"oss1:{adapter_kind}:tenant-isolated:"
    config = CacheConfig(default_ttl=30, max_ttl=30, key_prefix=prefix)
    adapter = _build_adapter(adapter_kind, config)
    try:
        assert await adapter.set("record", {"tenant": "isolated"}) is True

        if adapter_kind == "legacy":
            legacy_cache = adapter._cache  # type: ignore[attr-defined]
            assert "record" not in legacy_cache.store
            assert f"{prefix}record" in legacy_cache.store
        else:
            assert isinstance(adapter, AiocacheCacheAdapter)
            assert await adapter._cache.get("record") is None  # type: ignore[attr-defined]
            assert await adapter._cache.get(f"{prefix}record") is not None  # type: ignore[attr-defined]
    finally:
        await _close_if_supported(adapter)


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize("adapter_kind", ["legacy", "aiocache"])
async def test_cache_port_contract_pickle_serializer_is_blocked(adapter_kind: str) -> None:
    adapter = _build_adapter(
        adapter_kind,
        CacheConfig(default_ttl=30, max_ttl=30, key_prefix=f"oss1:{adapter_kind}:pickle:", serializer="pickle"),
    )
    try:
        assert await adapter.set("unsafe", {"blocked": True}) is False
        assert await adapter.get("unsafe") is None
    finally:
        await _close_if_supported(adapter)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cache_factory_keeps_legacy_default_and_requires_explicit_aiocache_opt_in() -> None:
    legacy = InMemoryLegacyCache(config=CacheConfig(key_prefix="oss1:factory:legacy:"))
    default_adapter = build_cache_port(legacy_cache=legacy)  # type: ignore[arg-type]
    aiocache_adapter = build_cache_port(
        provider=CacheProviderName.AIOCACHE,
        config=CacheConfig(key_prefix="oss1:factory:aiocache:"),
        allow_aiocache_memory_fallback=True,
    )
    try:
        assert isinstance(default_adapter, LegacyCacheAdapter)
        assert isinstance(aiocache_adapter, AiocacheCacheAdapter)
    finally:
        await _close_if_supported(aiocache_adapter)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_shadow_cache_comparator_reports_no_mismatches_for_equal_cacheport_operations() -> None:
    primary = LegacyCacheAdapter(
        InMemoryLegacyCache(config=CacheConfig(default_ttl=30, max_ttl=30, key_prefix="oss1:shadow:"))
    )  # type: ignore[arg-type]
    shadow = AiocacheCacheAdapter(
        config=CacheConfig(default_ttl=30, max_ttl=30, key_prefix="oss1:shadow:"),
        allow_memory_fallback=True,
    )
    comparator = ShadowCacheComparator(primary=primary, shadow=shadow)
    try:
        assert await comparator.set("item:1", {"value": 1}, ttl=30) is True
        assert await comparator.get("item:1") == {"value": 1}
        assert await comparator.exists("item:1") is True
        assert await comparator.increment("counter", amount=5, ttl=30) == 5
        assert await comparator.get("counter") == 5
        assert await comparator.delete("item:1") is True
        assert await comparator.clear_pattern("counter") == 1

        assert comparator.mismatches == []
    finally:
        await shadow.close()


@pytest.mark.unit
def test_aiocache_adapter_fails_closed_without_backend_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    with pytest.raises(ValueError, match="requires an explicit cache backend"):
        AiocacheCacheAdapter(config=CacheConfig(key_prefix="oss1:fail-closed:"))


@pytest.mark.unit
def test_aiocache_adapter_disallows_memory_fallback_in_production_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    with pytest.raises(ValueError, match="MEMORY fallback is disabled by default"):
        AiocacheCacheAdapter(
            config=CacheConfig(key_prefix="oss1:production:"),
            allow_memory_fallback=True,
        )


@pytest.mark.unit
def test_aiocache_adapter_allows_memory_fallback_with_explicit_opt_in_for_test_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "test")
    adapter = AiocacheCacheAdapter(
        config=CacheConfig(key_prefix="oss1:test-env:"),
        allow_memory_fallback=True,
    )
    try:
        assert adapter._cache is not None  # type: ignore[attr-defined]
    finally:
        # Close the internal backend for completeness.
        asyncio.run(adapter.close())
