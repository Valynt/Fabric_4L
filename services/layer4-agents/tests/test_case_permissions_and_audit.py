from __future__ import annotations

"""Security and audit tests for case routes."""


from typing import Any
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

import psycopg  # noqa: F401 — mandatory dep; install via layer4-agents[dev] (psycopg[binary])

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from value_fabric.shared.error_handling import register_exception_handlers
from value_fabric.shared.audit.models import AuditAction
from value_fabric.shared.identity.context import RequestContext
from layer4_agents.api.routes import analysis
from value_fabric.shared.models.typed_dict import TypedDictModel


class _FakeExecutor_get_resultResult(TypedDictModel):
    metadata: dict[str, Any]
    output: dict[str, Any]
    status: str
    workflow_id: Any


class _FakeExecutor:
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.state_manager = SimpleNamespace(save_state=self._save_state)

    async def _save_state(self, *args: Any, **kwargs: Any) -> None:
        return None

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
    test_app = FastAPI()
    register_exception_handlers(test_app)
    test_app.include_router(analysis.router, prefix="/v1")
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as ac:
        yield ac
    test_app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_missing_identity_rejected(client: AsyncClient):
    """Unauthenticated access to case routes should be rejected."""

    client._transport.app.dependency_overrides[analysis.get_executor] = lambda: _FakeExecutor(str(uuid4()))
    client._transport.app.dependency_overrides[analysis.get_route_db] = lambda: SimpleNamespace()

    response = await client.get("/v1/cases/case-123")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_cross_tenant_case_access_denied(client: AsyncClient):
    """Cross-tenant reads should fail with 403."""

    owner_tenant = uuid4()
    caller_tenant = uuid4()

    class FakeDB:
        async def get(self, *args: Any, **kwargs: Any) -> None:
            return None

    client._transport.app.dependency_overrides[analysis.get_executor] = lambda: _FakeExecutor(str(owner_tenant))
    client._transport.app.dependency_overrides[analysis.get_route_db] = lambda: FakeDB()
    client._transport.app.dependency_overrides[analysis.require_authenticated] = lambda: RequestContext(
        tenant_id=caller_tenant,
        user_id="user-1",
        roles=[],
        permissions=frozenset({"read:agents"}),
    )

    response = await client.get("/v1/cases/case-123")

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_audit_lifecycle_reconstructable(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    """Case lifecycle emits enough immutable events for full reconstruction."""

    tenant = uuid4()
    account_id = uuid4()
    executor = _FakeExecutor(str(tenant))
    captured_events = []

    async def _capture_audit(*, action, context, resource_type, resource_id, details):
        captured_events.append(
            SimpleNamespace(
                action=action,
                tenant_id=context.tenant_id,
                details={
                    "resource_type": resource_type,
                    "resource_id": resource_id,
                    **details,
                },
            )
        )

    async def _upload_bytes(**kwargs):
        return None

    async def _download_url(object_key: str):
        return f"https://example.local/{object_key}"

    class FakeAccountService:
        def __init__(self, db: Any) -> None:
            self.db = db

        async def get_account(self, requested_account_id: UUID, *, tenant_id: str | None = None) -> Any:
            assert requested_account_id == account_id
            assert tenant_id == str(tenant)
            return SimpleNamespace(id=account_id)

    class FakeDB:
        async def get(self, model: Any, key: str) -> Any:
            return SimpleNamespace(account_id=account_id)

        def add(self, record: Any) -> None:
            return None

        async def commit(self) -> None:
            return None

        async def refresh(self, record: Any) -> None:
            return None

    monkeypatch.setattr(analysis, "emit_and_persist_audit", _capture_audit)
    monkeypatch.setattr(analysis, "AccountService", FakeAccountService)
    monkeypatch.setattr(analysis, "upload_bytes", _upload_bytes)
    monkeypatch.setattr(analysis, "generate_download_url", _download_url)
    monkeypatch.setattr(
        analysis,
        "build_export_provenance_manifest",
        lambda **_: {"truth_object_ids": [], "source_references": []},
    )
    monkeypatch.setattr(analysis.settings, "export_storage_endpoint", "https://storage.local")

    client._transport.app.dependency_overrides[analysis.get_executor] = lambda: executor
    client._transport.app.dependency_overrides[analysis.get_route_db] = lambda: FakeDB()
    client._transport.app.dependency_overrides[analysis.require_authenticated] = lambda: RequestContext(
        tenant_id=tenant,
        user_id="auditor-user",
        roles=[],
        permissions=frozenset({"admin:system", "read:agents", "write:agents"}),
    )

    seed_response = await client.post(
        "/v1/validation/seed/business-case-lifecycle",
        headers={"X-Privileged-Reason": analysis.SEED_PRIVILEGED_REASON},
        json={
            "account_id": str(account_id),
            "draft_case_id": "case-draft",
            "approved_case_id": "case-123",
            "approved_case_aliases": [],
        },
    )
    assert seed_response.status_code == 200, seed_response.text

    export_response = await client.get("/v1/cases/case-123/export")
    assert export_response.status_code == 200, export_response.text

    actions = [event.action for event in captured_events]
    assert AuditAction.BUSINESS_CASE_GENERATED in actions
    assert AuditAction.BUSINESS_CASE_APPROVED in actions
    assert AuditAction.EXPORT_REQUESTED in actions
    assert AuditAction.EXPORT_PACKAGE_GENERATED in actions
    assert AuditAction.EXPORT_DOWNLOAD_ACCESSED in actions

    for event in captured_events:
        if event.action in {
            AuditAction.BUSINESS_CASE_GENERATED,
            AuditAction.BUSINESS_CASE_APPROVED,
            AuditAction.EXPORT_REQUESTED,
            AuditAction.EXPORT_PACKAGE_GENERATED,
            AuditAction.EXPORT_DOWNLOAD_ACCESSED,
        } and event.details.get("case_id") == "case-123":
            assert event.details.get("case_id") == "case-123"
            assert event.details.get("account_id") == str(account_id)
            assert UUID(str(event.tenant_id)) == tenant
