from __future__ import annotations

import pytest

from src.migrations.migrate_tenant_ids import TenantIdMigration


class _FakeResult:
    def __init__(self, updated: int):
        self._updated = updated

    async def single(self):
        return {"updated": self._updated}


class _FakeSession:
    def __init__(self):
        self.calls: list[tuple[str, dict | None]] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def run(self, query: str, params: dict | None = None):
        self.calls.append((query, params))
        return _FakeResult(updated=1)


class _FakeDriver:
    def __init__(self, session: _FakeSession):
        self._session = session

    def session(self):
        return self._session


@pytest.mark.asyncio
async def test_normalize_legacy_tenant_property_names_scopes_expected_labels() -> None:
    session = _FakeSession()
    migration = TenantIdMigration()
    migration._driver = _FakeDriver(session)

    updated = await migration.normalize_legacy_tenant_property_names()

    assert updated == {"Formula": 1, "Variable": 1}
    assert len(session.calls) == 2
    assert "MATCH (n:Formula)" in session.calls[0][0]
    assert "REMOVE n.tenantId" in session.calls[0][0]
    assert "MATCH (n:Variable)" in session.calls[1][0]


@pytest.mark.asyncio
async def test_backfill_tenant_for_expansion_labels_sets_tenant_id() -> None:
    session = _FakeSession()
    migration = TenantIdMigration()
    migration._driver = _FakeDriver(session)

    updated = await migration.backfill_tenant_for_expansion_labels("tenant-123")

    assert updated == {
        "Formula": 1,
        "Benchmark": 1,
        "ValueModel": 1,
        "BenchmarkPolicy": 1,
        "FormulaVersion": 1,
        "SourceBinding": 1,
    }
    assert len(session.calls) == 6
    for query, params in session.calls:
        assert "SET n.tenant_id = $tenant_id" in query
        assert params == {"tenant_id": "tenant-123"}
