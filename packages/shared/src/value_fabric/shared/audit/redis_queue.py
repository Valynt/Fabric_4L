"""Redis-backed durable queue for audit events with retry and dead-letter support.

P1-005: Replaces fire-and-forget BackgroundTask with a Redis list that survives
DB blips.  Events are pushed to environment/service-scoped audit pending keys
and drained by a background worker.  After 3 failed delivery attempts with
exponential backoff, events are moved to the matching dead-letter key for
manual inspection.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

from .models import AuditEvent

logger = logging.getLogger("vf.audit")

_TTL_SECONDS = 7 * 24 * 60 * 60  # 7 days
_MAX_RETRIES = 3
_DEFAULT_ENVIRONMENT = "development"
_DEFAULT_SERVICE_NAME = "value-fabric"
_COMPONENT_RE = re.compile(r"[^a-z0-9_.-]+")


def _normalise_key_component(value: str | None, *, fallback: str) -> str:
    """Return a Redis-key-safe, deterministic namespace component."""
    component = (value or fallback).strip().lower()
    component = _COMPONENT_RE.sub("-", component).strip("-._")
    return component or fallback


def _audit_redis_key(name: str) -> str:
    """Build an audit Redis key from the configured namespace and suffix.

    ``AUDIT_REDIS_KEY_PREFIX`` is an explicit compatibility escape hatch: when
    set to ``audit``, queues use the previous ``audit:pending`` and
    ``audit:dead-letter`` names.  Without that override, the namespace includes
    environment and service to prevent cross-environment queue sharing.
    """
    explicit_prefix = os.getenv("AUDIT_REDIS_KEY_PREFIX", "").strip().strip(":")
    if explicit_prefix:
        return f"{explicit_prefix}:{name}"

    environment = _normalise_key_component(
        os.getenv("ENVIRONMENT") or os.getenv("APP_ENV"),
        fallback=_DEFAULT_ENVIRONMENT,
    )
    service_name = _normalise_key_component(
        os.getenv("SERVICE_NAME"),
        fallback=_DEFAULT_SERVICE_NAME,
    )
    return f"audit:{environment}:{service_name}:{name}"


class RedisAuditQueue:
    """Durable Redis queue for audit events.

    Uses Redis lists (LPUSH / BRPOP) for simplicity and atomicity.
    Events are JSON-serialised with retry metadata.
    """

    def __init__(self, redis_client: Any | None = None) -> None:
        self._redis = redis_client
        self._available = redis_client is not None
        self._pending_key = _audit_redis_key("pending")
        self._dead_letter_key = _audit_redis_key("dead-letter")

    @classmethod
    def from_env(cls) -> "RedisAuditQueue":
        """Create a queue from REDIS_URL if available."""
        redis_url = os.getenv("REDIS_URL", "").strip()
        if not redis_url:
            return cls(None)
        try:
            import redis.asyncio as redis

            client = redis.from_url(redis_url, decode_responses=True)
            return cls(client)
        except Exception as exc:
            logger.warning("Redis audit queue unavailable: %s", exc)
            return cls(None)

    async def push(self, event: AuditEvent) -> bool:
        """Push an event onto the pending queue."""
        if not self._available or self._redis is None:
            return False
        payload = {
            "event": event.model_dump(mode="json"),
            "attempts": 0,
            "last_error": None,
        }
        try:
            await self._redis.lpush(self._pending_key, json.dumps(payload))
            await self._redis.expire(self._pending_key, _TTL_SECONDS)
            return True
        except Exception as exc:
            logger.error("Failed to push audit event to Redis: %s", exc)
            return False

    async def pop(self, timeout: float = 5.0) -> dict[str, Any] | None:
        """Pop an event from the pending queue (blocking with timeout).

        Returns the payload dict or None if the queue is empty.
        """
        if not self._available or self._redis is None:
            return None
        try:
            result = await self._redis.brpop(self._pending_key, timeout=timeout)
            if result is None:
                return None
            # result is (key, value)
            _, raw = result
            return json.loads(raw)
        except Exception as exc:
            logger.error("Failed to pop audit event from Redis: %s", exc)
            return None

    async def dead_letter(self, payload: dict[str, Any], reason: str) -> None:
        """Move a failed event to the dead-letter queue."""
        if not self._available or self._redis is None:
            return
        payload["dead_letter_reason"] = reason
        payload["dead_letter_at"] = logger.makeRecord(
            "vf.audit", 20, "", 0, "", (), None
        ).created
        try:
            await self._redis.lpush(self._dead_letter_key, json.dumps(payload))
            await self._redis.expire(self._dead_letter_key, _TTL_SECONDS)
        except Exception as exc:
            logger.error("Failed to dead-letter audit event: %s", exc)

    async def requeue(self, payload: dict[str, Any]) -> bool:
        """Re-queue an event for retry (pushed to the left for near-FIFO)."""
        if not self._available or self._redis is None:
            return False
        try:
            await self._redis.lpush(self._pending_key, json.dumps(payload))
            await self._redis.expire(self._pending_key, _TTL_SECONDS)
            return True
        except Exception as exc:
            logger.error("Failed to requeue audit event: %s", exc)
            return False

    async def pending_count(self) -> int:
        """Return the number of events in the pending queue."""
        if not self._available or self._redis is None:
            return 0
        try:
            count = await self._redis.llen(self._pending_key)
            return count or 0
        except Exception:
            return 0

    async def dead_letter_count(self) -> int:
        """Return the number of events in the dead-letter queue."""
        if not self._available or self._redis is None:
            return 0
        try:
            count = await self._redis.llen(self._dead_letter_key)
            return count or 0
        except Exception:
            return 0
