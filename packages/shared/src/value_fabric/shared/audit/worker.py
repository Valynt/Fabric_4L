"""Background worker that drains the Redis audit queue into PostgreSQL.

P1-005: Runs as an asyncio task (typically started in a FastAPI lifespan) and
polls the ``audit:pending`` Redis list.  Each event is written to the
``audit_events`` table with exponential-backoff retry.  After 3 failed attempts
the event is moved to ``audit:dead-letter``.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Callable

from .models import AuditEvent
from .redis_queue import RedisAuditQueue, _MAX_RETRIES

logger = logging.getLogger("vf.audit.worker")

# Exponential backoff: 1s, 2s, 4s
_BACKOFF_DELAYS = [1.0, 2.0, 4.0]


class AuditWorker:
    """Durable audit-event worker.

    Usage in a FastAPI lifespan::

        async def lifespan(app: FastAPI):
            worker = AuditWorker(get_db_from_context)
            task = asyncio.create_task(worker.run())
            yield
            worker.stop()
            await task
    """

    def __init__(
        self,
        db_factory: Callable,
        queue: RedisAuditQueue | None = None,
        poll_interval: float = 5.0,
    ) -> None:
        self.db_factory = db_factory
        self.queue = queue or RedisAuditQueue.from_env()
        self.poll_interval = poll_interval
        self._running = False
        self._task: asyncio.Task | None = None

    def start(self) -> asyncio.Task:
        """Start the worker as a background asyncio task."""
        self._running = True
        self._task = asyncio.create_task(self.run())
        return self._task

    def stop(self) -> None:
        """Signal the worker to stop gracefully."""
        self._running = False

    async def run(self) -> None:
        """Main loop: drain Redis queue and write to PostgreSQL."""
        if not self.queue._available:
            logger.info("Audit worker: Redis queue unavailable; worker idle.")
            return

        logger.info("Audit worker started")
        while self._running:
            try:
                payload = await self.queue.pop(timeout=self.poll_interval)
                if payload is None:
                    continue
                await self._process_one(payload)
            except asyncio.CancelledError:
                logger.info("Audit worker cancelled")
                raise
            except Exception as exc:
                logger.error("Audit worker loop error: %s", exc, exc_info=True)
                await asyncio.sleep(self.poll_interval)

        logger.info("Audit worker stopped")

    async def _process_one(self, payload: dict[str, Any]) -> None:
        """Write a single event to the DB with retry logic."""
        event_data = payload.get("event", {})
        attempts = payload.get("attempts", 0)

        # Convert JSON dict back to AuditEvent for the DB insert
        event = AuditEvent.model_validate(event_data)

        for attempt in range(attempts, _MAX_RETRIES):
            try:
                async with self.db_factory() as session:
                    from sqlalchemy import text

                    await session.execute(
                        text(
                            """
                            INSERT INTO audit_events (
                                id, tenant_id, user_id, api_key_id,
                                action, resource_type, resource_id,
                                ip_address, user_agent, request_id,
                                outcome, details, timestamp
                            ) VALUES (
                                :id, :tenant_id, :user_id, :api_key_id,
                                :action, :resource_type, :resource_id,
                                :ip_address, :user_agent, :request_id,
                                :outcome, :details::jsonb, :timestamp
                            )
                            """
                        ),
                        {
                            "id": event.id,
                            "tenant_id": event.tenant_id,
                            "user_id": event.user_id,
                            "api_key_id": event.api_key_id,
                            "action": event.action,
                            "resource_type": event.resource_type,
                            "resource_id": event.resource_id,
                            "ip_address": event.ip_address,
                            "user_agent": event.user_agent,
                            "request_id": event.request_id,
                            "outcome": event.outcome,
                            "details": json.dumps(event.details),
                            "timestamp": event.timestamp,
                        },
                    )
                    await session.commit()
                logger.debug("Audit event %s persisted", event.id)
                return
            except Exception as exc:
                payload["attempts"] = attempt + 1
                payload["last_error"] = str(exc)
                logger.warning(
                    "Audit event %s DB write failed (attempt %d/%d): %s",
                    event.id,
                    attempt + 1,
                    _MAX_RETRIES,
                    exc,
                )
                if attempt + 1 < _MAX_RETRIES:
                    delay = _BACKOFF_DELAYS[attempt]
                    await asyncio.sleep(delay)

        # All retries exhausted → dead-letter
        logger.error(
            "Audit event %s exhausted retries; moving to dead-letter",
            event.id,
        )
        await self.queue.dead_letter(payload, reason="max_retries_exhausted")
