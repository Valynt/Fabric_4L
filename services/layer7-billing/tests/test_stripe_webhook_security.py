from __future__ import annotations

import hashlib
import hmac
import json
import time

import pytest
from httpx import AsyncClient

from layer7_billing.api.main import _STRIPE_WEBHOOK_REPLAY_CACHE
from layer7_billing.webhook_security import verify_stripe_webhook_signature

WEBHOOK_SECRET = "whsec_test_dummy_secret_for_layer7_billing"


def _stripe_signature(
    payload: bytes, secret: str = WEBHOOK_SECRET, *, timestamp: int | None = None
) -> str:
    signed_at = int(time.time()) if timestamp is None else timestamp
    signed_payload = f"{signed_at}.".encode("utf-8") + payload
    digest = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    return f"t={signed_at},v1={digest}"


@pytest.fixture(autouse=True)
def stripe_webhook_secret(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", WEBHOOK_SECRET)
    _STRIPE_WEBHOOK_REPLAY_CACHE.clear()
    yield
    _STRIPE_WEBHOOK_REPLAY_CACHE.clear()


def test_verify_stripe_webhook_signature_rejects_tampered_payload() -> None:
    original_payload = b'{"id":"evt_original","type":"invoice.paid"}'
    tampered_payload = b'{"id":"evt_tampered","type":"invoice.paid"}'
    signature = _stripe_signature(original_payload)

    with pytest.raises(ValueError, match="Invalid Stripe webhook signature"):
        verify_stripe_webhook_signature(tampered_payload, signature, WEBHOOK_SECRET)


def test_verify_stripe_webhook_signature_rejects_stale_timestamp() -> None:
    payload = b'{"id":"evt_stale","type":"invoice.paid"}'
    stale_timestamp = int(time.time()) - 301
    signature = _stripe_signature(payload, timestamp=stale_timestamp)

    with pytest.raises(ValueError, match="outside tolerance"):
        verify_stripe_webhook_signature(
            payload,
            signature,
            WEBHOOK_SECRET,
            tolerance_seconds=300,
        )


@pytest.mark.asyncio
async def test_billing_webhook_rejects_missing_stripe_signature(isolated_client: AsyncClient):
    payload = {"id": "evt_missing_sig", "type": "invoice.paid"}

    response = await isolated_client.post("/v1/billing/webhook", json=payload)

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_billing_webhook_accepts_valid_stripe_signature_without_tenant_header(
    isolated_client: AsyncClient,
):
    body = json.dumps({"id": "evt_valid", "type": "invoice.paid"}, separators=(",", ":")).encode(
        "utf-8"
    )

    response = await isolated_client.post(
        "/v1/billing/webhook",
        content=body,
        headers={
            "Stripe-Signature": _stripe_signature(body),
            "Content-Type": "application/json",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"received": True, "event_id": "evt_valid"}


@pytest.mark.asyncio
async def test_billing_webhook_rejects_replayed_event_id(isolated_client: AsyncClient):
    body = json.dumps({"id": "evt_replay", "type": "invoice.paid"}, separators=(",", ":")).encode(
        "utf-8"
    )
    headers = {"Stripe-Signature": _stripe_signature(body), "Content-Type": "application/json"}

    first_response = await isolated_client.post(
        "/v1/billing/webhook", content=body, headers=headers
    )
    replay_response = await isolated_client.post(
        "/v1/billing/webhook", content=body, headers=headers
    )

    assert first_response.status_code == 200
    assert replay_response.status_code == 400
