from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from value_fabric.shared.error_handling.exceptions import ConflictError, NotFoundError

from ..database import get_db_from_context
from ..models.assumption_governance import (
    ApprovalRequest,
    AssumptionRecord,
    LifecycleState,
    PolicyRule,
)
from .auth import TokenClaims, get_current_user

router = APIRouter(prefix="/api/v1", tags=["assumption-governance"])


class AssumptionCreate(BaseModel):
    name: str
    description: str | None = None
    impact_value: float = Field(default=0.0, ge=0.0)


class AssumptionResponse(AssumptionCreate):
    id: UUID
    lifecycle_state: LifecycleState
    is_approved_for_use: bool

    model_config = {"from_attributes": True}


class PolicyRuleCreate(BaseModel):
    name: str
    min_impact_threshold: float = 0.0
    required_reviewer_role: str


class ApplySelectionRequest(BaseModel):
    context: str = "evaluation"


@router.post("/assumptions", response_model=AssumptionResponse, status_code=status.HTTP_201_CREATED)
async def create_assumption(payload: AssumptionCreate, caller: TokenClaims = Depends(get_current_user), db: AsyncSession = Depends(get_db_from_context)) -> AssumptionResponse:
    record = AssumptionRecord(tenant_id=caller.tenant_id, name=payload.name, description=payload.description, impact_value=payload.impact_value)
    db.add(record)
    await db.flush()
    return AssumptionResponse.model_validate(record)


@router.post("/policy-rules", response_model=PolicyRuleCreate, status_code=status.HTTP_201_CREATED)
async def create_policy_rule(payload: PolicyRuleCreate, caller: TokenClaims = Depends(get_current_user), db: AsyncSession = Depends(get_db_from_context)) -> PolicyRuleCreate:
    policy = PolicyRule(tenant_id=caller.tenant_id, name=payload.name, min_impact_threshold=payload.min_impact_threshold, required_reviewer_role=payload.required_reviewer_role)
    db.add(policy)
    await db.flush()
    return payload


@router.post("/assumptions/{assumption_id}/apply")
async def apply_assumption_selection(assumption_id: UUID, payload: ApplySelectionRequest, caller: TokenClaims = Depends(get_current_user), db: AsyncSession = Depends(get_db_from_context)) -> dict[str, str]:
    assumption = (await db.execute(select(AssumptionRecord).where(and_(AssumptionRecord.id == assumption_id, AssumptionRecord.tenant_id == caller.tenant_id)))).scalar_one_or_none()
    if not assumption:
        raise NotFoundError(message = "AssumptionRecord not found")

    policies = (await db.execute(select(PolicyRule).where(and_(PolicyRule.tenant_id == caller.tenant_id, PolicyRule.active.is_(True))))).scalars().all()
    matched = next((p for p in policies if assumption.impact_value > p.min_impact_threshold), None)
    if matched and not assumption.is_approved_for_use:
        approval = ApprovalRequest(tenant_id=caller.tenant_id, assumption_id=assumption.id, policy_rule_id=matched.id, requested_by=caller.user_id or caller.email)
        db.add(approval)
        raise ConflictError(message=f"Approval required for high-impact assumption. required_reviewer_role={matched.required_reviewer_role}")

    if assumption.lifecycle_state not in {LifecycleState.APPROVED.value, LifecycleState.PUBLISHED.value}:
        raise ConflictError(message="Assumption is not in an approved lifecycle state")

    return {"status": "applied", "context": payload.context}
