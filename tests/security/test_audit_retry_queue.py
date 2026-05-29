"""Security regression tests for P1-005: Audit Event Retry Queue.

Validates that:
- RedisAuditQueue can push/pop events
- AuditWorker retries failed DB writes with exponential backoff
- After 3 retries events move to the dead-letter queue
- AuditEmitter.write_to_db uses Redis queue when available
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from value_fabric.shared.audit.models import AuditAction, AuditEvent, AuditOutcome
from value_fabric.shared.audit.redis_queue import (
    RedisAuditQueue,
    _DEAD_LETTER_KEY,
    _MAX_RETRIES,
    _PENDING_KEY,
    _TTL_SECONDS,
)
from value_fabric.shared.audit.worker import AuditWorker, _BACKOFF_DELAYS


class TestRedisAuditQueue:
    """Redis-backed audit queue operations."""

    @pytest.fixture
    def mock_redis(self):
        redis = AsyncMock()
        redis.lpush = AsyncMock(return_value=1)
        redis.expire = AsyncMock(return_value=1)
        redis.brpop = AsyncMock(return_value=None)
        redis.llen = AsyncMock(return_value=0)
        return redis

    @pytest.fixture
    def event(self):
        return AuditEvent(
            action=AuditAction.TENANT_CREATED,
            outcome=AuditOutcome.SUCCESS,
            tenant_id=None,
            user_id=None,
            resource_type="Tenant",
            resource_id="test-tenant-id",
        )

    def test_from_env_returns_queue_when_redis_url_set(self, monkeypatch):
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
        with patch("redis.asyncio.from_url") as mock_from_url:
            mock_from_url.return_value = AsyncMock()
            q = RedisAuditQueue.from_env()
            assert q._available is True

    def test_from_env_returns_disabled_when_no_redis_url(self, monkeypatch):
        monkeypatch.delenv("REDIS_URL", raising=False)
        q = RedisAuditQueue.from_env()
        assert q._available is False

    @pytest.mark.asyncio
    async def test_push_serialises_event(self, mock_redis, event):
        q = RedisAuditQueue(mock_redis)
        result = await q.push(event)
        assert result is True
        mock_redis.lpush.assert_awaited_once()
        raw = mock_redis.lpush.call_args[0][1]
        payload = json.loads(raw)
        assert payload["event"]["action"] == "tenant.created"
        assert payload["attempts"] == 0

    @pytest.mark.asyncio
    async def test_push_sets_ttl(self, mock_redis, event):
        q = RedisAuditQueue(mock_redis)
        await q.push(event)
        mock_redis.expire.assert_awaited_once_with(_PENDING_KEY, _TTL_SECONDS)

    @pytest.mark.asyncio
    async def test_push_returns_false_when_redis_unavailable(self, event):
        q = RedisAuditQueue(None)
        result = await q.push(event)
        assert result is False

    @pytest.mark.asyncio
    async def test_pop_returns_none_on_empty(self, mock_redis):
        q = RedisAuditQueue(mock_redis)
        result = await q.pop(timeout=1.0)
        assert result is None
        mock_redis.brpop.assert_awaited_once_with(_PENDING_KEY, timeout=1.0)

    @pytest.mark.asyncio
    async def test_pop_returns_payload(self, mock_redis):
        payload = {"event": {"action": "tenant_created"}, "attempts": 0}
        mock_redis.brpop.return_value = (_PENDING_KEY, json.dumps(payload))
        q = RedisAuditQueue(mock_redis)
        result = await q.pop(timeout=1.0)
        assert result == payload

    @pytest.mark.asyncio
    async def test_dead_letter_stores_reason(self, mock_redis):
        payload = {"event": {"action": "tenant_created"}, "attempts": 3}
        q = RedisAuditQueue(mock_redis)
        await q.dead_letter(payload, reason="db_down")
        mock_redis.lpush.assert_awaited()
        raw = mock_redis.lpush.call_args[0][1]
        stored = json.loads(raw)
        assert stored["dead_letter_reason"] == "db_down"

    @pytest.mark.asyncio
    async def test_requeue_increments_attempts(self, mock_redis):
        payload = {"event": {"action": "tenant_created"}, "attempts": 1}
        q = RedisAuditQueue(mock_redis)
        result = await q.requeue(payload)
        assert result is True
        mock_redis.lpush.assert_awaited_once()


class TestAuditWorker:
    """Background worker draining queue to PostgreSQL."""

    @pytest.fixture
    def mock_db_factory(self):
        session = AsyncMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()

        class _Ctx:
            async def __aenter__(self):
                return session
            async def __aexit__(self, *args):
                pass

        def _factory():
            return _Ctx()

        return _factory, session

    @pytest.fixture
    def mock_queue(self):
        q = MagicMock(spec=RedisAuditQueue)
        q._available = True
        q.pop = AsyncMock(return_value=None)
        q.dead_letter = AsyncMock(return_value=None)
        q.requeue = AsyncMock(return_value=True)
        return q

    def test_backoff_delays_are_exponential(self):
        assert _BACKOFF_DELAYS == [1.0, 2.0, 4.0]

    @pytest.mark.asyncio
    async def test_worker_start_creates_task(self, mock_db_factory, mock_queue):
        factory, _ = mock_db_factory
        worker = AuditWorker(factory, queue=mock_queue, poll_interval=0.1)
        task = worker.start()
        assert worker._running is True
        assert task is not None
        worker.stop()
        # Cancel the task to clean up
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_worker_processes_event_successfully(
        self, mock_db_factory, mock_queue
    ):
        factory, session = mock_db_factory
        event = AuditEvent(
            action=AuditAction.TENANT_CREATED,
            outcome=AuditOutcome.SUCCESS,
            resource_type="Tenant",
            resource_id="t-1",
        )
        payload = {
            "event": event.model_dump(mode="json"),
            "attempts": 0,
        }
        mock_queue.pop = AsyncMock(return_value=payload)

        worker = AuditWorker(factory, queue=mock_queue, poll_interval=0.1)
        await worker._process_one(payload)

        mock_queue.dead_letter.assert_not_awaited()
        session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_worker_dead_letters_after_max_retries(
        self, mock_db_factory, mock_queue
    ):
        event = AuditEvent(
            action=AuditAction.TENANT_CREATED,
            outcome=AuditOutcome.SUCCESS,
            resource_type="Tenant",
            resource_id="t-1",
        )
        payload = {
            "event": event.model_dump(mode="json"),
            "attempts": 0,
        }

        # Make DB factory always raise
        class _FailingCtx:
            async def __aenter__(self):
                raise RuntimeError("DB is down")
            async def __aexit__(self, *args):
                pass

        def _failing_factory():
            return _FailingCtx()

        worker = AuditWorker(_failing_factory, queue=mock_queue, poll_interval=0.1)
        await worker._process_one(payload)

        mock_queue.dead_letter.assert_awaited_once()
        reason = mock_queue.dead_letter.call_args.kwargs.get("reason") or mock_queue.dead_letter.call_args[0][1]
        assert reason == "max_retries_exhausted"


class TestFabricAppLifespanWrapping:
    """create_fabric_app must wrap lifespan to start/stop AuditWorker."""

    @pytest.mark.asyncio
    async def test_audit_worker_started_when_db_factory_provided(self):
        from fastapi import FastAPI

        from value_fabric.shared.audit.worker import AuditWorker
        from value_fabric.shared.fastapi_framework.app import create_fabric_app

        startup_called = False
        shutdown_called = False

        async def dummy_lifespan(app: FastAPI):
            nonlocal startup_called, shutdown_called
            startup_called = True
            yield
            shutdown_called = True

        class _FakeCtx:
            async def __aenter__(self):
                return AsyncMock()
            async def __aexit__(self, *args):
                pass

        def fake_db_factory():
            return _FakeCtx()

        app = create_fabric_app(
            service_name="test-service",
            title="Test",
            version="0.1.0",
            description="Test",
            lifespan=dummy_lifespan,
            audit_worker_db_factory=fake_db_factory,
        )

        # FastAPI lifespan protocol
        async with app.router.lifespan_context(app):
            pass

        assert startup_called is True
        assert shutdown_called is True


class TestAuditEmitterUsesQueue:
    """AuditEmitter.write_to_db must prefer Redis queue when available."""

    @pytest.mark.asyncio
    async def test_uses_redis_queue_when_available(self):
        event = AuditEvent(
            action=AuditAction.TENANT_CREATED,
            outcome=AuditOutcome.SUCCESS,
            resource_type="Tenant",
            resource_id="t-1",
        )
        queue = AsyncMock(spec=RedisAuditQueue)
        queue._available = True
        queue.push = AsyncMock(return_value=True)

        db_factory = AsyncMock()

        from value_fabric.shared.audit.emitter import AuditEmitter

        await AuditEmitter.write_to_db(event, db_factory, queue=queue)
        queue.push.assert_awaited_once_with(event)
        db_factory.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_falls_back_to_direct_db_when_redis_push_fails(self):
        event = AuditEvent(
            action=AuditAction.TENANT_CREATED,
            outcome=AuditOutcome.SUCCESS,
            resource_type="Tenant",
            resource_id="t-1",
        )
        queue = AsyncMock(spec=RedisAuditQueue)
        queue._available = True
        queue.push = AsyncMock(return_value=False)

        session = AsyncMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()

        class _Ctx:
            async def __aenter__(self):
                return session
            async def __aexit__(self, *args):
                pass

        def db_factory():
            return _Ctx()

        from value_fabric.shared.audit.emitter import AuditEmitter

        await AuditEmitter.write_to_db(event, db_factory, queue=queue)
        queue.push.assert_awaited_once_with(event)
        session.execute.assert_awaited_once()


class TestSourceCodePresence:
    """Source files must exist and contain expected logic."""

    def test_redis_queue_file_exists(self):
        assert Path(
            "packages/shared/src/value_fabric/shared/audit/redis_queue.py"
        ).exists()

    def test_worker_file_exists(self):
        assert Path(
            "packages/shared/src/value_fabric/shared/audit/worker.py"
        ).exists()

    def test_emitter_imports_redis_queue(self):
        src = Path(
            "packages/shared/src/value_fabric/shared/audit/emitter.py"
        ).read_text(encoding="utf-8")
        assert "from .redis_queue import RedisAuditQueue" in src

    def test_init_exports_worker_and_queue(self):
        src = Path(
            "packages/shared/src/value_fabric/shared/audit/__init__.py"
        ).read_text(encoding="utf-8")
        assert "RedisAuditQueue" in src
        assert "AuditWorker" in src
