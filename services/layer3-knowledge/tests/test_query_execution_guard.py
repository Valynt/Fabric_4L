from __future__ import annotations

"""Regression coverage for Layer 3 query execution tenant fail-closed behavior."""


import pytest
from value_fabric.shared.identity.isolation import QueryScope

from src.db.query_execution import (
    MAX_QUERY_DEPTH,
    CypherDepthLimitExceeded,
    CypherInjectionDetected,
    DangerousProcedureBlockedError,
    MissingTenantContextError,
    TenantExecutionContext,
    TenantParameterMismatchError,
    TenantQueryExecutor,
    TenantQueryValidationError,
    UnscopedTenantLabelError,
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
async def test_run_tenant_query_rejects_tenant_owned_label_without_tenant_predicate() -> (
    None
):
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
    assert (
        sanitize_query_timeout_seconds("not-a-number") == DEFAULT_QUERY_TIMEOUT_SECONDS
    )


@pytest.mark.asyncio
async def test_run_tenant_query_rejects_workflow_label_without_tenant_predicate() -> (
    None
):
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
async def test_detects_multiple_statements_cypher_injection() -> None:
    class FakeSession:
        async def run(self, query, params):
            raise AssertionError("injected multi-statement must be blocked")

    with pytest.raises(CypherInjectionDetected) as exc_info:
        await run_tenant_query(
            FakeSession(),
            "MATCH (e:Entity {tenant_id: $tenant_id}) RETURN e; MATCH (n) DETACH DELETE n",
            {"tenant_id": "tenant-a"},
            tenant_id="tenant-a",
        )
    assert exc_info.value.code == "CYPHER_INJECTION_DETECTED"


@pytest.mark.asyncio
async def test_detects_injection_with_comment_hiding_second_statement() -> None:
    class FakeSession:
        async def run(self, query, params):
            raise AssertionError("injected statement must be blocked")

    with pytest.raises(CypherInjectionDetected):
        await run_tenant_query(
            FakeSession(),
            "MATCH (e:Entity {tenant_id: $tenant_id}) RETURN e; /* comment */ MATCH (n) RETURN n",
            {"tenant_id": "tenant-a"},
            tenant_id="tenant-a",
        )


@pytest.mark.asyncio
async def test_blocks_dangerous_procedures() -> None:
    class FakeSession:
        async def run(self, query, params):
            raise AssertionError("dangerous procedure must be blocked")

    with pytest.raises(DangerousProcedureBlockedError) as exc_info:
        await run_tenant_query(
            FakeSession(),
            "CALL dbms.security.createUser('attacker', 'pass', false)",
            {"tenant_id": "tenant-a"},
            tenant_id="tenant-a",
        )
    assert exc_info.value.code == "DANGEROUS_PROCEDURE_BLOCKED"

    with pytest.raises(DangerousProcedureBlockedError):
        await run_tenant_query(
            FakeSession(),
            "CALL apoc.custom.declareProcedure('evil()', 'RETURN 1')",
            {"tenant_id": "tenant-a"},
            tenant_id="tenant-a",
        )


@pytest.mark.asyncio
async def test_blocks_nested_parameter_tenant_mismatch() -> None:
    class FakeSession:
        async def run(self, query, params):
            raise AssertionError("mismatched parameter must be blocked")

    with pytest.raises(TenantParameterMismatchError) as exc_info:
        await run_tenant_query(
            FakeSession(),
            "MATCH (e:Entity {tenant_id: $tenant_id}) WHERE e.filter = $filter.val RETURN e",
            {
                "tenant_id": "tenant-a",
                "filter": {"tenant_id": "tenant-b", "val": 123},
            },
            tenant_id="tenant-a",
        )
    assert exc_info.value.code == "TENANT_PARAM_MISMATCH"


@pytest.mark.asyncio
async def test_blocks_map_parameter_tenant_mismatch() -> None:
    class FakeSession:
        async def run(self, query, params):
            raise AssertionError("mismatched map parameter must be blocked")

    with pytest.raises(TenantParameterMismatchError):
        await run_tenant_query(
            FakeSession(),
            "MATCH (e:Entity $props) RETURN e",
            {
                "props": {"tenant_id": "tenant-b", "name": "foo"},
            },
            tenant_id="tenant-a",
        )


@pytest.mark.asyncio
async def test_missing_tenant_context_raises_specialized_error() -> None:
    class FakeSession:
        async def run(self, query, params):
            raise AssertionError("missing tenant must be blocked")

    with pytest.raises(MissingTenantContextError) as exc_info:
        await run_tenant_query(
            FakeSession(),
            "MATCH (e:Entity {tenant_id: $tenant_id}) RETURN e",
            {"tenant_id": "tenant-a"},
            tenant_id=None,
        )
    assert exc_info.value.code == "MISSING_TENANT_CONTEXT"


@pytest.mark.asyncio
async def test_unscoped_tenant_label_in_subquery_is_rejected() -> None:
    class FakeSession:
        async def run(self, query, params):
            raise AssertionError("unscoped subquery must be blocked")

    with pytest.raises(UnscopedTenantLabelError) as exc_info:
        await run_tenant_query(
            FakeSession(),
            "CALL { MATCH (e:Entity) RETURN e } RETURN count(e)",
            {"tenant_id": "tenant-a"},
            tenant_id="tenant-a",
        )
    assert exc_info.value.code == "UNSCOPED_TENANT_LABEL"


@pytest.mark.asyncio
async def test_execute_with_timeout_success() -> None:
    async def fake_run(q, p):
        return ["record1"]

    res, elapsed = await TenantQueryExecutor._execute_with_timeout(
        fake_run, "RETURN 1", {}
    )
    assert res == ["record1"]
    assert elapsed >= 0.0


def test_record_query_metrics_safe_without_metrics() -> None:
    # Should not raise exception
    TenantQueryExecutor._record_query_metrics(1.5, ["rec1", "rec2"])
