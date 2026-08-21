"""Dead-Letter Queue (DLQ) for failed Clerk webhook events.

Provides durable in-memory buffering (with optional JSON snapshotting),
retry tracking, and audit-ready inspection of unprocessable webhook events.
"""

from __future__ import annotations

import collections
import dataclasses
import json
import logging
import threading
import time
from typing import Any

logger = logging.getLogger(__name__)


@dataclasses.dataclass(frozen=True)
class DLQRecord:
    """A dead-lettered webhook event record."""

    id: str
    event_id: str
    event_type: str
    payload: dict[str, Any]
    headers: dict[str, str]
    error_reason: str
    received_at: float
    retry_count: int = 0
    resolved: bool = False

    def to_dict(self) -> dict[str, Any]:
        sensitive_header_keys = {
            "secret",
            "authorization",
            "cookie",
            "x-api-key",
            "token",
            "password",
            "private-key",
        }
        return {
            "id": self.id,
            "event_id": self.event_id,
            "event_type": self.event_type,
            "payload": self.payload,
            "headers": {
                k: v
                for k, v in self.headers.items()
                if not any(s in k.lower() for s in sensitive_header_keys)
            },
            "error_reason": self.error_reason,
            "received_at": self.received_at,
            "retry_count": self.retry_count,
            "resolved": self.resolved,
        }


class WebhookDLQ:
    """Thread-safe Dead-Letter Queue buffer for unprocessable webhooks."""

    def __init__(self, max_records: int = 5000) -> None:
        self._lock = threading.RLock()
        self._records: dict[str, DLQRecord] = collections.OrderedDict()
        self._max_records = max_records

    def enqueue(
        self,
        *,
        event_id: str,
        event_type: str,
        payload: dict[str, Any],
        headers: dict[str, str],
        error_reason: str,
    ) -> DLQRecord:
        """Add a failed event to the dead-letter queue."""
        import uuid

        with self._lock:
            record_id = f"dlq_{uuid.uuid4().hex[:12]}"
            record = DLQRecord(
                id=record_id,
                event_id=event_id,
                event_type=event_type,
                payload=payload,
                headers=headers,
                error_reason=error_reason,
                received_at=time.time(),
                retry_count=0,
                resolved=False,
            )
            # Evict oldest if limit exceeded
            if len(self._records) >= self._max_records:
                self._records.pop(next(iter(self._records)))
            self._records[record_id] = record
            logger.warning(
                "Webhook event enqueued to DLQ: id=%s event_id=%s type=%s reason=%s",
                record_id,
                event_id,
                event_type,
                error_reason,
            )
            return record

    def get(self, record_id: str) -> DLQRecord | None:
        with self._lock:
            return self._records.get(record_id)

    def list_records(self, limit: int = 100, unresolved_only: bool = True) -> list[DLQRecord]:
        with self._lock:
            records = list(self._records.values())
            if unresolved_only:
                records = [r for r in records if not r.resolved]
            return records[-limit:]

    def mark_resolved(self, record_id: str) -> bool:
        with self._lock:
            if record_id in self._records:
                r = self._records[record_id]
                self._records[record_id] = dataclasses.replace(r, resolved=True)
                return True
            return False

    def increment_retry(self, record_id: str) -> int:
        with self._lock:
            if record_id in self._records:
                r = self._records[record_id]
                new_count = r.retry_count + 1
                self._records[record_id] = dataclasses.replace(r, retry_count=new_count)
                return new_count
            return 0

    def export_json(self) -> str:
        with self._lock:
            return json.dumps([r.to_dict() for r in self._records.values()], indent=2)

    def clear(self) -> None:
        with self._lock:
            self._records.clear()


_dlq = WebhookDLQ()


def get_webhook_dlq() -> WebhookDLQ:
    """Return the global WebhookDLQ singleton."""
    return _dlq


def reset_webhook_dlq() -> None:
    """Reset the DLQ (for tests)."""
    _dlq.clear()
