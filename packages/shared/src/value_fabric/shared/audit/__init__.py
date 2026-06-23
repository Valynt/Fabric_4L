"""Shared audit log package for Value Fabric.

Provides:
- AuditAction  — canonical enum of auditable actions
- AuditEvent   — Pydantic model for an audit record
- AuditEmitter — async emitter; writes via Redis-backed queue or direct DB
- RedisAuditQueue — durable Redis list for audit events
- AuditWorker — background worker draining queue to PostgreSQL
"""

from .models import (
    AuditAction,
    AuditEvent,
    AuditOutcome,
    TenantResolvedDetails,
    TenantContextSetDetails,
    ToolInvocationRecord,
    PolicyDecisionRecord,
    MemoryAccessRecord,
    ReplaySnapshotRecord,
)
from .redis_queue import RedisAuditQueue
from .worker import AuditWorker
from .siem_integration import SIEMAuditSink, SIEMDeliveryConfig

# Lazy-load emitter to avoid circular import with Layer 4 routes
# that import from this package during module initialization.
def __getattr__(name: str):
    if name in ("AuditEmitter", "emit_audit_event"):
        from .emitter import AuditEmitter, emit_audit_event
        globals()["AuditEmitter"] = AuditEmitter
        globals()["emit_audit_event"] = emit_audit_event
        return AuditEmitter if name == "AuditEmitter" else emit_audit_event
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "TenantResolvedDetails",
    "TenantContextSetDetails",
    "AuditAction",
    "AuditEvent",
    "AuditOutcome",
    "AuditEmitter",
    "emit_audit_event",
    "RedisAuditQueue",
    "AuditWorker",
    "ToolInvocationRecord",
    "PolicyDecisionRecord",
    "MemoryAccessRecord",
    "ReplaySnapshotRecord",
    "SIEMAuditSink",
    "SIEMDeliveryConfig",
]
