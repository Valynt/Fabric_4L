"""Audit event emitter.

Design (per review feedback — no Celery):
- Primary path: structured JSON log to stdout via ``logging``.  In production
  this is captured by the log aggregator (e.g., Loki, Datadog, CloudWatch)
  and can be ingested into the audit_events table by a log-router sidecar.
- Secondary path (optional): if a ``db_session_factory`` is provided at
  construction time, events are also persisted directly to ``audit_events``
  via a FastAPI ``BackgroundTask`` (fire-and-forget, zero latency on the
  hot path).

The dual-path approach means audit logging works immediately without
requiring any additional infrastructure, and the DB write is a progressive
enhancement.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Any, Callable, Dict, Optional, Set
from uuid import UUID, uuid4

try:
    from prometheus_client import Counter, REGISTRY

    _METRIC_NAME = "value_fabric_audit_write_failures_total"
    if _METRIC_NAME in REGISTRY._names_to_collectors:
        _AUDIT_WRITE_FAILURES = REGISTRY._names_to_collectors[_METRIC_NAME]
    else:
        _AUDIT_WRITE_FAILURES = Counter(
            _METRIC_NAME,
            "Total number of audit event write failures",
            ["failure_type"],
        )
    _METRICS_AVAILABLE = True
except ImportError:
    _METRICS_AVAILABLE = False
    _AUDIT_WRITE_FAILURES = None

import httpx

from .models import AuditAction, AuditEvent, AuditOutcome
from .redis_queue import RedisAuditQueue
from value_fabric.shared.models.typed_dict import TypedDictModel
from value_fabric.shared.security.redaction import REDACTED_VALUE, is_sensitive_key, redact_value


class _scrub_detailsResult(TypedDictModel):
    pass

logger = logging.getLogger("vf.audit")


class _AuditConfigValidation:
    """Awaitable result for startup audit-sink validation.

    The historical startup gate calls ``validate_audit_config()`` synchronously for
    fail-fast missing-production configuration and awaits it for optional
    reachability checks. This lightweight awaitable preserves both call patterns
    without forcing synchronous callers to manage an event loop.
    """

    def __init__(self, audit_sink_url: str, timeout: float) -> None:
        self.audit_sink_url = audit_sink_url
        self.timeout = timeout

    def __await__(self):
        return self._run().__await__()

    async def _run(self) -> None:
        if not self.audit_sink_url:
            return None
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.audit_sink_url,
                    json={"event": "startup_audit_validation", "status": "probe"},
                )
                response.raise_for_status()
        except Exception as exc:
            raise ValueError(f"Audit sink is unreachable: {exc}") from exc
        return None


def validate_audit_config() -> _AuditConfigValidation:
    """Validate audit-sink startup configuration.

    Production must be configured fail-closed with an explicit audit sink. In
    development, a missing sink is allowed but logged as a degraded control so
    local startup remains usable while the operator-visible warning contract is
    preserved.
    """

    environment = os.getenv("ENVIRONMENT", "development").lower()
    audit_sink_url = os.getenv("AUDIT_SINK_URL", "")
    timeout_raw = os.getenv("AUDIT_SINK_TIMEOUT", "5")
    try:
        timeout = float(timeout_raw)
    except ValueError:
        timeout = 5.0

    if environment == "production" and not audit_sink_url:
        raise ValueError("AUDIT_SINK_URL is required in production")

    if environment == "development" and not audit_sink_url:
        logger.warning(
            "Audit sink is not configured in development mode; audit events are "
            "limited to structured logs until AUDIT_SINK_URL is set."
        )

    ledger_mode = os.getenv("AUDIT_LEDGER_MODE", "disabled").lower()
    instance_count_raw = os.getenv("INSTANCE_COUNT", "1")
    try:
        instance_count = int(instance_count_raw)
    except ValueError:
        instance_count = 1
    redis_url = os.getenv("REDIS_URL", "")
    if ledger_mode == "enabled" and instance_count > 1 and not redis_url:
        raise ValueError(
            "AUDIT_LEDGER_MODE=enabled requires distributed chain backend in multi-instance "
            "deployments. Configure REDIS_URL (or disable ledger mode) to prevent hash forks."
        )

    return _AuditConfigValidation(audit_sink_url=audit_sink_url, timeout=timeout)

# Keys that must never appear in the structured log (scrubbed from ``details``).
_SENSITIVE_KEYS: Set[str] = {
    "authorization",
    "card_number",
    "checkout_session",
    "client_secret",
    "password",
    "hashed_password",
    "payment_details",
    "payment_method",
    "session_token",
    "secret",
    "token",
    "api_key",
    "key_hash",
    "access_token",
    "refresh_token",
    "private_key",
    "stripe_payment_intent",
    "vf_session",
}


def _scrub_value(value: Any) -> Any:
    if isinstance(value, dict):
        return _scrub_details(value)
    if isinstance(value, list):
        return [_scrub_value(item) for item in value]
    return redact_value(value)


def _scrub_details(details: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of *details* with sensitive keys replaced by '[REDACTED]'."""
    # Keep the public emitter contract as a plain mapping.  The lightweight
    # TypedDictModel wrapper is useful for generated typing, but AuditEvent and
    # downstream DB serialization expect a concrete dict.
    return {
        k: REDACTED_VALUE if k.lower() in _SENSITIVE_KEYS or is_sensitive_key(k) else _scrub_value(v)
        for k, v in details.items()
    }


# ---------------------------------------------------------------------------
# Global helper — call this from any layer
# ---------------------------------------------------------------------------


def emit_audit_event(
    action: AuditAction,
    *,
    tenant_id: Optional[UUID] = None,
    user_id: Optional[str] = None,
    api_key_id: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    request_id: Optional[str] = None,
    outcome: AuditOutcome = AuditOutcome.SUCCESS,
    details: Optional[Dict[str, Any]] = None,
    chain_id: Optional[str] = None,
) -> AuditEvent:
    """Create and emit an audit event.

    The event is written to the structured audit logger immediately.
    Returns the :class:`AuditEvent` so callers can pass it to the DB writer
    via a BackgroundTask if desired.

    Example::

        from value_fabric.shared.audit import emit_audit_event, AuditAction

        event = emit_audit_event(
            AuditAction.TENANT_CREATED,
            tenant_id=new_tenant.id,
            user_id=ctx.user_id,
            resource_type="Tenant",
            resource_id=str(new_tenant.id),
        )
        background_tasks.add_task(AuditEmitter.write_to_db, event, get_db)
    """
    safe_details = _scrub_details(details or {})

    event = AuditEvent(
        action=action,
        tenant_id=tenant_id,
        user_id=user_id,
        api_key_id=api_key_id,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=ip_address,
        user_agent=user_agent,
        request_id=request_id,
        outcome=outcome,
        details=safe_details,
        chain_id=chain_id,
    )

    # Write to structured log (always).  Sensitive keys are scrubbed above.
    # Wrapped in try/except so logger failures never break the caller.
    try:
        logger.info(
        json.dumps(
            {
                "audit": True,
                "event_id": str(event.id),
                "action": event.action,
                "tenant_id": str(event.tenant_id) if event.tenant_id else None,
                "user_id": event.user_id,
                "api_key_id": event.api_key_id,
                "resource_type": event.resource_type,
                "resource_id": event.resource_id,
                "outcome": event.outcome,
                "ip_address": event.ip_address,
                "request_id": event.request_id,
                "timestamp": event.timestamp.isoformat(),
                "details": event.details,
                "chain_id": chain_id,
            }
        )
    )
    except Exception:
        # Logger failure - swallow to avoid breaking caller
        pass

    return event


# Compatibility helper used by test_ledger_chain.py
def _create_audit_event(
    action: AuditAction,
    *,
    tenant_id: Optional[UUID] = None,
    user_id: Optional[str] = None,
    api_key_id: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    request_id: Optional[str] = None,
    outcome: AuditOutcome = AuditOutcome.SUCCESS,
    details: Optional[Dict[str, Any]] = None,
    chain_id: Optional[str] = None,
) -> AuditEvent:
    """Create an AuditEvent without emitting to the log stream.

    Used by ledger chain tests and other callers that need a plain
    event object for correlation without side effects.
    """
    safe_details = _scrub_details(details or {})
    return AuditEvent(
        action=action,
        tenant_id=tenant_id,
        user_id=user_id,
        api_key_id=api_key_id,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=ip_address,
        user_agent=user_agent,
        request_id=request_id,
        outcome=outcome,
        details=safe_details,
        chain_id=chain_id,
    )


# ---------------------------------------------------------------------------
# AuditEmitter — optional DB persistence via BackgroundTask
# ---------------------------------------------------------------------------


class AuditEmitter:
    """Handles optional DB persistence of audit events.

    Usage in a FastAPI route::

        @router.post("/v1/tenants")
        async def create_tenant(
            request: TenantCreateRequest,
            background_tasks: BackgroundTasks,
            ctx = Depends(require_super_admin),
            db: AsyncSession = Depends(get_db_from_context),
        ):
            tenant = await service.create_tenant(db, request)
            event = emit_audit_event(
                AuditAction.TENANT_CREATED,
                tenant_id=tenant.id,
                user_id=ctx.user_id,
                resource_type="Tenant",
                resource_id=str(tenant.id),
            )
            background_tasks.add_task(AuditEmitter.write_to_db, event, get_db_from_context)
            return tenant
    """

    @staticmethod
    async def write_to_db(
        event: AuditEvent,
        db_factory: Callable,
        queue: RedisAuditQueue | None = None,
    ) -> None:
        """Persist an audit event to the ``audit_events`` table.

        P1-005: When a Redis queue is available, events are pushed to the
        durable queue instead of being written directly.  A background worker
        drains the queue to PostgreSQL with exponential-backoff retry.
        This survives DB blips and prevents audit loss.

        Args:
            event:      The :class:`AuditEvent` to persist.
            db_factory: An async context manager factory (e.g. ``get_db``
                        from ``layer4-agents/src/database.py``).
            queue:      Optional :class:`RedisAuditQueue`.  If ``None``,
                        one is created from ``REDIS_URL`` env var.
        """
        _queue = queue or RedisAuditQueue.from_env()
        if _queue._available:
            pushed = await _queue.push(event)
            if pushed:
                return
            # Redis push failed → fall through to direct write

        # Fallback: direct DB write (original behaviour)
        try:
            async with db_factory() as session:
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
        except Exception as exc:
            logger.error(
                "Failed to persist audit event %s to DB: %s",
                event.id,
                exc,
                exc_info=True,
            )
            if _METRICS_AVAILABLE and _AUDIT_WRITE_FAILURES is not None:
                _AUDIT_WRITE_FAILURES.labels(failure_type="db_write").inc()
