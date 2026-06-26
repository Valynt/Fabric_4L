from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_authenticated

from app.clients.billing_publisher import BillingEventPublisher
from app.core.quota_service import QuotaService
from app.core.usage_meter import record_usage
from app.models.product import (
    AssumptionScoreRequest,
    CFONarrativeGenerateRequest,
    EvidenceExtractRequest,
    ProductJobResponse,
    RealizationCompareRequest,
    ValueDriversMapRequest,
    ValueModelGenerateRequest,
    ValueModelQARequest,
    ValueModelValidateRequest,
)

router = APIRouter(tags=["Product Endpoints"])


def _get_billing_publisher() -> BillingEventPublisher:
    return BillingEventPublisher()


def _get_quota_service() -> QuotaService:
    return QuotaService()


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


def _accept_job(product_code: str, result: dict | None = None) -> ProductJobResponse:
    return ProductJobResponse(
        job_id=f"job_{uuid.uuid4().hex}",
        product_code=product_code,
        status="accepted",
        result=result,
    )


async def _record_and_publish(
    request: Request, ctx: RequestContext, product_code: str, publisher: BillingEventPublisher
) -> None:
    event = record_usage(request=request, ctx=ctx, product_code=product_code)
    await publisher.publish(event)


@router.post("/value-drivers/map")
async def map_value_drivers(
    request: Request,
    payload: ValueDriversMapRequest,
    ctx: RequestContext = Depends(require_authenticated),
    publisher: BillingEventPublisher = Depends(_get_billing_publisher),
    quota: QuotaService = Depends(_get_quota_service),
):
    _require_quota(ctx, "value_drivers", quota)
    await _record_and_publish(request, ctx, "value_drivers", publisher)
    return _accept_job("value_drivers", {"mapped_drivers": []})


@router.post("/value-models/generate")
async def generate_value_model(
    request: Request,
    payload: ValueModelGenerateRequest,
    ctx: RequestContext = Depends(require_authenticated),
    publisher: BillingEventPublisher = Depends(_get_billing_publisher),
    quota: QuotaService = Depends(_get_quota_service),
):
    _require_quota(ctx, "value_models", quota)
    await _record_and_publish(request, ctx, "value_models", publisher)
    return _accept_job("value_models", {"generated_model": {}})


@router.post("/value-models/validate")
async def validate_value_model(
    request: Request,
    payload: ValueModelValidateRequest,
    ctx: RequestContext = Depends(require_authenticated),
    publisher: BillingEventPublisher = Depends(_get_billing_publisher),
    quota: QuotaService = Depends(_get_quota_service),
):
    _require_quota(ctx, "value_models", quota)
    await _record_and_publish(request, ctx, "value_models", publisher)
    return _accept_job("value_models", {"valid": True, "issues": []})


@router.post("/value-models/qa")
async def qa_value_model(
    request: Request,
    payload: ValueModelQARequest,
    ctx: RequestContext = Depends(require_authenticated),
    publisher: BillingEventPublisher = Depends(_get_billing_publisher),
    quota: QuotaService = Depends(_get_quota_service),
):
    _require_quota(ctx, "value_models", quota)
    await _record_and_publish(request, ctx, "value_models", publisher)
    return _accept_job("value_models", {"answer": ""})


@router.post("/assumptions/score")
async def score_assumption(
    request: Request,
    payload: AssumptionScoreRequest,
    ctx: RequestContext = Depends(require_authenticated),
    publisher: BillingEventPublisher = Depends(_get_billing_publisher),
    quota: QuotaService = Depends(_get_quota_service),
):
    _require_quota(ctx, "assumptions", quota)
    await _record_and_publish(request, ctx, "assumptions", publisher)
    return _accept_job("assumptions", {"score": 0.0, "confidence": "medium"})


@router.post("/evidence/extract-value-signals")
async def extract_value_signals(
    request: Request,
    payload: EvidenceExtractRequest,
    ctx: RequestContext = Depends(require_authenticated),
    publisher: BillingEventPublisher = Depends(_get_billing_publisher),
    quota: QuotaService = Depends(_get_quota_service),
):
    _require_quota(ctx, "evidence", quota)
    await _record_and_publish(request, ctx, "evidence", publisher)
    return _accept_job("evidence", {"signals": []})


@router.post("/cfo-narratives/generate")
async def generate_cfo_narrative(
    request: Request,
    payload: CFONarrativeGenerateRequest,
    ctx: RequestContext = Depends(require_authenticated),
    publisher: BillingEventPublisher = Depends(_get_billing_publisher),
    quota: QuotaService = Depends(_get_quota_service),
):
    _require_quota(ctx, "cfo_narratives", quota)
    await _record_and_publish(request, ctx, "cfo_narratives", publisher)
    return _accept_job("cfo_narratives", {"narrative": ""})


@router.post("/realization/compare")
async def compare_realization(
    request: Request,
    payload: RealizationCompareRequest,
    ctx: RequestContext = Depends(require_authenticated),
    publisher: BillingEventPublisher = Depends(_get_billing_publisher),
    quota: QuotaService = Depends(_get_quota_service),
):
    _require_quota(ctx, "realization", quota)
    await _record_and_publish(request, ctx, "realization", publisher)
    return _accept_job("realization", {"variance": {}})
