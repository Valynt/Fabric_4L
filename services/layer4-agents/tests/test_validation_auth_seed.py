from __future__ import annotations

"""Security regression tests for the backend-integrated validation auth seed."""


import os
from typing import Any
from uuid import UUID

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from value_fabric.shared.error_handling import register_exception_handlers

os.environ.setdefault("API_KEY_HMAC_SECRET", "test-api-key-hmac-secret-for-validation-seed-1234567890")
os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/test")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-for-validation-seed-1234567890")
os.environ.setdefault("SERVICE_AUTH_SECRET", "test-service-auth-secret-for-validation-seed-1234567890")

from value_fabric.shared.identity.context import RequestContext

from layer4_agents.api.routes import analysis
from layer4_agents.tenants.models.api_key import APIKey
from layer4_agents.tenants.models.tenant import Tenant
from layer4_agents.tenants.models.user import User

TENANT_ID = UUID(os.environ.get("BACKEND_E2E_TENANT_ID", "00000000-0000-4000-e2e0-000000000001"))


class FakeDb:
    def __init__(self) -> None:
        self.records: dict[tuple[type[Any], Any], Any] = {}
        self.added: list[Any] = []
        self.flushed = False

    async def get(self, model: type[Any], key: Any) -> Any | None:
        return self.records.get((model, key))

    def add(self, record: Any) -> None:
        self.added.append(record)
        key = getattr(record, "id", getattr(record, "key_id", None))
        self.records[(type(record), key)] = record

    async def flush(self) -> None:
        self.flushed = True


@pytest.fixture
def validation_app(monkeypatch: pytest.MonkeyPatch) -> tuple[FastAPI, FakeDb]:
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(analysis.router, prefix="/v1")
    db = FakeDb()

    async def auth_context() -> RequestContext:
        return RequestContext(
            tenant_id=TENANT_ID,
            user_id="e2e-admin-user",
            roles=["super_admin"],
            auth_source="service_account",
            service_account_id="svc-playwright-backend-validation",
            service_account_scopes=["validation:seed"],
        )

    monkeypatch.setattr(analysis.settings, "environment", "development")
    app.dependency_overrides[analysis.require_authenticated] = auth_context
    app.dependency_overrides[analysis.get_route_db] = lambda: db
    return app, db


async def _post_auth_seed(
    app: FastAPI,
    *,
    body: dict[str, Any] | None = None,
    reason: str = analysis.SEED_PRIVILEGED_REASON,
) -> Any:
    headers = {"X-Privileged-Reason": reason} if reason else {}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        return await client.post(
            "/v1/validation/seed/auth-context",
            json=body
            if body is not None
            else {
                "tenant_id": str(TENANT_ID),
                "api_key": {
                    "key_id": "vf_e2e_backend_integrated_validation",
                    "key_hash": "a" * 64,
                    "prefix": "vf_e2e_seed",
                    "role": "system",
                    "permissions": [],
                    "metadata": {"validation_only": True},
                },
            },
            headers=headers,
        )


@pytest.mark.asyncio
async def test_validation_auth_seed_persists_only_non_secret_material(
    validation_app: tuple[FastAPI, FakeDb],
) -> None:
    app, db = validation_app

    response = await _post_auth_seed(app)

    assert response.status_code == 200
    payload = response.json()
    assert payload["raw_secret_persisted"] is False
    assert payload["tenant"]["id"] == str(TENANT_ID)
    assert len(payload["users"]) == 4
    assert payload["service_account"]["metadata_seeded"] is True
    assert payload["api_key"]["raw_secret_persisted"] is False

    assert db.flushed is True
    assert any(isinstance(record, Tenant) for record in db.added)
    assert sum(isinstance(record, User) for record in db.added) == 4
    api_keys = [record for record in db.added if isinstance(record, APIKey)]
    assert len(api_keys) == 1
    assert api_keys[0].key_hash == "a" * 64
    assert api_keys[0].metadata_["raw_secret_persisted"] is False
    assert not hasattr(api_keys[0], "raw_key")


@pytest.mark.asyncio
async def test_validation_auth_seed_rejects_cross_tenant_payload(
    validation_app: tuple[FastAPI, FakeDb],
) -> None:
    app, _ = validation_app

    response = await _post_auth_seed(
        app,
        body={"tenant_id": os.environ.get("BACKEND_E2E_TENANT_BETA_ID", "00000000-0000-4000-e2e0-000000000002")},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_validation_auth_seed_rejects_raw_secret_fields(
    validation_app: tuple[FastAPI, FakeDb],
) -> None:
    app, _ = validation_app

    response = await _post_auth_seed(
        app,
        body={
            "tenant_id": str(TENANT_ID),
            "service_auth_secret": "must-not-be-accepted",
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_validation_auth_seed_requires_privileged_reason(
    validation_app: tuple[FastAPI, FakeDb],
) -> None:
    app, _ = validation_app

    response = await _post_auth_seed(app, reason="wrong-reason")

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_validation_auth_seed_disabled_in_production(
    validation_app: tuple[FastAPI, FakeDb],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, _ = validation_app
    monkeypatch.setattr(analysis.settings, "environment", "production")

    response = await _post_auth_seed(app)

    assert response.status_code == 403
