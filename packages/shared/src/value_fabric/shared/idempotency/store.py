from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from typing import Protocol

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StoredIdempotencyRecord:
    tenant_id: str
    endpoint_key: str
    idempotency_key: str
    request_fingerprint: str
    status_code: int
    body: Any
    headers: dict[str, str]
    expires_at: datetime


class IdempotencyStore(Protocol):
    def get(self, tenant_id: str, endpoint_key: str, idempotency_key: str) -> StoredIdempotencyRecord | None: ...

    def set(self, record: StoredIdempotencyRecord) -> None: ...


class InMemoryIdempotencyStore:
    def __init__(self) -> None:
        self._records: dict[tuple[str, str, str], StoredIdempotencyRecord] = {}

    def get(self, tenant_id: str, endpoint_key: str, idempotency_key: str) -> StoredIdempotencyRecord | None:
        key = (tenant_id, endpoint_key, idempotency_key)
        record = self._records.get(key)
        if record is None:
            return None
        if record.expires_at <= datetime.now(UTC):
            self._records.pop(key, None)
            return None
        return record

    def set(self, record: StoredIdempotencyRecord) -> None:
        self._records[(record.tenant_id, record.endpoint_key, record.idempotency_key)] = record


class RedisIdempotencyStore:
    """Redis-backed idempotency store for distributed deployments.

    Falls back to in-memory operation if Redis is unavailable, but logs
    a warning so operators know the store is not shared across workers.

    Includes a recovery mechanism that periodically attempts to reconnect
    to Redis after failures.
    """

    def __init__(self, redis_client: Any, recovery_interval_seconds: int = 60) -> None:
        self._redis = redis_client
        self._fallback = InMemoryIdempotencyStore()
        self._fallback_active = False
        self._recovery_interval_seconds = recovery_interval_seconds
        self._last_recovery_attempt = 0.0

    def _make_key(self, tenant_id: str, endpoint_key: str, idempotency_key: str) -> str:
        return f"idempotency:{tenant_id}:{endpoint_key}:{idempotency_key}"

    def _attempt_recovery(self) -> bool:
        """Attempt to recover Redis connectivity by performing a simple PING.

        Returns True if recovery succeeded, False otherwise.
        """
        now = time.time()
        if now - self._last_recovery_attempt < self._recovery_interval_seconds:
            return False

        self._last_recovery_attempt = now
        try:
            # Handle both sync and async Redis clients
            if hasattr(self._redis, "ping"):
                ping_result = self._redis.ping()
                # If the client is async, the result is a coroutine
                if asyncio.iscoroutine(ping_result):
                    # This method is called from sync context, so we can't await
                    # Fall back to sync check or skip recovery for async clients
                    logger.debug("Redis client is async; recovery check skipped in sync context")
                    return False
            else:
                # Fallback for clients without ping method
                return False
            logger.info("Redis idempotency store recovered from fallback mode")
            self._fallback_active = False
            return True
        except Exception as exc:
            logger.debug("Redis idempotency recovery attempt failed: %s", exc)
            return False

    def _record_to_json(self, record: StoredIdempotencyRecord) -> str:
        return json.dumps({
            "tenant_id": record.tenant_id,
            "endpoint_key": record.endpoint_key,
            "idempotency_key": record.idempotency_key,
            "request_fingerprint": record.request_fingerprint,
            "status_code": record.status_code,
            "body": record.body,
            "headers": record.headers,
            "expires_at": record.expires_at.isoformat(),
        })

    def _record_from_json(self, raw: str) -> StoredIdempotencyRecord:
        data = json.loads(raw)
        return StoredIdempotencyRecord(
            tenant_id=data["tenant_id"],
            endpoint_key=data["endpoint_key"],
            idempotency_key=data["idempotency_key"],
            request_fingerprint=data["request_fingerprint"],
            status_code=data["status_code"],
            body=data["body"],
            headers=data["headers"],
            expires_at=datetime.fromisoformat(data["expires_at"]),
        )

    def get(self, tenant_id: str, endpoint_key: str, idempotency_key: str) -> StoredIdempotencyRecord | None:
        if self._fallback_active:
            # Attempt recovery before using fallback
            if self._attempt_recovery():
                # Recovery succeeded, try Redis again
                pass
            else:
                return self._fallback.get(tenant_id, endpoint_key, idempotency_key)

        try:
            raw = self._redis.get(self._make_key(tenant_id, endpoint_key, idempotency_key))
            if raw is None:
                return None
            return self._record_from_json(raw)
        except Exception as exc:
            logger.warning("Redis idempotency get failed, falling back to in-memory: %s", exc)
            self._fallback_active = True
            return self._fallback.get(tenant_id, endpoint_key, idempotency_key)

    def set(self, record: StoredIdempotencyRecord) -> None:
        if self._fallback_active:
            # Attempt recovery before using fallback
            if self._attempt_recovery():
                # Recovery succeeded, try Redis again
                pass
            else:
                self._fallback.set(record)
                return

        try:
            ttl_seconds = max(1, int((record.expires_at - datetime.now(UTC)).total_seconds()))
            key = self._make_key(record.tenant_id, record.endpoint_key, record.idempotency_key)
            self._redis.setex(key, ttl_seconds, self._record_to_json(record))
        except Exception as exc:
            logger.warning("Redis idempotency set failed, falling back to in-memory: %s", exc)
            self._fallback_active = True
            self._fallback.set(record)
