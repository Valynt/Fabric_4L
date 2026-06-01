from __future__ import annotations

"""L4 Ground Truth Proxy Routes

Exposes L5 Ground Truth endpoints via L4 for frontend consumption.
All routes forward requests to L5 using Layer5GroundTruthClient.

Endpoints:
  GET    /v1/ground-truth/truths                    -> L5 GET /truths
  GET    /v1/ground-truth/truths/{id}               -> L5 GET /truths/{id}
  GET    /v1/ground-truth/truths/{id}/audit         -> L5 GET /truths/{id}/audit
  POST   /v1/ground-truth/truths/{id}/validate      -> L5 POST /truths/{id}/validate
  GET    /v1/ground-truth/truths/freshness-summary  -> L5 GET /truths/freshness-summary
  GET    /v1/ground-truth/truths/stale              -> L5 GET /truths/stale
  GET    /v1/ground-truth/maturity-ladder           -> L5 GET /maturity-ladder
"""


import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from value_fabric.shared.error_handling.exceptions import ServiceUnavailableError
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_authenticated

from ...integration.layer5_client import Layer5GroundTruthClient, get_layer5_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/ground-truth", tags=["ground-truth-proxy"])


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _handle_l5_result(result: dict[str, Any]) -> dict[str, Any]:
    """Raise HTTPException if L5 returned an error dict, otherwise return result."""
    error = result.get("error")
    if error:
        logger.error("L5 proxy error: %s", error)
        raise ServiceUnavailableError(message=f"Ground Truth service error: {error}")
    return result


# -----------------------------------------------------------------------------
# Request/Response Models
# -----------------------------------------------------------------------------


class ValidateTruthRequest(BaseModel):
    action: str
    actor: str
    actor_type: str = "user"
    notes: str | None = None


# -----------------------------------------------------------------------------
# Dependency Injection
# -----------------------------------------------------------------------------


async def get_l5_client() -> Layer5GroundTruthClient:
    """Get Layer5GroundTruthClient with default config."""
    return get_layer5_client()


# -----------------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------------


@router.get("/truths", summary="List TruthObjects")
async def list_truths(
    status: str | None = Query(None, description="Filter by validation status"),
    claim_type: str | None = Query(None, description="Filter by claim type"),
    min_maturity: int | None = Query(None, ge=0, le=5, description="Minimum maturity level"),
    min_confidence: float | None = Query(None, ge=0.0, le=1.0, description="Minimum confidence"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    ctx: RequestContext = Depends(require_authenticated),
    l5_client: Layer5GroundTruthClient = Depends(get_l5_client),
) -> dict[str, Any]:
    """List TruthObjects with optional filtering."""
    result = await l5_client.list_truths(
        organization_id=str(ctx.tenant_id) if ctx.tenant_id else None,
        status=status,
        claim_type=claim_type,
        min_maturity=min_maturity,
        min_confidence=min_confidence,
        limit=limit,
        offset=offset,
    )
    return _handle_l5_result(result)


@router.get("/truths/{truth_id}", summary="Get a TruthObject")
async def get_truth(
    truth_id: UUID,
    ctx: RequestContext = Depends(require_authenticated),
    l5_client: Layer5GroundTruthClient = Depends(get_l5_client),
) -> dict[str, Any]:
    """Get a single TruthObject with full detail."""
    result = await l5_client.get_truth(
        truth_id=str(truth_id),
        organization_id=str(ctx.tenant_id) if ctx.tenant_id else None,
    )
    return _handle_l5_result(result)


@router.get("/truths/{truth_id}/audit", summary="Get TruthObject audit trail")
async def get_truth_audit(
    truth_id: UUID,
    ctx: RequestContext = Depends(require_authenticated),
    l5_client: Layer5GroundTruthClient = Depends(get_l5_client),
) -> list[dict[str, Any]]:
    """Get validation event log for a TruthObject."""
    result = await l5_client.get_truth_audit(
        truth_id=str(truth_id),
        organization_id=str(ctx.tenant_id) if ctx.tenant_id else None,
    )

    _handle_l5_result(result)
    return result.get("events", [])


@router.post("/truths/{truth_id}/validate", summary="Apply validation transition")
async def validate_truth(
    truth_id: UUID,
    request: ValidateTruthRequest,
    ctx: RequestContext = Depends(require_authenticated),
    l5_client: Layer5GroundTruthClient = Depends(get_l5_client),
) -> dict[str, Any]:
    """Apply a named validation action to a TruthObject."""
    result = await l5_client.validate_truth(
        truth_id=str(truth_id),
        action=request.action,
        actor=request.actor,
        actor_type=request.actor_type,
        organization_id=str(ctx.tenant_id) if ctx.tenant_id else None,
        notes=request.notes,
    )
    return _handle_l5_result(result)


@router.get("/truths/freshness-summary", summary="Get freshness summary")
async def get_freshness_summary(
    ctx: RequestContext = Depends(require_authenticated),
    l5_client: Layer5GroundTruthClient = Depends(get_l5_client),
) -> dict[str, Any]:
    """Get freshness summary across all TruthObjects."""
    result = await l5_client.get_freshness_summary(
        organization_id=str(ctx.tenant_id) if ctx.tenant_id else None,
    )
    return _handle_l5_result(result)


@router.get("/truths/stale", summary="Get stale TruthObjects")
async def get_stale_truths(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    ctx: RequestContext = Depends(require_authenticated),
    l5_client: Layer5GroundTruthClient = Depends(get_l5_client),
) -> dict[str, Any]:
    """Get TruthObjects that have become stale and need revalidation."""
    result = await l5_client.get_stale_truths(
        organization_id=str(ctx.tenant_id) if ctx.tenant_id else None,
        limit=limit,
        offset=offset,
    )
    return _handle_l5_result(result)


@router.get("/maturity-ladder", summary="Get maturity ladder definition")
async def get_maturity_ladder(
    ctx: RequestContext = Depends(require_authenticated),
    l5_client: Layer5GroundTruthClient = Depends(get_l5_client),
) -> dict[str, Any]:
    """Get the full maturity ladder definition for reference."""
    result = await l5_client.get_maturity_ladder(
        organization_id=str(ctx.tenant_id) if ctx.tenant_id else None,
    )
    return _handle_l5_result(result)
