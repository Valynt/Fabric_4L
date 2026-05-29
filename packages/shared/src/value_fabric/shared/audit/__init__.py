"""Shared audit log package for Value Fabric.

Provides:
- AuditAction  — canonical enum of auditable actions
- AuditEvent   — Pydantic model for an audit record
- AuditEmitter — async emitter; writes via Redis-backed queue or direct DB
- RedisAuditQueue — durable Redis list for audit events
- AuditWorker — background worker draining queue to PostgreSQL
"""

from .emitter import AuditEmitter, emit_audit_event
from .redis_queue import RedisAuditQueue
from .worker import AuditWorker
from .siem_integration import SIEMAuditSink, SIEMDeliveryConfig
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
