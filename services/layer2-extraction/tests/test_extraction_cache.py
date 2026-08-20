"""Unit tests for layer2_extraction.extraction.cache.ExtractionCache."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, patch

import pytest

from layer2_extraction.extraction.cache import ExtractionCache, _InMemoryLRUCache

DEFAULT_SCOPE = ("tenant-a", "source-hash-a", "v1", "value-pack-default")


# ---------------------------------------------------------------------------
# _InMemoryLRUCache (internal)
# ---------------------------------------------------------------------------

class TestInMemoryLRUCache:
    def test_get_returns_none_for_missing_key(self):
        cache = _InMemoryLRUCache()
        assert cache.get("missing") is None

    def test_set_and_get_round_trip(self):
        cache = _InMemoryLRUCache()
        cache.set("k1", {"result": 42})
        assert cache.get("k1") == {"result": 42}

    def test_set_overwrites_existing_key(self):
        cache = _InMemoryLRUCache()
        cache.set("k1", "first")
        cache.set("k1", "second")
        assert cache.get("k1") == "second"

    def test_evicts_oldest_when_maxsize_exceeded(self):
        cache = _InMemoryLRUCache(maxsize=2)
        cache.set("k1", "v1")
        cache.set("k2", "v2")
        cache.set("k3", "v3")  # k1 should be evicted
        assert cache.get("k1") is None
        assert cache.get("k2") == "v2"
        assert cache.get("k3") == "v3"

    def test_get_promotes_key_to_prevent_eviction(self):
        cache = _InMemoryLRUCache(maxsize=2)
        cache.set("k1", "v1")
        cache.set("k2", "v2")
        cache.get("k1")  # promote k1
        cache.set("k3", "v3")  # k2 should be evicted, not k1
        assert cache.get("k1") == "v1"
        assert cache.get("k2") is None


# ---------------------------------------------------------------------------
# ExtractionCache (in-memory fallback, no Redis)
# ---------------------------------------------------------------------------

class TestExtractionCacheInMemory:
    @pytest.mark.asyncio
    async def test_get_returns_none_on_cache_miss(self):
        cache = ExtractionCache(redis_url=None)  # no redis_url → in-memory fallback
        result = await cache.get(*DEFAULT_SCOPE, "entities")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_and_get_round_trip(self):
        cache = ExtractionCache(redis_url=None)
        value = {"entities": ["A", "B"]}
        await cache.set(*DEFAULT_SCOPE, "entities", value)
        retrieved = await cache.get(*DEFAULT_SCOPE, "entities")
        assert retrieved == value

    @pytest.mark.asyncio
    async def test_cache_hit_returns_stored_value(self):
        cache = ExtractionCache(redis_url=None)
        call_count = 0

        async def expensive_fn():
            nonlocal call_count
            call_count += 1
            return {"result": "expensive"}

        # First call — miss
        cached = await cache.get(*DEFAULT_SCOPE, "endpoint")
        if cached is None:
            result = await expensive_fn()
            await cache.set(*DEFAULT_SCOPE, "endpoint", result)

        # Second call — hit
        cached = await cache.get(*DEFAULT_SCOPE, "endpoint")
        assert cached == {"result": "expensive"}
        assert call_count == 1  # expensive_fn called only once

    @pytest.mark.asyncio
    async def test_different_endpoints_have_different_keys(self):
        cache = ExtractionCache(redis_url=None)
        await cache.set(*DEFAULT_SCOPE, "entities", {"type": "entities"})
        await cache.set(*DEFAULT_SCOPE, "relationships", {"type": "relationships"})
        assert await cache.get(*DEFAULT_SCOPE, "entities") == {"type": "entities"}
        assert await cache.get(*DEFAULT_SCOPE, "relationships") == {"type": "relationships"}

    @pytest.mark.asyncio
    async def test_different_source_hashes_have_different_keys(self):
        cache = ExtractionCache(redis_url=None)
        await cache.set("tenant-a", "source-hash-a", "v1", "value-pack-default", "entities", "result A")
        await cache.set("tenant-a", "source-hash-b", "v1", "value-pack-default", "entities", "result B")
        assert (
            await cache.get(
                "tenant-a",
                "source-hash-a",
                "v1",
                "value-pack-default",
                "entities",
            )
            == "result A"
        )
        assert (
            await cache.get(
                "tenant-a",
                "source-hash-b",
                "v1",
                "value-pack-default",
                "entities",
            )
            == "result B"
        )

    @pytest.mark.asyncio
    async def test_different_models_have_different_keys(self):
        cache = ExtractionCache(redis_url=None)
        await cache.set(*DEFAULT_SCOPE, "entities", "gpt4", model="gpt-4")
        await cache.set(*DEFAULT_SCOPE, "entities", "gpt4mini", model="gpt-4o-mini")
        assert await cache.get(*DEFAULT_SCOPE, "entities", model="gpt-4") == "gpt4"
        assert await cache.get(*DEFAULT_SCOPE, "entities", model="gpt-4o-mini") == "gpt4mini"

    @pytest.mark.asyncio
    async def test_close_does_not_raise_without_redis(self):
        cache = ExtractionCache(redis_url=None)
        await cache.close()  # should not raise


class TestExtractionCacheMakeKey:
    def test_same_inputs_produce_same_key(self):
        cache = ExtractionCache(redis_url=None)
        k1 = cache._make_key(*DEFAULT_SCOPE, "entities", model="gpt-4", temperature=0.0)
        k2 = cache._make_key(*DEFAULT_SCOPE, "entities", model="gpt-4", temperature=0.0)
        assert k1 == k2

    def test_key_starts_with_l2_cache_prefix(self):
        cache = ExtractionCache(redis_url=None)
        key = cache._make_key(*DEFAULT_SCOPE, "entities")
        assert key.startswith("l2_cache:")

    def test_different_temperatures_produce_different_keys(self):
        cache = ExtractionCache(redis_url=None)
        k1 = cache._make_key(*DEFAULT_SCOPE, "entities", temperature=0.0)
        k2 = cache._make_key(*DEFAULT_SCOPE, "entities", temperature=0.5)
        assert k1 != k2


class TestExtractionCacheFailureBehavior:
    @pytest.mark.asyncio
    async def test_redis_read_failure_logs_and_uses_fallback(self, caplog: pytest.LogCaptureFixture):
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(side_effect=RuntimeError("redis down"))

        with patch("redis.asyncio.from_url", return_value=mock_redis):
            cache = ExtractionCache(redis_url="redis://localhost:6379")

        assert cache._fallback is not None
        cache._fallback.set(cache._make_key(*DEFAULT_SCOPE, "entities"), {"ok": True})
        caplog.set_level(logging.WARNING, logger="layer2_extraction.extraction.cache")

        result = await cache.get(
            *DEFAULT_SCOPE,
            "entities",
            context={"tenant_id": "tenant-a", "job_id": "job-1", "correlation_id": "corr-1"},
        )

        assert result == {"ok": True}
        assert "Cache operation failed; continuing without cache" in caplog.text
        assert any(getattr(record, "operation", None) == "read" for record in caplog.records)
        assert any(getattr(record, "exception_class", None) == "RuntimeError" for record in caplog.records)

    @pytest.mark.asyncio
    async def test_redis_write_failure_logs_and_does_not_crash(self, caplog: pytest.LogCaptureFixture):
        mock_redis = AsyncMock()
        mock_redis.setex = AsyncMock(side_effect=RuntimeError("redis down"))

        with patch("redis.asyncio.from_url", return_value=mock_redis):
            cache = ExtractionCache(redis_url="redis://localhost:6379")

        caplog.set_level(logging.WARNING, logger="layer2_extraction.extraction.cache")
        await cache.set(
            *DEFAULT_SCOPE,
            "entities",
            {"fallback": "written"},
            context={"tenant_id": "tenant-a", "job_id": "job-2", "correlation_id": "corr-2"},
        )

        result = await cache.get(*DEFAULT_SCOPE, "entities")
        assert result == {"fallback": "written"}
        assert "Cache operation failed; continuing without cache" in caplog.text
        assert any(getattr(record, "operation", None) == "write" for record in caplog.records)
        assert any(getattr(record, "exception_class", None) == "RuntimeError" for record in caplog.records)

    @pytest.mark.asyncio
    async def test_redis_close_failure_logs_and_does_not_crash(self, caplog: pytest.LogCaptureFixture):
        mock_redis = AsyncMock()
        mock_redis.close = AsyncMock(side_effect=RuntimeError("close failed"))

        with patch("redis.asyncio.from_url", return_value=mock_redis):
            cache = ExtractionCache(redis_url="redis://localhost:6379")

        caplog.set_level(logging.WARNING, logger="layer2_extraction.extraction.cache")
        await cache.close()

        assert "Cache operation failed; continuing without cache" in caplog.text
        assert any(getattr(record, "operation", None) == "invalidate" for record in caplog.records)
        assert any(getattr(record, "exception_class", None) == "RuntimeError" for record in caplog.records)

    @pytest.mark.asyncio
    async def test_cache_read_failure_does_not_interrupt_core_extraction_flow(
        self, caplog: pytest.LogCaptureFixture
    ):
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(side_effect=RuntimeError("redis down"))
        mock_redis.setex = AsyncMock(return_value=True)

        with patch("redis.asyncio.from_url", return_value=mock_redis):
            cache = ExtractionCache(redis_url="redis://localhost:6379")

        async def core_extraction(text: str, endpoint: str):
            cached = await cache.get(
                "tenant-a",
                "source-hash-a",
                "v1",
                "value-pack-default",
                endpoint,
                context={"tenant_id": "tenant-a", "job_id": "job-read", "correlation_id": "corr-read"},
            )
            if cached is not None:
                return cached
            computed = {"entities": ["alpha"]}
            await cache.set(
                "tenant-a",
                "source-hash-a",
                "v1",
                "value-pack-default",
                endpoint,
                computed,
                context={"tenant_id": "tenant-a", "job_id": "job-read", "correlation_id": "corr-read"},
            )
            return computed

        caplog.set_level(logging.WARNING, logger="layer2_extraction.extraction.cache")
        result = await core_extraction("text", "entities")
        assert result == {"entities": ["alpha"]}
        assert any(getattr(record, "operation", None) == "read" for record in caplog.records)

    @pytest.mark.asyncio
    async def test_cache_write_failure_does_not_interrupt_core_extraction_flow(
        self, caplog: pytest.LogCaptureFixture
    ):
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.setex = AsyncMock(side_effect=RuntimeError("redis down"))

        with patch("redis.asyncio.from_url", return_value=mock_redis):
            cache = ExtractionCache(redis_url="redis://localhost:6379")

        async def core_extraction(text: str, endpoint: str):
            cached = await cache.get(
                "tenant-a",
                "source-hash-a",
                "v1",
                "value-pack-default",
                endpoint,
                context={"tenant_id": "tenant-a", "job_id": "job-write", "correlation_id": "corr-write"},
            )
            if cached is not None:
                return cached
            computed = {"entities": ["beta"]}
            await cache.set(
                "tenant-a",
                "source-hash-a",
                "v1",
                "value-pack-default",
                endpoint,
                computed,
                context={"tenant_id": "tenant-a", "job_id": "job-write", "correlation_id": "corr-write"},
            )
            return computed

        caplog.set_level(logging.WARNING, logger="layer2_extraction.extraction.cache")
        result = await core_extraction("text", "entities")
        assert result == {"entities": ["beta"]}
        assert any(getattr(record, "operation", None) == "write" for record in caplog.records)

    @pytest.mark.asyncio
    async def test_cache_keys_are_distinct_across_tenant_version_and_value_pack_scopes(self):
        cache = ExtractionCache(redis_url=None)
        scope_a = ("tenant-a", "shared-source-hash", "v1", "value-pack-default")
        scope_b = ("tenant-b", "shared-source-hash", "v1", "value-pack-default")
        scope_c = ("tenant-a", "shared-source-hash", "v2", "value-pack-default")
        scope_d = ("tenant-a", "shared-source-hash", "v1", "value-pack-retail")

        await cache.set(*scope_a, "entities", "result-a")
        await cache.set(*scope_b, "entities", "result-b")
        await cache.set(*scope_c, "entities", "result-c")
        await cache.set(*scope_d, "entities", "result-d")

        assert await cache.get(*scope_a, "entities") == "result-a"
        assert await cache.get(*scope_b, "entities") == "result-b"
        assert await cache.get(*scope_c, "entities") == "result-c"
        assert await cache.get(*scope_d, "entities") == "result-d"


# ---------------------------------------------------------------------------
# ExtractionCache (Redis safe serialization & security tests)
# ---------------------------------------------------------------------------

class TestExtractionCacheSafeSerialization:
    @pytest.mark.asyncio
    async def test_redis_set_and_get_round_trip(self):
        stored_values: dict[str, bytes] = {}
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(side_effect=lambda k: stored_values.get(k))
        mock_redis.setex = AsyncMock(side_effect=lambda k, ttl, val: stored_values.update({k: val}))

        with patch("redis.asyncio.from_url", return_value=mock_redis):
            cache = ExtractionCache(redis_url="redis://localhost:6379")

        value = {"entities": ["A", "B"], "nested": {"score": 0.95}, "flag": True}
        await cache.set(*DEFAULT_SCOPE, "entities", value)

        # Verify envelope structure in Redis storage
        key = cache._make_key(*DEFAULT_SCOPE, "entities")
        raw_stored = stored_values[key]
        assert isinstance(raw_stored, bytes)
        import json
        parsed = json.loads(raw_stored.decode("utf-8"))
        assert parsed["version"] == 1
        assert parsed["tenant_id"] == "tenant-a"
        assert parsed["endpoint"] == "entities"
        assert parsed["data"] == value

        # Retrieve and verify round-trip
        retrieved = await cache.get(*DEFAULT_SCOPE, "entities")
        assert retrieved == value

    @pytest.mark.asyncio
    async def test_malformed_json_fails_safely_as_cache_miss(self, caplog: pytest.LogCaptureFixture):
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=b"{invalid json payload")

        with patch("redis.asyncio.from_url", return_value=mock_redis):
            cache = ExtractionCache(redis_url="redis://localhost:6379")

        caplog.set_level(logging.WARNING, logger="layer2_extraction.extraction.cache")
        result = await cache.get(*DEFAULT_SCOPE, "entities")

        assert result is None
        assert "Cache operation failed; continuing without cache" in caplog.text
        assert any(getattr(record, "operation", None) == "read" for record in caplog.records)

    @pytest.mark.asyncio
    async def test_non_utf8_binary_fails_safely_as_cache_miss(self, caplog: pytest.LogCaptureFixture):
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=b"\x80\x04\x95\x1f\x00\x00\x00\x00\x00\x00\x00")

        with patch("redis.asyncio.from_url", return_value=mock_redis):
            cache = ExtractionCache(redis_url="redis://localhost:6379")

        caplog.set_level(logging.WARNING, logger="layer2_extraction.extraction.cache")
        result = await cache.get(*DEFAULT_SCOPE, "entities")

        assert result is None
        assert "Cache operation failed; continuing without cache" in caplog.text

    @pytest.mark.asyncio
    async def test_schema_invalid_envelope_fails_safely_as_cache_miss(self, caplog: pytest.LogCaptureFixture):
        mock_redis = AsyncMock()
        # Missing required fields like tenant_id / endpoint / data
        mock_redis.get = AsyncMock(return_value=b'{"version": 1, "some_unrelated_field": "test"}')

        with patch("redis.asyncio.from_url", return_value=mock_redis):
            cache = ExtractionCache(redis_url="redis://localhost:6379")

        caplog.set_level(logging.WARNING, logger="layer2_extraction.extraction.cache")
        result = await cache.get(*DEFAULT_SCOPE, "entities")

        assert result is None
        assert "Cache operation failed; continuing without cache" in caplog.text

    @pytest.mark.asyncio
    async def test_unknown_envelope_version_fails_safely_as_cache_miss(self, caplog: pytest.LogCaptureFixture):
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(
            return_value=b'{"version": 999, "tenant_id": "tenant-a", "endpoint": "entities", "data": {"result": 1}}'
        )

        with patch("redis.asyncio.from_url", return_value=mock_redis):
            cache = ExtractionCache(redis_url="redis://localhost:6379")

        caplog.set_level(logging.WARNING, logger="layer2_extraction.extraction.cache")
        result = await cache.get(*DEFAULT_SCOPE, "entities")

        assert result is None
        assert "Cache operation failed; continuing without cache" in caplog.text

    @pytest.mark.asyncio
    async def test_tenant_mismatch_in_envelope_fails_safely_as_cache_miss(self, caplog: pytest.LogCaptureFixture):
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(
            return_value=b'{"version": 1, "tenant_id": "tenant-b", "endpoint": "entities", "data": {"result": 1}}'
        )

        with patch("redis.asyncio.from_url", return_value=mock_redis):
            cache = ExtractionCache(redis_url="redis://localhost:6379")

        caplog.set_level(logging.WARNING, logger="layer2_extraction.extraction.cache")
        result = await cache.get(*DEFAULT_SCOPE, "entities")

        assert result is None
        assert "Cache operation failed; continuing without cache" in caplog.text

    @pytest.mark.asyncio
    async def test_legacy_pickle_payload_rejected_without_deserialization(self):
        import pickle
        legacy_data = {"entities": ["legacy-capability"]}
        legacy_pickle_bytes = pickle.dumps(legacy_data)

        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=legacy_pickle_bytes)

        with patch("redis.asyncio.from_url", return_value=mock_redis):
            cache = ExtractionCache(redis_url="redis://localhost:6379")

        result = await cache.get(*DEFAULT_SCOPE, "entities")
        assert result is None

    @pytest.mark.asyncio
    async def test_foreign_executable_pickle_object_is_never_executed(self):
        import pickle

        executed = False

        class MaliciousPayload:
            def __reduce__(self):
                nonlocal executed
                executed = True
                return (str, ("executed",))

        poisoned_bytes = pickle.dumps(MaliciousPayload())

        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=poisoned_bytes)

        with patch("redis.asyncio.from_url", return_value=mock_redis):
            cache = ExtractionCache(redis_url="redis://localhost:6379")

        result = await cache.get(*DEFAULT_SCOPE, "entities")

        assert result is None
        assert executed is False, "Malicious pickle __reduce__ was executed!"

    @pytest.mark.asyncio
    async def test_cached_content_not_logged_on_decode_failure(self, caplog: pytest.LogCaptureFixture):
        secret_marker = "SUPER_SECRET_TENANT_PII_12345"
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(
            return_value=f'{{"version": 1, "{secret_marker}": invalid_json}}'.encode()
        )

        with patch("redis.asyncio.from_url", return_value=mock_redis):
            cache = ExtractionCache(redis_url="redis://localhost:6379")

        caplog.set_level(logging.WARNING, logger="layer2_extraction.extraction.cache")
        await cache.get(*DEFAULT_SCOPE, "entities")

        for record in caplog.records:
            # The secret payload content should not be present in the message or extra metadata
            assert secret_marker not in record.getMessage()
            extra_dict = getattr(record, "__dict__", {})
            for key, val in extra_dict.items():
                if key not in ("args", "exc_info"):
                    assert secret_marker not in str(val)
