from fastapi import APIRouter, Depends, HTTPException
from value_fabric.shared.error_handling.exceptions import NotFoundError

from app.core.database import db
from app.core.tenant_context import tenant_required
from app.models.schemas import (
    ROICalculation,
    RealizationPlanActualsPatchRequest,
    RealizationPlanCreateRequest,
    RealizationRecommendationsResponse,
    RealizationVarianceResponse,
)

router = APIRouter(prefix="/accounts/{account_id}", tags=["Realization"])


@router.post("/realization-plans", response_model=ROICalculation)
async def create_realization_plan(
    account_id: str,
    plan: RealizationPlanCreateRequest,
    tenant_id: str = Depends(tenant_required),
):
    roi_payload = ROICalculation(
        id=plan.id,
        account_id=account_id,
        tenant_id=tenant_id,
        scenario_id=plan.scenario_id,
        revenue_uplift=plan.revenue_uplift or 0.0,
        cost_savings=plan.cost_savings or 0.0,
        risk_reduction=plan.risk_reduction or 0.0,
        total_benefit=plan.total_benefit or 0.0,
        solution_cost=plan.solution_cost or 0.0,
        net_benefit=plan.net_benefit or 0.0,
        roi_percent=plan.roi_percent or 0.0,
        payback_months=plan.payback_months or 0.0,
        calculation_trace=plan.calculation_trace,
        evidence_ids=plan.evidence_ids,
        assumption_ids=plan.assumption_ids,
    )
    db.roi_calculations.insert(roi_payload.id, roi_payload.model_dump())
    return roi_payload


@router.get("/realization-plans", response_model=list[ROICalculation])
async def list_realization_plans(
    account_id: str,
    tenant_id: str = Depends(tenant_required),
):
    return db.roi_calculations.list(
        tenant_id=tenant_id,
        filter_fn=lambda r: r.account_id == account_id,
    )


@router.patch("/realization-plans/{plan_id}/actuals", response_model=ROICalculation)
async def update_actuals(
    account_id: str,
    plan_id: str,
    fields: RealizationPlanActualsPatchRequest,
    tenant_id: str = Depends(tenant_required),
):
    plan = db.roi_calculations.get(plan_id, tenant_id=tenant_id)
    if not plan or plan.account_id != account_id:
        raise NotFoundError(message="Plan not found")
    updated_fields = fields.model_dump(exclude_unset=True)
    updated = db.roi_calculations.update(plan_id, tenant_id=tenant_id, **updated_fields)
    return updated


@router.get("/realization-plans/{plan_id}/variance", response_model=RealizationVarianceResponse)
async def get_variance(
    account_id: str,
    plan_id: str,
    tenant_id: str = Depends(tenant_required),
):
    plan = db.roi_calculations.get(plan_id, tenant_id=tenant_id)
    if not plan or plan.account_id != account_id:
        raise NotFoundError(message="Plan not found")
    return {
        "plan_id": plan_id,
        "projected": getattr(plan, "total_benefit", 0),
        "actual": getattr(plan, "actual_benefit", 0),
        "variance": getattr(plan, "total_benefit", 0) - getattr(plan, "actual_benefit", 0),
    }


@router.get("/realization-plans/{plan_id}/recommendations", response_model=RealizationRecommendationsResponse)
async def get_recommendations(
    account_id: str,
    plan_id: str,
    tenant_id: str = Depends(tenant_required),
):
    plan = db.roi_calculations.get(plan_id, tenant_id=tenant_id)
    if not plan or plan.account_id != account_id:
        raise NotFoundError(message="Plan not found")
    return {
        "plan_id": plan_id,
        "recommendations": [
            "Review underperforming metrics quarterly",
            "Expand to adjacent use cases",
            "Schedule renewal narrative review",
        ],
    }
