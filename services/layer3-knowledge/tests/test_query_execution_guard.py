"""Regression coverage for Layer 3 query execution tenant fail-closed behavior."""

from __future__ import annotations

import pytest
from value_fabric.shared.identity.isolation import QueryScope

from db.query_execution import (
    CypherDepthLimitExceeded,
    MAX_QUERY_DEPTH,
    TenantExecutionContext,
    TenantQueryExecutor,
    TenantQueryValidationError,
    run_system_query,
    run_tenant_query,
)


@pytest.mark.asyncio
async def test_run_tenant_query_rejects_tenant_owned_label_without_tenant_predicate() -> None:
    class FakeSession:
        async def run(self, query, params):  # pragma: no cover
            raise AssertionError("unsafe query must be blocked before execution")

    with pytest.raises(TenantQueryValidationError, match="missing tenant scoping"):
        await run_tenant_query(
            FakeSession(),
            "MATCH (e:Entity) WHERE e.id = $entity_id RETURN e",
            {"entity_id": "ent-1"},
            tenant_id="tenant-a",
        )


@pytest.mark.asyncio
async def test_run_system_query_rejects_non_allowlisted_scope() -> None:
    class FakeSession:
        async def run(self, query, params):  # pragma: no cover
            raise AssertionError("invalid scope must be blocked before execution")

    with pytest.raises(TenantQueryValidationError, match="Unsupported system scope"):
        await run_system_query(
            FakeSession(),
            "RETURN 1 as ok",
            scope=QueryScope.TENANT,
        )


def test_extract_max_depth_with_literal_bounds() -> None:
    """Literal depth bounds are parsed correctly."""
    query = "MATCH path = (a)-[*1..5]->(b) RETURN path"
    assert TenantQueryExecutor._extract_max_depth(query, {}) == 5


def test_extract_max_depth_with_parametrized_bound() -> None:
    """Parameterized $depth is resolved from the params mapping."""
    query = "MATCH path = (a)-[*1..$depth]->(b) RETURN path"
    assert TenantQueryExecutor._extract_max_depth(query, {"depth": 7}) == 7


def test_extract_max_depth_with_parametrized_start_and_end() -> None:
    """Mixed literal and parameterized bounds are resolved."""
    query = "MATCH path = (a)-[*1..$max_depth]->(b) RETURN path"
    assert TenantQueryExecutor._extract_max_depth(query, {"max_depth": 4}) == 4


def test_extract_max_depth_returns_none_when_param_missing() -> None:
    """Unresolvable $param returns None rather than crashing."""
    query = "MATCH path = (a)-[*1..$missing]->(b) RETURN path"
    assert TenantQueryExecutor._extract_max_depth(query, {}) is None


def test_extract_max_depth_raises_when_param_exceeds_limit() -> None:
    """CypherDepthLimitExceeded is raised when resolved param exceeds MAX_QUERY_DEPTH."""
    query = "MATCH path = (a)-[*1..$depth]->(b) RETURN path"
    with pytest.raises(CypherDepthLimitExceeded):
        TenantQueryExecutor._validate(
            query,
            {"depth": MAX_QUERY_DEPTH + 1},
            TenantExecutionContext(tenant_id="tenant-a"),
        )
