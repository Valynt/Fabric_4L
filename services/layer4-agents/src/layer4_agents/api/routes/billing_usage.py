"""Phase 1 forwarding stub — canonical implementation now in layer7-billing.

Layer 4 retains this shim for backward compatibility. All calls are
forwarded to the Layer 7 Billing Service via HTTP client stubs.
"""

from __future__ import annotations

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
)
router.add_api_route(
    "/usage/{customer_id}/events",
    billing.list_usage_events,
    methods=["GET"],
)
router.add_api_route(
    "/usage/{customer_id}/sync",
    billing.sync_usage_to_stripe,
    methods=["POST"],
)
