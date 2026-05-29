from __future__ import annotations

from types import SimpleNamespace
import base64
import hashlib
import hmac
import json
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_authenticated

from layer4_agents.api.routes import integrations as integrations_route


@pytest.fixture
def app(monkeypatch) -> FastAPI:
    test_app = FastAPI()
    test_app.include_router(integrations_route.router, prefix="/v1")

    tenant_id = uuid4()

    async def override_auth() -> RequestContext:
        return RequestContext(
            tenant_id=tenant_id,
            user_id="user-123",
            roles=["tenant_admin"],
            auth_source="jwt_claim",
        )

    async def override_db():
        return object()

    monkeypatch.setenv("SALESFORCE_CLIENT_ID", "client-id")
    monkeypatch.setenv("SALESFORCE_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("JWT_SECRET", "test-jwt-secret-1234567890")
    monkeypatch.setenv("PUBLIC_API_URL", "https://api.example.com")

    test_app.dependency_overrides[require_authenticated] = override_auth
    test_app.dependency_overrides[integrations_route.get_db_from_context] = override_db
    return test_app


@pytest.fixture
async def client(app: FastAPI) -> AsyncClient:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        follow_redirects=False,
    ) as ac:
        yield ac


@pytest.mark.asyncio
async def test_start_salesforce_oauth_returns_authorize_url(client: AsyncClient) -> None:
    response = await client.post(
        "/v1/integrations/salesforce/oauth/start",
        json={"return_to": "/context/integrations?provider=salesforce"},
    )

    assert response.status_code == 200
    data = response.json()
    parsed = urlparse(data["authorization_url"])
    params = parse_qs(parsed.query)
    assert parsed.netloc == "login.salesforce.com"
    assert params["client_id"] == ["client-id"]
    assert params["redirect_uri"] == ["https://api.example.com/v1/integrations/salesforce/oauth/callback"]
    assert "state" in params


@pytest.mark.asyncio
async def test_complete_salesforce_oauth_redirects_after_success(client: AsyncClient, app: FastAPI, monkeypatch) -> None:
    service = SimpleNamespace()

    async def exchange_salesforce_oauth_code(**_kwargs):
        return {
            "access_token": "access-token",
            "refresh_token": "refresh-token",
            "instance_url": "https://tenant.my.salesforce.com",
        }

    async def upsert_salesforce_oauth_integration(**_kwargs):
        return None

    service.exchange_salesforce_oauth_code = exchange_salesforce_oauth_code
    service.upsert_salesforce_oauth_integration = upsert_salesforce_oauth_integration
    app.dependency_overrides[integrations_route.get_integration_service] = lambda: service

    auth_response = await client.post(
        "/v1/integrations/salesforce/oauth/start",
        json={"return_to": "/context/integrations?provider=salesforce"},
    )
    state = parse_qs(urlparse(auth_response.json()["authorization_url"]).query)["state"][0]

    response = await client.get(
        "/v1/integrations/salesforce/oauth/callback",
        params={"code": "auth-code", "state": state},
    )

    assert response.status_code == 303
    assert response.headers["location"].startswith("/context/integrations")
    assert "oauth_status=connected" in response.headers["location"]


@pytest.mark.asyncio
async def test_complete_salesforce_oauth_rejects_invalid_state(client: AsyncClient) -> None:
    response = await client.get(
        "/v1/integrations/salesforce/oauth/callback",
        params={"code": "auth-code", "state": "bad.state"},
    )

    assert response.status_code == 303
    assert "oauth_status=error" in response.headers["location"]


@pytest.mark.asyncio
async def test_complete_salesforce_oauth_rejects_state_with_invalid_tenant_mapping(
    client: AsyncClient,
    app: FastAPI,
) -> None:
    service = SimpleNamespace()
    service.exchange_salesforce_oauth_code = pytest.fail
    service.upsert_salesforce_oauth_integration = pytest.fail
    app.dependency_overrides[integrations_route.get_integration_service] = lambda: service

    auth_response = await client.post(
        "/v1/integrations/salesforce/oauth/start",
        json={"return_to": "/context/integrations?provider=salesforce"},
    )
    state = parse_qs(urlparse(auth_response.json()["authorization_url"]).query)["state"][0]
    payload, signature = state.split(".", 1)
    tampered_state = f"{payload}.{signature[:-1]}0" if signature[-1] != "0" else f"{payload}.{signature[:-1]}1"

    response = await client.get(
        "/v1/integrations/salesforce/oauth/callback",
        params={"code": "auth-code", "state": tampered_state},
    )

    assert response.status_code == 303
    assert "oauth_status=error" in response.headers["location"]


def test_decode_signed_state_rejects_non_uuid_tenant(monkeypatch) -> None:
    monkeypatch.setenv("JWT_SECRET", "test-jwt-secret-1234567890")
    payload = {
        "tenant_id": "tenant-not-uuid",
        "user_id": "user-123",
        "return_to": "/context/integrations?provider=salesforce",
        "oauth_base_url": "https://login.salesforce.com",
        "iat": 2_000_000_000,
    }
    payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    encoded_payload = base64.urlsafe_b64encode(payload_json).decode("utf-8").rstrip("=")
    signature = hmac.new(
        b"test-jwt-secret-1234567890",
        encoded_payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    state = f"{encoded_payload}.{signature}"

    with pytest.raises(integrations_route.IntegrationValidationError, match="tenant mapping is invalid"):
        integrations_route._decode_signed_state(state)
