"""Stripe webhook billing route.

Layer 4 is the canonical billing runtime; there is no separate Layer 7
Billing Service. The handler registered here is re-exported from the
local ``billing`` module (Stripe webhook with signature verification).
Patch this service, not a Layer 7 package.
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
