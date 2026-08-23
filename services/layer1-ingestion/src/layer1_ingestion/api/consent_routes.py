"""Consent management routes for canonical source ingestion.

Provides explicit consent lifecycle endpoints required by Fabric_4L v3.0:
create consent, grant consent, revoke consent, and list active consent.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..shared.consent_service import ConsentService
from ..shared.database import get_db_from_context_sync
from ..shared.models import SourceConsent, SourceConsentStatus

try:
    from value_fabric.shared.observability.logging import get_logger
except ImportError as e:
    raise ImportError(
        f"Failed to import from value_fabric.shared. Ensure packages/shared is in PYTHONPATH. Error: {e}"
    ) from e


logger = get_logger(__name__)
router = APIRouter()


# Lazy dependency imports to avoid circular imports with the main router module.
def _get_tenant_id(request: Request) -> uuid.UUID:
    from .main import get_tenant_id

    return get_tenant_id(request)


def _get_current_user_id(request: Request) -> uuid.UUID:
    from .main import get_current_user_id

    return get_current_user_id(request)


# =============================================================================
# PYDANTIC SCHEMAS
# =============================================================================


class ConsentCreateRequest(BaseModel):
    """Request to create a consent record."""

    account_id: str = Field(..., min_length=1, max_length=255)
    source_type: str = Field(..., min_length=1, max_length=50)
    scope: dict[str, Any] = Field(default_factory=dict)
    expires_at: datetime | None = None


class ConsentGrantRequest(BaseModel):
    """Request to grant an existing consent record."""

    consent_id: str
    expires_at: datetime | None = None


class ConsentRevokeRequest(BaseModel):
    """Request to revoke an existing consent record."""

    consent_id: str


class ConsentResponse(BaseModel):
    """Consent record response."""

    id: str
    tenant_id: str
    account_id: str
    source_type: str
    status: str
    consent_hash: str
    scope: dict[str, Any]
    granted_by: str | None
    granted_at: datetime | None
    expires_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime


# =============================================================================
# API ENDPOINTS
# =============================================================================


async def create_consent(
    request: ConsentCreateRequest,
    http_request: Request,
    org_id: uuid.UUID = Depends(_get_tenant_id),
    user_id: uuid.UUID = Depends(_get_current_user_id),
    db: Session = Depends(get_db_from_context_sync),
):
    """Create a pending consent record for a source ingestion scope."""
    service = ConsentService(db)
    consent = service.create_consent(
        tenant_id=org_id,
        account_id=request.account_id,
        source_type=request.source_type,
        scope=request.scope,
        granted_by=user_id,
        expires_at=request.expires_at,
    )
    db.commit()
    db.refresh(consent)
    logger.info(
        "consent_created",
        tenant_id=str(org_id),
        account_id=request.account_id,
        consent_id=str(consent.id),
        source_type=request.source_type,
    )
    return ConsentResponse(
        id=str(consent.id),
        tenant_id=str(consent.tenant_id),
        account_id=consent.account_id,
        source_type=consent.source_type,
        status=consent.status,
        consent_hash=consent.consent_hash,
        scope=consent.scope,
        granted_by=str(consent.granted_by) if consent.granted_by else None,
        granted_at=consent.granted_at,
        expires_at=consent.expires_at,
        revoked_at=consent.revoked_at,
        created_at=consent.created_at,
    )


async def grant_consent(
    request: ConsentGrantRequest,
    http_request: Request,
    org_id: uuid.UUID = Depends(_get_tenant_id),
    user_id: uuid.UUID = Depends(_get_current_user_id),
    db: Session = Depends(get_db_from_context_sync),
):
    """Grant an existing pending consent record."""
    service = ConsentService(db)
    consent = service.grant_consent(
        consent_id=uuid.UUID(request.consent_id),
        granted_by=user_id,
        expires_at=request.expires_at,
    )
    db.commit()
    db.refresh(consent)
    logger.info(
        "consent_granted",
        tenant_id=str(org_id),
        consent_id=str(consent.id),
        granted_by=str(user_id),
    )
    return ConsentResponse(
        id=str(consent.id),
        tenant_id=str(consent.tenant_id),
        account_id=consent.account_id,
        source_type=consent.source_type,
        status=consent.status,
        consent_hash=consent.consent_hash,
        scope=consent.scope,
        granted_by=str(consent.granted_by) if consent.granted_by else None,
        granted_at=consent.granted_at,
        expires_at=consent.expires_at,
        revoked_at=consent.revoked_at,
        created_at=consent.created_at,
    )


async def revoke_consent(
    request: ConsentRevokeRequest,
    http_request: Request,
    org_id: uuid.UUID = Depends(_get_tenant_id),
    user_id: uuid.UUID = Depends(_get_current_user_id),
    db: Session = Depends(get_db_from_context_sync),
):
    """Revoke an existing consent record."""
    service = ConsentService(db)
    consent = service.revoke_consent(
        consent_id=uuid.UUID(request.consent_id),
        revoked_by=user_id,
    )
    db.commit()
    db.refresh(consent)
    logger.info(
        "consent_revoked",
        tenant_id=str(org_id),
        consent_id=str(consent.id),
        revoked_by=str(user_id),
    )
    return ConsentResponse(
        id=str(consent.id),
        tenant_id=str(consent.tenant_id),
        account_id=consent.account_id,
        source_type=consent.source_type,
        status=consent.status,
        consent_hash=consent.consent_hash,
        scope=consent.scope,
        granted_by=str(consent.granted_by) if consent.granted_by else None,
        granted_at=consent.granted_at,
        expires_at=consent.expires_at,
        revoked_at=consent.revoked_at,
        created_at=consent.created_at,
    )


async def list_active_consent(
    account_id: str,
    http_request: Request,
    org_id: uuid.UUID = Depends(_get_tenant_id),
    db: Session = Depends(get_db_from_context_sync),
):
    """List active granted consent records for an account."""
    consents = (
        db.query(SourceConsent)
        .filter(
            SourceConsent.tenant_id == org_id,
            SourceConsent.account_id == account_id,
            SourceConsent.status == SourceConsentStatus.GRANTED.value,
        )
        .filter(
            SourceConsent.expires_at.is_(None)
            | (SourceConsent.expires_at > datetime.now(UTC))
        )
        .all()
    )
    return [
        ConsentResponse(
            id=str(consent.id),
            tenant_id=str(consent.tenant_id),
            account_id=consent.account_id,
            source_type=consent.source_type,
            status=consent.status,
            consent_hash=consent.consent_hash,
            scope=consent.scope,
            granted_by=str(consent.granted_by) if consent.granted_by else None,
            granted_at=consent.granted_at,
            expires_at=consent.expires_at,
            revoked_at=consent.revoked_at,
            created_at=consent.created_at,
        )
        for consent in consents
    ]


# =============================================================================
# ROUTE REGISTRATION
# =============================================================================


def register_routes(parent_router: APIRouter) -> None:
    """Register consent management routes under the parent router."""
    parent_router.add_api_route(
        "/consents",
        create_consent,
        methods=["POST"],
        response_model=ConsentResponse,
        tags=["Consent"],
        summary="Create a consent record",
        description="Create a pending consent record for a source ingestion scope.",
    )
    parent_router.add_api_route(
        "/consents/grant",
        grant_consent,
        methods=["POST"],
        response_model=ConsentResponse,
        tags=["Consent"],
        summary="Grant a consent record",
        description="Approve a pending consent record so ingestion can proceed.",
    )
    parent_router.add_api_route(
        "/consents/revoke",
        revoke_consent,
        methods=["POST"],
        response_model=ConsentResponse,
        tags=["Consent"],
        summary="Revoke a consent record",
        description="Revoke an existing consent record.",
    )
    parent_router.add_api_route(
        "/consents/active",
        list_active_consent,
        methods=["GET"],
        response_model=list[ConsentResponse],
        tags=["Consent"],
        summary="List active consent records",
        description="List granted, non-expired consent records for an account.",
    )
