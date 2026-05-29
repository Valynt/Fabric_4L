"""Tenant isolation tests for evidence link listing endpoint."""

from collections.abc import Iterator
from typing import Any

from fastapi.testclient import TestClient

from api.dependencies import get_neo4j_driver
from api.main import app
from value_fabric.shared.security.dil_auth import get_verified_tenant_id


class _FakeResult:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    async def data(self) -> list[dict[str, Any]]:
        return self._rows


class _FakeSession:
    def __init__(self, dataset: list[dict[str, Any]], calls: list[tuple[str, dict[str, Any]]]) -> None:
        self._dataset = dataset
        self._calls = calls

    async def __aenter__(self) -> "_FakeSession":
        return self

    async def __aexit__(self, *_: Any) -> None:
        return None

    async def run(self, query: str, params: dict[str, Any]) -> _FakeResult:
        self._calls.append((query, params))

        # Emulate fail-closed behavior from query tenant constraints.
        tenant_id = params["tenant_id"]
        rows = [row for row in self._dataset if row["tenant_id"] == tenant_id]
        return _FakeResult(rows)


class _FakeDriver:
    def __init__(self, dataset: list[dict[str, Any]], calls: list[tuple[str, dict[str, Any]]]) -> None:
        self._dataset = dataset
        self._calls = calls

    def session(self) -> _FakeSession:
        return _FakeSession(self._dataset, self._calls)


def _build_dataset() -> list[dict[str, Any]]:
    return [
        {
            "tenant_id": "tenant-a",
            "evidence_id": "ev-shared-key",
            "evidence_title": "Tenant A Proof",
            "evidence_type": "case_study",
        },
        {
            "tenant_id": "tenant-b",
            "evidence_id": "ev-shared-key",
            "evidence_title": "Tenant B Proof",
            "evidence_type": "case_study",
        },
        # Hostile fixture: malformed cross-tenant relationship accidentally links
        # tenant-a driver to tenant-b evidence with similarly keyed entities.
        {
            "tenant_id": "tenant-b",
            "evidence_id": "ev-hostile-cross-tenant",
            "evidence_title": "Hostile Cross Tenant Evidence",
            "evidence_type": "benchmark",
        },
    ]


def _make_client(tenant_id: str, calls: list[tuple[str, dict[str, Any]]]) -> TestClient:
    app.dependency_overrides[get_verified_tenant_id] = lambda: tenant_id
    app.dependency_overrides[get_neo4j_driver] = lambda: _FakeDriver(_build_dataset(), calls)
    return TestClient(app)


def test_list_evidence_links_returns_only_same_tenant_rows() -> None:
    calls: list[tuple[str, dict[str, Any]]] = []

    with _make_client("tenant-a", calls) as client:
        response = client.get("/api/v1/evidence/links", params={"driver_id": "driver-shared-key"})

    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["links"] == [
        {
            "evidence_id": "ev-shared-key",
            "evidence_title": "Tenant A Proof",
            "evidence_type": "case_study",
        }
    ]

    query, params = calls[0]
    assert "(e:Evidence {tenant_id: $tenant_id})" in query
    assert "WHERE e.tenant_id = $tenant_id" in query
    assert params == {"driver_id": "driver-shared-key", "tenant_id": "tenant-a"}


def test_list_evidence_links_excludes_hostile_cross_tenant_fixture() -> None:
    calls: list[tuple[str, dict[str, Any]]] = []

    with _make_client("tenant-b", calls) as client:
        response = client.get("/api/v1/evidence/links", params={"driver_id": "driver-shared-key"})

    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["links"] == [
        {
            "evidence_id": "ev-shared-key",
            "evidence_title": "Tenant B Proof",
            "evidence_type": "case_study",
        },
        {
            "evidence_id": "ev-hostile-cross-tenant",
            "evidence_title": "Hostile Cross Tenant Evidence",
            "evidence_type": "benchmark",
        },
    ]
