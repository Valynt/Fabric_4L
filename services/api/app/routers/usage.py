from __future__ import annotations

from fastapi import APIRouter, Depends
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_authenticated

from app.core.quota_service import QuotaService
from app.core.security import require_bearer_declaration
from app.core.usage_meter import list_usage_events

router = APIRouter(
    prefix="/usage",
    tags=["Usage"],
    dependencies=[Depends(require_bearer_declaration)],
)


def _get_quota_service() -> QuotaService:
    return QuotaService()


@router.get("")
def get_usage(
    ctx: RequestContext = Depends(require_authenticated),
    limit: int = 100,
):
    events = list_usage_events(str(ctx.tenant_id), limit=limit)
    return {
        "tenant_id": str(ctx.tenant_id),
        "events": [e.model_dump() for e in events],
        "total": len(events),
    }


@router.get("/quotas")
def get_quotas(
    ctx: RequestContext = Depends(require_authenticated),
    quota: QuotaService = Depends(_get_quota_service),
):
    return {
        "tenant_id": str(ctx.tenant_id),
        "quotas": quota.quotas(str(ctx.tenant_id)),
    }
