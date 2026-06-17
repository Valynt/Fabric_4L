from fastapi import APIRouter, Depends, HTTPException, Query
from value_fabric.shared.error_handling.exceptions import NotFoundError

from app.core.database import db
from app.core.account_scope import require_account_scope
from app.core.security import TokenPayload, require_authenticated
from app.core.tenant_enforcement import enforce_authenticated_tenant
from app.core.tenant_context import tenant_required
from app.models.schemas import EnrichmentResponse, FirmographicsResponse, OntologyMatchResponse, PaginatedResponse, Signal, Stakeholder

router = APIRouter(prefix="/accounts/{account_id}", tags=["Intelligence"])
legacy_router = APIRouter(prefix="/intelligence/account/{account_id}", tags=["Intelligence"])


@router.get("/signals", response_model=PaginatedResponse[Signal])
async def list_signals(
    account_id: str,
    tenant_id: str = Depends(tenant_required),
    auth: TokenPayload = Depends(require_authenticated),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    require_account_scope(auth=auth, account_id=account_id, route="/v1/accounts/{account_id}/signals")
    items = db.signals.list(tenant_id=tenant_id, filter_fn=lambda s: s.account_id == account_id, limit=limit, offset=offset)
    total = db.signals.count(tenant_id=tenant_id, filter_fn=lambda s: s.account_id == account_id)
    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)


@router.post("/signals/extract", response_model=Signal, status_code=201)
async def extract_signal(
    account_id: str, signal: Signal, tenant_id: str = Depends(tenant_required), auth: TokenPayload = Depends(require_authenticated)
):
    require_account_scope(auth=auth, account_id=account_id, route="/v1/accounts/{account_id}/signals/extract")
    enforce_authenticated_tenant(
        body_tenant_id=signal.tenant_id,
        authenticated_tenant_id=tenant_id,
        route="/v1/accounts/{account_id}/signals/extract",
        operation="extract_signal",
    )
    signal.account_id = account_id
    signal.tenant_id = tenant_id
    db.signals.insert(signal.id, signal)
    return signal


@router.get("/stakeholders", response_model=PaginatedResponse[Stakeholder])
async def list_stakeholders(
    account_id: str,
    tenant_id: str = Depends(tenant_required),
    auth: TokenPayload = Depends(require_authenticated),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    require_account_scope(auth=auth, account_id=account_id, route="/v1/accounts/{account_id}/stakeholders")
    items = db.stakeholders.list(tenant_id=tenant_id, filter_fn=lambda s: s.account_id == account_id, limit=limit, offset=offset)
    total = db.stakeholders.count(tenant_id=tenant_id, filter_fn=lambda s: s.account_id == account_id)
    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/ontology-match", response_model=OntologyMatchResponse)
async def get_ontology_match(
    account_id: str,
    tenant_id: str = Depends(tenant_required),
    auth: TokenPayload = Depends(require_authenticated),
):
    require_account_scope(auth=auth, account_id=account_id, route="/v1/accounts/{account_id}/ontology-match")
    acc = db.accounts.get(account_id, tenant_id=tenant_id)
    if not acc:
        raise NotFoundError(message="Account not found")
    pack = db.value_packs.get(acc.value_pack_id) if acc.value_pack_id else None
    return OntologyMatchResponse(
        account_id=account_id,
        matched_pack=pack,
        confidence=0.85 if pack else 0.0,
        gaps=[] if pack else ["No value pack assigned"],
    )


@router.get("/enrichment", response_model=EnrichmentResponse)
async def get_enrichment(
    account_id: str,
    tenant_id: str = Depends(tenant_required),
    auth: TokenPayload = Depends(require_authenticated),
):
    require_account_scope(auth=auth, account_id=account_id, route="/v1/accounts/{account_id}/enrichment")
    acc = db.accounts.get(account_id, tenant_id=tenant_id)
    if not acc:
        raise NotFoundError(message="Account not found")
    return EnrichmentResponse(
        account_id=account_id,
        firmographics=FirmographicsResponse(
            revenue=acc.annual_revenue,
            employees=acc.employee_count,
            industry=acc.industry,
            website=acc.website,
        ),
        tech_stack=["Salesforce", "HubSpot", "Slack"],
        public_sources=["LinkedIn", "Crunchbase"],
    )


@legacy_router.get("/signals", response_model=PaginatedResponse[Signal])
async def list_signals_legacy(
    account_id: str,
    tenant_id: str = Depends(tenant_required),
    auth: TokenPayload = Depends(require_authenticated),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    return await list_signals(account_id=account_id, tenant_id=tenant_id, auth=auth, limit=limit, offset=offset)


@legacy_router.post("/signals/extract", response_model=Signal, status_code=201)
async def extract_signal_legacy(
    account_id: str,
    signal: Signal,
    tenant_id: str = Depends(tenant_required),
    auth: TokenPayload = Depends(require_authenticated),
):
    return await extract_signal(account_id=account_id, signal=signal, tenant_id=tenant_id, auth=auth)


@legacy_router.get("/stakeholders", response_model=PaginatedResponse[Stakeholder])
async def list_stakeholders_legacy(
    account_id: str,
    tenant_id: str = Depends(tenant_required),
    auth: TokenPayload = Depends(require_authenticated),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    return await list_stakeholders(account_id=account_id, tenant_id=tenant_id, auth=auth, limit=limit, offset=offset)


@legacy_router.get("/ontology-match", response_model=OntologyMatchResponse)
async def get_ontology_match_legacy(
    account_id: str,
    tenant_id: str = Depends(tenant_required),
    auth: TokenPayload = Depends(require_authenticated),
):
    return await get_ontology_match(account_id=account_id, tenant_id=tenant_id, auth=auth)


@legacy_router.get("/enrichment", response_model=EnrichmentResponse)
async def get_enrichment_legacy(
    account_id: str,
    tenant_id: str = Depends(tenant_required),
    auth: TokenPayload = Depends(require_authenticated),
):
    return await get_enrichment(account_id=account_id, tenant_id=tenant_id, auth=auth)
