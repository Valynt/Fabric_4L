from __future__ import annotations

import hashlib
import hmac
import json
import time
from uuid import uuid4
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from value_fabric.shared.error_handling.handlers import register_exception_handlers

from layer4_agents.api.routes import billing as billing_route
from layer4_agents.api.routes import crm_webhooks as crm_route
from layer4_agents.tenants.api.routes import provisioning as prov_route


def _provisioning_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(prov_route.router, prefix="/v1")
    monkeypatch.setenv("PROVISIONING_WEBHOOK_SECRET", "secret")
    prov_route._memory_webhook_cache.clear()

    async def _fake_db():
        yield object()

    monkeypatch.setattr(prov_route, "get_db", _fake_db)
    monkeypatch.setattr(prov_route, "get_tenant", AsyncMock(return_value=object()))
    monkeypatch.setattr(prov_route, "provision_tenant", AsyncMock(return_value=type("S", (), {"status": type("V", (), {"value": "completed"})()})()))
    return TestClient(app)


def _signature(payload: bytes, secret: str = "secret") -> str:
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


def test_provisioning_invalid_signature_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _provisioning_client(monkeypatch)
    payload = {"tenant_id": str(uuid4()), "triggered_by": "ci", "timestamp": int(time.time())}
    response = client.post(
        f"/v1/tenants/{uuid4()}/provisioning/webhook",
        headers={"X-Webhook-Signature": "bad", "X-Webhook-ID": "w1"},
        json=payload,
    )
    assert response.status_code == 401
    assert response.json()["error"]["message"] == "Invalid webhook signature"


def test_provisioning_expired_timestamp_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _provisioning_client(monkeypatch)
    payload = {"tenant_id": str(uuid4()), "triggered_by": "ci", "timestamp": int(time.time()) - 9999}
    raw = json.dumps(payload).encode()
    response = client.post(
        f"/v1/tenants/{uuid4()}/provisioning/webhook",
        headers={"X-Webhook-Signature": _signature(raw), "X-Webhook-ID": "w2", "Content-Type": "application/json"},
        content=raw,
    )
    assert response.status_code == 401
    assert "expired" in response.json()["error"]["message"].lower()


def test_provisioning_reused_webhook_id_returns_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _provisioning_client(monkeypatch)
    tenant = str(uuid4())
    payload = {"tenant_id": tenant, "triggered_by": "ci", "timestamp": int(time.time())}
    raw = json.dumps(payload).encode()
    headers = {"X-Webhook-Signature": _signature(raw), "X-Webhook-ID": "w3", "Content-Type": "application/json"}
    first = client.post(f"/v1/tenants/{uuid4()}/provisioning/webhook", headers=headers, content=raw)
    second = client.post(f"/v1/tenants/{uuid4()}/provisioning/webhook", headers=headers, content=raw)
    assert first.status_code == 202
    assert second.status_code == 202
    assert second.json()["message"].startswith("Already processed")


@pytest.mark.asyncio
async def test_crm_wrong_tenant_token_rejected() -> None:
    integration = type("I", (), {"credentials_encrypted": 'enc:{"webhook_token":"expected"}', "encryption_key_id": "k"})()
    with patch.object(crm_route, "_decrypt_integration_credentials", AsyncMock(return_value={"webhook_token": "expected"})):
        with pytest.raises(Exception):
            await crm_route._authenticate_webhook(  # noqa: SLF001
                integration,
                provided_token="wrong",
                provided_signature=None,
                body=b"{}",
                app_state_webhook_secret=None,
            )


def test_billing_invalid_signature_and_expired_timestamp_return_400(monkeypatch: pytest.MonkeyPatch) -> None:
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(billing_route.router, prefix="/v1")
    monkeypatch.setattr(billing_route, "STRIPE_WEBHOOK_SECRET", "whsec")
    monkeypatch.setattr(billing_route, "validate_webhook_request_security", lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("Timestamp outside tolerance (stale/replay)")))
    client = TestClient(app)
    response = client.post("/v1/billing/webhook", headers={"Stripe-Signature": "t=1,v1=bad"}, json={})
    assert response.status_code == 400
    assert response.json()["error"]["message"] == "Invalid webhook payload"
