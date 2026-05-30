from __future__ import annotations

"""Usage ingestion and query billing routes."""

from fastapi import APIRouter

from . import billing

router = APIRouter()

router.add_api_route(
    "/events",
    billing.ingest_usage_event,
    methods=["POST"],
    response_model=billing.ingest_usage_eventResult,
)
router.add_api_route(
    "/events/batch",
    billing.ingest_usage_batch,
    methods=["POST"],
    response_model=billing.ingest_usage_batchResult,
)
router.add_api_route(
    "/usage/{customer_id}/summary",
    billing.get_usage_summary,
    methods=["GET"],
    response_model=billing.UsageSummaryResponse,
)
router.add_api_route(
    "/usage/{customer_id}/events",
    billing.list_usage_events,
    methods=["GET"],
    response_model=list[billing.UsageEventResponse],
)
router.add_api_route(
    "/usage/{customer_id}/sync",
    billing.sync_usage_to_stripe,
    methods=["POST"],
    response_model=billing.UsageSyncResponse,
)
