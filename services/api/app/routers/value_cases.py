from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from value_fabric.shared.error_handling.exceptions import AuthorizationError, NotFoundError

from app.core.database import db
from app.core.tenant_context import tenant_required
from app.models.schemas import BusinessCase, ValueCaseExportResponse
from app.services.gate_service import all_gates_pass, check_gates, get_gate_summary
from app.services.export_service import generate_export

router = APIRouter(prefix="/accounts/{account_id}", tags=["Value Case"])


@router.get("/value-case", response_model=BusinessCase)
async def get_value_case(account_id: str, tenant_id: str = Depends(tenant_required)):
    cases = db.business_cases.list(
        tenant_id=tenant_id, filter_fn=lambda c: c.account_id == account_id
    )
    if not cases:
        raise NotFoundError(message="No value case found for account")
    return cases[0]


@router.post("/value-case/generate", response_model=BusinessCase, status_code=201)
async def generate_value_case(
    account_id: str, case: BusinessCase, tenant_id: str = Depends(tenant_required)
):
    case.account_id = account_id
    case.tenant_id = tenant_id
    db.business_cases.insert(case.id, case)
    return case


@router.patch("/value-cases/{value_case_id}", response_model=BusinessCase)
async def update_value_case(
    value_case_id: str,
    fields: dict[str, Any],
    tenant_id: str = Depends(tenant_required),
):
    bc = db.business_cases.update(value_case_id, tenant_id=tenant_id, **fields)
    if not bc:
        raise NotFoundError(message="Value case not found")
    return bc


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
