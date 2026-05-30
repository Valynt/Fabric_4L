"""Integration tests for Redis-backed audit queue (message-queue contract).

These tests exercise the durable Redis queue used for audit-event delivery,
verifying push/pop, dead-letter, TTL, and graceful degradation.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest

from ..models import AuditAction, AuditEvent
from ..redis_queue import RedisAuditQueue, _DEAD_LETTER_KEY, _PENDING_KEY, _TTL_SECONDS

pytestmark = [pytest.mark.integration]


class TestRedisAuditQueueUnit:
    """Unit-level tests with mocked Redis client."""

    @pytest.fixture
    def mock_redis(self):
        """Provide a mock async Redis client."""
        client = AsyncMock()
        client.lpush = AsyncMock(return_value=1)
        client.expire = AsyncMock(return_value=1)
        client.brpop = AsyncMock(return_value=(_PENDING_KEY, json.dumps({
            "event": {"action": "user.login", "id": "test-uuid", "timestamp": "2024-01-01T00:00:00"},
            "attempts": 0,
            "last_error": None,
        })))
        client.rpush = AsyncMock(return_value=1)
        return client

    def test_unavailable_when_no_redis(self):
        queue = RedisAuditQueue(None)
        assert queue._available is False

    def test_available_with_client(self, mock_redis):
        queue = RedisAuditQueue(mock_redis)
        assert queue._available is True

    @pytest.mark.asyncio
    async def test_push_returns_false_when_unavailable(self):
        queue = RedisAuditQueue(None)
        event = AuditEvent(action=AuditAction.USER_LOGIN)
        result = await queue.push(event)
        assert result is False

    @pytest.mark.asyncio
    async def test_push_sends_lpush_with_ttl(self, mock_redis):
        queue = RedisAuditQueue(mock_redis)
        event = AuditEvent(action=AuditAction.USER_LOGIN)
        result = await queue.push(event)

        assert result is True
        mock_redis.lpush.assert_awaited_once()
        mock_redis.expire.assert_awaited_once_with(_PENDING_KEY, _TTL_SECONDS)

    @pytest.mark.asyncio
    async def test_pop_returns_none_when_unavailable(self):
        queue = RedisAuditQueue(None)
        result = await queue.pop(timeout=1.0)
        assert result is None

    @pytest.mark.asyncio
    async def test_pop_returns_payload(self, mock_redis):
        queue = RedisAuditQueue(mock_redis)
        payload = await queue.pop(timeout=5.0)

        assert payload is not None
        assert payload["attempts"] == 0
        assert payload["last_error"] is None
        assert payload["event"]["action"] == "user.login"
        mock_redis.brpop.assert_awaited_once_with(_PENDING_KEY, timeout=5.0)

    @pytest.mark.asyncio
    async def test_dead_letter_noop_when_unavailable(self):
        queue = RedisAuditQueue(None)
        payload = {"event": {}, "attempts": 1, "last_error": None}
        await queue.dead_letter(payload, reason="test")

    @pytest.mark.asyncio
    async def test_dead_letter_pushes_with_reason(self, mock_redis):
        queue = RedisAuditQueue(mock_redis)
        payload = {"event": {}, "attempts": 1, "last_error": None}
        await queue.dead_letter(payload, reason="max_retries")

        mock_redis.lpush.assert_awaited_once()
        args = mock_redis.lpush.call_args[0]
        assert args[0] == _DEAD_LETTER_KEY
        dead_payload = json.loads(args[1])
        assert dead_payload["attempts"] == 1
        assert dead_payload["dead_letter_reason"] == "max_retries"

    @pytest.mark.asyncio
    async def test_requeue_returns_false_when_unavailable(self):
        queue = RedisAuditQueue(None)
        payload = {"event": {}, "attempts": 1}
        result = await queue.requeue(payload)
        assert result is False

    @pytest.mark.asyncio
    async def test_requeue_pushes_back_to_pending(self, mock_redis):
        queue = RedisAuditQueue(mock_redis)
        payload = {"event": {}, "attempts": 1, "last_error": "timeout"}
        result = await queue.requeue(payload)

        assert result is True
        mock_redis.lpush.assert_awaited_once()
        args = mock_redis.lpush.call_args[0]
        assert args[0] == _PENDING_KEY
        new_payload = json.loads(args[1])
        assert new_payload["attempts"] == 1
        mock_redis.expire.assert_awaited_once_with(_PENDING_KEY, _TTL_SECONDS)

    @pytest.mark.asyncio
    async def test_pending_count_returns_zero_when_unavailable(self):
        queue = RedisAuditQueue(None)
        assert await queue.pending_count() == 0

    @pytest.mark.asyncio
    async def test_pending_count_returns_length(self, mock_redis):
        mock_redis.llen = AsyncMock(return_value=5)
        queue = RedisAuditQueue(mock_redis)
        count = await queue.pending_count()
        assert count == 5
        mock_redis.llen.assert_awaited_once_with(_PENDING_KEY)

    @pytest.mark.asyncio
    async def test_dead_letter_count_returns_zero_when_unavailable(self):
        queue = RedisAuditQueue(None)
        assert await queue.dead_letter_count() == 0

    @pytest.mark.asyncio
    async def test_dead_letter_count_returns_length(self, mock_redis):
        mock_redis.llen = AsyncMock(return_value=3)
        queue = RedisAuditQueue(mock_redis)
        count = await queue.dead_letter_count()
        assert count == 3
        mock_redis.llen.assert_awaited_once_with(_DEAD_LETTER_KEY)


@pytest.mark.integration
class TestRedisAuditQueueIntegration:
    """Integration tests requiring a live Redis instance.

    Skip automatically when REDIS_URL is not available or Redis is unreachable.
    """

    @pytest.fixture(scope="class")
    async def redis_client(self):
        import os

        redis_url = os.getenv("REDIS_URL", "").strip()
        if not redis_url:
            pytest.skip("REDIS_URL not set")
        try:
            import redis.asyncio as redis

            client = redis.from_url(redis_url, decode_responses=True)
            await client.ping()
            return client
        except Exception as exc:
            pytest.skip(f"Redis unavailable: {exc}")

    @pytest.fixture(autouse=True)
    async def clean_queues(self, redis_client):
        await redis_client.delete(_PENDING_KEY, _DEAD_LETTER_KEY)
        yield
        await redis_client.delete(_PENDING_KEY, _DEAD_LETTER_KEY)

    @pytest.mark.asyncio
    async def test_push_pop_roundtrip(self, redis_client):
        queue = RedisAuditQueue(redis_client)
        event = AuditEvent(action=AuditAction.USER_LOGIN, tenant_id="t1")
        pushed = await queue.push(event)
        assert pushed is True

        payload = await queue.pop(timeout=2.0)
        assert payload is not None
        assert payload["event"]["action"] == "user.login"
        assert payload["event"]["tenant_id"] == "t1"
        assert payload["attempts"] == 0

    @pytest.mark.asyncio
    async def test_pop_returns_none_on_empty_queue(self, redis_client):
        queue = RedisAuditQueue(redis_client)
        payload = await queue.pop(timeout=1.0)
        assert payload is None

    @pytest.mark.asyncio
    async def test_dead_letter_moves_event(self, redis_client):
        queue = RedisAuditQueue(redis_client)
        event = AuditEvent(action=AuditAction.DATA_EXPORT)
        await queue.push(event)
        payload = await queue.pop(timeout=2.0)

        await queue.dead_letter(payload, reason="test_failure")

        dead_len = await redis_client.llen(_DEAD_LETTER_KEY)
        assert dead_len == 1
        pending_len = await redis_client.llen(_PENDING_KEY)
        assert pending_len == 0

    @pytest.mark.asyncio
    async def test_fifo_ordering(self, redis_client):
        queue = RedisAuditQueue(redis_client)
        for i in range(3):
            event = AuditEvent(action=AuditAction.USER_LOGIN, details={"seq": i})
            await queue.push(event)

        payloads = []
        for _ in range(3):
            p = await queue.pop(timeout=2.0)
            payloads.append(p)

        seqs = [p["event"]["details"]["seq"] for p in payloads]
        assert seqs == [0, 1, 2]

    @pytest.mark.asyncio
    async def test_ttl_set_on_pending(self, redis_client):
        queue = RedisAuditQueue(redis_client)
        event = AuditEvent(action=AuditAction.USER_LOGIN)
        await queue.push(event)

        ttl = await redis_client.ttl(_PENDING_KEY)
        assert ttl > 0
        assert ttl <= _TTL_SECONDS
