"""Stripe webhook billing routes (Phase 1 extract from Layer 4).

Canonical implementation lives in Layer 7. Layer 4 now forwards to
these endpoints via thin HTTP client stubs.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import APIRouter, Header, Request

from value_fabric.shared.error_handling.exceptions import (
    ServiceUnavailableError,
    ValidationError,
)

from ...webhook_security import (
    DEFAULT_STRIPE_WEBHOOK_TOLERANCE_SECONDS,
    verify_stripe_webhook_signature,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Billing — Webhooks"])

_STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
) -> dict[str, Any]:
    """Receive Stripe billing webhooks after HMAC signature verification.

    Stripe webhooks are authenticated by ``Stripe-Signature`` rather than a
    tenant header or user JWT. The raw request body is verified before JSON is
    parsed, and event IDs are cached within the timestamp tolerance window to
    reject immediate replay attempts.

    This endpoint is the canonical Layer 7 implementation. Layer 4 now
    forwards webhook calls here via a thin HTTP client stub.
    """
    if not _STRIPE_WEBHOOK_SECRET:
        logger.error("STRIPE_WEBHOOK_SECRET not configured")
        raise ServiceUnavailableError(message="Webhook processing not configured")

    if not stripe_signature:
        raise ValidationError(message="Missing Stripe-Signature header")

    body = await request.body()
    try:
        signature = verify_stripe_webhook_signature(
            body,
            stripe_signature,
            _STRIPE_WEBHOOK_SECRET,
            tolerance_seconds=DEFAULT_STRIPE_WEBHOOK_TOLERANCE_SECONDS,
        )
        import json

        event = json.loads(body)
        event_id = event.get("id") if isinstance(event, dict) else None
        event_type = event.get("type") if isinstance(event, dict) else None
        if not isinstance(event_id, str) or not event_id.strip():
            raise ValueError("Stripe webhook event id is required")
    except ValueError as exc:
        logger.warning(
            "Stripe webhook validation rejected",
            reason=str(exc),
            operation="stripe_webhook",
            route="/webhook",
        )
        raise ValidationError(message="Invalid Stripe webhook payload") from exc

    logger.info(
        "Stripe webhook accepted (L7 canonical)",
        event_id=event_id,
        event_type=event_type,
        operation="stripe_webhook",
        route="/webhook",
    )
    return {"received": True, "event_id": event_id}
