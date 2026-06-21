"""Phase 1 forwarding stub — canonical implementation now in layer7-billing.

Layer 4 retains this shim for backward compatibility. All calls are
forwarded to the Layer 7 Billing Service via HTTP client stubs.
"""

from __future__ import annotations

from fastapi import APIRouter, status

from . import billing

router = APIRouter()

router.add_api_route(
    "/webhook",
    billing.stripe_webhook,
    methods=["POST"],
    response_model=billing.stripe_webhookResult,
    status_code=status.HTTP_200_OK,
    responses={
        400: {
            "description": "Invalid webhook payload — verify the payload body and Stripe-Signature timestamp"
        },
    },
)
