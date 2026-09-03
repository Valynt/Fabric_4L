"""Stripe webhook billing routes (Phase 1 extract from Layer 4).

Canonical implementation lives in Layer 7. Layer 4 now forwards to
these endpoints via thin HTTP client stubs.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from fastapi import APIRouter, Header, Request

from value_fabric.shared.error_handling.exceptions import (
    ServiceUnavailableError,
    ValidationError,
)
from value_fabric.shared.idempotency import (
    IdempotencyRecord,
    IdempotencyRequest,
    IdempotencyService,
    InMemoryIdempotencyStore,
    RedisIdempotencyStore,
    build_request_fingerprint,
)

from ...webhook_security import (
    DEFAULT_STRIPE_WEBHOOK_TOLERANCE_SECONDS,
    verify_stripe_webhook_signature,
)
from ...database import redis_client_async

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Billing — Webhooks"])

_STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

# Configure idempotency service with Redis store (falls back to in-memory if Redis unavailable)
_idempotency_store = (
    RedisIdempotencyStore(redis_client_async)
    if redis_client_async is not None
    else InMemoryIdempotencyStore()
)

_idempotency_service = IdempotencyService(store=_idempotency_store, ttl_seconds=24 * 60 * 60)


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict[str, Any]:
    """Receive Stripe billing webhooks after HMAC signature verification.

    Stripe webhooks are authenticated by ``Stripe-Signature`` rather than a
    tenant header or user JWT. The raw request body is verified before JSON is
    parsed, and event IDs are cached within the timestamp tolerance window to
    reject immediate replay attempts.

    This endpoint is the canonical Layer 7 implementation. Layer 4 now
    forwards webhook calls here via a thin HTTP client stub.

    Idempotency is enforced via:
    - ``Idempotency-Key`` header (if provided by client)
    - Event ID from Stripe payload (fallback)
    """
    if not _STRIPE_WEBHOOK_SECRET:
        logger.error("STRIPE_WEBHOOK_SECRET not configured")
        raise ServiceUnavailableError(message="Webhook processing not configured")

    if not stripe_signature:
        raise ValidationError(message="Missing Stripe-Signature header")

    body = await request.body()
    try:
        verify_stripe_webhook_signature(
            body,
            stripe_signature,
            _STRIPE_WEBHOOK_SECRET,
            tolerance_seconds=DEFAULT_STRIPE_WEBHOOK_TOLERANCE_SECONDS,
        )

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

    # Idempotency check: use Idempotency-Key header if provided, otherwise use event_id
    key = idempotency_key or event_id
    if not key:
        raise ValidationError(message="Either Idempotency-Key header or valid event_id required for idempotency")
    endpoint_key = "POST:/webhook"

    # Build request fingerprint for payload validation
    try:
        event_dict = event if isinstance(event, dict) else {}
        request_fingerprint = build_request_fingerprint("POST", "/webhook", event_dict)
    except Exception as exc:
        logger.warning("Request fingerprinting failed, using event_id as fallback", error=str(exc))
        request_fingerprint = event_id

    idempotency_request = IdempotencyRequest(
        tenant_id="stripe",  # Stripe webhooks are tenant-agnostic
        endpoint_key=endpoint_key,
        idempotency_key=key,
        request_fingerprint=request_fingerprint,
    )

    # Check for replay
    try:
        cached_response = _idempotency_service.check_replay(idempotency_request)
        if cached_response is not None:
            logger.info(
                "Stripe webhook replay detected, returning cached response",
                event_id=event_id,
                idempotency_key=key,
                operation="stripe_webhook",
                route="/webhook",
            )
            return cached_response.body
    except Exception as exc:
        logger.warning("Idempotency check failed, proceeding with processing", error=str(exc))

    # Process webhook
    # TODO(VF-L7-WEBHOOK-DEBT-001): Implement actual webhook processing logic (e.g., handle payment.created, invoice.paid events)
    logger.info(
        "Stripe webhook accepted (L7 canonical)",
        event_id=event_id,
        event_type=event_type,
        idempotency_key=key,
        operation="stripe_webhook",
        route="/webhook",
    )

    response = {"received": True, "event_id": event_id}

    # Store response for idempotency (non-critical if it fails)
    try:
        _idempotency_service.store_response(
            idempotency_request,
            IdempotencyRecord(
                status_code=200,
                body=response,
                headers={},
            ),
        )
    except Exception as exc:
        logger.warning("Failed to store idempotency response", error=str(exc))

    return response
