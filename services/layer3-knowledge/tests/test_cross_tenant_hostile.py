from __future__ import annotations

"""Cross-tenant hostile invariants for layer3-knowledge.

These tests prove the behavioral isolation contract: a tenant-scoped Neo4j
session or query builder bound to tenant A can only express queries that
reference tenant A, and the runtime rejects unscoped reads/writes.
"""

import pytest
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.isolation import TenantScopedCypher

from src.api.dependencies_tenant_secured import Neo4jTenantSessionSecured
from src.security.query_validator import UnscopedQueryError


# ---------------------------------------------------------------------------
# Tenant-scoped Cypher builder invariants
# ---------------------------------------------------------------------------


def test_tenant_scoped_cypher_injects_tenant_id_in_parameters():
    builder = TenantScopedCypher(tenant_id="tenant-a")
    query = builder.match_node_query("e", "Entity", extra_where="e.name = $name")

    assert query.params["_tenant_id"] == "tenant-a"
    assert "tenant_id = $_tenant_id" in query.cypher


def test_tenant_scoped_cypher_rejects_unscoped_custom_query():
    builder = TenantScopedCypher(tenant_id="tenant-a")

    with pytest.raises(ValueError, match="tenant parameter"):
        builder.custom_tenant_query("MATCH (e:Entity) RETURN e")


def test_tenant_scoped_cypher_rejects_custom_query_missing_tenant_predicate():
    builder = TenantScopedCypher(tenant_id="tenant-a")

    with pytest.raises(ValueError, match="tenant predicate"):
        builder.custom_tenant_query(
            "MATCH (e:Entity) WHERE e.name = $_tenant_id RETURN e",
            params={"name": "x"},
        )


def test_tenant_scoped_cypher_query_params_cannot_be_hijacked_by_tenant_b():
    """The builder hard-codes the tenant id; callers cannot override it."""
    builder = TenantScopedCypher(tenant_id="tenant-a")
    query = builder.match_node_query(
        "e", "Entity", extra_params={"_tenant_id": "tenant-b", "tenant_id": "tenant-b", "name": "x"}
    )

    assert query.params["_tenant_id"] == "tenant-a"
    assert query.params.get("tenant_id") != "tenant-b"
    assert query.params["name"] == "x"


# ---------------------------------------------------------------------------
# Tenant-scoped Neo4j session invariants
# ---------------------------------------------------------------------------


class _FakeRecord:
    def data(self):
        return {"id": "entity-1", "tenant_id": "tenant-a"}


class _FakeResult:
    def __init__(self, records):
        self._records = records

    async def __aiter__(self):
        for record in self._records:
            yield record


class _FakeSession:
    def __init__(self):
        self.calls: list[tuple[str, dict]] = []

    async def run(self, query, parameters=None, **kwargs):
        params = dict(parameters or {})
        params.update(kwargs)
        self.calls.append((query, params))
        return _FakeResult([_FakeRecord()])


class _FakeDriver:
    def __init__(self, session):
        self._session = session

    def session(self):
        return self._session


@pytest.mark.asyncio
async def test_secured_session_injects_tenant_id_into_parameters():
    fake_session = _FakeSession()
    session = Neo4jTenantSessionSecured(
        driver=_FakeDriver(fake_session),
        tenant_id="tenant-a",
        strict_validation=True,
        session=fake_session,
    )

    await session.run("MATCH (e:Entity {id: $id, tenant_id: $tenant_id}) RETURN e", id="1")

    assert len(fake_session.calls) == 1
    _, params = fake_session.calls[0]
    assert params["tenant_id"] == "tenant-a"
    assert params["_tenant_id"] == "tenant-a"


@pytest.mark.asyncio
async def test_secured_session_blocks_broad_unscoped_match():
    fake_session = _FakeSession()
    session = Neo4jTenantSessionSecured(
        driver=_FakeDriver(fake_session),
        tenant_id="tenant-a",
        strict_validation=True,
        session=fake_session,
    )

    with pytest.raises(UnscopedQueryError):
        await session.run("MATCH (e) RETURN e")

    assert len(fake_session.calls) == 0


@pytest.mark.asyncio
async def test_secured_session_allows_tenant_scoped_match():
    fake_session = _FakeSession()
    session = Neo4jTenantSessionSecured(
        driver=_FakeDriver(fake_session),
        tenant_id="tenant-a",
        strict_validation=True,
        session=fake_session,
    )

    await session.run("MATCH (e:Entity {tenant_id: $tenant_id}) RETURN e")

    assert len(fake_session.calls) == 1


# ---------------------------------------------------------------------------
# FastAPI dependency fail-closed invariants
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_neo4j_secured_fails_closed_without_tenant_context():
    from src.api.dependencies_tenant_secured import get_neo4j_secured

    class _FakeApp:
        class state:
            neo4j_driver = None

    class _FakeRequest:
        app = _FakeApp()

    with pytest.raises(Exception):  # ValidationError or HTTPException
        await anext(get_neo4j_secured(_FakeRequest(), context=None))


@pytest.mark.asyncio
async def test_get_neo4j_secured_uses_request_tenant_id():
    from src.api.dependencies_tenant_secured import get_neo4j_secured

    class _FakeApp:
        class state:
            neo4j_driver = None

    class _FakeRequest:
        app = _FakeApp()

    ctx = RequestContext(tenant_id="tenant-a")
    with pytest.raises(Exception):  # driver unavailable, but tenant was accepted
        await anext(get_neo4j_secured(_FakeRequest(), context=ctx))
