from __future__ import annotations

from value_fabric.shared.error_handling.exceptions import NotFoundError
"""
Value Hypotheses API routes — Data Intelligence Layer Phase 2, Task 2.1.

Provides REST endpoints for generating, retrieving, ranking, and validating
value hypotheses. These endpoints orchestrate the ValueHypothesisEngine
service and expose its capabilities to the frontend and other consumers.

All endpoints require authentication via GovernanceMiddleware.
Tenant identity is extracted from the verified JWT/API-key context (V-001, V-002).
Hypothesis status transitions are validated against an enum (V-008).
"""


import logging
from typing import Any

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from value_fabric.shared.models.typed_dict import TypedDictModel
from value_fabric.shared.security.dil_auth import (
    VALID_HYPOTHESIS_STATUSES,
    get_verified_tenant_id,
    validate_enum_value,
)


class generate_hypothesesResult(TypedDictModel):
    account_id: Any
    count: Any
    hypotheses: Any
    status: str

class validate_hypothesisResult(TypedDictModel):
    hypothesis: Any
    promoted_artifacts: Any = None
    status: str

class delete_hypothesisResult(TypedDictModel):
    hypothesis_id: Any
    status: str

class rank_hypothesesResult(TypedDictModel):
    count: Any
    hypotheses: Any
    strategy: Any

class convert_hypothesisResult(TypedDictModel):
    hypothesis_id: str
    account_id: str
    tenant_id: str
    evidence_ids: list[str]
    value_model_id: str | None = None
    tree_id: str | None = None
    status: str

router = APIRouter(prefix="/hypotheses", tags=["Value Hypotheses"])


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------


class GenerateHypothesesRequest(BaseModel):
    """Request to generate value hypotheses for an account."""
    account_id: str = Field(..., description="Account ID to generate hypotheses for")
    min_confidence: float = Field(0.3, ge=0.0, le=1.0)
    max_hypotheses: int = Field(20, ge=1, le=100)
    include_evidence: bool = Field(True)


class ValidateHypothesisRequest(BaseModel):
    """Request to validate or reject a hypothesis."""
    feedback: str = Field(..., min_length=1, max_length=2000)
    new_status: str | None = Field(
        None,
        description="New status: validated, rejected, or converted",
    )
    confidence_adjustment: float = Field(
        0.0,
        ge=-1.0,
        le=1.0,
        description="Additive confidence adjustment",
    )


class RankHypothesesRequest(BaseModel):
    """Request to re-rank hypotheses."""
    hypothesis_ids: list[str] = Field(..., min_length=1, max_length=200)
    strategy: str = Field("balanced", description="Ranking strategy")


class PromoteSignalRequest(BaseModel):
    """Request to promote a pain signal to a value hypothesis."""
    account_id: str = Field(..., description="Account ID the signal belongs to")
    signal_id: str = Field(..., description="Pain signal ID to promote")
    value_path_category: str | None = Field(
        None,
        description="Value path classification: revenue_uplift, cost_savings, risk_reduction, blended",
    )
    product_id: str | None = Field(None)
    product_name: str | None = Field(None)
    capability_id: str | None = Field(None)
    capability_name: str | None = Field(None)


class PromoteSignalResponse(BaseModel):
    status: str
    hypothesis_id: str
    signal_id: str
    account_id: str
    value_path_category: str | None


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _get_neo4j_driver(request: Request):
    """Get Neo4j driver from app state."""
    return getattr(request.app.state, "neo4j_driver", None)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/generate", response_model=generate_hypothesesResult)
async def generate_hypotheses(
    body: GenerateHypothesesRequest,
    request: Request,
    tenant_id: str = Depends(get_verified_tenant_id),
):
    """Generate value hypotheses for an account.

    Traverses the knowledge graph to find signal->capability->product paths,
    enriches with evidence, and returns ranked hypotheses.
    """
    from ...services.value_hypothesis_engine import ValueHypothesisEngine

    driver = _get_neo4j_driver(request)
    engine = ValueHypothesisEngine(driver)

    hypotheses = await engine.generate_hypotheses(
        tenant_id,
        body.account_id,
        min_confidence=body.min_confidence,
        max_hypotheses=body.max_hypotheses,
        include_evidence=body.include_evidence,
    )

    return generate_hypothesesResult.model_validate({
        "status": "success",
        "account_id": body.account_id,
        "count": len(hypotheses),
        "hypotheses": hypotheses,
    })


@router.post("/from-signal", response_model=PromoteSignalResponse)
async def promote_signal(
    body: PromoteSignalRequest,
    request: Request,
    tenant_id: str = Depends(get_verified_tenant_id),
):
    """Promote a single pain signal to a value hypothesis.

    This is the canonical hinge between Signal Discovery and Value Path
    Classification. Creates a ValueHypothesis node linked to the signal.
    """
    from ...services.value_hypothesis_engine import ValueHypothesisEngine

    driver = _get_neo4j_driver(request)
    engine = ValueHypothesisEngine(driver)

    try:
        hypothesis = await engine.promote_signal(
            tenant_id,
            body.account_id,
            body.signal_id,
            value_path_category=body.value_path_category,
            product_id=body.product_id,
            product_name=body.product_name,
            capability_id=body.capability_id,
            capability_name=body.capability_name,
        )
    except ValueError as exc:
        logger.warning("signal_promotion_value_error", extra={"error": str(exc)})
        raise NotFoundError(message = "Signal not found") from exc

    return PromoteSignalResponse.model_validate({
        "status": "success",
        "hypothesis_id": hypothesis["id"],
        "signal_id": body.signal_id,
        "account_id": body.account_id,
        "value_path_category": body.value_path_category,
    })


@router.get("/{hypothesis_id}")
async def get_hypothesis(
    hypothesis_id: str,
    request: Request,
    tenant_id: str = Depends(get_verified_tenant_id),
):
    """Get a single value hypothesis with full detail."""
    from ...services.value_hypothesis_engine import ValueHypothesisEngine

    driver = _get_neo4j_driver(request)
    engine = ValueHypothesisEngine(driver)

    result = await engine.get_hypothesis(tenant_id, hypothesis_id)
    if not result:
        raise NotFoundError(message = "Hypothesis not found")

    return result


@router.get("/account/{account_id}")
async def get_account_hypotheses(
    account_id: str,
    request: Request,
    status: str | None = Query(None, description="Filter by status"),
    value_path_category: str | None = Query(None, description="Filter by value path category: revenue_uplift, cost_savings, risk_reduction, blended"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    tenant_id: str = Depends(get_verified_tenant_id),
):
    """List all hypotheses for an account with optional filtering."""
    from ...services.value_hypothesis_engine import ValueHypothesisEngine

    driver = _get_neo4j_driver(request)
    if driver is None:
        # Account workspaces should render a safe empty hypothesis state when
        # graph-backed hypothesis generation is unavailable in a validation
        # stack. Auth and tenant resolution have already succeeded above.
        return {"hypotheses": [], "total": 0}

    engine = ValueHypothesisEngine(driver)

    return await engine.get_account_hypotheses(
        tenant_id,
        account_id,
        status=status,
        value_path_category=value_path_category,
        skip=skip,
        limit=limit,
    )


@router.post("/{hypothesis_id}/validate", response_model=validate_hypothesisResult)
async def validate_hypothesis(
    hypothesis_id: str,
    body: ValidateHypothesisRequest,
    request: Request,
    tenant_id: str = Depends(get_verified_tenant_id),
):
    """Validate, reject, or provide feedback on a hypothesis."""
    from ...services.value_hypothesis_engine import ValueHypothesisEngine

    driver = _get_neo4j_driver(request)
    engine = ValueHypothesisEngine(driver)

    # V-008: Validate status transition against enum
    if body.new_status is not None:
        validate_enum_value(body.new_status, VALID_HYPOTHESIS_STATUSES, "new_status")

    result = await engine.validate_hypothesis(
        tenant_id,
        hypothesis_id,
        feedback=body.feedback,
        new_status=body.new_status,
        confidence_adjustment=body.confidence_adjustment,
    )

    if not result:
        raise NotFoundError(message = "Hypothesis not found")

    promoted_artifacts = await engine.orchestrate_post_validation(
        tenant_id,
        hypothesis_id,
        new_status=body.new_status,
    )

    return validate_hypothesisResult.model_validate({
        "status": "updated",
        "hypothesis": result,
        "promoted_artifacts": promoted_artifacts,
    })


@router.delete("/{hypothesis_id}", response_model=delete_hypothesisResult)
async def delete_hypothesis(
    hypothesis_id: str,
    request: Request,
    tenant_id: str = Depends(get_verified_tenant_id),
):
    """Delete a value hypothesis."""
    from ...services.value_hypothesis_engine import ValueHypothesisEngine

    driver = _get_neo4j_driver(request)
    engine = ValueHypothesisEngine(driver)

    deleted = await engine.delete_hypothesis(tenant_id, hypothesis_id)
    if not deleted:
        raise NotFoundError(message = "Hypothesis not found")

    return delete_hypothesisResult.model_validate({"status": "deleted", "hypothesis_id": hypothesis_id})


@router.post("/{hypothesis_id}/convert", response_model=convert_hypothesisResult)
async def convert_hypothesis_to_tree(
    hypothesis_id: str,
    request: Request,
    tenant_id: str = Depends(get_verified_tenant_id),
):
    """Convert a hypothesis to a driver tree/value model linkage."""
    from ...services.value_hypothesis_engine import ValueHypothesisEngine

    driver = _get_neo4j_driver(request)
    engine = ValueHypothesisEngine(driver)

    result = await engine.convert_hypothesis_to_tree(tenant_id, hypothesis_id)
    if not result:
        raise NotFoundError(message = "Hypothesis not found")

    return convert_hypothesisResult.model_validate(result)


@router.get("/summary/stats")
async def get_hypothesis_summary(
    request: Request,
    account_id: str | None = Query(None),
    tenant_id: str = Depends(get_verified_tenant_id),
):
    """Get aggregate statistics about hypotheses."""
    from ...services.value_hypothesis_engine import ValueHypothesisEngine

    driver = _get_neo4j_driver(request)
    engine = ValueHypothesisEngine(driver)

    return await engine.get_hypothesis_summary(tenant_id, account_id)


@router.post("/rank", response_model=rank_hypothesesResult)
async def rank_hypotheses(
    body: RankHypothesesRequest,
    request: Request,
    tenant_id: str = Depends(get_verified_tenant_id),
):
    """Re-rank a set of hypotheses using a specified strategy."""
    from ...services.value_hypothesis_engine import ValueHypothesisEngine

    driver = _get_neo4j_driver(request)
    engine = ValueHypothesisEngine(driver)

    # Fetch each hypothesis
    hypotheses = []
    for hid in body.hypothesis_ids:
        h = await engine.get_hypothesis(tenant_id, hid)
        if h:
            hypotheses.append(h)

    if not hypotheses:
        raise NotFoundError(message = "No valid hypotheses found")

    ranked = engine.rank_hypotheses(hypotheses, body.strategy)

    return rank_hypothesesResult.model_validate({
        "strategy": body.strategy,
        "count": len(ranked),
        "hypotheses": ranked,
    })
