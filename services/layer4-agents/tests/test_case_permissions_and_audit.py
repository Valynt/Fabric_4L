from __future__ import annotations

"""Security and audit tests for case routes."""


from typing import Any
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

import psycopg  # noqa: F401 — mandatory dep; install via layer4-agents[dev] (psycopg[binary])

from httpx import ASGITransport, AsyncClient

from value_fabric.shared.audit.models import AuditAction
from value_fabric.shared.identity.context import RequestContext
from value_fabric.layer4.api.main import app
from value_fabric.layer4.api.routes import analysis
from value_fabric.shared.identity.dependencies import require_authenticated
from value_fabric.shared.models.typed_dict import TypedDictModel


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

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_cross_tenant_case_access_denied(client: AsyncClient):
    """Cross-tenant reads should fail with 403."""

    owner_tenant = uuid4()
    caller_tenant = uuid4()

    app.dependency_overrides[analysis.get_executor] = lambda: _FakeExecutor(str(owner_tenant))
    app.dependency_overrides[require_authenticated] = lambda: RequestContext(
        tenant_id=caller_tenant,
        user_id="user-1",
        roles=[],
    )

    response = await client.get("/v1/cases/case-123")

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_audit_lifecycle_reconstructable(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    """Case lifecycle emits enough immutable events for full reconstruction."""

    tenant = uuid4()
    executor = _FakeExecutor(str(tenant))
    captured_events = []

    async def _capture(event, _db_factory):
        captured_events.append(event)

    async def _upload_bytes(**kwargs):
        return None

    async def _download_url(object_key: str):
        return f"https://example.local/{object_key}"

    monkeypatch.setattr("src.api.routes.analysis.AuditEmitter.write_to_db", _capture)
    monkeypatch.setattr("src.api.routes.analysis.upload_bytes", _upload_bytes)
    monkeypatch.setattr("src.api.routes.analysis.generate_download_url", _download_url)
    monkeypatch.setattr(
        "src.api.routes.analysis.build_export_provenance_manifest",
        lambda **_: {"truth_object_ids": [], "source_references": []},
    )
    monkeypatch.setattr("src.api.routes.analysis.settings.export_storage_endpoint", "https://storage.local")

    app.dependency_overrides[analysis.get_executor] = lambda: executor
    app.dependency_overrides[require_authenticated] = lambda: RequestContext(
        tenant_id=tenant,
        user_id="auditor-user",
        roles=[],
    )

    create_response = await client.post(
        "/v1/cases",
        json={
            "prospect_id": "prospect-1",
            "sections": ["executive_summary"],
            "output_format": "pdf",
            "custom_inputs": {"account_id": "acct-001"},
        },
    )
    assert create_response.status_code == 200

    update_response = await client.patch(
        "/v1/cases/case-123",
        json={"workflow_id": "case-123", "account_id": "acct-001", "updates": {"summary": "new"}},
    )
    assert update_response.status_code == 200

    approve_response = await client.post(
        "/v1/cases/case-123/approve",
        json={"workflow_id": "case-123", "account_id": "acct-001", "approved": True, "notes": "ship it"},
    )
    assert approve_response.status_code == 200

    export_response = await client.get("/v1/cases/case-123/export")
    assert export_response.status_code == 200

    actions = [event.action for event in captured_events]
    assert AuditAction.BUSINESS_CASE_GENERATED in actions
    assert AuditAction.BUSINESS_CASE_UPDATED in actions
    assert AuditAction.BUSINESS_CASE_APPROVED in actions
    assert AuditAction.EXPORT_REQUESTED in actions
    assert AuditAction.EXPORT_PACKAGE_GENERATED in actions
    assert AuditAction.EXPORT_DOWNLOAD_ACCESSED in actions

    for event in captured_events:
        if event.action in {
            AuditAction.BUSINESS_CASE_GENERATED,
            AuditAction.BUSINESS_CASE_UPDATED,
            AuditAction.BUSINESS_CASE_APPROVED,
            AuditAction.EXPORT_REQUESTED,
            AuditAction.EXPORT_PACKAGE_GENERATED,
            AuditAction.EXPORT_DOWNLOAD_ACCESSED,
        }:
            assert event.details.get("case_id") == "case-123"
            assert event.details.get("workflow_id") == "case-123"
            assert event.details.get("account_id") == "acct-001"
            assert UUID(str(event.tenant_id)) == tenant
