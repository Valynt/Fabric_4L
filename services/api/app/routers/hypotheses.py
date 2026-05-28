from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from value_fabric.shared.error_handling.exceptions import NotFoundError

from app.core.database import db
from app.core.tenant_enforcement import enforce_authenticated_tenant
from app.core.tenant_context import tenant_required
from app.models.schemas import PaginatedResponse, ValueHypothesis

router = APIRouter(prefix="/accounts/{account_id}", tags=["Hypotheses"])


@router.get("/hypotheses", response_model=PaginatedResponse[ValueHypothesis])
async def list_hypotheses(
    account_id: str,
    tenant_id: str = Depends(tenant_required),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    items = db.hypotheses.list(tenant_id=tenant_id, filter_fn=lambda h: h.account_id == account_id, limit=limit, offset=offset)
    total = len(db.hypotheses.list(tenant_id=tenant_id, filter_fn=lambda h: h.account_id == account_id))
    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)


@router.post("/hypotheses/generate", response_model=ValueHypothesis, status_code=201)
async def generate_hypothesis(
    account_id: str, hypothesis: ValueHypothesis, tenant_id: str = Depends(tenant_required)
):
    enforce_authenticated_tenant(
        body_tenant_id=hypothesis.tenant_id,
        authenticated_tenant_id=tenant_id,
        route="/v1/accounts/{account_id}/hypotheses/generate",
        operation="generate_hypothesis",
    )
    hypothesis.account_id = account_id
    hypothesis.tenant_id = tenant_id
    db.hypotheses.insert(hypothesis.id, hypothesis)
    return hypothesis


@router.patch("/hypotheses/{hypothesis_id}", response_model=ValueHypothesis)
async def update_hypothesis(
    hypothesis_id: str,
    fields: dict[str, Any],
    tenant_id: str = Depends(tenant_required),
):
    hyp = db.hypotheses.update(hypothesis_id, tenant_id=tenant_id, **fields)
    if not hyp:
        raise NotFoundError(message="Hypothesis not found")
    return hyp
