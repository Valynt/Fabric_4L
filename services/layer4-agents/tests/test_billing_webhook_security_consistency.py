from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from value_fabric.shared.error_handling import register_exception_handlers

from layer4_agents.api.routes import billing as billing_route
from layer4_agents.services import billing_security, billing_webhook_security


def test_ip_allowlist_logic_matches_canonical_module() -> None:
    for ip in ("3.18.12.63", "127.0.0.1", "8.8.8.8", "not-an-ip"):
        assert billing_route._is_stripe_webhook_ip(ip) == billing_security.is_stripe_webhook_ip(ip)
        assert billing_webhook_security.is_stripe_webhook_ip(ip) == billing_security.is_stripe_webhook_ip(ip)


def test_client_ip_extraction_matches_canonical_module() -> None:
    request = SimpleNamespace(
        headers={"X-Forwarded-For": "3.18.12.63, 10.0.0.2", "X-Real-IP": "52.15.183.38"},
        client=SimpleNamespace(host="10.0.0.1"),
    )
    expected = billing_security.get_client_ip(request)
    assert billing_route._get_client_ip(request) == expected
    assert billing_webhook_security.get_client_ip(request) == expected


@pytest.fixture
def webhook_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(billing_route.router, prefix="/v1")

    monkeypatch.setattr(billing_route, "STRIPE_WEBHOOK_SECRET", "whsec_test_dummy")
    monkeypatch.setattr(billing_route, "STRIPE_WEBHOOK_SKIP_IP_CHECK", False)
    monkeypatch.setattr(billing_route, "_is_stripe_webhook_ip", lambda ip: ip == "3.18.12.63")

    async def _fake_get_db():
        yield AsyncMock()

    app.dependency_overrides[billing_route.get_route_db] = _fake_get_db
    return TestClient(app)


def test_webhook_blocks_non_allowlisted_ip(webhook_client: TestClient) -> None:
    resp = webhook_client.post(
        "/v1/billing/webhook",
        headers={"Stripe-Signature": "t=1,v1=sig", "X-Forwarded-For": "8.8.8.8"},
        content=b"{}",
    )
    assert resp.status_code == 403


def test_webhook_accepts_allowlisted_ip_with_valid_signature(monkeypatch: pytest.MonkeyPatch, webhook_client: TestClient) -> None:
    service = AsyncMock()
    service.handle_webhook = AsyncMock(return_value=True)
    monkeypatch.setattr(billing_route, "BillingService", lambda db: service)
    monkeypatch.setattr(billing_route, "validate_webhook_request_security", lambda *_args, **_kwargs: None)

    resp = webhook_client.post(
        "/v1/billing/webhook",
        headers={"Stripe-Signature": "t=1,v1=sig", "X-Forwarded-For": "3.18.12.63"},
        content=b'{"id":"evt_1"}',
    )
    assert resp.status_code == 200


def test_webhook_rejects_invalid_signature_and_stale_or_replayed_timestamp(
    monkeypatch: pytest.MonkeyPatch, webhook_client: TestClient
) -> None:
    service = AsyncMock()
    service.handle_webhook = AsyncMock(side_effect=ValueError("Timestamp outside tolerance (stale/replay)"))
    monkeypatch.setattr(billing_route, "BillingService", lambda db: service)

    resp = webhook_client.post(
        "/v1/billing/webhook",
        headers={"Stripe-Signature": "t=1,v1=bad", "X-Forwarded-For": "3.18.12.63"},
        content=b'{"id":"evt_1"}',
    )
    assert resp.status_code == 400



def test_signature_helpers_match_across_entrypoints() -> None:
    header = "t=1700000000,v1=sig1,v1=sig2"
    direct = billing_security.parse_stripe_signature_header(header)
    compat = billing_webhook_security.parse_stripe_signature_header(header)
    assert direct == compat


def test_timestamp_tolerance_helpers_match(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(billing_security, "_STRIPE_TIMESTAMP_TOLERANCE_SECONDS", 5)
    billing_security.ensure_timestamp_within_tolerance(100, now=104)
    billing_webhook_security.ensure_timestamp_within_tolerance(100, now=104)

    with pytest.raises(ValueError, match="stale/replay"):
        billing_security.ensure_timestamp_within_tolerance(100, now=200)
    with pytest.raises(ValueError, match="stale/replay"):
        billing_webhook_security.ensure_timestamp_within_tolerance(100, now=200)
