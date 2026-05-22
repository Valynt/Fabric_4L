"""Shared audit log package for Value Fabric.

Provides:
- AuditAction  — canonical enum of auditable actions
- AuditEvent   — Pydantic model for an audit record
- AuditEmitter — async emitter; writes via FastAPI BackgroundTasks
"""

from .emitter import AuditEmitter, emit_audit_event
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
    "ToolInvocationRecord",
    "PolicyDecisionRecord",
    "MemoryAccessRecord",
    "ReplaySnapshotRecord",
    "SIEMAuditSink",
    "SIEMDeliveryConfig",
]
