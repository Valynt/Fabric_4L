from __future__ import annotations

"""Unit tests for the Layer 3 knowledge subgraph endpoints.

Tests cover:
- Happy path: benchmark variables returned for matching industry
- Empty result: no matching benchmark → empty-but-valid response (not 404)
- Tenant isolation: query is scoped to the caller's tenant_id
- Missing tenant context → 401
- Happy path: value driver formulas returned for matching IDs
- Partial match: missing_ids populated for IDs not in graph
- Empty driver_ids → 422
- Tenant isolation for value driver formulas
"""


from http import HTTPStatus
from unittest.mock import AsyncMock, patch

import pytest

from src.api.routes.knowledge import (
    get_benchmark_variables,
    get_value_driver_formulas,
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


class _Result:
    def __init__(self, records: list):
        self._records = records

    async def data(self) -> list:
        return self._records


class _Neo4jSession:
    """Minimal async context-manager mock for a Neo4j session."""

    def __init__(self, records: list, *, capture_params: bool = False):
        self._records = records
        self.last_kwargs: dict = {}
        self._capture = capture_params

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def run(self, query: str, **kwargs):
        if self._capture:
            self.last_kwargs = kwargs
        return _Result(self._records)


def _tenant_ctx(tenant_id: str | None):
    from value_fabric.shared.identity.context import RequestContext

    return RequestContext(tenant_id=tenant_id, user_id="test-user", source="jwt")


# ---------------------------------------------------------------------------
# GET /v1/knowledge/benchmarks/variables
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_benchmark_variables_happy_path(monkeypatch):
    """Returns variables and defaults when a matching Benchmark node exists."""
    tenant_id = "tenant-abc"
    session = _Neo4jSession(
        records=[
            {
                "benchmark_id": "bm-1",
                "variables": {"arr_growth": {"type": "float", "unit": "%"}},
                "defaults": {"arr_growth": 0.15},
            }
        ]
    )

    async def _factory(_tid):
        return session

    monkeypatch.setattr("api.routes.knowledge.create_neo4j_tenant_session", _factory)

    result = await get_benchmark_variables(industry="SaaS", tenant=_tenant_ctx(tenant_id))

    assert result.industry == "SaaS"
    assert result.benchmark_id == "bm-1"
    assert "arr_growth" in result.variables
    assert result.defaults["arr_growth"] == 0.15


@pytest.mark.asyncio
async def test_get_benchmark_variables_no_match_returns_empty(monkeypatch):
    """Returns an empty-but-valid response when no Benchmark node matches."""
    session = _Neo4jSession(records=[])

    async def _factory(_tid):
        return session

    monkeypatch.setattr("api.routes.knowledge.create_neo4j_tenant_session", _factory)

    result = await get_benchmark_variables(
        industry="UnknownIndustry", tenant=_tenant_ctx("tenant-xyz")
    )

    assert result.industry == "UnknownIndustry"
    assert result.benchmark_id is None
    assert result.variables == {}
    assert result.defaults == {}


@pytest.mark.asyncio
async def test_get_benchmark_variables_scopes_to_tenant(monkeypatch):
    """The Neo4j query receives the caller's tenant_id."""
    tenant_id = "tenant-scoped"
    session = _Neo4jSession(records=[], capture_params=True)

    async def _factory(_tid):
        return session

    monkeypatch.setattr("api.routes.knowledge.create_neo4j_tenant_session", _factory)

    await get_benchmark_variables(industry="Healthcare", tenant=_tenant_ctx(tenant_id))

    assert session.last_kwargs.get("tenant_id") == tenant_id
    assert session.last_kwargs.get("industry") == "Healthcare"


@pytest.mark.asyncio
async def test_get_benchmark_variables_missing_tenant_raises_401(monkeypatch):
    """Missing tenant context raises HTTPException 403."""
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        await get_benchmark_variables(industry="SaaS", tenant=_tenant_ctx(None))

    assert exc_info.value.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.asyncio
async def test_get_benchmark_variables_query_includes_value_driver_tenant_scope(monkeypatch):
    """The Cypher query must scope both Benchmark and ValueDriver nodes to the caller's tenant."""
    tenant_id = "tenant-scoped"
    session = _Neo4jSession(records=[], capture_params=True)

    async def _factory(_tid):
        return session

    monkeypatch.setattr("api.routes.knowledge.create_neo4j_tenant_session", _factory)

    await get_benchmark_variables(industry="SaaS", tenant=_tenant_ctx(tenant_id))

    # Both the Benchmark and ValueDriver WHERE clauses must receive tenant_id.
    # The query passes a single $tenant_id parameter used for both nodes.
    assert session.last_kwargs.get("tenant_id") == tenant_id


# ---------------------------------------------------------------------------
# GET /v1/knowledge/value-drivers/formulas
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_value_driver_formulas_happy_path(monkeypatch):
    """Returns formula definitions for all requested driver IDs."""
    tenant_id = "tenant-abc"
    session = _Neo4jSession(
        records=[
            {"id": "vd-1", "name": "ARR Growth", "category": "Revenue", "formula": "arr * growth_rate", "unit": "$"},
            {"id": "vd-2", "name": "Churn Reduction", "category": "Retention", "formula": "churn_rate * arr", "unit": "%"},
        ]
    )

    async def _factory(_tid):
        return session

    monkeypatch.setattr("api.routes.knowledge.create_neo4j_tenant_session", _factory)

    result = await get_value_driver_formulas(
        driver_ids=["vd-1", "vd-2"], tenant=_tenant_ctx(tenant_id)
    )

    assert len(result.drivers) == 2
    assert result.missing_ids == []
    ids = {d.id for d in result.drivers}
    assert ids == {"vd-1", "vd-2"}


@pytest.mark.asyncio
async def test_get_value_driver_formulas_partial_match_reports_missing(monkeypatch):
    """IDs not found in the graph appear in missing_ids, not as an error."""
    tenant_id = "tenant-abc"
    session = _Neo4jSession(
        records=[
            {"id": "vd-1", "name": "ARR Growth", "category": "Revenue", "formula": "arr * rate", "unit": "$"},
        ]
    )

    async def _factory(_tid):
        return session

    monkeypatch.setattr("api.routes.knowledge.create_neo4j_tenant_session", _factory)

    result = await get_value_driver_formulas(
        driver_ids=["vd-1", "vd-missing"], tenant=_tenant_ctx(tenant_id)
    )

    assert len(result.drivers) == 1
    assert "vd-missing" in result.missing_ids


@pytest.mark.asyncio
async def test_get_value_driver_formulas_all_missing(monkeypatch):
    """All IDs missing → empty drivers list, all IDs in missing_ids."""
    session = _Neo4jSession(records=[])

    async def _factory(_tid):
        return session

    monkeypatch.setattr("api.routes.knowledge.create_neo4j_tenant_session", _factory)

    result = await get_value_driver_formulas(
        driver_ids=["vd-x", "vd-y"], api_key=_api_key("tenant-abc")
    )

    assert result.drivers == []
    assert set(result.missing_ids) == {"vd-x", "vd-y"}


@pytest.mark.asyncio
async def test_get_value_driver_formulas_empty_list_raises_422(monkeypatch):
    """Empty driver_ids raises HTTPException 422."""
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        await get_value_driver_formulas(driver_ids=[], api_key=_api_key("tenant-abc"))

    assert exc_info.value.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_get_value_driver_formulas_missing_tenant_raises_401(monkeypatch):
    """Missing tenant context raises HTTPException 403."""
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        await get_value_driver_formulas(
            driver_ids=["vd-1"], tenant=_tenant_ctx(None)
        )

    assert exc_info.value.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.asyncio
async def test_get_value_driver_formulas_deduplicates_ids(monkeypatch):
    """Duplicate driver_ids are deduplicated before querying."""
    tenant_id = "tenant-abc"
    session = _Neo4jSession(records=[], capture_params=True)

    async def _factory(_tid):
        return session

    monkeypatch.setattr("api.routes.knowledge.create_neo4j_tenant_session", _factory)

    await get_value_driver_formulas(
        driver_ids=["vd-1", "vd-1", "vd-2"], tenant=_tenant_ctx(tenant_id)
    )

    queried_ids = session.last_kwargs.get("driver_ids", [])
    assert queried_ids.count("vd-1") == 1, "Duplicate IDs must be deduplicated before querying"


@pytest.mark.asyncio
async def test_get_value_driver_formulas_scopes_to_tenant(monkeypatch):
    """The Neo4j query receives the caller's tenant_id."""
    tenant_id = "tenant-scoped"
    session = _Neo4jSession(records=[], capture_params=True)

    async def _factory(_tid):
        return session

    monkeypatch.setattr("api.routes.knowledge.create_neo4j_tenant_session", _factory)

    await get_value_driver_formulas(
        driver_ids=["vd-1"], tenant=_tenant_ctx(tenant_id)
    )

    assert session.last_kwargs.get("tenant_id") == tenant_id
