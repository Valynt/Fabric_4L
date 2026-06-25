from __future__ import annotations

"""H-01 regression tests for the audit-log route.

The production route must query durable audit records rather than returning a
local-development stub, and unsupported provenance-only requests must fail
closed instead of inventing data.
"""


from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from value_fabric.shared.error_handling import register_exception_handlers
from value_fabric.shared.identity.context import RequestContext

from layer4_agents.api.routes import audit


class _ScalarResult:
    def __init__(self, value: object) -> None:
        self._value = value

    def scalar(self) -> object:
        return self._value


class _MappingRows:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self._rows = [SimpleNamespace(**row) for row in rows]

    def mappings(self) -> _MappingRows:
        return self

    def all(self) -> list[SimpleNamespace]:
        return self._rows


class _AuditDb:
    def __init__(self, tenant_id: UUID) -> None:
        self.tenant_id = tenant_id
        self.calls: list[dict[str, object]] = []

    async def execute(self, statement: object, params: dict[str, object]) -> object:
        sql = str(statement)
        self.calls.append({"sql": sql, "params": dict(params)})
        assert params["tenant_id"] == self.tenant_id
        if "COUNT(*)" in sql:
            return _ScalarResult(1)
        return _MappingRows(
            [
                {
                    "id": uuid4(),
                    "timestamp": datetime(2026, 5, 1, tzinfo=UTC),
                    "action": "tenant.updated",
                    "resource_id": "tenant-1",
                    "resource_type": "Tenant",
                    "user_id": "admin-user",
                    "api_key_id": None,
                    "details": {"reason": "test"},
                }
            ]
        )


@pytest.fixture
def audit_app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(audit.router, prefix="/v1")
    return app


@pytest.mark.asyncio
async def test_audit_logs_query_persisted_audit_events(audit_app: FastAPI) -> None:
    tenant_id = UUID("12345678-1234-1234-1234-123456789abc")
    db = _AuditDb(tenant_id)

    async def mock_require_tenant_admin() -> RequestContext:
        return RequestContext(tenant_id=tenant_id, user_id="admin-user", roles=["tenant_admin"])

    audit_app.dependency_overrides[audit.require_tenant_admin] = mock_require_tenant_admin
    audit_app.dependency_overrides[audit.get_db_from_context] = lambda: db

    async with AsyncClient(transport=ASGITransport(app=audit_app), base_url="http://test") as client:
        response = await client.get(
            "/v1/audit/logs",
            params={"source": "access", "event_type": "tenant.updated", "agent": "admin-user"},
        )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["total"] == 1
    assert payload["entries"][0]["source"] == "access_log"
    assert payload["entries"][0]["event_type"] == "tenant.updated"
    assert payload["entries"][0]["agent"] == "admin-user"
    assert any("audit_events" in call["sql"] for call in db.calls)
    assert db.calls[0]["params"]["event_type"] == "tenant.updated"


@pytest.mark.asyncio
async def test_audit_logs_provenance_source_fails_closed(audit_app: FastAPI) -> None:
    tenant_id = UUID("12345678-1234-1234-1234-123456789abc")

    async def mock_require_tenant_admin() -> RequestContext:
        return RequestContext(tenant_id=tenant_id, user_id="admin-user", roles=["tenant_admin"])

    audit_app.dependency_overrides[audit.require_tenant_admin] = mock_require_tenant_admin
    audit_app.dependency_overrides[audit.get_db_from_context] = lambda: object()

    async with AsyncClient(transport=ASGITransport(app=audit_app), base_url="http://test") as client:
        response = await client.get("/v1/audit/logs", params={"source": "provenance"})

    assert response.status_code == 503
    assert "Provenance" in response.json()["error"]["message"]
