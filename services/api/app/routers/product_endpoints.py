from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_authenticated

from app.clients.billing_publisher import BillingEventPublisher
from app.core.quota_service import QuotaService
from app.core.security import require_bearer_declaration
from app.core.usage_meter import record_usage
from app.models.product import (
    AssumptionScoreRequest,
    CFONarrativeGenerateRequest,
    EvidenceExtractRequest,
    RealizationCompareRequest,
    ValueDriversMapRequest,
    ValueModelGenerateRequest,
    ValueModelQARequest,
    ValueModelValidateRequest,
)
from app.services.product_orchestrator import ProductOrchestrator

router = APIRouter(
    tags=["Product Endpoints"],
    dependencies=[Depends(require_bearer_declaration)],
)


def _get_billing_publisher() -> BillingEventPublisher:
    return BillingEventPublisher()


def _get_quota_service() -> QuotaService:
    return QuotaService()


def _get_orchestrator() -> ProductOrchestrator:
    return ProductOrchestrator()


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
    orchestrator: ProductOrchestrator = Depends(_get_orchestrator),
):
    _require_quota(ctx, "value_drivers", quota)
    response = await orchestrator.map_value_drivers(str(ctx.tenant_id), payload)
    await _record_and_publish(request, ctx, "value_drivers", publisher)
    return response


@router.post("/value-models/generate")
async def generate_value_model(
    request: Request,
    payload: ValueModelGenerateRequest,
    ctx: RequestContext = Depends(require_authenticated),
    publisher: BillingEventPublisher = Depends(_get_billing_publisher),
    quota: QuotaService = Depends(_get_quota_service),
    orchestrator: ProductOrchestrator = Depends(_get_orchestrator),
):
    _require_quota(ctx, "value_models", quota)
    response = await orchestrator.generate_value_model(str(ctx.tenant_id), payload)
    await _record_and_publish(request, ctx, "value_models", publisher)
    return response


@router.post("/value-models/validate")
async def validate_value_model(
    request: Request,
    payload: ValueModelValidateRequest,
    ctx: RequestContext = Depends(require_authenticated),
    publisher: BillingEventPublisher = Depends(_get_billing_publisher),
    quota: QuotaService = Depends(_get_quota_service),
    orchestrator: ProductOrchestrator = Depends(_get_orchestrator),
):
    _require_quota(ctx, "value_models", quota)
    response = await orchestrator.validate_value_model(str(ctx.tenant_id), payload)
    await _record_and_publish(request, ctx, "value_models", publisher)
    return response


@router.post("/value-models/qa")
async def qa_value_model(
    request: Request,
    payload: ValueModelQARequest,
    ctx: RequestContext = Depends(require_authenticated),
    publisher: BillingEventPublisher = Depends(_get_billing_publisher),
    quota: QuotaService = Depends(_get_quota_service),
    orchestrator: ProductOrchestrator = Depends(_get_orchestrator),
):
    _require_quota(ctx, "value_models", quota)
    response = await orchestrator.qa_value_model(str(ctx.tenant_id), payload)
    await _record_and_publish(request, ctx, "value_models", publisher)
    return response


@router.post("/assumptions/score")
async def score_assumption(
    request: Request,
    payload: AssumptionScoreRequest,
    ctx: RequestContext = Depends(require_authenticated),
    publisher: BillingEventPublisher = Depends(_get_billing_publisher),
    quota: QuotaService = Depends(_get_quota_service),
    orchestrator: ProductOrchestrator = Depends(_get_orchestrator),
):
    _require_quota(ctx, "assumptions", quota)
    response = await orchestrator.score_assumption(str(ctx.tenant_id), payload)
    await _record_and_publish(request, ctx, "assumptions", publisher)
    return response


@router.post("/evidence/extract-value-signals")
async def extract_value_signals(
    request: Request,
    payload: EvidenceExtractRequest,
    ctx: RequestContext = Depends(require_authenticated),
    publisher: BillingEventPublisher = Depends(_get_billing_publisher),
    quota: QuotaService = Depends(_get_quota_service),
    orchestrator: ProductOrchestrator = Depends(_get_orchestrator),
):
    _require_quota(ctx, "evidence", quota)
    response = await orchestrator.extract_value_signals(str(ctx.tenant_id), payload)
    await _record_and_publish(request, ctx, "evidence", publisher)
    return response


@router.post("/cfo-narratives/generate")
async def generate_cfo_narrative(
    request: Request,
    payload: CFONarrativeGenerateRequest,
    ctx: RequestContext = Depends(require_authenticated),
    publisher: BillingEventPublisher = Depends(_get_billing_publisher),
    quota: QuotaService = Depends(_get_quota_service),
    orchestrator: ProductOrchestrator = Depends(_get_orchestrator),
):
    _require_quota(ctx, "cfo_narratives", quota)
    response = await orchestrator.generate_cfo_narrative(str(ctx.tenant_id), payload)
    await _record_and_publish(request, ctx, "cfo_narratives", publisher)
    return response


@router.post("/realization/compare")
async def compare_realization(
    request: Request,
    payload: RealizationCompareRequest,
    ctx: RequestContext = Depends(require_authenticated),
    publisher: BillingEventPublisher = Depends(_get_billing_publisher),
    quota: QuotaService = Depends(_get_quota_service),
    orchestrator: ProductOrchestrator = Depends(_get_orchestrator),
):
    _require_quota(ctx, "realization", quota)
    response = await orchestrator.compare_realization(str(ctx.tenant_id), payload)
    await _record_and_publish(request, ctx, "realization", publisher)
    return response
