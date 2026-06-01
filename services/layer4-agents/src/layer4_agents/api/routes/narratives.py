from __future__ import annotations

from value_fabric.shared.error_handling.exceptions import NotFoundError

"""
Narrative Builder API routes — Data Intelligence Layer Phase 3, Task 3.1.

Provides REST endpoints for generating, managing, and retrieving
sales narratives built from intelligence data.

All endpoints require authentication via GovernanceMiddleware.
Tenant identity is extracted from the verified JWT/API-key context (V-001, V-002).
Pre-fetched data is flagged as unverified (V-009).
Status transitions are validated against an enum (V-010).
"""


from typing import Any

import structlog
from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, ConfigDict, Field
from value_fabric.shared.models.typed_dict import TypedDictModel
from value_fabric.shared.security.dil_auth import (
    VALID_NARRATIVE_AUDIENCES,
    VALID_NARRATIVE_STATUSES,
    VALID_NARRATIVE_TONES,
    get_verified_tenant_id,
    validate_enum_value,
)


class delete_narrativeResult(TypedDictModel):
    narrative_id: Any
    status: str

logger = structlog.get_logger()

router = APIRouter(prefix="/narratives", tags=["Narratives"])


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------


class NarrativeGenerateRequest(BaseModel):
    """Request to generate a narrative."""

    model_config = ConfigDict(extra="forbid")

    account_id: str = Field(..., description="Account to generate narrative for")
    title: str = Field("Account Intelligence Narrative", max_length=500)
    tone: str = Field("executive", description="Tone: executive, technical, financial, consultative")
    audience: str = Field("c_suite", description="Audience: c_suite, vp_director, technical_buyer, champion, evaluation_committee")
    include_sections: list[str] = Field(
        default=[
            "executive_summary",
            "pain_points",
            "value_hypotheses",
            "competitive_positioning",
            "roi_projection",
            "evidence",
            "next_steps",
        ],
        description="Sections to include in the narrative",
    )
    ranking_strategy: str = Field("balanced", description="Hypothesis ranking strategy")
    roi_scenario: str = Field("moderate", description="ROI scenario for projections")
    roi_time_horizon_months: int = Field(36, ge=1, le=120)
    top_n_hypotheses: int = Field(5, ge=1, le=20)
    custom_next_steps: list[str] = Field(default_factory=list)
    # V-009: Pre-fetched data is accepted but flagged as unverified
    account_data: dict[str, Any] | None = Field(None, description="Pre-fetched account data (flagged as unverified)")
    signals_data: list[dict[str, Any]] | None = Field(None, description="Pre-fetched signals (flagged as unverified)")
    hypotheses_data: list[dict[str, Any]] | None = Field(None, description="Pre-fetched hypotheses (flagged as unverified)")
    competitive_data: dict[str, Any] | None = Field(None, description="Pre-fetched competitive landscape (flagged as unverified)")
    roi_data: dict[str, Any] | None = Field(None, description="Pre-fetched ROI results (flagged as unverified)")
    evidence_data: list[dict[str, Any]] | None = Field(None, description="Pre-fetched evidence (flagged as unverified)")


class StatusUpdateRequest(BaseModel):
    """Request to update narrative status."""

    status: str = Field(..., description="New status: draft, review, approved, delivered")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_neo4j_driver(request: Request):
    """Get Neo4j driver from app state."""
    return request.app.state.neo4j_driver


def _has_prefetched_data(body: NarrativeGenerateRequest) -> bool:
    """Check if the request includes any pre-fetched data."""
    return any([
        body.account_data,
        body.signals_data,
        body.hypotheses_data,
        body.competitive_data,
        body.roi_data,
        body.evidence_data,
    ])


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/generate")
async def generate_narrative(
    body: NarrativeGenerateRequest,
    request: Request,
    tenant_id: str = Depends(get_verified_tenant_id),
):
    """Generate a new sales narrative from intelligence data.

    V-009: If pre-fetched data is supplied, the narrative is tagged with
    ``data_source: "caller_supplied"`` and ``verified: false`` so downstream
    consumers know the numbers were not independently verified.
    """
    from ...services.narrative_builder_service import (
        NarrativeBuilderService,
        NarrativeRequest,
    )

    # Validate tone and audience against enums
    validate_enum_value(body.tone, VALID_NARRATIVE_TONES, "tone")
    validate_enum_value(body.audience, VALID_NARRATIVE_AUDIENCES, "audience")

    driver = _get_neo4j_driver(request)
    svc = NarrativeBuilderService(driver)

    narr_request = NarrativeRequest(
        account_id=body.account_id,
        title=body.title,
        tone=body.tone,
        audience=body.audience,
        include_sections=body.include_sections,
        ranking_strategy=body.ranking_strategy,
        roi_scenario=body.roi_scenario,
        roi_time_horizon_months=body.roi_time_horizon_months,
        top_n_hypotheses=body.top_n_hypotheses,
        custom_next_steps=body.custom_next_steps,
    )

    result = await svc.generate_narrative(
        narr_request,
        tenant_id=tenant_id,
        account_data=body.account_data,
        signals_data=body.signals_data,
        hypotheses_data=body.hypotheses_data,
        competitive_data=body.competitive_data,
        roi_data=body.roi_data,
        evidence_data=body.evidence_data,
    )

    # V-009: Tag narratives built from caller-supplied data
    if _has_prefetched_data(body):
        result["data_source"] = "caller_supplied"
        result["verified"] = False
        logger.warning(
            "narrative_generated_from_prefetched_data",
            tenant_id=tenant_id,
            account_id=body.account_id,
            narrative_id=result.get("id"),
        )
    else:
        result["data_source"] = "server_fetched"
        result["verified"] = True

    return result


@router.get("")
async def list_narratives(
    request: Request,
    account_id: str | None = Query(None),
    status: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    tenant_id: str = Depends(get_verified_tenant_id),
):
    """List narratives with optional filtering."""
    from ...services.narrative_builder_service import NarrativeBuilderService

    driver = _get_neo4j_driver(request)
    svc = NarrativeBuilderService(driver)

    return await svc.list_narratives(
        tenant_id, account_id=account_id, status=status, skip=skip, limit=limit
    )


@router.get("/{narrative_id}")
async def get_narrative(
    narrative_id: str,
    request: Request,
    tenant_id: str = Depends(get_verified_tenant_id),
):
    """Get a specific narrative."""
    from ...services.narrative_builder_service import NarrativeBuilderService

    driver = _get_neo4j_driver(request)
    svc = NarrativeBuilderService(driver)

    result = await svc.get_narrative(tenant_id, narrative_id)
    if not result:
        raise NotFoundError(message = "Narrative not found")
    return result


@router.patch("/{narrative_id}/status")
async def update_narrative_status(
    narrative_id: str,
    body: StatusUpdateRequest,
    request: Request,
    tenant_id: str = Depends(get_verified_tenant_id),
):
    """Update narrative status.

    V-010: Status is validated against the allowed enum.
    """
    from ...services.narrative_builder_service import NarrativeBuilderService

    # V-010: Validate status against enum
    validate_enum_value(body.status, VALID_NARRATIVE_STATUSES, "status")

    driver = _get_neo4j_driver(request)
    svc = NarrativeBuilderService(driver)

    result = await svc.update_status(tenant_id, narrative_id, body.status)
    if not result:
        raise NotFoundError(message = "Narrative not found")
    return result


@router.delete("/{narrative_id}")
async def delete_narrative(
    narrative_id: str,
    request: Request,
    tenant_id: str = Depends(get_verified_tenant_id),
):
    """Delete a narrative."""
    from ...services.narrative_builder_service import NarrativeBuilderService

    driver = _get_neo4j_driver(request)
    svc = NarrativeBuilderService(driver)

    deleted = await svc.delete_narrative(tenant_id, narrative_id)
    if not deleted:
        raise NotFoundError(message = "Narrative not found")
    return delete_narrativeResult.model_validate({"status": "deleted", "narrative_id": narrative_id})
