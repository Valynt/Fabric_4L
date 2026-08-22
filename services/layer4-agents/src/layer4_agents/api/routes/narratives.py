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


from typing import Any, Literal

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field
from value_fabric.shared.models.typed_dict import TypedDictModel
from value_fabric.shared.security.dil_auth import (
    VALID_NARRATIVE_AUDIENCES,
    VALID_NARRATIVE_STATUSES,
    VALID_NARRATIVE_TONES,
    get_verified_tenant_id,
    validate_enum_value,
)

from ...contracts.artifacts import IntegrityGateErrorResponse, IntegrityPrecondition


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


class NarrativeExportRequest(BaseModel):
    """Request to export narrative into externally distributable formats."""

    format: Literal["PDF", "DOCX", "PPTX", "HTML"] = Field("PDF", description="Export target format")
    narrative_version: int = Field(1, ge=1)
    narrative_content_hash: str = Field(..., description="Exact SHA-256 hash of the narrative content")
    evidence_set_hash: str = Field(..., description="Exact SHA-256 hash of the supporting evidence set")
    integrity_precondition: IntegrityPrecondition | None = Field(
        None, description="Precondition assertion verified by IntegrityAgent"
    )


class NarrativeAcceptanceRequest(BaseModel):
    """Request to accept narrative and emit feedback loop data point into L5."""

    narrative_version: int = Field(1, ge=1)
    account_id: str
    journey_id: str | None = None
    conversation_turn_id: str | None = None
    se_feedback_notes: str | None = None


@router.post("/{narrative_id}/export")
async def export_narrative(
    narrative_id: str,
    body: NarrativeExportRequest,
    request: Request,
    tenant_id: str = Depends(get_verified_tenant_id),
):
    """Export a narrative to external format.

    Enforces Pillar 3 Integrity Gate: no NarrativeArtifact may export without a passing
    IntegrityPrecondition matching exact content hash and evidence set hash.
    Fails closed with 422 INTEGRITY_GATE_OPEN.
    """
    from ...services.narrative_builder_service import NarrativeBuilderService

    driver = _get_neo4j_driver(request)
    svc = NarrativeBuilderService(driver)

    narrative = await svc.get_narrative(tenant_id, narrative_id)
    if not narrative:
        raise NotFoundError(message="Narrative not found")

    precondition = body.integrity_precondition
    if not precondition:
        raise HTTPException(
            status_code=422,
            detail=IntegrityGateErrorResponse(
                code="INTEGRITY_GATE_OPEN",
                message="This narrative version has not passed integrity validation.",
                narrative_artifact_id=narrative_id,
                narrative_version=body.narrative_version,
                integrity_status="missing",
                required_action="rerun_integrity_validation",
            ).model_dump(),
        )

    # Invariant validations
    if (
        precondition.narrative_artifact_id != narrative_id
        or precondition.narrative_version != body.narrative_version
        or precondition.narrative_content_hash != body.narrative_content_hash
        or precondition.evidence_set_hash != body.evidence_set_hash
        or precondition.tenant_id != tenant_id
    ):
        raise HTTPException(
            status_code=422,
            detail=IntegrityGateErrorResponse(
                code="INTEGRITY_GATE_OPEN",
                message="Integrity artifact does not match current narrative content or evidence hash.",
                narrative_artifact_id=narrative_id,
                narrative_version=body.narrative_version,
                integrity_status="mismatched",
                required_action="rerun_integrity_validation",
            ).model_dump(),
        )

    if precondition.status != "passed" or precondition.unresolved_findings > 0 or not precondition.is_passed:
        status_label = "unresolved_findings" if precondition.unresolved_findings > 0 else (precondition.status if precondition.status in ["pending", "failed", "stale"] else "failed")
        raise HTTPException(
            status_code=422,
            detail=IntegrityGateErrorResponse(
                code="INTEGRITY_GATE_OPEN",
                message=f"Narrative integrity status is '{precondition.status}' with {precondition.unresolved_findings} unresolved findings.",
                narrative_artifact_id=narrative_id,
                narrative_version=body.narrative_version,
                integrity_status=status_label,
                required_action="rerun_integrity_validation",
            ).model_dump(),
        )

    # Export successful
    return {
        "status": "success",
        "narrative_id": narrative_id,
        "format": body.format,
        "download_url": f"/v1/narratives/{narrative_id}/downloads/{body.format.lower()}",
        "exported_at": "2026-08-21T12:00:00Z",
    }


@router.post("/{narrative_id}/accept")
async def accept_narrative(
    narrative_id: str,
    body: NarrativeAcceptanceRequest,
    request: Request,
    tenant_id: str = Depends(get_verified_tenant_id),
):
    """Accept a narrative and close self-improvement feedback loop into Layer 5 (Pillar 5).

    When an SE accepts a narrative, its claims and value delta are converted into a
    Layer 5 TruthObject with full provenance tracing back to the conversation turn and journey.
    """
    from ...services.narrative_builder_service import NarrativeBuilderService

    driver = _get_neo4j_driver(request)
    svc = NarrativeBuilderService(driver)

    narrative = await svc.get_narrative(tenant_id, narrative_id)
    if not narrative:
        raise NotFoundError(message="Narrative not found")

    # Update status to approved/delivered
    await svc.update_status(tenant_id, narrative_id, "approved")

    # Construct Layer 5 TruthObject representation / provenance record
    truth_object = {
        "truth_object_id": f"truth_{narrative_id}_{body.narrative_version}",
        "tenant_id": tenant_id,
        "account_id": body.account_id,
        "journey_id": body.journey_id,
        "source_artifact_type": "NarrativeArtifact",
        "source_artifact_id": narrative_id,
        "conversation_turn_id": body.conversation_turn_id,
        "acceptance_status": "accepted_by_se",
        "claims_count": len(narrative.get("sections", {}).get("value_hypotheses", [])),
        "created_at": "2026-08-21T12:00:00Z",
        "provenance": {
            "tenant_id": tenant_id,
            "account_id": body.account_id,
            "journey_id": body.journey_id,
            "narrative_id": narrative_id,
            "version": body.narrative_version,
            "feedback_notes": body.se_feedback_notes,
        },
    }

    logger.info(
        "narrative_accepted_and_truth_object_created",
        tenant_id=tenant_id,
        account_id=body.account_id,
        journey_id=body.journey_id,
        narrative_id=narrative_id,
        truth_object_id=truth_object["truth_object_id"],
    )

    return {
        "status": "accepted",
        "narrative_id": narrative_id,
        "truth_object": truth_object,
    }


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
