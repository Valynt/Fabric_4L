"""
Admin tools with strict permission enforcement.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from value_fabric.shared.audit import AuditAction, AuditOutcome, emit_audit_event
from value_fabric.shared.error_handling.exceptions import (
    ConflictError,
    NotFoundError,
    ServiceUnavailableError,
    ValueFabricException,
)
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.policy_registry import authorize_action
from value_fabric.shared.models.typed_dict import TypedDictModel

from ..tenants.service import update_tenant_status


class suspend_tenantResult(TypedDictModel):
    success: bool
    tenant_id: Any
    status: str


logger = logging.getLogger(__name__)


async def suspend_tenant(
    tenant_id: UUID,
    context: RequestContext | None = None,
    db: AsyncSession | None = None,
    reason: str | None = None,
) -> dict[str, str | bool]:
    context = authorize_action(
        "layer4.tool.admin.suspend_tenant",
        context,
        target_tenant_id=str(tenant_id),
    )

    if db is None:
        raise ServiceUnavailableError(
            message="Tenant suspension requires a database session and cannot be completed as a dry-run tool."
        )

    admin_id = str(context.user_id or "unknown")
    suspension_reason = reason or "Suspended by administrator"

    try:
        updated = await update_tenant_status(
            db,
            tenant_id,
            "suspended",
            reason=suspension_reason,
            changed_by=admin_id,
        )
        if not updated:
            raise NotFoundError(resource_type="Tenant", resource_id=str(tenant_id))
        await db.commit()
    except ValueFabricException:
        raise
    except ValueError as exc:
        logger.warning("admin_tool_value_error", error=str(exc))
        raise ConflictError(message="Admin operation conflict") from exc

    emit_audit_event(
        AuditAction.TENANT_SUSPENDED,
        tenant_id=tenant_id,
        user_id=admin_id,
        resource_type="Tenant",
        resource_id=str(tenant_id),
        request_id=getattr(context, "request_id", None),
        outcome=AuditOutcome.SUCCESS,
        details={"reason": suspension_reason},
    )

    logger.info("Tenant %s suspended by admin %s", tenant_id, admin_id)
    return suspend_tenantResult.model_validate(
        {"success": True, "tenant_id": str(tenant_id), "status": "suspended"}
    )
