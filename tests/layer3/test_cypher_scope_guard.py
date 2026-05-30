from __future__ import annotations

import re
from pathlib import Path

import pytest

from value_fabric.shared.identity.isolation import QueryScope, ScopedQuery
from src.db.query_execution import (
    TenantExecutionContext,
    TenantQueryExecutor,
    TenantQueryValidationError,
    run_scoped_query,
)
from src.services.cypher_scope_guard import validate_tenant_scoped_cypher


_QUERY_BLOCK = re.compile(r'(?s)(?:query|count_query|list_query)\s*=\s*f?"""(.*?)"""')
_TENANT_OWNED = {
    "Product",
    "Feature",
    "Capability",
    "PainSignal",
    "Competitor",
    "Battlecard",
}


@pytest.mark.parametrize(
    "query",
    [
        "MATCH (p:Product {tenant_id: $tenant_id}) RETURN p",
        "MATCH (p:Product) WHERE p.tenant_id = $tenant_id RETURN p",
        "OPTIONAL MATCH (c:Capability) WHERE c.tenant_id = $tenant_id OR c.tenant_id IS NULL RETURN c",
        "MATCH (n:Industry) RETURN n",
    ],
)
def test_validate_tenant_scoped_cypher_accepts_scoped_or_unowned_queries(query: str) -> None:
    validate_tenant_scoped_cypher(query, tenant_owned_labels=_TENANT_OWNED)


@pytest.mark.parametrize(
    "query",
    [
        "MATCH (p:Product) RETURN p",
        "MATCH (:Product) RETURN count(*)",
        "MATCH (p:Product {id: $product_id}) RETURN p",
        "MATCH (p:Product {tenant_id: $tenant_id}) OPTIONAL MATCH (f:Feature) RETURN f",
    ],
)
def test_validate_tenant_scoped_cypher_rejects_unscoped_tenant_owned_reads(query: str) -> None:
    with pytest.raises(ValueError, match="missing tenant_id filter"):
        validate_tenant_scoped_cypher(query, tenant_owned_labels=_TENANT_OWNED)


@pytest.mark.parametrize(
    "relative_path",
    [
        "value_fabric/layer3/services/product_service.py",
        "value_fabric/layer3/services/competitive_intel_service.py",
        "services/layer3-knowledge/src/services/product_service.py",
        "services/layer3-knowledge/src/services/competitive_intel_service.py",
    ],
)
def test_query_templates_are_tenant_scoped(relative_path: str) -> None:
    content = Path(relative_path).read_text(encoding="utf-8")
    queries = [query for query in _QUERY_BLOCK.findall(content) if "MATCH" in query.upper()]

    if not queries and "Compatibility wrapper for value_fabric.layer3.services." in content:
        assert "from src.services." in content
        return

    assert queries, f"No query templates found in {relative_path}"
    for idx, query in enumerate(queries):
        validate_tenant_scoped_cypher(
            query,
            tenant_owned_labels=_TENANT_OWNED,
            query_name=f"{relative_path}#{idx}",
        )


def test_executor_rejects_marker_only_bypass_pattern_without_per_path_scope() -> None:
    query = "MATCH (p:Capability {tenant_id: $tenant_id}) OPTIONAL MATCH (f:Capability) RETURN p, f"
    with pytest.raises(TenantQueryValidationError, match="missing tenant scoping"):
        TenantQueryExecutor._validate(
            query=query,
            params={"tenant_id": "tenant-a"},
            context=TenantExecutionContext(tenant_id="tenant-a"),
        )


def test_executor_fails_closed_on_ambiguous_multiclause_query() -> None:
    query = "MATCH (a:Capability {tenant_id: $tenant_id}) MATCH (b:Capability {tenant_id: $tenant_id}) RETURN a, b"
    with pytest.raises(TenantQueryValidationError, match="ambiguous or multi-clause"):
        TenantQueryExecutor._validate(
            query=query,
            params={"tenant_id": "tenant-a"},
            context=TenantExecutionContext(tenant_id="tenant-a"),
        )


def test_executor_allows_ambiguous_query_when_explicitly_allowlisted_system_query() -> None:
    query = "MATCH (a:Capability {tenant_id: $tenant_id}) MATCH (b:Capability {tenant_id: $tenant_id}) RETURN a, b"
    TenantQueryExecutor._validate(
        query=query,
        params={"tenant_id": "tenant-a"},
        context=TenantExecutionContext(tenant_id="tenant-a", allow_system_query=True),
    )


@pytest.mark.parametrize(
    "query",
    [
        "MATCH (a:Capability {tenant_id: $tenant_id}) RETURN a UNION MATCH (b:Capability {tenant_id: $tenant_id}) RETURN b",
        "CALL { MATCH (a:Capability {tenant_id: $tenant_id}) RETURN a } RETURN a",
        "MATCH (a:Capability {tenant_id: $tenant_id}) MATCH (b:Capability {tenant_id: $tenant_id}) RETURN a, b",
    ],
)
def test_executor_blocks_union_call_and_multimatch_without_system_opt_in(query: str) -> None:
    with pytest.raises(TenantQueryValidationError, match="ambiguous or multi-clause"):
        TenantQueryExecutor._validate(
            query=query,
            params={"tenant_id": "tenant-a"},
            context=TenantExecutionContext(tenant_id="tenant-a"),
        )


@pytest.mark.asyncio
async def test_run_scoped_query_enforces_tenant_for_tenant_scoped_queries() -> None:
    async def _run(_query: str, _params: dict[str, str]):
        return "ok"

    with pytest.raises(TenantQueryValidationError, match="Tenant context is required"):
        await run_scoped_query(
            _run,
            ScopedQuery(cypher="MATCH (p:Product) RETURN p", scope=QueryScope.TENANT),
        )


@pytest.mark.asyncio
async def test_run_scoped_query_allows_explicit_system_scope() -> None:
    calls: list[tuple[str, dict[str, str]]] = []

    async def _run(query: str, params: dict[str, str]):
        calls.append((query, params))
        return "ok"

    result = await run_scoped_query(
        _run,
        ScopedQuery(cypher="CALL db.labels()", scope=QueryScope.SCHEMA, allowlist_key="test.schema"),
    )

    assert result == "ok"
    assert calls == [("CALL db.labels()", {})]
