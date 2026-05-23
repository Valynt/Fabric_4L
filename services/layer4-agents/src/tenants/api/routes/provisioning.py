"""Tenant provisioning status and webhook endpoints.

Webhook security uses HMAC-SHA256 signature verification with idempotency
tracking to prevent duplicate processing.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import time
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from value_fabric.shared.audit import AuditAction, AuditOutcome, emit_audit_event
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_authenticated, require_super_admin

from ....database import get_db_from_context
from ...provisioning import (
    ProvisioningStatus,
    TenantProvisioningService,
    provision_tenant,
)
from ...service import get_tenant

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tenants/{tenant_id}/provisioning", tags=["Provisioning"])

# In-memory idempotency cache (production: use Redis or DB table)
# Maps webhook_id -> {"status": str, "tenant_id": str, "processed_at": float}
_processed_webhooks: dict[str, dict] = {}
_WEBHOOK_CACHE_TTL_SECONDS = 86400  # 24 hours
_WEBHOOK_SIGNATURE_TOLERANCE_SECONDS = 300  # 5 minutes


class ProvisioningStatusResponse(BaseModel):
    """Response for provisioning status query."""

    tenant_id: str
    status: str
    current_step: str | None
    completed_steps: list[str]
    error: str | None
    retryable: bool
    started_at: str | None
    completed_at: str | None
    retry_count: int
    max_retries: int


class RetryProvisioningResponse(BaseModel):
    """Response from retry provisioning request."""

    message: str
    tenant_id: str
    status: str


class WebhookProvisioningRequest(BaseModel):
    """Request to trigger provisioning via webhook.

    The request body is signed with HMAC-SHA256 using a shared secret.
    The signature is passed in the X-Webhook-Signature header.
    """

    tenant_id: UUID
    timestamp: int = Field(
        ...,
        description="Unix timestamp of the request (for replay protection)",
    )
    metadata: dict | None = Field(
        default=None,
        description="Optional metadata from the external system",
    )


class WebhookProvisioningResponse(BaseModel):
    """Response from webhook provisioning request."""

    message: str
    tenant_id: str
    status: str
    webhook_id: str | None = None


def _verify_hmac_signature(
    payload: bytes,
    signature: str,
    secret: str,
) -> bool:
    """Verify HMAC-SHA256 signature using constant-time comparison.

    Args:
        payload: Raw request body bytes
        signature: Hex-encoded HMAC-SHA256 signature from header
        secret: Shared webhook secret

    Returns:
        True if signature is valid
    """
    expected = hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(signature, expected)


def _cleanup_expired_webhooks() -> None:
    """Remove expired entries from the idempotency cache."""
    now = time.time()
    expired = [
        wid
        for wid, data in _processed_webhooks.items()
        if now - data.get("processed_at", 0) > _WEBHOOK_CACHE_TTL_SECONDS
    ]
    for wid in expired:
        del _processed_webhooks[wid]


@router.get("/status", response_model=ProvisioningStatusResponse)
async def get_provisioning_status(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db_from_context),
    context: RequestContext = Depends(require_authenticated),
) -> ProvisioningStatusResponse:
    """Get provisioning status for a tenant.

    Returns the current state of tenant provisioning including:
    - Overall status (pending, in_progress, completed, failed, etc.)
    - Current step being executed
    - List of completed steps
    - Error information if failed
    - Retry information
    """
    # Verify tenant exists
    tenant = await get_tenant(db, tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    # Check permissions - only tenant admin or super admin can view
    if str(context.tenant_id) != str(tenant_id) and not context.is_super_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Create provisioning service to get state
    service = TenantProvisioningService(db)

    # Try to get current state by attempting to provision
    # This will return completed state if already done
    state = await service.provision_tenant(tenant_id)

    return ProvisioningStatusResponse(
        tenant_id=str(tenant_id),
        status=state.status.value,
        current_step=state.current_step.name if state.current_step else None,
        completed_steps=[s.name for s in state.completed_steps],
        error=state.error,
        retryable=state.retryable,
        started_at=state.started_at.isoformat() if state.started_at else None,
        completed_at=state.completed_at.isoformat() if state.completed_at else None,
        retry_count=state.retry_count,
        max_retries=state.max_retries,
    )


@router.post("/retry", response_model=RetryProvisioningResponse)
async def retry_provisioning(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db_from_context),
    context: RequestContext = Depends(require_super_admin),
) -> RetryProvisioningResponse:
    """Retry failed provisioning for a tenant (super admin only).

    This endpoint allows super admins to manually retry provisioning
    for tenants that failed and are marked as retryable.
    """
    # Verify tenant exists
    tenant = await get_tenant(db, tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    # Retry provisioning with force flag
    service = TenantProvisioningService(db)
    state = await service.provision_tenant(tenant_id, force_retry=True)

    if state.status == ProvisioningStatus.COMPLETED:
        return RetryProvisioningResponse(
            message="Provisioning completed successfully",
            tenant_id=str(tenant_id),
            status=state.status.value,
        )
    elif state.status == ProvisioningStatus.FAILED:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Provisioning retry failed",
                "error": state.error,
                "retryable": state.retryable,
            },
        )
    else:
        return RetryProvisioningResponse(
            message="Provisioning in progress",
            tenant_id=str(tenant_id),
            status=state.status.value,
        )


@router.post(
    "/webhook",
    response_model=WebhookProvisioningResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def webhook_provisioning(
    tenant_id: UUID,
    http_request: Request,
    x_webhook_signature: str = Header(
        ...,
        alias="X-Webhook-Signature",
        description="HMAC-SHA256 hex digest of the request body",
    ),
    x_webhook_id: str = Header(
        ...,
        alias="X-Webhook-ID",
        description="Unique webhook delivery ID for idempotency",
    ),
    # SECURITY: Webhook uses get_db intentionally — external systems
    # authenticate via HMAC signature, not JWT.
    db: AsyncSession = Depends(get_db_from_context),
) -> WebhookProvisioningResponse:
    """Trigger provisioning via webhook (external systems).

    Security:
    - HMAC-SHA256 signature verification using shared secret
    - Timestamp validation to prevent replay attacks (5 min tolerance)
    - Idempotency via X-Webhook-ID header (24h dedup window)

    The webhook secret should be configured in environment variables:
    PROVISIONING_WEBHOOK_SECRET
    """
    # --- Step 1: Verify HMAC signature ---
    webhook_secret = os.getenv("PROVISIONING_WEBHOOK_SECRET", "")
    if not webhook_secret:
        logger.error("PROVISIONING_WEBHOOK_SECRET not configured")
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Webhook provisioning not configured",
        )

    body = await http_request.body()
    if not _verify_hmac_signature(body, x_webhook_signature, webhook_secret):
        logger.warning(
            "Invalid webhook signature for webhook_id=%s tenant_id=%s",
            x_webhook_id,
            tenant_id,
        )
        await emit_audit_event(
            action=AuditAction.TENANT_PROVISIONED_WEBHOOK,
            outcome=AuditOutcome.DENIED,
            tenant_id=tenant_id,
            details={
                "webhook_id": x_webhook_id,
                "reason": "invalid_signature",
            },
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )

    # --- Step 2: Parse and validate payload ---
    import json

    try:
        payload = WebhookProvisioningRequest(**json.loads(body))
    except Exception as e:
        logger.warning("Invalid webhook payload: %s", e)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid webhook payload",
        ) from e

    # Validate timestamp (replay protection)
    now = int(time.time())
    if abs(now - payload.timestamp) > _WEBHOOK_SIGNATURE_TOLERANCE_SECONDS:
        logger.warning(
            "Webhook timestamp out of tolerance: webhook_id=%s delta=%ds",
            x_webhook_id,
            abs(now - payload.timestamp),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Webhook timestamp expired or too far in the future",
        )

    # --- Step 3: Idempotency check ---
    _cleanup_expired_webhooks()
    if x_webhook_id in _processed_webhooks:
        cached = _processed_webhooks[x_webhook_id]
        logger.info("Duplicate webhook_id=%s, returning cached result", x_webhook_id)
        return WebhookProvisioningResponse(
            message="Already processed (idempotent)",
            tenant_id=cached["tenant_id"],
            status=cached["status"],
            webhook_id=x_webhook_id,
        )

    # --- Step 4: Verify tenant exists ---
    tenant = await get_tenant(db, payload.tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    # --- Step 5: Execute provisioning ---
    state = await provision_tenant(db, payload.tenant_id)

    # Cache result for idempotency
    _processed_webhooks[x_webhook_id] = {
        "status": state.status.value,
        "tenant_id": str(payload.tenant_id),
        "processed_at": time.time(),
    }

    # Emit audit event
    await emit_audit_event(
        action=AuditAction.TENANT_PROVISIONED_WEBHOOK,
        outcome=(
            AuditOutcome.SUCCESS
            if state.status == ProvisioningStatus.COMPLETED
            else AuditOutcome.FAILURE
        ),
        tenant_id=payload.tenant_id,
        details={
            "webhook_id": x_webhook_id,
            "provisioning_status": state.status.value,
            "metadata": payload.metadata,
        },
    )

    if state.status == ProvisioningStatus.COMPLETED:
        return WebhookProvisioningResponse(
            message="Provisioning completed",
            tenant_id=str(payload.tenant_id),
            status=state.status.value,
            webhook_id=x_webhook_id,
        )
    elif state.status == ProvisioningStatus.FAILED:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Provisioning failed",
                "error": state.error,
                "retryable": state.retryable,
                "webhook_id": x_webhook_id,
            },
        )
    else:
        return WebhookProvisioningResponse(
            message="Provisioning initiated",
            tenant_id=str(payload.tenant_id),
            status=state.status.value,
            webhook_id=x_webhook_id,
        )
