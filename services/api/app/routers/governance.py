from fastapi import APIRouter, Depends, Query

from app.core.database import db
from app.core.tenant_context import tenant_required
from app.models.schemas import AuditLogListResponse, GovernanceGate, GovernanceReviewQueueResponse, PaginatedResponse, ReviewDecision

router = APIRouter(prefix="/governance", tags=["Governance"])


@router.get("/review-queue", response_model=GovernanceReviewQueueResponse)
async def get_review_queue(tenant_id: str = Depends(tenant_required)):
    hypotheses = db.hypotheses.list(
        tenant_id=tenant_id, filter_fn=lambda h: h.status == "generated"
    )
    formulas = db.formulas.list(
        tenant_id=tenant_id, filter_fn=lambda f: f.validation_status == "draft"
    )
    evidence = db.evidence.list(
        tenant_id=tenant_id, filter_fn=lambda e: e.audit.review_state == "needs_review"
    )
    return GovernanceReviewQueueResponse(
        hypotheses=hypotheses,
        formulas=formulas,
        evidence=evidence,
        total=len(hypotheses) + len(formulas) + len(evidence),
    )


@router.post("/review-decisions", response_model=ReviewDecision, status_code=201)
async def create_review_decision(
    decision: ReviewDecision, tenant_id: str = Depends(tenant_required)
):
    decision.tenant_id = tenant_id
    db.review_decisions.insert(decision.id, decision)
    return decision


@router.get("/prod-gates", response_model=PaginatedResponse[GovernanceGate])
async def list_prod_gates(
    tenant_id: str = Depends(tenant_required),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    items = db.governance_gates.list(tenant_id=tenant_id, limit=limit, offset=offset)
    total = len(db.governance_gates.list(tenant_id=tenant_id))
    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/audit-log", response_model=AuditLogListResponse)
async def get_audit_log(tenant_id: str = Depends(tenant_required)):
    return AuditLogListResponse(items=db.audit_logs.list(tenant_id=tenant_id))
