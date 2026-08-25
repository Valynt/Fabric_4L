from __future__ import annotations

"""Regression coverage for Layer 3 query execution tenant fail-closed behavior."""


import pytest
from value_fabric.shared.identity.isolation import QueryScope

from src.db.query_execution import (
    CypherDepthLimitExceeded,
    MAX_QUERY_DEPTH,
    TenantExecutionContext,
    TenantQueryExecutor,
    TenantQueryValidationError,
    run_system_query,
    run_tenant_query,
)
from src.graph.query_guards import (
    DEFAULT_MAX_QUERY_DEPTH,
    DEFAULT_QUERY_TIMEOUT_SECONDS,
    sanitize_query_depth,
    sanitize_query_timeout_seconds,
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


def test_extract_max_depth_returns_literal_when_param_missing() -> None:
    """Unresolvable $param is skipped; the literal part is still extracted."""
    query = "MATCH path = (a)-[*1..$missing]->(b) RETURN path"
    assert TenantQueryExecutor._extract_max_depth(query, {}) == 1


def test_extract_max_depth_returns_none_for_pure_param_no_literal() -> None:
    """Pure $param with no literal fallback returns None when missing."""
    query = "MATCH path = (a)-[*$missing]->(b) RETURN path"
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


def test_sanitize_query_depth_clamps_hostile_value() -> None:
    """Out-of-policy depth is clamped to centralized max depth."""
    assert sanitize_query_depth(DEFAULT_MAX_QUERY_DEPTH + 99) == DEFAULT_MAX_QUERY_DEPTH


def test_sanitize_query_timeout_falls_back_on_invalid_input() -> None:
    """Invalid timeout input fails closed to the centralized safe default."""
    assert sanitize_query_timeout_seconds("not-a-number") == DEFAULT_QUERY_TIMEOUT_SECONDS


@pytest.mark.asyncio
async def test_run_tenant_query_rejects_workflow_label_without_tenant_predicate() -> None:
    """Workflow must be recognized as a tenant-owned label (regression for missing-label drift)."""

    class FakeSession:
        async def run(self, query, params):  # pragma: no cover
            raise AssertionError("unsafe query must be blocked before execution")

    with pytest.raises(TenantQueryValidationError, match="missing tenant scoping"):
        await run_tenant_query(
            FakeSession(),
            "MATCH (w:Workflow) WHERE w.id = $workflow_id RETURN w",
            {"workflow_id": "wf-1"},
            tenant_id="tenant-a",
        )


@pytest.mark.asyncio
async def test_execute_with_timeout_success() -> None:
    async def fake_run(q, p):
        return ["record1"]

    res, elapsed = await TenantQueryExecutor._execute_with_timeout(fake_run, "RETURN 1", {})
    assert res == ["record1"]
    assert elapsed >= 0.0


def test_record_query_metrics_safe_without_metrics() -> None:
    # Should not raise exception
    TenantQueryExecutor._record_query_metrics(1.5, ["rec1", "rec2"])
