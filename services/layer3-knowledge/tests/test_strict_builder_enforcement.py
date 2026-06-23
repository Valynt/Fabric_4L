from __future__ import annotations

"""Strict builder enforcement tests for Layer 3 Neo4j tenant isolation.

These tests encode the application-layer tenant isolation contract used because
Neo4j Community Edition does not provide native row-level security. Tenant-owned
Layer 3 graph queries must carry explicit tenant scope metadata and fail closed
when no tenant context is available.
"""


from types import SimpleNamespace
from uuid import uuid4
from collections.abc import AsyncIterator

import pytest

from src.analytics.centrality import CentralityAnalyzer
from src.analytics.communities import CommunityDetector
from src.analytics.similarity import SimilarityAnalyzer
from src.retrieval.graph_rag import GraphRAGEngine
from src.retrieval.hybrid_search import HybridSearch
from src.retrieval.vector_store import Neo4jVectorStore
from value_fabric.shared.identity.context import (
    RequestContext,
    RequestContextManager,
    clear_current_context,
)
from value_fabric.shared.identity.isolation import (
    DEFAULT_TENANT_LABEL_POLICY,
    QueryScope,
    ScopedQuery,
    SystemCypher,
    TenantLabelPolicy,
    TenantScopedCypher,
)
from src.api.dependencies_tenant import Neo4jTenantSession
from unittest.mock import AsyncMock


def _settings_stub() -> SimpleNamespace:
    """Return the minimal settings object needed by constructor-only tests."""

    return SimpleNamespace(
        neo4j_database="neo4j",
        neo4j_uri="bolt://localhost:7687",
        neo4j_auth=("neo4j", "test"),
        neo4j_max_pool_size=1,
    )


class _AsyncResult(AsyncIterator[dict]):
    """Minimal async Neo4j result iterator for analytics regression tests."""

    def __init__(self, records: list[dict]):
        self._records = records
        self._index = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._index >= len(self._records):
            raise StopAsyncIteration
        current = self._records[self._index]
        self._index += 1
        return current


@pytest.fixture(autouse=True)
def _clear_identity_context():
    """Ensure tenant context does not leak between fail-closed tests."""

    clear_current_context()
    yield
    clear_current_context()


def test_scoped_query_metadata_and_tuple_compatibility() -> None:
    """ScopedQuery must preserve strict metadata while supporting legacy tuples."""

    query = ScopedQuery(
        cypher="MATCH (n:Capability) WHERE n.tenant_id = $_tenant_id RETURN n",
        params={"_tenant_id": "tenant-a", "limit": 10},
        scope=QueryScope.TENANT,
        tenant_id="tenant-a",
        operation="capability_lookup",
        labels=("Capability",),
    )

    cypher, params = query.as_tuple()

    assert cypher == query.cypher
    assert params == {"_tenant_id": "tenant-a", "limit": 10}
    assert params is not query.params
    assert query.scope is QueryScope.TENANT
    assert query.tenant_id == "tenant-a"
    assert query.operation == "capability_lookup"
    assert query.labels == ("Capability",)


def test_tenant_label_policy_covers_registered_labels() -> None:
    """Every registered business-domain label must require tenant scope."""

    policy = DEFAULT_TENANT_LABEL_POLICY

    assert policy.tenant_labels, "tenant-owned label registry must not be empty"
    for label in policy.tenant_labels:
        assert policy.is_tenant_owned(label), f"{label} should be tenant-owned"
        assert policy.requires_scope([label]), f"{label} should require scope"

    for label in policy.global_labels:
        assert not policy.is_tenant_owned(label), f"{label} should be globally reviewed"

    assert not policy.requires_scope([])
    assert not policy.requires_scope(["Migration", "SchemaVersion", "SystemMetadata"])
    assert policy.requires_scope(["Migration", "Capability"])


def test_custom_label_policy_respects_tenant_and_global_sets() -> None:
    """Custom label policies should fail closed only for configured tenant labels."""

    policy = TenantLabelPolicy(
        tenant_labels=frozenset({"TenantOwned"}),
        global_labels=frozenset({"GlobalMetadata"}),
    )

    assert policy.is_tenant_owned("TenantOwned")
    assert policy.requires_scope(["GlobalMetadata", "TenantOwned"])
    assert not policy.is_tenant_owned("GlobalMetadata")
    assert not policy.requires_scope(["GlobalMetadata"])


@pytest.mark.asyncio
async def test_detect_louvain_shapes_valid_communities_without_import_runtime_errors(monkeypatch) -> None:
    """Louvain detection should shape valid communities deterministically."""

    class _FakeSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def run(self, query, params=None):
            if "gds.version" in query:
                return _AsyncResult([])
            if "gds.louvain.stream" in query:
                return _AsyncResult(
                    [
                        {"node": {"id": "n1", "name": "Node 1", "labels": ["Capability"]}, "communityId": 1},
                        {"node": {"id": "n2", "name": "Node 2", "labels": ["Capability"]}, "communityId": 1},
                        {"node": {"id": "n3", "name": "Node 3", "labels": ["UseCase"]}, "communityId": 2},
                    ]
                )
            return _AsyncResult([])

    class _FakeDriver:
        def session(self, database=None):
            return _FakeSession()

    detector = CommunityDetector(driver=_FakeDriver(), settings=_settings_stub())
    monkeypatch.setattr(detector, "_project_graph", AsyncMock(return_value=None))
    monkeypatch.setattr(detector, "_calculate_modularity", AsyncMock(return_value=0.42))

    result = await detector.detect_louvain(min_community_size=2, tenant_id="tenant-a")

    assert result["communities"]
    assert result["valid_communities"] == 1
    assert result["total_communities"] == 2


@pytest.mark.parametrize(
    ("factory", "scope", "operation"),
    [
        (
            lambda: SystemCypher.health_check(
                reason="verify connectivity", allowlist_key="system.health_check.test"
            ),
            QueryScope.HEALTH,
            "health_check",
        ),
        (
            lambda: SystemCypher.schema_operation(
                "CREATE INDEX entity_id IF NOT EXISTS FOR (n:Entity) ON (n.id)",
                reason="ensure reviewed index",
                allowlist_key="schema.entity_id_index",
            ),
            QueryScope.SCHEMA,
            "schema_operation",
        ),
        (
            lambda: SystemCypher.migration(
                "MATCH (m:Migration) RETURN count(m) AS applied",
                reason="read migration ledger",
                allowlist_key="migration.ledger_read",
            ),
            QueryScope.MIGRATION,
            "migration",
        ),
        (
            lambda: SystemCypher.backup(
                "MATCH (m:SystemMetadata) RETURN m",
                reason="backup metadata export",
                allowlist_key="backup.system_metadata",
            ),
            QueryScope.BACKUP,
            "backup",
        ),
    ],
)
def test_system_cypher_factories_require_audited_scope(factory, scope, operation) -> None:
    """SystemCypher factories must emit audited non-tenant metadata objects."""

    query = factory()

    assert isinstance(query, ScopedQuery)
    assert query.scope is scope
    assert query.operation == operation
    assert query.reason
    assert query.allowlist_key
    assert query.tenant_id is None


@pytest.mark.parametrize(
    "build",
    [
        lambda: SystemCypher.schema_operation(
            "CREATE INDEX x IF NOT EXISTS FOR (n:Entity) ON (n.id)",
            reason=" ",
            allowlist_key="schema.x",
        ),
        lambda: SystemCypher.schema_operation(
            "CREATE INDEX x IF NOT EXISTS FOR (n:Entity) ON (n.id)",
            reason="reviewed index",
            allowlist_key="",
        ),
        lambda: SystemCypher.migration(
            "RETURN 1 AS ok", reason="", allowlist_key="migration.invalid"
        ),
        lambda: SystemCypher.backup(
            "RETURN 1 AS ok", reason="backup", allowlist_key="   "
        ),
    ],
)
def test_system_cypher_rejects_missing_audit_fields(build) -> None:
    """Explicit system-scope escape hatches require a reason and allowlist key."""

    with pytest.raises(ValueError):
        build()


@pytest.mark.parametrize(
    "cypher",
    [
        "MATCH (n:Capability) RETURN n",
        "CALL db.index.fulltext.queryNodes('entity', 'finance') YIELD node RETURN node",
        "CREATE (n:Entity {id: 'x'}) RETURN n",
    ],
)
def test_health_check_rejects_unsafe_cypher_patterns(cypher: str) -> None:
    """Health checks may not become unaudited tenant-owned read/write paths."""

    with pytest.raises(ValueError, match="health_check only allows"):
        SystemCypher.health_check(cypher, reason="unsafe", allowlist_key="system.health")


def test_tenant_scoped_builder_injects_tenant_predicates_and_metadata() -> None:
    """Built queries must carry tenant metadata and predicates on tenant nodes."""

    builder = TenantScopedCypher("tenant-a")

    match = builder.match_node_query(
        "n",
        "Capability",
        extra_where="n.status = $status",
        extra_params={"status": "active"},
        return_clause="n.id AS id",
    )
    assert match.scope is QueryScope.TENANT
    assert match.tenant_id == "tenant-a"
    assert match.operation == "match_node"
    assert match.labels == ("Capability",)
    assert "n.tenant_id = $_tenant_id" in match.cypher
    assert match.params == {"_tenant_id": "tenant-a", "status": "active"}

    relationship = builder.match_relationship_query(
        "a",
        "Capability",
        "ENABLES",
        "b",
        "UseCase",
        return_clause="a.id AS source, b.id AS target",
    )
    assert "a.tenant_id = $_tenant_id" in relationship.cypher
    assert "b.tenant_id = $_tenant_id" in relationship.cypher
    assert relationship.labels == ("Capability", "UseCase")

    created = builder.create_node_query("n", "Entity", {"id": "e-1", "name": "Example"})
    assert created.params["_n_tenant_id"] == "tenant-a"
    assert "tenant_id: $_n_tenant_id" in created.cypher


def test_custom_tenant_query_requires_explicit_tenant_parameter_and_predicate() -> None:
    """Complex custom Cypher is allowed only when tenant scope is explicit."""

    builder = TenantScopedCypher("tenant-a")
    scoped = builder.custom_tenant_query(
        """
        MATCH (c:Capability)-[:ENABLES]->(u:UseCase)
        WHERE c.tenant_id = $_tenant_id AND u.tenant_id = $_tenant_id
        RETURN c.id AS capability_id, u.id AS use_case_id
        """,
        params={"limit": 10},
        operation="capability_to_use_case",
        labels=("Capability", "UseCase"),
    )

    assert scoped.scope is QueryScope.TENANT
    assert scoped.params["_tenant_id"] == "tenant-a"
    assert scoped.params["limit"] == 10


@pytest.mark.asyncio
async def test_tenant_session_rejects_raw_cypher_for_tenant_owned_labels() -> None:
    """Tenant-owned raw Cypher reads must carry tenant predicates."""

    session = AsyncMock()
    tenant_session = Neo4jTenantSession(
        driver=AsyncMock(),
        tenant_id="tenant-a",
        session=session,
    )

    with pytest.raises(Exception, match="tenant|scope|Query validation"):
        await tenant_session.run("MATCH (n:Entity) RETURN n")


@pytest.mark.asyncio
async def test_tenant_session_rejects_raw_mutation_for_tenant_owned_labels() -> None:
    """Tenant-owned raw mutations must go through audited mutation helpers."""

    session = AsyncMock()
    tenant_session = Neo4jTenantSession(
        driver=AsyncMock(),
        tenant_id="tenant-a",
        session=session,
    )

    with pytest.raises(Exception, match="Direct CREATE/MERGE/DELETE|AuditedGraphMutation"):
        await tenant_session.run(
            "CREATE (n:Entity {id: $id, tenant_id: $tenant_id}) RETURN n",
            {"id": "entity-1", "tenant_id": "tenant-a"},
        )


def test_explicit_or_context_tenant_resolution_for_migrated_services() -> None:
    """Migrated services should resolve explicit tenants and request-context tenants."""

    services = [
        CentralityAnalyzer(driver=object(), settings=_settings_stub()),
        CommunityDetector(driver=object(), settings=_settings_stub()),
        SimilarityAnalyzer(driver=object(), settings=_settings_stub()),
        GraphRAGEngine(driver=object(), settings=_settings_stub()),
        HybridSearch(driver=object(), settings=_settings_stub()),
        Neo4jVectorStore(driver=object(), settings=_settings_stub()),
    ]

    for service in services:
        assert service._resolve_tenant_id("explicit-tenant") == "explicit-tenant"

    with RequestContextManager(RequestContext(tenant_id="context-tenant")):
        for service in services:
            assert service._resolve_tenant_id() == "context-tenant"


@pytest.mark.parametrize(
    "service",
    [
        CentralityAnalyzer(driver=object(), settings=_settings_stub()),
        CommunityDetector(driver=object(), settings=_settings_stub()),
        SimilarityAnalyzer(driver=object(), settings=_settings_stub()),
        GraphRAGEngine(driver=object(), settings=_settings_stub()),
        HybridSearch(driver=object(), settings=_settings_stub()),
        Neo4jVectorStore(driver=object(), settings=_settings_stub()),
    ],
)
def test_migrated_services_fail_closed_without_tenant_context(service) -> None:
    """Analytics and retrieval services must raise before executing unscoped graph reads."""

    with pytest.raises((RuntimeError, ValueError), match="tenant_id|No RequestContext"):
        service._resolve_tenant_id()


@pytest.mark.asyncio
async def test_scoped_execution_filters_mocked_cross_tenant_data() -> None:
    """The tenant contract should pass tenant params through the execution seam."""

    tenant_a_rows = [{"id": "cap-a", "tenant_id": "tenant-a", "name": "A"}]
    tenant_b_rows = [{"id": "cap-b", "tenant_id": "tenant-b", "name": "B"}]
    all_rows = tenant_a_rows + tenant_b_rows

    class FilteringSession:
        def __init__(self, rows):
            self.rows = rows
            self.calls = []

        async def run(self, cypher, params):
            self.calls.append((cypher, params))
            tenant = params["_tenant_id"]
            return [row for row in self.rows if row["tenant_id"] == tenant]

    query = TenantScopedCypher("tenant-a").match_node_query("n", "Capability")

    for service in (
        CentralityAnalyzer(driver=object(), settings=_settings_stub()),
        SimilarityAnalyzer(driver=object(), settings=_settings_stub()),
    ):
        session = FilteringSession(all_rows)
        result = await service._run_scoped(session, query)

        assert result == tenant_a_rows
        assert tenant_b_rows[0] not in result
        assert session.calls == [
            (query.cypher, {"_tenant_id": "tenant-a", "tenant_id": "tenant-a"})
        ]
        assert "n.tenant_id = $_tenant_id" in session.calls[0][0]
        assert session.calls[0][1]["_tenant_id"] == "tenant-a"
        assert session.calls[0][1]["tenant_id"] == "tenant-a"
