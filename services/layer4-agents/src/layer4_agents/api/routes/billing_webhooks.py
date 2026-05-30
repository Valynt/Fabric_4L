from __future__ import annotations

"""Stripe webhook billing routes."""

from fastapi import APIRouter, status

from . import billing

router = APIRouter()

router.add_api_route(
    "/webhook",
    billing.stripe_webhook,
    methods=["POST"],
    response_model=billing.stripe_webhookResult,
    status_code=status.HTTP_200_OK,
)
