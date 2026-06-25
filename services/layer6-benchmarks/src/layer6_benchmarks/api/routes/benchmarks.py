"""Benchmark domain routes for Layer 6 API."""


from fastapi import APIRouter, Depends

from ..deps import get_request_context, industry_filter, segment_filter
from ..schemas import (
    BenchmarkProvenanceResponse,
    CompareDistributionRequestPayload,
    CompareDistributionResponse,
    ComparisonRequestPayload,
    ComparisonResponse,
    CoverageStatusResponse,
    DatasetDetail,
    DatasetSummary,
    DatasetUpsertPayload,
    DatasetUpsertResponse,
    IndustriesResponse,
    MetricCatalogResponse,
    MetricProvenanceRequestPayload,
    RecommendRangeRequestPayload,
    RecommendRangeResponse,
    ValidateValueRequestPayload,
    ValidateValueResponse,
    ValidationRequestPayload,
    ValidationResponse,
    VMRTTracePromotionRequestPayload,
    VMRTTraceRecordResponse,
    VMRTTraceUpsertRequestPayload,
    VMRTValidationRequestPayload,
    VMRTValidationResponse,
)

router = APIRouter(prefix="/v1/benchmarks", tags=["benchmarks"])


@router.get("/datasets", response_model=list[DatasetSummary])
async def list_datasets(
    industry: str | None = Depends(industry_filter),
    segment: str | None = Depends(segment_filter),
    ctx=Depends(get_request_context),
):
    from .. import main as handlers

    return await handlers.list_datasets(industry=industry, segment=segment, ctx=ctx)


@router.get("/datasets/{dataset_id}", response_model=DatasetDetail)
async def get_dataset(
    dataset_id: str,
    ctx=Depends(get_request_context),
):
    from .. import main as handlers

    return await handlers.get_dataset(dataset_id, ctx=ctx)


@router.post("/compare", response_model=ComparisonResponse)
async def compare(
    payload: ComparisonRequestPayload,
    ctx=Depends(get_request_context),
):
    from .. import main as handlers

    return await handlers.compare(payload, ctx=ctx)


@router.post("/validate", response_model=ValidationResponse)
async def validate(
    payload: ValidationRequestPayload,
    ctx=Depends(get_request_context),
):
    from .. import main as handlers

    return await handlers.validate(payload, ctx=ctx)


@router.post("/recommend-range", response_model=RecommendRangeResponse)
async def recommend_range(
    payload: RecommendRangeRequestPayload,
    ctx=Depends(get_request_context),
):
    from .. import main as handlers

    return await handlers.recommend_range(payload, ctx=ctx)


@router.post("/compare-distribution", response_model=CompareDistributionResponse)
async def compare_distribution(
    payload: CompareDistributionRequestPayload,
    ctx=Depends(get_request_context),
):
    from .. import main as handlers

    return await handlers.compare_distribution(payload, ctx=ctx)


@router.post("/validate-value", response_model=ValidateValueResponse)
async def validate_value(
    payload: ValidateValueRequestPayload,
    ctx=Depends(get_request_context),
):
    from .. import main as handlers

    return await handlers.validate_value(payload, ctx=ctx)


@router.get("/metrics", response_model=MetricCatalogResponse)
async def list_metric_catalog(
    industry: str | None = Depends(industry_filter),
    segment: str | None = Depends(segment_filter),
    ctx=Depends(get_request_context),
):
    from .. import main as handlers

    return await handlers.list_metric_catalog(industry=industry, segment=segment, ctx=ctx)


@router.post("/metric-provenance", response_model=BenchmarkProvenanceResponse)
async def get_metric_provenance(
    payload: MetricProvenanceRequestPayload,
    ctx=Depends(get_request_context),
):
    from .. import main as handlers

    return await handlers.get_metric_provenance(payload, ctx=ctx)


@router.get("/coverage", response_model=CoverageStatusResponse)
async def get_coverage_status(
    ctx=Depends(get_request_context),
):
    from .. import main as handlers

    return await handlers.get_coverage_status(ctx=ctx)


@router.post("/vmrt/validate", response_model=VMRTValidationResponse)
async def validate_vmrt(
    payload: VMRTValidationRequestPayload,
    ctx=Depends(get_request_context),
):
    from .. import main as handlers

    return await handlers.validate_vmrt(payload, ctx=ctx)


@router.post("/vmrt/traces", response_model=VMRTTraceRecordResponse)
async def upsert_vmrt_trace(
    payload: VMRTTraceUpsertRequestPayload,
    ctx=Depends(get_request_context),
):
    from .. import main as handlers

    return await handlers.upsert_vmrt_trace(payload, ctx=ctx)


@router.get("/vmrt/traces/{trace_id}", response_model=VMRTTraceRecordResponse)
async def get_vmrt_trace(
    trace_id: str,
    ctx=Depends(get_request_context),
):
    from .. import main as handlers

    return await handlers.get_vmrt_trace(trace_id, ctx=ctx)


@router.post("/vmrt/traces/{trace_id}/promote", response_model=VMRTTraceRecordResponse)
async def promote_vmrt_trace(
    trace_id: str,
    payload: VMRTTracePromotionRequestPayload,
    ctx=Depends(get_request_context),
):
    from .. import main as handlers

    return await handlers.promote_vmrt_trace(trace_id, payload, ctx=ctx)


@router.get("/industries", response_model=IndustriesResponse)
async def list_industries(
    ctx=Depends(get_request_context),
):
    from .. import main as handlers

    return await handlers.list_industries(ctx=ctx)


@router.post("/datasets", response_model=DatasetUpsertResponse)
async def upsert_dataset(
    payload: DatasetUpsertPayload,
    ctx=Depends(get_request_context),
):
    from .. import main as handlers

    return await handlers.upsert_dataset(payload, ctx=ctx)


@router.put("/datasets/{dataset_id}", response_model=DatasetUpsertResponse)
async def update_dataset(
    dataset_id: str,
    payload: DatasetUpsertPayload,
    ctx=Depends(get_request_context),
):
    from .. import main as handlers

    enforced_payload = payload.model_copy(update={"dataset_id": dataset_id})
    return await handlers.upsert_dataset(enforced_payload, ctx=ctx)
