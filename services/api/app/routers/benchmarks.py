from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_authenticated
from value_fabric.shared.identity.permissions import Permission

from app.clients.billing_publisher import BillingEventPublisher
from app.clients.layer6_client import Layer6Client
from app.core.quota_service import QuotaService
from app.core.security import require_bearer_declaration
from app.core.usage_meter import record_usage
from app.models.schemas import PaginatedResponse

router = APIRouter(
    prefix="/benchmarks",
    tags=["Benchmarks"],
    dependencies=[Depends(require_bearer_declaration)],
)


def _get_layer6_client() -> Layer6Client:
    return Layer6Client()


def _get_quota_service() -> QuotaService:
    return QuotaService()


def _get_billing_publisher() -> BillingEventPublisher:
    return BillingEventPublisher()


def _require_quota(ctx: RequestContext, product_code: str, quota: QuotaService) -> None:
    check = quota.check(str(ctx.tenant_id), product_code, quantity=1.0)
    if not check["allowed"]:
        raise HTTPException(
            status_code=429,
            detail={
                "code": "QUOTA_EXCEEDED",
                "product_code": product_code,
                "limit": check["limit"],
                "used": check["used"],
            },
        )


def _require_benchmark_access(ctx: RequestContext) -> None:
    if not ctx.has_permission(Permission.READ_BENCHMARKS):
        raise HTTPException(
            status_code=403,
            detail={"code": "INSUFFICIENT_SCOPE", "permission": Permission.READ_BENCHMARKS.value},
        )


@router.get("", response_model=PaginatedResponse[dict[str, Any]])
async def list_benchmarks(
    request: Request,
    ctx: RequestContext = Depends(require_authenticated),
    client: Layer6Client = Depends(_get_layer6_client),
    quota: QuotaService = Depends(_get_quota_service),
    publisher: BillingEventPublisher = Depends(_get_billing_publisher),
):
    _require_quota(ctx, "benchmarks", quota)
    _require_benchmark_access(ctx)
    datasets = await client.list_datasets(str(ctx.tenant_id))
    event = record_usage(request=request, ctx=ctx, product_code="benchmarks", quantity=1.0, unit="request")
    await publisher.publish(event)
    return PaginatedResponse(items=datasets, total=len(datasets), limit=100, offset=0)


@router.post("/compare")
async def compare_benchmarks(
    request: Request,
    payload: dict[str, Any],
    ctx: RequestContext = Depends(require_authenticated),
    client: Layer6Client = Depends(_get_layer6_client),
    quota: QuotaService = Depends(_get_quota_service),
    publisher: BillingEventPublisher = Depends(_get_billing_publisher),
):
    _require_quota(ctx, "benchmarks", quota)
    _require_benchmark_access(ctx)
    result = await client.compare(str(ctx.tenant_id), payload)
    event = record_usage(request=request, ctx=ctx, product_code="benchmarks", quantity=1.0, unit="request")
    await publisher.publish(event)
    return result
