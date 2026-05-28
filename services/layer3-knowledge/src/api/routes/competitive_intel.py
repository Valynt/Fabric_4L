from __future__ import annotations

from value_fabric.shared.error_handling.exceptions import NotFoundError, ValidationError
"""Allowed service-local exception for Layer 3 service wrapper.

Owner: layer3-knowledge
Removal/migration target: 2026-09-30
Reason: Competitive Intelligence API routes — Data Intelligence Layer Phase 2, Task 2.2.

Provides REST endpoints for managing competitors, battlecards, win/loss records,
and competitive landscape analysis.

All endpoints require authentication via GovernanceMiddleware.
Tenant identity is extracted from the verified JWT/API-key context (V-001, V-002).
Competitor updates use an allowlisted field set (V-006).
Win/loss outcomes are validated against an enum (V-011).
"""


from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from value_fabric.shared.models.typed_dict import TypedDictModel
from value_fabric.shared.security.dil_auth import (
    VALID_WIN_LOSS_OUTCOMES,
    AllowlistedFieldUpdate,
    get_verified_tenant_id,
    validate_enum_value,
)


class add_competitorResult(TypedDictModel):
    status: str

class update_competitorResult(TypedDictModel):
    status: str

class delete_competitorResult(TypedDictModel):
    competitor_id: Any
    status: str

class add_battlecardResult(TypedDictModel):
    status: str

class record_win_lossResult(TypedDictModel):
    status: str

router = APIRouter(prefix="/competitive", tags=["Competitive Intelligence"])

# V-006: Allowlisted fields for competitor updates
_COMPETITOR_UPDATER = AllowlistedFieldUpdate(
    allowed={
        "name", "description", "domain", "strengths", "weaknesses",
        "market_position", "pricing_tier", "target_segments", "founded_year",
    },
    strict=True,
)


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------


class CompetitorCreateRequest(BaseModel):
    """Request to create a competitor."""
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1, max_length=5000)
    domain: str | None = Field(None, max_length=200)
    founded_year: int | None = Field(None, ge=1900, le=2030)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    market_position: str = Field("challenger")
    pricing_tier: str = Field("mid")
    target_segments: list[str] = Field(default_factory=list)


class CompetitorUpdateRequest(BaseModel):
    """Request to update a competitor."""
    name: str | None = None
    description: str | None = None
    domain: str | None = None
    strengths: list[str] | None = None
    weaknesses: list[str] | None = None
    market_position: str | None = None
    pricing_tier: str | None = None
    target_segments: list[str] | None = None


class BattlecardCreateRequest(BaseModel):
    """Request to create a battlecard."""
    product_id: str = Field(...)
    positioning: str = Field(..., min_length=1, max_length=5000)
    differentiators: list[str] = Field(default_factory=list)
    objection_handlers: list[dict[str, str]] = Field(default_factory=list)
    talk_tracks: list[str] = Field(default_factory=list)
    win_themes: list[str] = Field(default_factory=list)
    trap_questions: list[str] = Field(default_factory=list)


class WinLossRequest(BaseModel):
    """Request to record a win or loss."""
    competitor_id: str = Field(...)
    product_id: str = Field(...)
    outcome: str = Field(..., description="'won' or 'lost'")
    deal_size_usd: float = Field(0.0, ge=0)
    reason: str = Field("", max_length=2000)
    industry: str = Field("", max_length=200)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _get_neo4j_driver(request: Request):
    """Get Neo4j driver from app state."""
    return request.app.state.neo4j_driver


# ---------------------------------------------------------------------------
# Competitor Endpoints
# ---------------------------------------------------------------------------


@router.post("/competitors")
async def add_competitor(
    body: CompetitorCreateRequest,
    request: Request,
    tenant_id: str = Depends(get_verified_tenant_id),
):
    """Add a new competitor to the knowledge graph."""
    from services.competitive_intel_service import (
        CompetitiveIntelService,
        CompetitorCreate,
    )

    driver = _get_neo4j_driver(request)
    svc = CompetitiveIntelService(driver)

    competitor = CompetitorCreate(
        name=body.name,
        description=body.description,
        domain=body.domain,
        founded_year=body.founded_year,
        strengths=body.strengths,
        weaknesses=body.weaknesses,
        market_position=body.market_position,
        pricing_tier=body.pricing_tier,
        target_segments=body.target_segments,
    )
    result = await svc.add_competitor(tenant_id, competitor)
    return add_competitorResult.model_validate({"status": "created", **result})


@router.get("/competitors")
async def list_competitors(
    request: Request,
    market_position: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    tenant_id: str = Depends(get_verified_tenant_id),
):
    """List competitors with optional filtering."""
    from services.competitive_intel_service import CompetitiveIntelService

    driver = _get_neo4j_driver(request)
    svc = CompetitiveIntelService(driver)

    return await svc.list_competitors(
        tenant_id,
        market_position=market_position,
        skip=skip,
        limit=limit,
    )


@router.get("/competitors/{competitor_id}")
async def get_competitor(
    competitor_id: str,
    request: Request,
    tenant_id: str = Depends(get_verified_tenant_id),
):
    """Get a competitor with related products and battlecards."""
    from services.competitive_intel_service import CompetitiveIntelService

    driver = _get_neo4j_driver(request)
    svc = CompetitiveIntelService(driver)

    result = await svc.get_competitor(tenant_id, competitor_id)
    if not result:
        raise NotFoundError(message = "Competitor not found")
    return result


@router.put("/competitors/{competitor_id}")
async def update_competitor(
    competitor_id: str,
    body: CompetitorUpdateRequest,
    request: Request,
    tenant_id: str = Depends(get_verified_tenant_id),
):
    """Update a competitor's properties.

    Only allowlisted fields are accepted (V-006 remediation).
    """
    from services.competitive_intel_service import CompetitiveIntelService

    driver = _get_neo4j_driver(request)
    svc = CompetitiveIntelService(driver)

    raw_updates = body.model_dump(exclude_none=True)
    if not raw_updates:
        raise ValidationError(message = "No updates provided")

    # V-006: Validate field names against allowlist before passing to service
    try:
        safe_updates, _, _ = _COMPETITOR_UPDATER.build("c", raw_updates)
    except ValueError as exc:
        raise ValidationError(message="Invalid competitor update fields") from exc

    if not safe_updates:
        raise ValidationError(message="No valid fields in update")

    result = await svc.update_competitor(tenant_id, competitor_id, safe_updates)
    if not result:
        raise NotFoundError(message = "Competitor not found")
    return update_competitorResult.model_validate({"status": "updated", **result})


@router.delete("/competitors/{competitor_id}")
async def delete_competitor(
    competitor_id: str,
    request: Request,
    tenant_id: str = Depends(get_verified_tenant_id),
):
    """Delete a competitor and its battlecards."""
    from services.competitive_intel_service import CompetitiveIntelService

    driver = _get_neo4j_driver(request)
    svc = CompetitiveIntelService(driver)

    deleted = await svc.delete_competitor(tenant_id, competitor_id)
    if not deleted:
        raise NotFoundError(message = "Competitor not found")
    return delete_competitorResult.model_validate({"status": "deleted", "competitor_id": competitor_id})


# ---------------------------------------------------------------------------
# Battlecard Endpoints
# ---------------------------------------------------------------------------


@router.post("/competitors/{competitor_id}/battlecards")
async def add_battlecard(
    competitor_id: str,
    body: BattlecardCreateRequest,
    request: Request,
    tenant_id: str = Depends(get_verified_tenant_id),
):
    """Create a battlecard for a competitor + product pair."""
    from services.competitive_intel_service import (
        BattlecardCreate,
        CompetitiveIntelService,
    )

    driver = _get_neo4j_driver(request)
    svc = CompetitiveIntelService(driver)

    bc = BattlecardCreate(
        product_id=body.product_id,
        positioning=body.positioning,
        differentiators=body.differentiators,
        objection_handlers=body.objection_handlers,
        talk_tracks=body.talk_tracks,
        win_themes=body.win_themes,
        trap_questions=body.trap_questions,
    )
    result = await svc.add_battlecard(tenant_id, competitor_id, bc)
    return add_battlecardResult.model_validate({"status": "created", **result})


@router.get("/competitors/{competitor_id}/battlecards")
async def get_battlecards(
    competitor_id: str,
    request: Request,
    product_id: str | None = Query(None),
    tenant_id: str = Depends(get_verified_tenant_id),
):
    """Get battlecards for a competitor."""
    from services.competitive_intel_service import CompetitiveIntelService

    driver = _get_neo4j_driver(request)
    svc = CompetitiveIntelService(driver)

    return await svc.get_battlecard(tenant_id, competitor_id, product_id)


# Compatibility alias: frontend contract uses singular "battlecard".
@router.get("/competitors/{competitor_id}/battlecard")
async def get_battlecard_compat(
    competitor_id: str,
    request: Request,
    product_id: str | None = Query(None),
    tenant_id: str = Depends(get_verified_tenant_id),
):
    """Compatibility alias for /competitors/{id}/battlecards."""
    return await get_battlecards(competitor_id, request, product_id, tenant_id)


# ---------------------------------------------------------------------------
# Win/Loss Endpoints
# ---------------------------------------------------------------------------


@router.post("/win-loss")
async def record_win_loss(
    body: WinLossRequest,
    request: Request,
    tenant_id: str = Depends(get_verified_tenant_id),
):
    """Record a competitive win or loss."""
    from services.competitive_intel_service import (
        CompetitiveIntelService,
        WinLossRecord,
    )

    driver = _get_neo4j_driver(request)
    svc = CompetitiveIntelService(driver)

    # V-011: Validate outcome against enum
    validate_enum_value(body.outcome, VALID_WIN_LOSS_OUTCOMES, "outcome")

    wl = WinLossRecord(
        competitor_id=body.competitor_id,
        product_id=body.product_id,
        outcome=body.outcome,
        deal_size_usd=body.deal_size_usd,
        reason=body.reason,
        industry=body.industry,
    )
    result = await svc.record_win_loss(tenant_id, wl)
    return record_win_lossResult.model_validate({"status": "recorded", **result})


@router.get("/win-loss/summary")
async def get_win_loss_summary(
    request: Request,
    tenant_id: str = Depends(get_verified_tenant_id),
):
    """Get aggregated win/loss data across all competitors."""
    from services.competitive_intel_service import CompetitiveIntelService

    driver = _get_neo4j_driver(request)
    svc = CompetitiveIntelService(driver)

    return await svc.get_win_loss_summary(tenant_id)


# ---------------------------------------------------------------------------
# Analysis Endpoints
# ---------------------------------------------------------------------------


@router.get("/landscape")
async def get_competitive_landscape(
    request: Request,
    product_id: str | None = Query(None),
    tenant_id: str = Depends(get_verified_tenant_id),
):
    """Analyze the competitive landscape."""
    from services.competitive_intel_service import CompetitiveIntelService

    driver = _get_neo4j_driver(request)
    svc = CompetitiveIntelService(driver)

    return await svc.analyze_competitive_landscape(tenant_id, product_id)
