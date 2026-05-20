"""Agents domain router — value-tree, whitespace, ROI, narrative, provenance, workflow.

Migrated from app_monolith.py as part of ARCH-L3-011 (Sprint 3 cutover).
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from ...api.dependencies import (
    get_narrative_synthesis_agent,
    get_provenance_tracking_agent,
    get_roi_calculation_agent,
    get_value_tree_projection_agent,
    get_whitespace_analysis_agent,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/agents", tags=["Agents"])


def _require_tenant_id(request: Request) -> str:
    """Extract tenant_id from the authenticated request context.

    Raises 401 if the context is absent or carries no tenant_id.
    """
    ctx = getattr(request.state, "context", None)
    tenant_id = str(ctx.tenant_id) if ctx and getattr(ctx, "tenant_id", None) else None
    if not tenant_id:
        raise HTTPException(
            status_code=401,
            detail="Authenticated tenant context required",
        )
    return tenant_id


@router.post("/value-tree-projection")
async def value_tree_projection(
    body: dict[str, Any],
    fastapi_request: Request,
    agent=Depends(get_value_tree_projection_agent),
) -> Any:
    """Execute value tree projection agent for traversal and semantic matching."""
    tenant_id = _require_tenant_id(fastapi_request)
    try:
        result = await agent.execute({**body, "tenant_id": tenant_id})
        return result.to_dict() if hasattr(result, "to_dict") else result.__dict__
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Value tree projection failed: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Value tree projection failed. Please try again later.",
        )


@router.post("/whitespace-analysis")
async def whitespace_analysis(
    body: dict[str, Any],
    fastapi_request: Request,
    agent=Depends(get_whitespace_analysis_agent),
) -> Any:
    """Execute whitespace analysis agent for gap identification and account planning."""
    tenant_id = _require_tenant_id(fastapi_request)
    try:
        result = await agent.execute({**body, "tenant_id": tenant_id})
        return result.to_dict() if hasattr(result, "to_dict") else result.__dict__
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Whitespace analysis failed: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Whitespace analysis failed. Please try again later.",
        )


@router.post("/roi-calculation")
async def roi_calculation(
    body: dict[str, Any],
    fastapi_request: Request,
    agent=Depends(get_roi_calculation_agent),
) -> Any:
    """Execute ROI calculation agent for formula execution and sensitivity analysis."""
    tenant_id = _require_tenant_id(fastapi_request)
    try:
        result = await agent.execute({**body, "tenant_id": tenant_id})
        return result.to_dict() if hasattr(result, "to_dict") else result.__dict__
    except HTTPException:
        raise
    except Exception as e:
        logger.error("ROI calculation failed: %s", e)
        raise HTTPException(
            status_code=500,
            detail="ROI calculation failed. Please try again later.",
        )


@router.post("/narrative-synthesis")
async def narrative_synthesis(
    body: dict[str, Any],
    fastapi_request: Request,
    agent=Depends(get_narrative_synthesis_agent),
) -> Any:
    """Execute narrative synthesis agent for report generation."""
    tenant_id = _require_tenant_id(fastapi_request)
    try:
        result = await agent.execute({**body, "tenant_id": tenant_id})
        return result.to_dict() if hasattr(result, "to_dict") else result.__dict__
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Narrative synthesis failed: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Narrative synthesis failed. Please try again later.",
        )


@router.post("/provenance-tracking")
async def provenance_tracking(
    body: dict[str, Any],
    fastapi_request: Request,
    agent=Depends(get_provenance_tracking_agent),
) -> Any:
    """Execute provenance tracking agent for lineage and decision traces."""
    tenant_id = _require_tenant_id(fastapi_request)
    try:
        result = await agent.execute({**body, "tenant_id": tenant_id})
        return result.to_dict() if hasattr(result, "to_dict") else result.__dict__
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Provenance tracking failed: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Provenance tracking failed. Please try again later.",
        )


@router.post("/workflow")
async def agent_workflow(
    workflow_type: str,
    context: dict[str, Any],
    fastapi_request: Request,
    value_tree_agent=Depends(get_value_tree_projection_agent),
    whitespace_agent=Depends(get_whitespace_analysis_agent),
    roi_agent=Depends(get_roi_calculation_agent),
    narrative_agent=Depends(get_narrative_synthesis_agent),
    provenance_agent=Depends(get_provenance_tracking_agent),
) -> dict[str, Any]:
    """Execute multi-agent workflow for end-to-end business case generation.

    Supported workflows:
    - ``whitespace_analysis``: Gap identification → Account plan
    - ``business_case``: Opportunity eval → ROI calc → Narrative synthesis
    """
    tenant_id = _require_tenant_id(fastapi_request)
    # Stamp tenant_id from auth context; ignore any tenant_id in the body.
    context = {**context, "tenant_id": tenant_id}

    try:
        results: list[dict[str, Any]] = []

        if workflow_type == "whitespace_analysis":
            gap_result = await whitespace_agent.execute(
                {"operation": "gap_analysis", **context}
            )
            results.append(
                {"step": 1, "agent": "WhitespaceAnalysisAgent", "result": gap_result}
            )

            plan_result = await whitespace_agent.execute(
                {"operation": "account_plan", **context}
            )
            results.append(
                {"step": 2, "agent": "WhitespaceAnalysisAgent", "result": plan_result}
            )

            await provenance_agent.execute(
                {
                    "operation": "create_decision_trace",
                    "workflow_id": "whitespace_analysis_v1",
                    "workflow_instance_id": f"ws-{datetime.utcnow().timestamp()}",
                    "output_type": "account_plan",
                    "output_id": plan_result.output.get("plan_id", "unknown"),
                    "steps": results,
                }
            )

        elif workflow_type == "business_case":
            vt_result = await value_tree_agent.execute(
                {"operation": "upward_traversal", **context}
            )
            results.append(
                {"step": 1, "agent": "ValueTreeProjectionAgent", "result": vt_result}
            )

            roi_result = await roi_agent.execute({"operation": "calculate", **context})
            results.append(
                {"step": 2, "agent": "ROICalculationAgent", "result": roi_result}
            )

            narrative_result = await narrative_agent.execute(
                {"operation": "generate_executive_summary", **context}
            )
            results.append(
                {"step": 3, "agent": "NarrativeSynthesisAgent", "result": narrative_result}
            )

            await provenance_agent.execute(
                {
                    "operation": "create_decision_trace",
                    "workflow_id": "business_case_v1",
                    "workflow_instance_id": f"bc-{datetime.utcnow().timestamp()}",
                    "output_type": "business_case",
                    "output_id": narrative_result.output.get("narrative_id", "unknown"),
                    "steps": results,
                }
            )
        else:
            raise HTTPException(
                status_code=400, detail=f"Unknown workflow type: {workflow_type}"
            )

        return {
            "workflow_type": workflow_type,
            "steps_completed": len(results),
            "results": results,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Agent workflow failed: %s", e)
        raise HTTPException(
            status_code=500, detail="Agent workflow failed. Please try again later."
        )
