from __future__ import annotations

"""
Intelligence Orchestration API routes — Data Intelligence Layer Phase 3, Task 3.2.

Cross-layer endpoints that assemble intelligence from all DIL services
into unified deliverables.

All endpoints require authentication via GovernanceMiddleware.
Tenant identity is extracted from the verified JWT/API-key context (V-001, V-002).
"""


from fastapi import APIRouter, Depends, Query, Request
from value_fabric.shared.security.dil_auth import get_verified_tenant_id

router = APIRouter(prefix="/intelligence", tags=["Intelligence"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_neo4j_driver(request: Request):
    """Get Neo4j driver from app state."""
    return request.app.state.neo4j_driver


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/account/{account_id}/briefing")
async def get_account_briefing(
    account_id: str,
    request: Request,
    include_narrative: bool = Query(False),
    top_n: int = Query(5, ge=1, le=20),
    roi_scenario: str = Query("moderate"),
    tenant_id: str = Depends(get_verified_tenant_id),
):
    """Get a complete intelligence briefing for an account.

    Assembles signals, hypotheses, competitive intel, ROI, evidence,
    and optionally a generated narrative into a single briefing document.
    """
    from ...services.intelligence_orchestrator import IntelligenceOrchestrator

    driver = _get_neo4j_driver(request)
    orchestrator = IntelligenceOrchestrator(driver)

    result = await orchestrator.get_account_briefing(
        account_id,
        tenant_id=tenant_id,
        include_narrative=include_narrative,
        top_n_hypotheses=top_n,
        roi_scenario=roi_scenario,
    )

    return result


@router.get("/account/{account_id}/deal-readiness")
async def get_deal_readiness(
    account_id: str,
    request: Request,
    tenant_id: str = Depends(get_verified_tenant_id),
):
    """Calculate deal readiness score for an account.

    Returns a weighted composite score (0-1) based on intelligence
    completeness: signals, hypotheses, competitive intel, ROI,
    evidence, and narrative availability.
    """
    from ...services.intelligence_orchestrator import IntelligenceOrchestrator

    driver = _get_neo4j_driver(request)
    orchestrator = IntelligenceOrchestrator(driver)

    return await orchestrator.get_deal_readiness(account_id, tenant_id=tenant_id)


@router.get("/pipeline-summary")
async def get_pipeline_summary(
    request: Request,
    tenant_id: str = Depends(get_verified_tenant_id),
):
    """Get aggregated intelligence across all accounts.

    Returns pipeline-level metrics: total accounts with hypotheses,
    total pipeline value, hypothesis counts, and per-account summaries.
    """
    from ...services.intelligence_orchestrator import IntelligenceOrchestrator

    driver = _get_neo4j_driver(request)
    orchestrator = IntelligenceOrchestrator(driver)

    return await orchestrator.get_pipeline_summary(tenant_id)
