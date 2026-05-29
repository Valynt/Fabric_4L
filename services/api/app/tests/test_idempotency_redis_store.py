"""P0-010: Idempotency store must use Redis when available.

Verifies that RedisIdempotencyStore serialises to Redis with TTL
and falls back to in-memory when Redis is unreachable.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest

from value_fabric.shared.idempotency import (
    InMemoryIdempotencyStore,
    RedisIdempotencyStore,
    StoredIdempotencyRecord,
)


def _make_record(tenant_id: str = "t-1", endpoint_key: str = "ep-1", idempotency_key: str = "ik-1") -> StoredIdempotencyRecord:
    return StoredIdempotencyRecord(
        tenant_id=tenant_id,
        endpoint_key=endpoint_key,
        idempotency_key=idempotency_key,
        request_fingerprint="fp-1",
        status_code=201,
        body={"id": "abc"},
        headers={"X-Idempotent-Replay": "false"},
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )


class TestRedisIdempotencyStore:
    """Redis-backed idempotency store behavior."""

    def test_get_returns_none_when_key_missing(self):
        redis_mock = MagicMock()
        redis_mock.get.return_value = None
        store = RedisIdempotencyStore(redis_mock)
        assert store.get("t-1", "ep-1", "ik-1") is None

    def test_get_deserialises_record(self):
        record = _make_record()
        redis_mock = MagicMock()
        redis_mock.get.return_value = json.dumps({
            "tenant_id": record.tenant_id,
            "endpoint_key": record.endpoint_key,
            "idempotency_key": record.idempotency_key,
            "request_fingerprint": record.request_fingerprint,
            "status_code": record.status_code,
            "body": record.body,
            "headers": record.headers,
            "expires_at": record.expires_at.isoformat(),
        })
        store = RedisIdempotencyStore(redis_mock)
        result = store.get("t-1", "ep-1", "ik-1")
        assert result is not None
        assert result.idempotency_key == "ik-1"
        assert result.status_code == 201

    def test_set_uses_setex_with_ttl(self):
        redis_mock = MagicMock()
        store = RedisIdempotencyStore(redis_mock)
        record = _make_record()
        store.set(record)

        redis_mock.setex.assert_called_once()
        args = redis_mock.setex.call_args[0]
        assert args[0] == "idempotency:t-1:ep-1:ik-1"
        assert args[1] > 0  # TTL must be positive
        stored = json.loads(args[2])
        assert stored["idempotency_key"] == "ik-1"

    def test_redis_error_falls_back_to_in_memory(self):
        redis_mock = MagicMock()
        redis_mock.get.side_effect = ConnectionError("Redis down")
        store = RedisIdempotencyStore(redis_mock)

        # First get triggers fallback
        result = store.get("t-1", "ep-1", "ik-1")
        assert result is None
        assert store._fallback_active is True

        # Subsequent writes go to fallback
        record = _make_record()
        store.set(record)
        assert store._fallback.get("t-1", "ep-1", "ik-1") == record

    def test_uses_correct_redis_key_format(self):
        redis_mock = MagicMock()
        redis_mock.get.return_value = None
        store = RedisIdempotencyStore(redis_mock)
        store.get("tenant-a", "POST /accounts", "key-123")
        redis_mock.get.assert_called_once_with("idempotency:tenant-a:POST /accounts:key-123")


class TestInMemoryIdempotencyStore:
    """In-memory store still works as standalone fallback."""

    def test_basic_get_set(self):
        store = InMemoryIdempotencyStore()
        record = _make_record()
        store.set(record)
        assert store.get("t-1", "ep-1", "ik-1") == record

    def test_expired_record_is_removed(self):
        store = InMemoryIdempotencyStore()
        record = StoredIdempotencyRecord(
            tenant_id="t-1",
            endpoint_key="ep-1",
            idempotency_key="ik-1",
            request_fingerprint="fp-1",
            status_code=201,
            body={},
            headers={},
            expires_at=datetime.now(UTC) - timedelta(seconds=1),
        )
        store.set(record)
        assert store.get("t-1", "ep-1", "ik-1") is None
