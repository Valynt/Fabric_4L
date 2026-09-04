"""Adversarial tenant-isolation regressions for POST /v1/tools/export-document."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from value_fabric.shared.error_handling import register_exception_handlers
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.permissions import Permission

from layer4_agents.api.routes import tools


def _async_dependency(value: object) -> Callable[[], Awaitable[object]]:
    async def dependency() -> object:
        return value

    return dependency


@dataclass
class FakeExecutor:
    tenant_owners: dict[str, str | None] = field(default_factory=dict)
    results_by_id: dict[str, dict[str, object]] = field(default_factory=dict)
    get_result_calls: list[str] = field(default_factory=list)
    get_result_for_tenant_calls: list[tuple[str, str]] = field(default_factory=list)

    async def get_result(self, workflow_id: str) -> dict[str, object] | None:
        self.get_result_calls.append(workflow_id)
        return self.results_by_id.get(workflow_id)

    async def get_result_for_tenant(
        self,
        workflow_id: str,
        tenant_id: str,
    ) -> dict[str, object] | None:
        self.get_result_for_tenant_calls.append((workflow_id, tenant_id))
        owner = self.tenant_owners.get(workflow_id)
        if owner is None or owner != tenant_id:
            return None
        return self.results_by_id.get(workflow_id)


@dataclass
class ExportSideEffects:
    gateway_calls: list[tuple[str, dict[str, object]]] = field(default_factory=list)
    provenance_calls: list[dict[str, object]] = field(default_factory=list)
    upload_calls: list[dict[str, object]] = field(default_factory=list)
    signed_url_calls: list[dict[str, object]] = field(default_factory=list)
    audit_events: list[object] = field(default_factory=list)


def _build_app(
    *,
    executor: FakeExecutor,
    context: RequestContext,
) -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(tools.router, prefix="/v1")
    app.dependency_overrides[tools.get_executor] = _async_dependency(executor)
    app.dependency_overrides[tools.get_tool_registry] = _async_dependency(SimpleNamespace())
    app.dependency_overrides[tools.require_authenticated] = _async_dependency(context)
    return app


def _install_export_stubs(
    monkeypatch: pytest.MonkeyPatch,
    side_effects: ExportSideEffects,
    *,
    tool_result: dict[str, object] | None = None,
) -> None:
    monkeypatch.setattr(
        tools,
        "get_settings",
        lambda: SimpleNamespace(
            export_storage_endpoint="https://storage.local",
            export_signed_url_ttl_seconds=900,
        ),
    )
    monkeypatch.setattr(tools, "require_tool_gateway_available", lambda: None)
    monkeypatch.setattr(
        tools,
        "AgentBillOfMaterials",
        SimpleNamespace(from_manifest_dir=lambda **_: SimpleNamespace()),
    )

    class _StubToolGateway:
        def __init__(self, *args: object, **kwargs: object) -> None:
            self._result = tool_result or {
                "success": True,
                "pdf_bytes": b"%PDF-1.4\nstub\n",
                "filename": "business_case.pdf",
                "file_size_bytes": 14,
            }

        async def execute(
            self, tool_name: str, tool_input: dict[str, object]
        ) -> dict[str, object]:
            side_effects.gateway_calls.append((tool_name, tool_input))
            return self._result

    async def _upload_bytes(**kwargs: object) -> None:
        side_effects.upload_calls.append(dict(kwargs))

    async def _generate_download_url(*, tenant_id: str, object_key: str) -> str:
        side_effects.signed_url_calls.append({"tenant_id": tenant_id, "object_key": object_key})
        return f"https://signed.local/{tenant_id}/{object_key}"

    async def _write_to_db(event: object, _db_factory: object) -> None:
        side_effects.audit_events.append(event)

    def _build_manifest(**kwargs: object) -> dict[str, object]:
        side_effects.provenance_calls.append(dict(kwargs))
        return {"truth_object_ids": ["truth-1"], "source_references": ["src-1"]}

    monkeypatch.setattr(tools, "ToolGateway", _StubToolGateway)
    monkeypatch.setattr(tools, "upload_bytes", _upload_bytes)
    monkeypatch.setattr(tools, "generate_download_url", _generate_download_url)
    monkeypatch.setattr(tools, "build_export_provenance_manifest", _build_manifest)
    monkeypatch.setattr(tools.AuditEmitter, "write_to_db", _write_to_db)


def _export_result(workflow_id: str) -> dict[str, object]:
    return {
        "workflow_id": workflow_id,
        "status": "completed",
        "metadata": {"workflow_id": workflow_id, "tenant_id": "authoritative-tenant"},
        "output": {
            "assemble_document": {
                "title": "Business Case",
                "organization": "Acme Corp",
                "use_cases": ["Automate reporting"],
                "executive_summary": "Summary",
            },
            "synthesize_narrative": {"narrative": "Summary"},
        },
    }


def test_export_document_openapi_documents_tenant_failure_envelopes() -> None:
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(tools.router, prefix="/v1")

    operation = app.openapi()["paths"]["/v1/tools/export-document"]["post"]
    request_schema = operation["requestBody"]["content"]["application/json"]["schema"]
    assert request_schema == {"$ref": "#/components/schemas/DocumentExportRequest"}

    for status_code in ("400", "404", "503"):
        error_schema = operation["responses"][status_code]["content"]["application/json"]["schema"]
        assert error_schema == {"$ref": "#/components/schemas/ErrorEnvelope"}


@pytest.mark.asyncio
async def test_export_document_returns_404_for_cross_tenant_workflow_without_side_effects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner_tenant = str(uuid4())
    caller_tenant = str(uuid4())
    workflow_id = "wf-cross-tenant-export"
    executor = FakeExecutor(
        tenant_owners={workflow_id: owner_tenant},
        results_by_id={workflow_id: _export_result(workflow_id)},
    )
    context = RequestContext(
        tenant_id=caller_tenant,
        user_id="user-b",
        roles=["tenant_admin"],
        permissions=frozenset({Permission.WRITE_AGENTS.value}),
        auth_source="jwt_claim",
    )
    app = _build_app(executor=executor, context=context)
    side_effects = ExportSideEffects()
    _install_export_stubs(monkeypatch, side_effects)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/v1/tools/export-document",
            json={"business_case_id": workflow_id, "format": "pdf"},
        )

    assert response.status_code == 404, response.text
    assert executor.get_result_for_tenant_calls == [(workflow_id, caller_tenant)]
    assert executor.get_result_calls == []
    assert side_effects.gateway_calls == []
    assert side_effects.provenance_calls == []
    assert side_effects.upload_calls == []
    assert side_effects.signed_url_calls == []
    assert side_effects.audit_events == []


@pytest.mark.asyncio
async def test_export_document_same_tenant_success_path_still_works(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_id = str(uuid4())
    workflow_id = "wf-same-tenant-export"
    executor = FakeExecutor(
        tenant_owners={workflow_id: tenant_id},
        results_by_id={workflow_id: _export_result(workflow_id)},
    )
    context = RequestContext(
        tenant_id=tenant_id,
        user_id="user-a",
        roles=["tenant_admin"],
        permissions=frozenset({Permission.WRITE_AGENTS.value}),
        auth_source="jwt_claim",
    )
    app = _build_app(executor=executor, context=context)
    side_effects = ExportSideEffects()
    _install_export_stubs(monkeypatch, side_effects)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/v1/tools/export-document",
            json={"business_case_id": workflow_id, "format": "pdf"},
        )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["success"] is True
    assert payload["export_id"]
    assert payload["download_url"]
    assert payload["manifest_url"]
    assert payload["filename"] == "business_case.pdf"
    assert executor.get_result_for_tenant_calls == [(workflow_id, tenant_id)]
    assert executor.get_result_calls == []
    assert [call[0] for call in side_effects.gateway_calls] == ["export_document"]
    assert len(side_effects.provenance_calls) == 1
    assert len(side_effects.upload_calls) == 2
    assert len(side_effects.signed_url_calls) == 2
    assert len(side_effects.audit_events) == 3


@pytest.mark.asyncio
async def test_export_document_denies_missing_tenant_metadata_without_side_effects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_id = str(uuid4())
    workflow_id = "wf-missing-tenant-export"
    executor = FakeExecutor(
        tenant_owners={workflow_id: None},
        results_by_id={workflow_id: _export_result(workflow_id)},
    )
    context = RequestContext(
        tenant_id=tenant_id,
        user_id="user-a",
        roles=["tenant_admin"],
        permissions=frozenset({Permission.WRITE_AGENTS.value}),
        auth_source="jwt_claim",
    )
    app = _build_app(executor=executor, context=context)
    side_effects = ExportSideEffects()
    _install_export_stubs(monkeypatch, side_effects)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/v1/tools/export-document",
            json={"business_case_id": workflow_id, "format": "pdf"},
        )

    assert response.status_code == 404, response.text
    assert executor.get_result_for_tenant_calls == [(workflow_id, tenant_id)]
    assert executor.get_result_calls == []
    assert side_effects.gateway_calls == []
    assert side_effects.provenance_calls == []
    assert side_effects.upload_calls == []
    assert side_effects.signed_url_calls == []
    assert side_effects.audit_events == []


@pytest.mark.asyncio
async def test_export_document_rejects_authenticated_context_without_tenant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workflow_id = "wf-tenantless-export"
    executor = FakeExecutor(
        tenant_owners={workflow_id: "None"},
        results_by_id={workflow_id: _export_result(workflow_id)},
    )
    context = RequestContext(
        tenant_id=None,
        user_id="user-without-tenant",
        roles=["tenant_admin"],
        permissions=frozenset({Permission.WRITE_AGENTS.value}),
        auth_source="jwt_claim",
    )
    app = _build_app(executor=executor, context=context)
    side_effects = ExportSideEffects()
    _install_export_stubs(monkeypatch, side_effects)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/v1/tools/export-document",
            json={"business_case_id": workflow_id, "format": "pdf"},
        )

    assert response.status_code == 400, response.text
    assert executor.get_result_for_tenant_calls == []
    assert executor.get_result_calls == []
    assert side_effects.gateway_calls == []
    assert side_effects.provenance_calls == []
    assert side_effects.upload_calls == []
    assert side_effects.signed_url_calls == []
    assert side_effects.audit_events == []
