from __future__ import annotations

from value_fabric.shared.error_handling.exceptions import NotFoundError, ValidationError

"""
Account Enrichment API Routes — Data Intelligence Layer Phase 1.

Provides endpoints for triggering and monitoring account enrichment:
- POST /enrich/{account_id}   — Enrich a single account
- POST /enrich/batch          — Enrich a batch of pending accounts
- GET  /enrich/status         — Get enrichment coverage statistics
- GET  /enrich/{account_id}   — Get enrichment details for an account

All endpoints require authentication via GovernanceMiddleware.
Tenant identity is extracted from the verified JWT/API-key context (V-001, V-002).
Account lookups are tenant-scoped to prevent IDOR (V-003).
Batch endpoint ignores body tenant_id and uses auth context (V-004).
"""


from typing import Any
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from value_fabric.shared.models.typed_dict import TypedDictModel
from value_fabric.shared.security.dil_auth import get_verified_tenant_id

from ...database import get_db_from_context
from ...models.account import Account
from ...services.enrichment_orchestrator import (
    EnrichmentOrchestrator,
    EnrichmentSource,
)


class get_account_enrichmentResult(TypedDictModel):
    account_id: Any
    competitive_landscape: bool
    enriched_at: Any
    enrichment_sources: bool
    enrichment_status: Any
    executives: bool
    financials: Any
    name: Any
    pain_signals: bool
    tech_stack: Any

logger = structlog.get_logger()

router = APIRouter(prefix="/enrichment", tags=["enrichment"])


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------

class EnrichAccountRequest(BaseModel):
    sources: list[str] | None = Field(
        None,
        description="Specific sources to use: sec_edgar, web_crawl, domain_lookup, news_scan",
    )
    force: bool = Field(False, description="Re-enrich even if already enriched")


class BatchEnrichRequest(BaseModel):
    # V-004: tenant_id removed from body — always comes from auth context
    limit: int = Field(50, ge=1, le=500, description="Max accounts to enrich")
    force: bool = Field(False, description="Re-enrich already enriched accounts")


class EnrichmentStatusResponse(BaseModel):
    total_accounts: int
    enriched: int
    pending: int
    in_progress: int
    failed: int
    stale: int
    coverage_pct: float


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_tenant_scoped_account(
    db: AsyncSession, account_id: UUID, tenant_id: str
) -> Account:
    """Load an account by ID, scoped to the authenticated tenant.

    Returns 404 (not 403) to avoid existence oracle (V-003).
    """
    stmt = select(Account).where(
        Account.id == account_id,
        Account.tenant_id == tenant_id,
    )
    result = await db.execute(stmt)
    account = result.scalar_one_or_none()
    if account is None:
        raise NotFoundError(message = str(f"Account {account_id} not found"))
    return account


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/{account_id}", summary="Enrich a single account")
async def enrich_account(
    account_id: UUID,
    request: EnrichAccountRequest | None = None,
    tenant_id: str = Depends(get_verified_tenant_id),
    db: AsyncSession = Depends(get_db_from_context),
) -> dict[str, Any]:
    """Trigger enrichment for a single account from multiple data sources.

    The account must belong to the authenticated tenant (V-003).
    """
    # V-003: Verify account belongs to this tenant before enriching
    await _get_tenant_scoped_account(db, account_id, tenant_id)

    orchestrator = EnrichmentOrchestrator(db)

    try:
        # Parse source list if provided
        sources = None
        if request and request.sources:
            try:
                sources = [EnrichmentSource(s) for s in request.sources]
            except ValueError as e:
                logger.warning("Invalid enrichment source: %s", e)
                raise ValidationError(message = "Invalid enrichment source") from e

        force = request.force if request else False
        result = await orchestrator.enrich_account(account_id, sources=sources, force=force)

        if result.get("status") == "error":
            raise NotFoundError(message = str(result.get("message")))

        return result
    finally:
        await orchestrator.close()


@router.post("/batch", summary="Enrich a batch of accounts")
async def enrich_batch(
    request: BatchEnrichRequest,
    tenant_id: str = Depends(get_verified_tenant_id),
    db: AsyncSession = Depends(get_db_from_context),
) -> dict[str, Any]:
    """Enrich a batch of accounts with pending/stale enrichment status.

    V-004: tenant_id always comes from auth context, never from request body.
    """
    orchestrator = EnrichmentOrchestrator(db)

    try:
        result = await orchestrator.enrich_batch(
            tenant_id=tenant_id,
            limit=request.limit,
            force=request.force,
        )
        return result
    finally:
        await orchestrator.close()


@router.get("/status", summary="Get enrichment coverage statistics", response_model=EnrichmentStatusResponse)
async def get_enrichment_status(
    tenant_id: str = Depends(get_verified_tenant_id),
    db: AsyncSession = Depends(get_db_from_context),
) -> EnrichmentStatusResponse:
    """Get enrichment coverage statistics for the authenticated tenant.

    V-007: tenant_id comes from auth context, not query parameter.
    """
    orchestrator = EnrichmentOrchestrator(db)

    try:
        status = await orchestrator.get_enrichment_status(tenant_id)
        return EnrichmentStatusResponse(**status)
    finally:
        await orchestrator.close()


@router.get("/{account_id}", summary="Get enrichment details for an account")
async def get_account_enrichment(
    account_id: UUID,
    tenant_id: str = Depends(get_verified_tenant_id),
    db: AsyncSession = Depends(get_db_from_context),
) -> dict[str, Any]:
    """Get the current enrichment data for a specific account.

    V-003: Account lookup is scoped to the authenticated tenant.
    """
    # V-003: Tenant-scoped account lookup
    account = await _get_tenant_scoped_account(db, account_id, tenant_id)

    return get_account_enrichmentResult.model_validate({
        "account_id": str(account.id),
        "name": account.name,
        "enrichment_status": account.enrichment_status,
        "enriched_at": account.enriched_at.isoformat() if account.enriched_at else None,
        "enrichment_sources": account.enrichment_sources or [],
        "tech_stack": account.tech_stack,
        "executives": account.executives or [],
        "financials": account.financials,
        "competitive_landscape": account.competitive_landscape or [],
        "pain_signals": account.pain_signals or [],
    })


