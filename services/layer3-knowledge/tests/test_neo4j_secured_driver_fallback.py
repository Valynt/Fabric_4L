"""Regression protection: the secured Neo4j dependency fallback must call
the canonical ``get_neo4j_driver`` with the active request.

Failure mode covered: the fallback in
``dependencies_tenant_secured.get_neo4j_secured`` called
``get_neo4j_driver()`` with no arguments even though the canonical provider
requires the ``Request``; the TypeError was swallowed and surfaced as a false
503 "Neo4j service unavailable" on a healthy database (observed via the
Meridian certification journey, 2026-08-12).
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi import Request

from src.api.dependencies_tenant_secured import get_neo4j_secured


def _make_request(app_state_driver=None) -> Request:
    app = MagicMock()
    app.state.neo4j_driver = app_state_driver
    scope = {"type": "http", "app": app, "headers": []}
    return Request(scope)


@pytest.mark.asyncio
async def test_secured_session_fallback_passes_request_to_driver_provider() -> None:
    """When app.state.neo4j_driver is unset, the fallback must not raise
    TypeError/503 for a healthy driver available via the canonical provider."""
    from src.api import dependencies as deps

    canonical_driver = MagicMock()
    original = deps.get_neo4j_driver
    deps.get_neo4j_driver = lambda request: canonical_driver
    try:
        session = await get_neo4j_secured(
            _make_request(app_state_driver=None),
            context=MagicMock(tenant_id="11111111-1111-4111-8111-111111111111"),
        )
        assert session is not None
    finally:
        deps.get_neo4j_driver = original


@pytest.mark.asyncio
async def test_secured_session_uses_app_state_driver_when_present() -> None:
    driver = MagicMock()
    session = await get_neo4j_secured(
        _make_request(app_state_driver=driver),
        context=MagicMock(tenant_id="11111111-1111-4111-8111-111111111111"),
    )
    assert session is not None
    # Regression: the dependency must eagerly initialize the underlying
    # driver session, or the first run() fails with HTTP 500
    # "Neo4j session not initialized".
    assert session._session is not None


@pytest.mark.asyncio
async def test_builder_produced_multi_clause_query_executes_with_tenant_predicates() -> None:
    """Regression: a canonical TenantScopedCypher-produced query using
    CALL {} / multiple MATCH clauses (e.g. the entity-list count+page query)
    must execute when every tenant-owned label carries an explicit tenant
    predicate. The secured session previously dropped the multi-clause
    opt-in, so the canonical entity-list route failed with HTTP 500 on a
    healthy graph (observed via the Meridian certification journey).
    """
    from src.api.dependencies_tenant_secured import Neo4jTenantSessionSecured

    class _FakeResult:
        def __aiter__(self):
            return self

        async def __anext__(self):
            raise StopAsyncIteration

    class _FakeSession:
        def __init__(self):
            self.queries = []

        async def run(self, query, params=None, **kwargs):
            self.queries.append(str(query))
            return _FakeResult()

        async def close(self):
            return None

    fake_session = _FakeSession()
    driver = MagicMock()
    driver.session.return_value = fake_session

    session = Neo4jTenantSessionSecured(
        driver=driver, tenant_id="11111111-1111-4111-8111-111111111111"
    )
    await session.__aenter__()

    from src.db.cypher_execution_helper import TenantScopedCypher

    builder = TenantScopedCypher("11111111-1111-4111-8111-111111111111")
    scoped = builder.custom_tenant_query(
        """
        CALL {
            MATCH (e:Entity)
            WHERE e.tenant_id = $_tenant_id
            RETURN count(e) as total
        }
        MATCH (e:Entity)
        WHERE e.tenant_id = $_tenant_id
        RETURN e.id as id, total
        """,
        params={},
        operation="entity_list",
        labels=("Entity",),
    )
    # Must not raise TenantQueryValidationError
    await session.run(scoped, {})
    await session.close()


@pytest.mark.asyncio
async def test_multi_clause_query_without_tenant_predicate_still_denied() -> None:
    """Hostile path: a multi-clause query touching tenant-owned labels with
    NO tenant predicate must still be rejected even with the builder opt-in.
    """
    from src.api.dependencies_tenant_secured import Neo4jTenantSessionSecured
    from src.security.query_validator import UnscopedQueryError

    class _FakeSession:
        async def run(self, query, params=None, **kwargs):
            raise AssertionError("denied query must never reach the driver")

        async def close(self):
            return None

    driver = MagicMock()
    driver.session.return_value = _FakeSession()

    session = Neo4jTenantSessionSecured(
        driver=driver, tenant_id="11111111-1111-4111-8111-111111111111"
    )
    await session.__aenter__()

    from src.db.cypher_execution_helper import TenantScopedCypher

    builder = TenantScopedCypher("11111111-1111-4111-8111-111111111111")
    # The canonical builder refuses predicate-less tenant queries at
    # construction; if that guard is ever bypassed, the executor must still
    # deny at run time.
    with pytest.raises(ValueError, match="tenant parameter"):
        builder.custom_tenant_query(
            """
            CALL {
                MATCH (e:Entity)
                RETURN count(e) as total
            }
            MATCH (e:Entity)
            RETURN e.id as id, total
            """,
            params={},
            operation="entity_list",
            labels=("Entity",),
        )
    await session.close()
