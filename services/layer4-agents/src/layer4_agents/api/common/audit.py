from __future__ import annotations

"""Shared audit helpers for API routes."""


from collections.abc import Mapping
from typing import Any

from value_fabric.shared.audit import AuditEmitter, emit_audit_event
from value_fabric.shared.identity.context import RequestContext

from ...database import get_db_from_context


async def emit_and_persist_audit(
    *,
    action: Any,
    context: RequestContext,
    resource_type: str,
    resource_id: str,
    details: Mapping[str, Any] | None = None,
) -> None:
    """Emit an audit event and persist it using the route DB dependency factory."""
    event = emit_audit_event(
        action,
        tenant_id=context.tenant_id,
        user_id=context.user_id,
        api_key_id=context.api_key_id,
        resource_type=resource_type,
        resource_id=resource_id,
        details=dict(details or {}),
    )
    await AuditEmitter.write_to_db(event, get_db_from_context)


async def emit_route_audit(
    *,
    action: Any,
    context: RequestContext,
    resource_type: str,
    resource_id: str,
    details: Mapping[str, Any] | None = None,
) -> None:
    """Route-level alias for consistent audit emission semantics."""
    await emit_and_persist_audit(
        action=action,
        context=context,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
    )
