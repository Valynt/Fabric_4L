from fastapi import APIRouter, Depends, HTTPException, Query
from value_fabric.shared.error_handling.exceptions import NotFoundError

from app.core.database import db
from app.core.account_scope import require_account_scope
from app.core.security import TokenPayload, require_authenticated
from app.core.tenant_enforcement import enforce_authenticated_tenant
from app.core.tenant_context import tenant_required
from app.models.schemas import Evidence, PaginatedResponse
from app.services.pii_detection_service import pii_summary

router = APIRouter(prefix="/accounts/{account_id}", tags=["Evidence"])


@router.get("/evidence", response_model=PaginatedResponse[Evidence])
async def list_evidence(
    account_id: str,
    tenant_id: str = Depends(tenant_required),
    auth: TokenPayload = Depends(require_authenticated),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    require_account_scope(auth=auth, account_id=account_id, route="/v1/accounts/{account_id}/evidence")
    items = db.evidence.list(tenant_id=tenant_id, filter_fn=lambda e: e.account_id == account_id, limit=limit, offset=offset)
    total = db.evidence.count(tenant_id=tenant_id, filter_fn=lambda e: e.account_id == account_id)
    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)


@router.post("/evidence/match", response_model=Evidence, status_code=201)
async def match_evidence(
    account_id: str, evidence: Evidence, tenant_id: str = Depends(tenant_required), auth: TokenPayload = Depends(require_authenticated)
):
    require_account_scope(auth=auth, account_id=account_id, route="/v1/accounts/{account_id}/evidence/match")
    enforce_authenticated_tenant(
        body_tenant_id=evidence.tenant_id,
        authenticated_tenant_id=tenant_id,
        route="/v1/accounts/{account_id}/evidence/match",
        operation="match_evidence",
    )
    evidence.account_id = account_id
    evidence.tenant_id = tenant_id
    db.evidence.insert(evidence.id, evidence)
    return evidence


@router.get("/evidence/{evidence_id}", response_model=Evidence)
async def get_evidence(evidence_id: str, tenant_id: str = Depends(tenant_required)):
    ev = db.evidence.get(evidence_id, tenant_id=tenant_id)
    if not ev:
        raise NotFoundError(message="Evidence not found")
    return ev


@router.post("/evidence/{evidence_id}/pii-scan")
async def scan_evidence_pii(
    account_id: str,
    evidence_id: str,
    tenant_id: str = Depends(tenant_required),
    auth: TokenPayload = Depends(require_authenticated),
):
    require_account_scope(auth=auth, account_id=account_id, route="/v1/accounts/{account_id}/evidence/{evidence_id}/pii-scan")
    ev = db.evidence.get(evidence_id, tenant_id=tenant_id)
    if not ev or ev.account_id != account_id:
        raise NotFoundError(message="Evidence not found")
    text = ev.excerpt or ev.title or ""
    return pii_summary(text)
