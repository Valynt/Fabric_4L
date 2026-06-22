"""Benchmark domain routes for Layer 6 API."""

from typing import List

from fastapi import APIRouter, Depends

from ..deps import get_request_context, industry_filter, segment_filter
from ..schemas import (
    ComparisonRequestPayload,
    ComparisonResponse,
    DatasetDetail,
    DatasetSummary,
    DatasetUpsertPayload,
    DatasetUpsertResponse,
    IndustriesResponse,
    ValidationRequestPayload,
    ValidationResponse,
)

router = APIRouter(prefix="/v1/benchmarks", tags=["benchmarks"])


@router.get("/datasets", response_model=List[DatasetSummary])
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
