"""Usage and usage-summary billing routes.

Layer 4 is the canonical billing runtime; there is no separate Layer 7
Billing Service. The handlers registered here are re-exported from the
local ``billing`` module (UsageService, BillingService, Stripe sync).
Patch this service, not a Layer 7 package.
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
