"""
GDPR/ CCPA administrative routes for Fabric 4L.

Provides endpoints for initiating tenant data deletion, querying status,
and retrieving the full immutable deletion report.

All endpoints require admin privileges and enforce role-based access
control (RBAC) via the require_admin dependency.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, Field

from value_fabric.auth import require_admin, get_current_user
from value_fabric.audit import log_audit_event

from .deletion import (
    delete_tenant_data,
    DeletionReport,
    DeletionStatus,
    DeletionError,
    SafetyLimitExceeded,
)
from .store import (
    get_deletion_job,
    save_deletion_job,
    list_deletion_jobs_for_tenant,
)

router = APIRouter(prefix="/admin/gdpr", tags=["gdpr"])


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class DeleteTenantRequest(BaseModel):
    """Request body for initiating a tenant deletion job."""
    tenant_id: str = Field(..., min_length=1, max_length=128,
                           description="Target tenant to erase")
    confirmation: str = Field(..., pattern="^(?i)delete [a-z0-9_-]+$",
                              description="Must be 'delete <tenant_id>' (case-insensitive)")
    reason: str = Field(..., min_length=5, max_length=500,
                        description="Regulatory or business reason for deletion")

    def validate_confirmation(self) -> None:
        expected = f"delete {self.tenant_id}"
        if self.confirmation.lower() != expected:
            raise ValueError(
                f"Confirmation must exactly match: '{expected}'"
            )


class LayerResultSchema(BaseModel):
    layer: str
    records_deleted: int
    tables_affected: list[str]
    duration_ms: int
    status: str
    error: Optional[str] = None


class DeletionStatusResponse(BaseModel):
    request_id: str
    tenant_id: str
    status: str
    initiated_by: str
    initiated_at: str
    completed_at: Optional[str] = None
    total_records_deleted: int
    verification_passed: bool
    progress_pct: float = Field(..., ge=0.0, le=100.0)


class DeletionReportResponse(BaseModel):
    request_id: str
    tenant_id: str
    initiated_by: str
    reason: str
    initiated_at: str
    completed_at: Optional[str] = None
    status: str
    total_records_deleted: int
    verification_passed: bool
    audit_log_hash: Optional[str] = None
    error_summary: Optional[str] = None
    layers: list[LayerResultSchema]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _admin_attr(admin: Any, name: str, default: Any = None) -> Any:
    """Read an attribute from an admin context (dict or object)."""
    if isinstance(admin, dict):
        return admin.get(name, default)
    return getattr(admin, name, default)


def _is_super_admin(admin: Any) -> bool:
    """True only for platform super-admins (cross-tenant authority)."""
    roles = _admin_attr(admin, "roles", None) or []
    values = {str(getattr(role, "value", role)).lower() for role in roles}
    return "super_admin" in values


def _caller_tenant_id(admin: Any) -> Optional[str]:
    tenant = _admin_attr(admin, "tenant_id") or _admin_attr(admin, "tenant")
    if tenant is None:
        return None
    return str(tenant)


def _enforce_tenant_scope(admin: Any, target_tenant_id: str) -> None:
    """Fail closed when a non-super-admin targets another tenant.

    Returns a uniform 404 (never 403) so the response does not reveal
    whether the target tenant or resource exists (no existence oracle).
    """
    if _is_super_admin(admin):
        return
    caller_tenant = _caller_tenant_id(admin)
    if caller_tenant is None or caller_tenant != target_tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found",
        )


def _not_found(request_id: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Deletion request {request_id} not found",
    )

async def _background_delete(
    tenant_id: str,
    request_id: str,
    initiated_by: str,
    reason: str,
) -> None:
    """Background task wrapper that handles DB session lifecycle."""
    try:
        report = await delete_tenant_data(
            tenant_id=tenant_id,
            request_id=request_id,
            initiated_by=initiated_by,
        )
        await save_deletion_job(report, reason=reason)
    except SafetyLimitExceeded as exc:
        await save_deletion_job(
            DeletionReport(
                tenant_id=tenant_id,
                request_id=request_id,
                initiated_by=initiated_by,
            ),
            status=DeletionStatus.FAILED,
            error=str(exc),
            reason=reason,
        )
    except DeletionError as exc:
        # Report already partially saved by delete_tenant_data
        pass


def _to_status_response(
    report: DeletionReport, reason: str = ""
) -> DeletionStatusResponse:
    """Map DeletionReport to the public status schema."""
    total_layers = 6
    completed_layers = sum(
        1 for r in report.results if r.status in ("success", "failed", "partial")
    )
    progress = (completed_layers / total_layers) * 100 if report.status == DeletionStatus.IN_PROGRESS else 100.0

    return DeletionStatusResponse(
        request_id=report.request_id,
        tenant_id=report.tenant_id,
        status=report.status.value,
        initiated_by=report.initiated_by,
        initiated_at=report.initiated_at.isoformat(),
        completed_at=report.completed_at.isoformat() if report.completed_at else None,
        total_records_deleted=report.total_records_deleted,
        verification_passed=report.verification_passed,
        progress_pct=round(progress, 1),
    )


def _to_report_response(
    report: DeletionReport, reason: str = ""
) -> DeletionReportResponse:
    """Map DeletionReport to the full report schema."""
    return DeletionReportResponse(
        request_id=report.request_id,
        tenant_id=report.tenant_id,
        initiated_by=report.initiated_by,
        reason=reason,
        initiated_at=report.initiated_at.isoformat(),
        completed_at=report.completed_at.isoformat() if report.completed_at else None,
        status=report.status.value,
        total_records_deleted=report.total_records_deleted,
        verification_passed=report.verification_passed,
        audit_log_hash=report.audit_log_hash,
        error_summary=report.error_summary,
        layers=[
            LayerResultSchema(
                layer=r.layer,
                records_deleted=r.records_deleted,
                tables_affected=list(r.tables_affected),
                duration_ms=r.duration_ms,
                status=r.status,
                error=r.error,
            )
            for r in report.results
        ],
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/delete-tenant",
    response_model=DeletionStatusResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Initiate tenant data deletion (GDPR/CCPA)",
    responses={
        202: {"description": "Deletion job accepted and running in background"},
        400: {"description": "Invalid confirmation or request body"},
        403: {"description": "Admin access required"},
        409: {"description": "Deletion job already in progress for tenant"},
        422: {"description": "Tenant record count exceeds safety limit"},
    },
)
async def initiate_deletion(
    body: DeleteTenantRequest,
    background_tasks: BackgroundTasks,
    admin: Dict[str, Any] = Depends(require_admin),
) -> DeletionStatusResponse:
    """
    Start an async GDPR/CCPA right-to-erasure job for a tenant.

    The operation runs in the background and can be polled via
    `/deletion-status/{request_id}`.

    **RBAC**: Admin role required. The action is audited under
    `admin.gdpr_deletion_initiated`.
    """
    # Validate confirmation phrase
    try:
        body.validate_confirmation()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Confirmation phrase validation failed") from exc

    # Tenant isolation: a tenant admin may only erase their own tenant.
    _enforce_tenant_scope(admin, body.tenant_id)

    # Idempotency: check for in-progress job on same tenant
    existing = await list_deletion_jobs_for_tenant(body.tenant_id, status_filter="in_progress")
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Deletion already in progress for tenant {body.tenant_id} "
                   f"(request_id: {existing[0].request_id})",
        )

    request_id = str(uuid.uuid4())
    initiated_by = admin.get("user_id", "unknown")

    # Audit: record the initiation before background work starts
    await log_audit_event(
        event_type="admin.gdpr_deletion_initiated",
        actor=initiated_by,
        tenant_id=body.tenant_id,
        resource=f"gdpr_request:{request_id}",
        outcome="accepted",
        metadata={"reason": body.reason},
    )

    # Kick off background deletion
    background_tasks.add_task(
        _background_delete,
        tenant_id=body.tenant_id,
        request_id=request_id,
        initiated_by=initiated_by,
        reason=body.reason,
    )

    # Return immediate status with 202 Accepted
    placeholder = DeletionReport(
        tenant_id=body.tenant_id,
        request_id=request_id,
        initiated_by=initiated_by,
    )
    return _to_status_response(placeholder, reason=body.reason)


@router.get(
    "/deletion-status/{request_id}",
    response_model=DeletionStatusResponse,
    summary="Check deletion job status",
    responses={
        200: {"description": "Current status of the deletion job"},
        403: {"description": "Admin access required"},
        404: {"description": "Request ID not found"},
    },
)
async def get_deletion_status(
    request_id: str,
    admin: Dict[str, Any] = Depends(require_admin),
) -> DeletionStatusResponse:
    """
    Poll the status of a deletion job started via `POST /delete-tenant`.

    Returns progress percentage, record counts, and verification state.
    """
    report, reason = await get_deletion_job(request_id)
    if report is None:
        raise _not_found(request_id)
    # Uniform 404 for cross-tenant reads: do not reveal existence.
    _enforce_tenant_scope(admin, report.tenant_id)
    return _to_status_response(report, reason=reason)


@router.get(
    "/deletion-report/{request_id}",
    response_model=DeletionReportResponse,
    summary="Retrieve full deletion report with audit trail",
    responses={
        200: {"description": "Complete immutable deletion report"},
        403: {"description": "Admin access required"},
        404: {"description": "Request ID not found"},
    },
)
async def get_deletion_report(
    request_id: str,
    admin: Dict[str, Any] = Depends(require_admin),
) -> DeletionReportResponse:
    """
    Return the full, immutable deletion report including:

    - Per-layer deletion results (tables, row counts, duration)
    - Verification pass outcome
    - Cryptographic audit hash
    - Error summaries (if partial failure occurred)

    This record is suitable for regulatory inspection and can be
    exported as PDF/CSV via the admin UI.
    """
    report, reason = await get_deletion_job(request_id)
    if report is None:
        raise _not_found(request_id)
    # Uniform 404 for cross-tenant reads: do not reveal existence.
    _enforce_tenant_scope(admin, report.tenant_id)
    return _to_report_response(report, reason=reason)
