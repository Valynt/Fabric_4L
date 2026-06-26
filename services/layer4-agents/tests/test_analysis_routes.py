from __future__ import annotations

"""Targeted tests for analysis routes executor integration."""


from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any
from uuid import UUID

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from value_fabric.shared.error_handling import register_exception_handlers

from layer4_agents.api.common.db import get_route_db
from layer4_agents.api.routes import analysis
from layer4_agents.config.settings import settings


async def _async_return(value: Any) -> Any:
    """Helper to create an awaitable that returns a value."""
    return value


@dataclass
class FakeExecutor:
    """Minimal executor stub for analysis route tests."""

    execute_response: Any
    results_by_id: dict[str, dict[str, Any]] = field(default_factory=dict)
    execute_calls: list[dict[str, Any]] = field(default_factory=list)
    get_result_calls: list[str] = field(default_factory=list)

    async def execute_workflow(self, **kwargs: Any) -> Any:
        self.execute_calls.append(kwargs)
        return self.execute_response

    async def get_result(self, workflow_id: str) -> dict[str, Any] | None:
        self.get_result_calls.append(workflow_id)
        return self.results_by_id.get(workflow_id)


class FakeScalarResult:
    def __init__(self, records: list[Any]) -> None:
        self.records = records

    def all(self) -> list[Any]:
        return self.records


class FakeExecuteResult:
    def __init__(self, records: list[Any] | None = None, rowcount: int = 0) -> None:
        self._records = records or []
        self.rowcount = rowcount

    def scalars(self) -> FakeScalarResult:
        return FakeScalarResult(self._records)

    def scalar_one_or_none(self) -> Any | None:
        return self._records[0] if self._records else None


class FakeScenarioDb:
    def __init__(self, records: list[Any] | None = None, delete_rowcount: int = 1) -> None:
        self.records = records or []
        self.delete_rowcount = delete_rowcount
        self.added: list[Any] = []

    async def execute(self, statement: Any) -> FakeExecuteResult:
        statement_text = str(statement)
        if statement_text.startswith("DELETE"):
            return FakeExecuteResult(rowcount=self.delete_rowcount)
        return FakeExecuteResult(records=self.records)

    def add(self, record: Any) -> None:
        self.added.append(record)
        self.records.append(record)

    async def commit(self) -> None:
        return None


@pytest.fixture
def analysis_app() -> FastAPI:
    """Build a small FastAPI app with analysis routes only."""
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(analysis.router, prefix="/v1")
    return app


async def _mock_context() -> Any:
    from value_fabric.shared.identity.context import RequestContext

    return RequestContext(
        tenant_id=UUID("12345678-1234-1234-1234-123456789abc"),
        user_id="test-user",
        roles=["tenant_admin"],
        permissions=frozenset(["read:agents", "write:agents"]),
    )


@pytest.mark.asyncio
async def test_post_cases_success_path(analysis_app: FastAPI, monkeypatch) -> None:
    """POST /cases (workspace path) should create a case record and return case_id."""
    account_uuid = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")

    class FakeDb:
        def __init__(self) -> None:
            self.added: list[Any] = []

        async def execute(self, stmt: Any) -> Any:
            return FakeExecuteResult()

        def add(self, record: Any) -> None:
            self.added.append(record)

        async def commit(self) -> None:
            pass

    fake_db = FakeDb()
    monkeypatch.setattr(
        analysis,
        "AccountService",
        lambda db: SimpleNamespace(
            get_account=lambda account_id, tenant_id=None: _async_return(
                SimpleNamespace(id=account_id, name="Acme Corp")
            )
        ),
    )

    analysis_app.dependency_overrides[analysis.require_authenticated] = _mock_context
    analysis_app.dependency_overrides[get_route_db] = lambda: fake_db
    analysis_app.dependency_overrides[analysis.get_executor] = lambda: None

    async with AsyncClient(transport=ASGITransport(app=analysis_app), base_url="http://test") as client:
        response = await client.post(
            "/v1/cases",
            json={"account_id": str(account_uuid), "title": "Test Case"},
        )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert "case_id" in payload
    assert payload["status"] in ("created", "completed")


@pytest.mark.asyncio
async def test_post_cases_uses_optional_case_id(analysis_app: FastAPI, monkeypatch) -> None:
    """POST /cases should accept and persist an optional deterministic case_id."""
    account_uuid = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    deterministic_case_id = "case-deterministic-001"

    class FakeDb:
        def __init__(self) -> None:
            self.added: list[Any] = []

        async def execute(self, stmt: Any) -> Any:
            return FakeExecuteResult()

        def add(self, record: Any) -> None:
            self.added.append(record)

        async def commit(self) -> None:
            pass

    fake_db = FakeDb()
    monkeypatch.setattr(
        analysis,
        "AccountService",
        lambda db: SimpleNamespace(
            get_account=lambda account_id, tenant_id=None: _async_return(
                SimpleNamespace(id=account_id, name="Acme Corp")
            )
        ),
    )

    analysis_app.dependency_overrides[analysis.require_authenticated] = _mock_context
    analysis_app.dependency_overrides[get_route_db] = lambda: fake_db
    analysis_app.dependency_overrides[analysis.get_executor] = lambda: None

    async with AsyncClient(transport=ASGITransport(app=analysis_app), base_url="http://test") as client:
        response = await client.post(
            "/v1/cases",
            json={
                "account_id": str(account_uuid),
                "title": "Deterministic Case",
                "case_id": deterministic_case_id,
            },
        )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["case_id"] == deterministic_case_id
    assert payload["status"] == "created"
    assert len(fake_db.added) == 1
    assert fake_db.added[0].case_id == deterministic_case_id


@pytest.mark.asyncio
async def test_get_case_retrieval(analysis_app: FastAPI) -> None:
    """GET /cases/{case_id} should retrieve persisted output via get_result."""
    fake_executor = FakeExecutor(execute_response=None)
    fake_executor.results_by_id["case-42"] = {
        "workflow_id": "case-42",
        "status": "completed",
        "created_at": "2026-04-23T00:00:00+00:00",
        "output": {
            "assemble_document": {
                "title": "Q2 Business Case",
                "executive_summary": "Strong ROI expected.",
                "total_estimated_value": 1000000.0,
                "implementation_cost_estimate": 250000.0,
                "roi_ratio": 4.0,
                "payback_months": 9,
                "confidence_score": 0.91,
                "recommendations": ["Proceed to pilot"],
            },
            "verify_truth_requirements": {"passed": True},
        },
    }

    class FakeDb:
        async def get(self, model: Any, key: str) -> Any:
            return None  # No DB record — tenant check falls back to metadata

    analysis_app.dependency_overrides[analysis.get_executor] = lambda: fake_executor
    analysis_app.dependency_overrides[analysis.require_authenticated] = _mock_context
    analysis_app.dependency_overrides[get_route_db] = lambda: FakeDb()

    async with AsyncClient(transport=ASGITransport(app=analysis_app), base_url="http://test") as client:
        response = await client.get("/v1/cases/case-42")

    assert response.status_code == 200
    payload = response.json()
    assert payload["case_id"] == "case-42"
    assert payload["title"] == "Q2 Business Case"
    assert payload["roi_ratio"] == 4.0
    assert fake_executor.get_result_calls == ["case-42"]


@pytest.mark.asyncio
async def test_export_route_uses_get_result_dependency(analysis_app: FastAPI, monkeypatch) -> None:
    """GET /cases/{case_id}/export should depend on get_result for retrieval."""
    from uuid import UUID as _UUID

    fake_executor = FakeExecutor(execute_response=None)
    fake_executor.results_by_id["case-export"] = {
        "workflow_id": "case-export",
        "status": "completed",
        "output": {
            "assemble_document": {
                "blocked": True,
                "truth_references": [{"id": "truth-2"}],
                "remediation_items": [{"action": "Add citation"}],
            },
            "verify_truth_requirements": {
                "passed": False,
                "requirements": ["All claims must be sourced"],
            },
        },
    }

    tenant_uuid = _UUID("12345678-1234-1234-1234-123456789abc")

    class FakeDb:
        async def get(self, model: Any, key: str) -> Any:
            return SimpleNamespace(
                case_id=key,
                account_id=_UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
                tenant_id=str(tenant_uuid),
                status="completed",
                document_url=None,
            )

        async def execute(self, stmt: Any) -> Any:
            return FakeExecuteResult()

    async def mock_require_authenticated_export() -> Any:
        from value_fabric.shared.identity.context import RequestContext
        return RequestContext(
            tenant_id=tenant_uuid,
            user_id="test-user",
            roles=["tenant_admin"],
            permissions=frozenset(["read:agents", "write:agents"]),
        )

    analysis_app.dependency_overrides[analysis.get_executor] = lambda: fake_executor
    analysis_app.dependency_overrides[analysis.require_authenticated] = mock_require_authenticated_export
    analysis_app.dependency_overrides[get_route_db] = lambda: FakeDb()
    monkeypatch.setattr(settings, "export_storage_endpoint", "http://storage.local", raising=False)
    # Stub AccountService to avoid real DB lookup
    async def _fake_get_account(account_id: Any, tenant_id: Any = None) -> Any:
        return SimpleNamespace(id=account_id, name="Acme")

    monkeypatch.setattr(analysis, "AccountService", lambda db: SimpleNamespace(
        get_account=_fake_get_account
    ))
    # Bypass approval gate so this test isolates the get_result dependency path
    async def _fake_require_approved_case(record: Any, context: Any, account: Any, format: str = "pdf") -> None:
        pass

    monkeypatch.setattr(analysis, "_require_approved_case", _fake_require_approved_case)

    async with AsyncClient(transport=ASGITransport(app=analysis_app), base_url="http://test") as client:
        response = await client.get("/v1/cases/case-export/export")

    assert response.status_code == 200
    payload = response.json()
    assert payload["case_id"] == "case-export"
    assert payload["blocked"] is True
    assert fake_executor.get_result_calls == ["case-export"]


@pytest.mark.asyncio
async def test_export_route_rejects_draft_case_before_document_generation(
    analysis_app: FastAPI,
    monkeypatch,
) -> None:
    """Draft cases must fail closed at the export endpoint, not only in the UI."""

    from uuid import UUID as _UUID

    tenant_uuid = _UUID("12345678-1234-1234-1234-123456789abc")
    account_uuid = _UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    fake_executor = FakeExecutor(execute_response=None)
    fake_executor.results_by_id["case-draft"] = {
        "workflow_id": "case-draft",
        "status": "completed",
        "output": {
            "assemble_document": {
                "document_bytes": b"%PDF-1.4 draft bytes",
                "blocked": False,
            },
            "verify_truth_requirements": {"passed": True},
        },
    }
    audit_events: list[dict[str, Any]] = []

    class FakeDb:
        async def get(self, model: Any, key: str) -> Any:
            return SimpleNamespace(
                case_id=key,
                account_id=account_uuid,
                tenant_id=str(tenant_uuid),
                status="draft",
                document_url=None,
            )

    async def mock_context() -> Any:
        from value_fabric.shared.identity.context import RequestContext

        return RequestContext(
            tenant_id=tenant_uuid,
            user_id="creator-user",
            roles=["tenant_admin"],
            permissions=frozenset(["read:agents", "write:agents"]),
        )

    async def fake_get_account(account_id: Any, tenant_id: Any = None) -> Any:
        return SimpleNamespace(id=account_id, name="Acme")

    async def capture_audit(**kwargs: Any) -> None:
        audit_events.append(kwargs)

    async def fail_upload(**kwargs: Any) -> None:
        raise AssertionError("draft export must not upload artifacts")

    analysis_app.dependency_overrides[analysis.get_executor] = lambda: fake_executor
    analysis_app.dependency_overrides[analysis.require_authenticated] = mock_context
    analysis_app.dependency_overrides[get_route_db] = lambda: FakeDb()
    monkeypatch.setattr(analysis, "AccountService", lambda db: SimpleNamespace(get_account=fake_get_account))
    monkeypatch.setattr(analysis, "emit_and_persist_audit", capture_audit)
    monkeypatch.setattr(analysis, "upload_bytes", fail_upload)

    async with AsyncClient(transport=ASGITransport(app=analysis_app), base_url="http://test") as client:
        response = await client.get("/v1/cases/case-draft/export")

    assert response.status_code == 409, response.text
    assert "Business case must be approved before export" in response.text
    assert fake_executor.get_result_calls == []
    assert len(audit_events) == 1
    audit = audit_events[0]
    assert audit["action"] == analysis.AuditAction.EXPORT_REQUESTED
    assert audit["resource_type"] == "BusinessCaseExport"
    assert audit["resource_id"] == "case-draft"
    assert audit["details"] == {
        "case_id": "case-draft",
        "format": "pdf",
        "outcome": "denied",
        "denied_reason": "approval_required",
        "tenant_id": str(tenant_uuid),
        "account_id": str(account_uuid),
        "case_status": "draft",
    }


@pytest.mark.asyncio
async def test_export_route_approved_case_uploads_tenant_scoped_artifacts_and_audits(
    analysis_app: FastAPI,
    monkeypatch,
) -> None:
    """Approved case export must create tenant-scoped artifacts and audit export events."""

    from uuid import UUID as _UUID

    tenant_uuid = _UUID("12345678-1234-1234-1234-123456789abc")
    account_uuid = _UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    fake_executor = FakeExecutor(execute_response=None)
    fake_executor.results_by_id["case-approved"] = {
        "workflow_id": "workflow-approved",
        "status": "completed",
        "output": {
            "assemble_document": {
                "document_bytes": b"%PDF-1.4 approved bytes",
                "blocked": False,
                "truth_references": [{"truth_object_id": "truth-1"}],
            },
            "verify_truth_requirements": {
                "passed": True,
                "truth_references": [{"truth_object_id": "truth-1"}],
            },
        },
    }
    uploads: list[dict[str, Any]] = []
    audit_events: list[dict[str, Any]] = []

    class FakeDb:
        async def get(self, model: Any, key: str) -> Any:
            return SimpleNamespace(
                case_id=key,
                account_id=account_uuid,
                tenant_id=str(tenant_uuid),
                status="approved",
                document_url=None,
            )

    async def mock_context() -> Any:
        from value_fabric.shared.identity.context import RequestContext

        return RequestContext(
            tenant_id=tenant_uuid,
            user_id="reviewer-user",
            roles=["tenant_admin"],
            permissions=frozenset(["read:agents", "write:agents"]),
        )

    async def fake_get_account(account_id: Any, tenant_id: Any = None) -> Any:
        return SimpleNamespace(id=account_id, name="Acme")

    async def capture_upload(**kwargs: Any) -> Any:
        uploads.append(kwargs)
        return SimpleNamespace(bucket="exports", key=f"{kwargs['tenant_id']}/{kwargs['object_key']}", etag="etag")

    async def fake_download_url(*, tenant_id: str, object_key: str, expires_in_seconds: int | None = None) -> str:
        return f"https://storage.local/{tenant_id}/{object_key}?signed=1"

    async def capture_audit(**kwargs: Any) -> None:
        audit_events.append(kwargs)

    monkeypatch.setattr(analysis, "get_settings", lambda: SimpleNamespace(export_storage_endpoint="http://storage.local", export_signed_url_ttl_seconds=900))
    analysis_app.dependency_overrides[analysis.get_executor] = lambda: fake_executor
    analysis_app.dependency_overrides[analysis.require_authenticated] = mock_context
    analysis_app.dependency_overrides[get_route_db] = lambda: FakeDb()
    monkeypatch.setattr(analysis, "AccountService", lambda db: SimpleNamespace(get_account=fake_get_account))
    monkeypatch.setattr(analysis, "upload_bytes", capture_upload)
    monkeypatch.setattr(analysis, "generate_download_url", fake_download_url)
    monkeypatch.setattr(analysis, "emit_and_persist_audit", capture_audit)

    async with AsyncClient(transport=ASGITransport(app=analysis_app), base_url="http://test") as client:
        response = await client.get("/v1/cases/case-approved/export")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["case_id"] == "case-approved"
    assert payload["download_ready"] is True
    assert payload["blocked"] is False
    assert payload["document_url"].startswith(f"https://storage.local/{tenant_uuid}/case-approved/")
    assert payload["manifest_url"].startswith(f"https://storage.local/{tenant_uuid}/case-approved/")
    assert fake_executor.get_result_calls == ["case-approved"]

    assert len(uploads) == 2
    assert all(upload["tenant_id"] == str(tenant_uuid) for upload in uploads)
    assert uploads[0]["object_key"].startswith("case-approved/")
    assert uploads[0]["metadata"]["tenant_id"] == str(tenant_uuid)
    assert uploads[0]["metadata"]["account-id"] == str(account_uuid)
    assert uploads[1]["object_key"].endswith("business_case_case-approved.provenance.json")

    assert [event["action"] for event in audit_events] == [
        analysis.AuditAction.EXPORT_REQUESTED,
        analysis.AuditAction.EXPORT_PACKAGE_GENERATED,
        analysis.AuditAction.EXPORT_DOWNLOAD_ACCESSED,
    ]
    assert all(event["resource_id"] == "case-approved" for event in audit_events)
    assert all(event["details"]["account_id"] == str(account_uuid) for event in audit_events)


@pytest.mark.asyncio
async def test_save_and_list_business_case_scenarios_are_server_side(
    analysis_app: FastAPI,
) -> None:
    fake_db = FakeScenarioDb()
    analysis_app.dependency_overrides[analysis.require_authenticated] = _mock_context
    analysis_app.dependency_overrides[get_route_db] = lambda: fake_db

    async with AsyncClient(transport=ASGITransport(app=analysis_app), base_url="http://test") as client:
        create_response = await client.post(
            "/v1/cases/case-123/scenarios",
            json={
                "name": "Cost pressure scenario",
                "adjustments": [{"name": "Implementation cost", "value": 125000}],
            },
        )
        list_response = await client.get("/v1/cases/case-123/scenarios")

    assert create_response.status_code == 201, create_response.text
    created = create_response.json()
    assert created["id"].startswith("scenario_")
    assert created["adjustments"] == [{"name": "Implementation cost", "value": 125000}]
    assert fake_db.added[0].tenant_id == "12345678-1234-1234-1234-123456789abc"

    assert list_response.status_code == 200, list_response.text
    listed = list_response.json()
    assert listed == [
        {
            "id": created["id"],
            "name": "Cost pressure scenario",
            "created_at": created["created_at"],
        }
    ]
    assert "adjustments" not in listed[0]


@pytest.mark.asyncio
async def test_delete_business_case_scenario_is_tenant_scoped(analysis_app: FastAPI) -> None:
    fake_db = FakeScenarioDb(delete_rowcount=0)
    analysis_app.dependency_overrides[analysis.require_authenticated] = _mock_context
    analysis_app.dependency_overrides[get_route_db] = lambda: fake_db

    async with AsyncClient(transport=ASGITransport(app=analysis_app), base_url="http://test") as client:
        response = await client.delete("/v1/cases/case-123/scenarios/scenario-missing")

    assert response.status_code == 404
    assert "Saved scenario not found" in response.text


# ═══════════════════════════════════════════════════════════════════════════════
# WORKSPACE TAB ENDPOINT TESTS
# These endpoints persist tab JSON per tenant/case/tab.
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_get_workspace_tab_returns_empty_shape_when_missing(analysis_app: FastAPI) -> None:
    """GET /cases/{case_id}/workspace/{tab_key} returns the canonical empty shape."""
    async def mock_require_authenticated():
        from value_fabric.shared.identity.context import RequestContext
        return RequestContext(
            tenant_id=UUID("12345678-1234-1234-1234-123456789abc"),
            user_id="test-user",
            roles=["tenant_admin"],
            permissions=frozenset(["read:agents", "write:agents"]),
        )

    analysis_app.dependency_overrides[analysis.require_authenticated] = mock_require_authenticated
    analysis_app.dependency_overrides[get_route_db] = lambda: FakeScenarioDb()

    test_case_id = "test-case-456"

    async with AsyncClient(transport=ASGITransport(app=analysis_app), base_url="http://test") as client:
        response = await client.get(f"/v1/cases/{test_case_id}/workspace/signals")
        assert response.status_code == 200, response.text
        assert response.json() == {"signals": []}


@pytest.mark.asyncio
async def test_get_workspace_tab_invalid_tab_key(analysis_app: FastAPI) -> None:
    """GET /cases/{case_id}/workspace/{tab_key} should reject invalid tab keys before 501."""
    async def mock_require_authenticated():
        from value_fabric.shared.identity.context import RequestContext
        return RequestContext(
            tenant_id=UUID("12345678-1234-1234-1234-123456789abc"),
            user_id="test-user",
            roles=["tenant_admin"],
            permissions=frozenset(["read:agents", "write:agents"]),
        )

    analysis_app.dependency_overrides[analysis.require_authenticated] = mock_require_authenticated
    analysis_app.dependency_overrides[get_route_db] = lambda: FakeScenarioDb()

    async with AsyncClient(transport=ASGITransport(app=analysis_app), base_url="http://test") as client:
        response = await client.get("/v1/cases/test-case/workspace/invalid-tab")
    assert response.status_code == 422
    payload = response.json()
    assert "Invalid tab_key" in payload["error"]["message"]


@pytest.mark.asyncio
async def test_get_workspace_tab_all_valid_tabs_return_empty_shape(analysis_app: FastAPI) -> None:
    """All valid workspace tab keys return a stable empty shape when no data exists."""
    async def mock_require_authenticated():
        from value_fabric.shared.identity.context import RequestContext
        return RequestContext(
            tenant_id=UUID("12345678-1234-1234-1234-123456789abc"),
            user_id="test-user",
            roles=["tenant_admin"],
            permissions=frozenset(["read:agents", "write:agents"]),
        )

    analysis_app.dependency_overrides[analysis.require_authenticated] = mock_require_authenticated
    analysis_app.dependency_overrides[get_route_db] = lambda: FakeScenarioDb()

    test_case_id = "test-case-tabs"
    valid_tabs = [
        "signals",
        "drivers",
        "evidence",
        "stakeholders",
        "action-plan",
        "value-model",
        "narrative",
        "intake",
        "evidence-links",
    ]

    async with AsyncClient(transport=ASGITransport(app=analysis_app), base_url="http://test") as client:
        for tab in valid_tabs:
            response = await client.get(f"/v1/cases/{test_case_id}/workspace/{tab}")
            assert response.status_code == 200, f"Tab '{tab}' should return 200, got {response.status_code}"
            assert response.json() == {tab: []}


@pytest.mark.asyncio
async def test_update_workspace_tab_persists_payload(analysis_app: FastAPI) -> None:
    """PUT /cases/{case_id}/workspace/{tab_key} persists tab data."""
    async def mock_require_authenticated():
        from value_fabric.shared.identity.context import RequestContext
        return RequestContext(
            tenant_id=UUID("12345678-1234-1234-1234-123456789abc"),
            user_id="test-user",
            roles=["tenant_admin"],
            permissions=frozenset(["read:agents", "write:agents"]),
        )

    analysis_app.dependency_overrides[analysis.require_authenticated] = mock_require_authenticated
    fake_db = FakeScenarioDb()
    analysis_app.dependency_overrides[get_route_db] = lambda: fake_db

    test_case_id = "test-case-update"
    test_signals = [
        {"id": "sig_1", "name": "Updated Signal", "category": "Cost", "confidence": 90}
    ]

    async with AsyncClient(transport=ASGITransport(app=analysis_app), base_url="http://test") as client:
        response = await client.put(
            f"/v1/cases/{test_case_id}/workspace/signals",
            json={"signals": test_signals}
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["updated"] is True
        assert payload["data"] == {"signals": test_signals}
        assert fake_db.added[0].case_id == test_case_id
        assert fake_db.added[0].tab_key == "signals"
        assert fake_db.added[0].data == {"signals": test_signals}


