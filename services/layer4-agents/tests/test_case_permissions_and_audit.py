from __future__ import annotations

"""Security and audit tests for case routes."""


from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

import psycopg  # noqa: F401 — mandatory dep; install via layer4-agents[dev] (psycopg[binary])
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from value_fabric.shared.audit import emit_audit_event
from value_fabric.shared.audit.models import AuditAction
from value_fabric.shared.error_handling import register_exception_handlers
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_authenticated
from value_fabric.shared.models.typed_dict import TypedDictModel

from layer4_agents.api.routes import analysis

app = FastAPI()
register_exception_handlers(app)
app.include_router(analysis.router, prefix="/v1")


class _FakeDb:
    async def get(self, model, key):
        return None

    def add(self, _obj):
        return None

    async def flush(self):
        return None

    async def execute(self, *_args, **_kwargs):
        return SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: []), scalar_one_or_none=lambda: None)


class _FakeExecutor_get_resultResult(TypedDictModel):
    metadata: dict[str, Any]
    output: dict[str, Any]
    status: str
    workflow_id: Any


class _FakeExecutor:
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id

    async def run(self, workflow_type: str, input_data: dict, tenant_id: str | None = None, user_id: str | None = None):
        return SimpleNamespace(
            workflow_id="case-123",
            status=SimpleNamespace(value="completed"),
            output_data={
                "assemble_document": {
                    "document_url": "https://example.local/case-123.pdf",
                    "document_bytes": b"pdf-bytes",
                    "case_metadata": {"account_id": "acct-001"},
                },
                "verify_truth_requirements": {"passed": True},
            },
        )

    async def get_result(self, case_id: str):
        return _FakeExecutor_get_resultResult.model_validate({
            "workflow_id": case_id,
            "metadata": {"tenant_id": self.tenant_id, "workflow_id": case_id},
            "status": "completed",
            "output": {
                "assemble_document": {
                    "title": "Case",
                    "executive_summary": "summary",
                    "document_bytes": b"pdf-bytes",
                    "case_metadata": {"account_id": "acct-001"},
                },
                "verify_truth_requirements": {"passed": True},
            },
        })


@pytest.fixture
async def client():
    app.dependency_overrides[analysis.get_route_db] = lambda: _FakeDb()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_missing_identity_rejected(client: AsyncClient):
    """Unauthenticated access to case routes should be rejected."""

    app.dependency_overrides[analysis.get_executor] = lambda: _FakeExecutor(str(uuid4()))

    response = await client.post(
        "/v1/cases",
        json={"prospect_id": "prospect-1", "sections": ["executive_summary"], "output_format": "pdf"},
    )

    assert response.status_code == 401, response.text


@pytest.mark.asyncio
async def test_cross_tenant_case_access_denied(client: AsyncClient):
    """Cross-tenant reads should fail with 403."""

    owner_tenant = uuid4()
    caller_tenant = uuid4()

    app.dependency_overrides[analysis.get_executor] = lambda: _FakeExecutor(str(owner_tenant))

    def _override_auth() -> RequestContext:
        return RequestContext(
            tenant_id=caller_tenant,
            user_id="user-1",
            roles=[],
            permissions=frozenset({"read:agents"}),
        )

    app.dependency_overrides[analysis.require_authenticated] = _override_auth
    app.dependency_overrides[require_authenticated] = _override_auth

    response = await client.get("/v1/cases/case-123")

    assert response.status_code == 403, response.text


@pytest.mark.asyncio
async def test_audit_lifecycle_reconstructable(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    """Case export lifecycle emits enough immutable events for reconstruction."""

    tenant = uuid4()
    account_id = uuid4()
    executor = _FakeExecutor(str(tenant))
    captured_events = []

    async def _capture(*, action, context, resource_type, resource_id, details=None):
        event = emit_audit_event(
            action,
            tenant_id=context.tenant_id,
            user_id=context.user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            details=dict(details or {}),
        )
        captured_events.append(event)

    async def _upload_bytes(**kwargs):
        return None

    async def _download_url(object_key: str, tenant_id: str | None = None):
        return f"https://example.local/{tenant_id or 'global'}/{object_key}"

    monkeypatch.setattr(analysis, "emit_and_persist_audit", _capture)
    monkeypatch.setattr(analysis, "upload_bytes", _upload_bytes)
    monkeypatch.setattr(analysis, "generate_download_url", _download_url)
    monkeypatch.setattr(
        analysis,
        "build_export_provenance_manifest",
        lambda **_: {"truth_object_ids": [], "source_references": []},
    )
    # Ensure the route and module use the same settings instance even if another
    # test cleared the get_settings cache.
    from layer4_agents.config.settings import get_settings
    get_settings.cache_clear()
    analysis.settings = get_settings()
    monkeypatch.setattr(analysis.settings, "export_storage_endpoint", "https://storage.local")

    class _DbWithCase(_FakeDb):
        async def get(self, model, key):
            return SimpleNamespace(case_id=key, account_id=account_id, status="approved")

    class _AccountService:
        def __init__(self, _db):
            pass

        async def get_account(self, _account_id, tenant_id=None):
            return SimpleNamespace(id=account_id, tenant_id=str(tenant))

    app.dependency_overrides[analysis.get_route_db] = lambda: _DbWithCase()
    app.dependency_overrides[analysis.get_executor] = lambda: executor

    def _override_auth() -> RequestContext:
        return RequestContext(
            tenant_id=tenant,
            user_id="auditor-user",
            roles=[],
            permissions=frozenset({"read:agents", "write:agents"}),
        )

    app.dependency_overrides[analysis.require_authenticated] = _override_auth
    app.dependency_overrides[require_authenticated] = _override_auth
    monkeypatch.setattr(analysis, "AccountService", _AccountService)

    export_response = await client.get("/v1/cases/case-123/export")
    assert export_response.status_code == 200

    actions = [event.action for event in captured_events]
    assert AuditAction.EXPORT_REQUESTED in actions
    assert AuditAction.EXPORT_PACKAGE_GENERATED in actions
    assert AuditAction.EXPORT_DOWNLOAD_ACCESSED in actions

    for event in captured_events:
        if event.action in {
            AuditAction.EXPORT_REQUESTED,
            AuditAction.EXPORT_PACKAGE_GENERATED,
            AuditAction.EXPORT_DOWNLOAD_ACCESSED,
        }:
            assert event.details.get("case_id") == "case-123"
            assert event.details.get("workflow_id") == "case-123"
            assert event.details.get("account_id") == str(account_id)
            assert UUID(str(event.tenant_id)) == tenant
