"""Tenant-boundary regressions for the Layer 2 signal lifecycle router."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
import pytest_asyncio
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient

from layer2_extraction.api.routes import signal_lifecycle
from layer2_extraction.services.signal_lifecycle_service import SignalLifecycleService
from value_fabric.shared.error_handling import register_exception_handlers


@pytest.fixture()
def signal_lifecycle_app(monkeypatch: pytest.MonkeyPatch) -> FastAPI:
    """Build an isolated app so every test starts with an empty lifecycle store."""
    monkeypatch.setattr(signal_lifecycle, "_service", SignalLifecycleService())

    app = FastAPI()
    register_exception_handlers(app)

    @app.middleware("http")
    async def inject_test_governance_context(
        request: Request, call_next
    ):  # type: ignore[no-untyped-def]
        tenant_id = request.headers.get("X-Test-Tenant-ID")
        account_id = request.headers.get("X-Test-Account-ID")
        user_id = request.headers.get("X-Test-User-ID")
        if tenant_id or account_id or user_id:
            request.state.governance_context = SimpleNamespace(
                tenant_id=tenant_id,
                account_id=account_id,
                user_id=user_id,
                subject=user_id,
            )
        return await call_next(request)

    app.include_router(signal_lifecycle.router)
    return app


@pytest_asyncio.fixture()
async def client(signal_lifecycle_app: FastAPI):
    async with AsyncClient(
        transport=ASGITransport(app=signal_lifecycle_app),
        base_url="http://test",
    ) as test_client:
        yield test_client


def _headers(tenant_id: str, account_id: str = "acct-1", user_id: str = "user-1") -> dict[str, str]:
    return {
        "X-Test-Tenant-ID": tenant_id,
        "X-Test-Account-ID": account_id,
        "X-Test-User-ID": user_id,
    }


@pytest.mark.asyncio
async def test_signal_create_stamps_authenticated_tenant_not_request_body(
    client: AsyncClient,
) -> None:
    response = await client.post(
        "/signals/signal-body-tenant-spoof",
        headers=_headers("tenant-a"),
        json={"tenant_id": "tenant-b", "account_id": "acct-b"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["tenant_id"] == "tenant-a"
    assert body["account_id"] == "acct-1"


@pytest.mark.asyncio
async def test_tenant_cannot_supersede_signal_with_cross_tenant_replacement(
    client: AsyncClient,
) -> None:
    create_source = await client.post("/signals/tenant-a-source", headers=_headers("tenant-a"))
    create_replacement = await client.post(
        "/signals/tenant-b-replacement", headers=_headers("tenant-b")
    )
    assert create_source.status_code == 200
    assert create_replacement.status_code == 200

    response = await client.post(
        "/signals/tenant-a-source/supersede",
        headers=_headers("tenant-a"),
        json={"target_signal_id": "tenant-b-replacement"},
    )

    assert response.status_code == 404
    assert response.json()["error"]["message"] == "Signal not found"


@pytest.mark.asyncio
async def test_tenant_cannot_merge_cross_tenant_source_into_own_signal(client: AsyncClient) -> None:
    create_source = await client.post("/signals/tenant-a-source", headers=_headers("tenant-a"))
    create_canonical = await client.post(
        "/signals/tenant-b-canonical", headers=_headers("tenant-b")
    )
    assert create_source.status_code == 200
    assert create_canonical.status_code == 200

    response = await client.post(
        "/signals/tenant-a-source/merge",
        headers=_headers("tenant-b"),
        json={"target_signal_id": "tenant-b-canonical"},
    )

    assert response.status_code == 404
    assert response.json()["error"]["message"] == "Signal not found"


@pytest.mark.asyncio
async def test_missing_tenant_context_fails_closed(client: AsyncClient) -> None:
    response = await client.post("/signals/no-context")

    assert response.status_code == 401
    assert response.json()["error"]["message"] == "Request could not be completed"
