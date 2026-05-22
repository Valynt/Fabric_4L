from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import time
from dataclasses import dataclass, field
from datetime import timezone
from typing import Any, Callable, Dict, List, Optional

import httpx

from .models import AuditEvent

SENSITIVE_FIELDS = {"password", "secret", "token", "api_key", "client_secret", "private_key"}


@dataclass
class DeliveryMetrics:
    delivered_total: int = 0
    failed_total: int = 0
    duplicate_suppressed_total: int = 0
    slo_breaches_total: int = 0
    delivery_latency_seconds: List[float] = field(default_factory=list)


@dataclass
class DeadLetterRecord:
    event_id: str
    payload: Dict[str, Any]
    reason: str
    failed_at_unix: float


@dataclass
class SIEMDeliveryConfig:
    endpoint: str
    auth_header: Optional[str] = None
    signature_secret: Optional[str] = None
    max_retries: int = 3
    backoff_seconds: float = 0.2
    timeout_seconds: float = 5.0
    slo_seconds: float = 300.0


class SIEMAuditSink:
    """Transforms internal audit events and delivers to SIEM webhooks."""

    schema_version = "v1"

    def __init__(
        self,
        config: SIEMDeliveryConfig,
        *,
        sleeper: Callable[[float], Any] = asyncio.sleep,
        client_factory: Callable[[], httpx.AsyncClient] | None = None,
        now_fn: Callable[[], float] = time.time,
    ) -> None:
        self._config = config
        self._sleeper = sleeper
        self._now_fn = now_fn
        self._client_factory = client_factory or (
            lambda: httpx.AsyncClient(timeout=self._config.timeout_seconds)
        )
        self._seen_event_ids: set[str] = set()
        self.dead_letter_queue: List[DeadLetterRecord] = []
        self.metrics = DeliveryMetrics()

    def to_siem_schema(self, event: AuditEvent, *, trace_id: Optional[str] = None) -> Dict[str, Any]:
        details = self._redact(event.details)
        return {
            "schema_version": self.schema_version,
            "event_id": str(event.id),
            "tenant_id": str(event.tenant_id) if event.tenant_id else None,
            "actor": {"user_id": event.user_id, "api_key_id": event.api_key_id},
            "action": event.action,
            "target": {"resource_type": event.resource_type, "resource_id": event.resource_id},
            "outcome": event.outcome,
            "trace": {"request_id": event.request_id, "trace_id": trace_id},
            "timestamps": {
                "created_at": event.timestamp.astimezone(timezone.utc).isoformat(),
                "dispatched_at": None,
            },
            "details": details,
        }

    async def deliver(self, event: AuditEvent, *, trace_id: Optional[str] = None) -> bool:
        event_id = str(event.id)
        if event_id in self._seen_event_ids:
            self.metrics.duplicate_suppressed_total += 1
            return True

        payload = self.to_siem_schema(event, trace_id=trace_id)
        payload["timestamps"]["dispatched_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(self._now_fn()))

        headers = self._headers(payload)
        last_error = "unknown"
        for attempt in range(self._config.max_retries + 1):
            try:
                async with self._client_factory() as client:
                    response = await client.post(self._config.endpoint, json=payload, headers=headers)
                if 200 <= response.status_code < 300:
                    self._seen_event_ids.add(event_id)
                    self.metrics.delivered_total += 1
                    latency = max(0.0, self._now_fn() - event.timestamp.timestamp())
                    self.metrics.delivery_latency_seconds.append(latency)
                    if latency > self._config.slo_seconds:
                        self.metrics.slo_breaches_total += 1
                    return True
                last_error = f"http_{response.status_code}"
            except Exception as exc:  # noqa: BLE001
                last_error = str(exc)

            if attempt < self._config.max_retries:
                await self._sleeper(self._config.backoff_seconds * (2**attempt))

        self.metrics.failed_total += 1
        self.dead_letter_queue.append(
            DeadLetterRecord(
                event_id=event_id,
                payload=payload,
                reason=last_error,
                failed_at_unix=self._now_fn(),
            )
        )
        return False

    async def replay_dead_letters(self) -> int:
        replayed = 0
        remaining: List[DeadLetterRecord] = []
        for record in self.dead_letter_queue:
            ok = await self._deliver_payload(record.event_id, record.payload)
            if ok:
                replayed += 1
            else:
                remaining.append(record)
        self.dead_letter_queue = remaining
        return replayed

    async def _deliver_payload(self, event_id: str, payload: Dict[str, Any]) -> bool:
        headers = self._headers(payload)
        try:
            async with self._client_factory() as client:
                response = await client.post(self._config.endpoint, json=payload, headers=headers)
            if 200 <= response.status_code < 300:
                self._seen_event_ids.add(event_id)
                return True
        except Exception:
            return False
        return False

    def _headers(self, payload: Dict[str, Any]) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "X-Event-ID": payload["event_id"],
            "Idempotency-Key": payload["event_id"],
        }
        if self._config.auth_header:
            headers["Authorization"] = self._config.auth_header
        if self._config.signature_secret:
            body = json.dumps(payload, sort_keys=True).encode("utf-8")
            sig = hmac.new(self._config.signature_secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
            headers["X-Signature-SHA256"] = sig
        return headers

    def _redact(self, details: Dict[str, Any]) -> Dict[str, Any]:
        return {k: ("[REDACTED]" if k.lower() in SENSITIVE_FIELDS else v) for k, v in details.items()}
