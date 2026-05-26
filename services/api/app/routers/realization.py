from fastapi import APIRouter, Depends, HTTPException

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
    plan_payload = plan.model_dump()
    plan_payload["account_id"] = account_id
    plan_payload["tenant_id"] = tenant_id
    plan_payload["status"] = "active"
    db.roi_calculations.insert(plan_payload["id"], plan_payload)
    return ROICalculation.model_validate(plan_payload)


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
        raise HTTPException(status_code=404, detail="Plan not found")
    updated = db.roi_calculations.update(plan_id, tenant_id=tenant_id, **fields.model_dump(exclude_none=True))
    return updated


@router.get("/realization-plans/{plan_id}/variance", response_model=RealizationVarianceResponse)
async def get_variance(
    account_id: str,
    plan_id: str,
    tenant_id: str = Depends(tenant_required),
):
    plan = db.roi_calculations.get(plan_id, tenant_id=tenant_id)
    if not plan or plan.account_id != account_id:
        raise HTTPException(status_code=404, detail="Plan not found")
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
        raise HTTPException(status_code=404, detail="Plan not found")
    return {
        "plan_id": plan_id,
        "recommendations": [
            "Review underperforming metrics quarterly",
            "Expand to adjacent use cases",
            "Schedule renewal narrative review",
        ],
    }
