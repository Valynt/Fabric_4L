from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from value_fabric.shared.error_handling.exceptions import AuthorizationError, NotFoundError

from app.core.database import db
from app.core.tenant_context import tenant_required
from app.models.schemas import AuditMeta, BusinessCase, ValueCaseContent, ValueCaseExportResponse
from app.services.export_service import generate_export
from app.services.gate_service import check_gates, get_gate_summary

router = APIRouter(prefix="/accounts/{account_id}", tags=["Value Case"])


class CreateValueCaseRequest(BaseModel):
    title: str
    value_case: ValueCaseContent


@router.get("/value-cases", response_model=list[BusinessCase])
async def list_value_cases(account_id: str, tenant_id: str = Depends(tenant_required)):
    """List all value cases for an account, most recently updated first."""
    cases = db.business_cases.list(
        tenant_id=tenant_id,
        filter_fn=lambda c: c.account_id == account_id,
    )
    return sorted(cases, key=lambda c: c.audit.updated_at, reverse=True)


@router.get("/value-case", response_model=BusinessCase)
async def get_account_value_case(account_id: str, tenant_id: str = Depends(tenant_required)):
    """Return the most recently updated value case for an account."""
    cases = db.business_cases.list(
        tenant_id=tenant_id,
        filter_fn=lambda c: c.account_id == account_id,
    )
    if not cases:
        raise NotFoundError(message="No value case found for account")
    return max(cases, key=lambda c: c.audit.updated_at)


@router.post("/value-case", response_model=BusinessCase, status_code=201)
async def create_value_case(
    account_id: str,
    request: CreateValueCaseRequest,
    tenant_id: str = Depends(tenant_required),
):
    """Create a new value case for an account."""
    now = AuditMeta().model_dump(mode="json")
    case = BusinessCase(
        id=str(uuid4()),
        account_id=account_id,
        tenant_id=tenant_id,
        title=request.title,
        value_case=request.value_case,
        audit=AuditMeta.model_validate(now),
    )
    db.business_cases.insert(case.id, case)
    return case


@router.post("/value-case/generate", response_model=BusinessCase, status_code=201)
async def generate_value_case(
    account_id: str,
    case: BusinessCase,
    tenant_id: str = Depends(tenant_required),
):
    """Persist a generated value case artifact."""
    case.account_id = account_id
    case.tenant_id = tenant_id
    if not case.id:
        case.id = str(uuid4())
    db.business_cases.insert(case.id, case)
    return case


@router.get("/value-cases/{value_case_id}", response_model=BusinessCase)
async def get_value_case(
    account_id: str,
    value_case_id: str,
    tenant_id: str = Depends(tenant_required),
):
    """Get a specific value case, verifying account ownership."""
    case = db.business_cases.get(value_case_id, tenant_id=tenant_id)
    if not case or case.account_id != account_id:
        raise NotFoundError(message="Value case not found")
    return case


@router.patch("/value-cases/{value_case_id}", response_model=BusinessCase)
async def update_value_case(
    account_id: str,
    value_case_id: str,
    fields: dict[str, Any],
    tenant_id: str = Depends(tenant_required),
):
    """Update editable fields on a value case."""
    case = db.business_cases.get(value_case_id, tenant_id=tenant_id)
    if not case or case.account_id != account_id:
        raise NotFoundError(message="Value case not found")

    allowed = {
        "title",
        "executive_summary",
        "value_narrative",
        "recommendation",
        "status",
        "value_case",
        "assumptions",
        "risks",
        "roi_calculation_ids",
        "evidence_ids",
    }
    updates = {k: v for k, v in fields.items() if k in allowed}
    updated = db.business_cases.update(value_case_id, tenant_id=tenant_id, **updates)
    if not updated:
        raise NotFoundError(message="Value case not found")
    return updated


@router.post("/value-cases/{value_case_id}/publish", response_model=BusinessCase)
async def publish_value_case(
    account_id: str,
    value_case_id: str,
    tenant_id: str = Depends(tenant_required),
):
    """Publish a draft value case."""
    case = db.business_cases.get(value_case_id, tenant_id=tenant_id)
    if not case or case.account_id != account_id:
        raise NotFoundError(message="Value case not found")
    updated = db.business_cases.update(
        value_case_id,
        tenant_id=tenant_id,
        status="published",
    )
    if not updated:
        raise NotFoundError(message="Value case not found")
    return updated


@router.get("/gates", response_model=dict[str, Any])
async def get_account_gates(account_id: str, tenant_id: str = Depends(tenant_required)):
    return get_gate_summary(account_id, tenant_id)


@router.post("/value-case/{value_case_id}/export", response_model=ValueCaseExportResponse)
async def export_value_case(
    account_id: str,
    value_case_id: str,
    format: str = "pdf",
    tenant_id: str = Depends(tenant_required),
):
    gates = check_gates(account_id, tenant_id)
    open_gates = [g for g in gates if not g.passed()]
    if open_gates:
        raise AuthorizationError(
            message="Export blocked: required gates are not closed",
            details={
                "open_gates": [
                    {"type": g.gate_type, "reason": g.reason} for g in open_gates
                ],
            },
        )
    case = db.business_cases.get(value_case_id, tenant_id=tenant_id)
    if not case or case.account_id != account_id:
        raise NotFoundError(message="Value case not found")
    result = generate_export(account_id, value_case_id, tenant_id, format)  # type: ignore[arg-type]
    return result
