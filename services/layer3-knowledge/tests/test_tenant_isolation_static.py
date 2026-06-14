from __future__ import annotations

"""Static tenant-isolation gates for Layer 3 Neo4j Cypher usage."""


from importlib import import_module
import subprocess
import sys
from pathlib import Path

import pytest

from src.security.query_validator import UnscopedQueryError


REPO_ROOT = Path(__file__).resolve().parents[3]
SERVICE_SRC = REPO_ROOT / "services" / "layer3-knowledge" / "src"
SHARED_SRC = REPO_ROOT / "packages" / "shared" / "src"

for import_root in (str(SHARED_SRC), str(SERVICE_SRC)):
    if import_root not in sys.path:
        sys.path.insert(0, import_root)


def _run_cypher_scope_guard(*paths: str) -> subprocess.CompletedProcess[str]:
    script = REPO_ROOT / "scripts" / "check_layer3_cypher_scope.py"
    command = [
        sys.executable,
        str(script),
        "--root",
        str(REPO_ROOT),
    ]
    if paths:
        command.extend(["--paths", *paths])
    command.append("--warnings-as-errors")

    return subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_layer3_cypher_scope_static_guard_passes() -> None:
    """The historical migrated-module scope gate must remain clean."""

    migrated_roots = [
        "services/layer3-knowledge/src/analytics",
        "services/layer3-knowledge/src/retrieval",
        "value_fabric/layer3/analytics",
        "value_fabric/layer3/retrieval",
    ]

    result = _run_cypher_scope_guard(*migrated_roots)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "0 error(s)" in result.stdout
    assert "0 warning(s)" in result.stdout


def test_broad_layer3_cypher_scope_static_guard_passes() -> None:
    """The broad/default Layer 3 Cypher scanner is the production tenant-isolation gate."""

    result = _run_cypher_scope_guard()

    assert result.returncode == 0, result.stdout + result.stderr
    assert "0 error(s)" in result.stdout
    assert "0 warning(s)" in result.stdout


def test_tenant_label_registry_has_schema_constraint_and_index_coverage() -> None:
    """Every registered tenant-owned node label must have schema guardrails."""

    from value_fabric.shared.identity.isolation import DEFAULT_TENANT_LABEL_POLICY

    constraints_module = import_module("src.schema.constraints")
    CONSTRAINTS = constraints_module.CONSTRAINTS
    INDEXES = constraints_module.INDEXES
    TENANT_CONSTRAINTS = constraints_module.TENANT_CONSTRAINTS

    required_labels = {
        "Account",
        "Prospect",
        "Company",
        "Contact",
        "Stakeholder",
        "Signal",
        "Evidence",
        "ValueDriver",
        "ValueLever",
        "ValueTree",
        "Formula",
        "BusinessCase",
        "Opportunity",
        "Document",
        "Chunk",
        "Entity",
    }
    labels = set(DEFAULT_TENANT_LABEL_POLICY.tenant_labels)

    assert required_labels <= labels
    assert not (labels & DEFAULT_TENANT_LABEL_POLICY.global_labels)

    composite_constraint_labels = {
        constraint.entity_type
        for constraint in CONSTRAINTS
        if constraint.constraint_type == "unique"
        and isinstance(constraint.property_name, list)
        and "tenant_id" in constraint.property_name
        and ("id" in constraint.property_name or "model_id" in constraint.property_name)
    }
    tenant_exists_labels = {
        constraint.entity_type
        for constraint in TENANT_CONSTRAINTS
        if constraint.constraint_type == "exists" and constraint.property_name == "tenant_id"
    }
    tenant_index_labels = {
        index.entity_type
        for index in INDEXES
        if tuple(index.properties) == ("tenant_id",)
    }
    tenant_lookup_index_labels = {
        index.entity_type
        for index in INDEXES
        if tuple(index.properties) in {("tenant_id", "id"), ("tenant_id", "model_id")}
    }

    missing_constraints = labels - composite_constraint_labels
    missing_exists = labels - tenant_exists_labels
    missing_tenant_indexes = labels - tenant_index_labels
    missing_lookup_indexes = labels - tenant_lookup_index_labels

    assert not missing_constraints, f"missing composite constraints: {sorted(missing_constraints)}"
    assert not missing_exists, f"missing Enterprise tenant existence constraints: {sorted(missing_exists)}"
    assert not missing_tenant_indexes, f"missing tenant_id indexes: {sorted(missing_tenant_indexes)}"
    assert not missing_lookup_indexes, f"missing tenant lookup indexes: {sorted(missing_lookup_indexes)}"


@pytest.mark.asyncio
async def test_neo4j_tenant_session_rejects_unscoped_raw_tenant_cypher() -> None:
    """The legacy session wrapper must fail closed for raw tenant-owned Cypher."""

    from src.api.dependencies_tenant import Neo4jTenantSession

    class FakeSession:
        async def run(self, query, params):  # pragma: no cover - should not be reached
            raise AssertionError(f"unsafe query unexpectedly executed: {query} {params}")

    tenant_session = Neo4jTenantSession(
        object(), tenant_id="tenant-a", session=FakeSession()
    )

    with pytest.raises(
        (ValueError, UnscopedQueryError), match="tenant isolation validation|explicit tenant predicates"
    ):
        await tenant_session.run("MATCH (a:Account) RETURN a")


@pytest.mark.asyncio
async def test_neo4j_tenant_session_executes_scoped_query_with_tenant_params() -> None:
    """Builder-created scoped queries remain the preferred execution boundary."""

    from src.api.dependencies_tenant import Neo4jTenantSession
    from value_fabric.shared.identity.isolation import QueryScope, ScopedQuery

    class FakeSession:
        def __init__(self) -> None:
            self.calls: list[tuple[str, dict]] = []

        async def run(self, query, params):
            self.calls.append((query, params))
            return []

    fake_session = FakeSession()
    tenant_session = Neo4jTenantSession(
        object(), tenant_id="tenant-a", session=fake_session
    )
    scoped_query = ScopedQuery(
        cypher="MATCH (a:Account {tenant_id: $tenant_id}) WHERE a.id = $id RETURN a",
        params={"id": "shared-id"},
        scope=QueryScope.TENANT,
        tenant_id="tenant-a",
        operation="test_lookup",
        labels=("Account",),
    )

    await tenant_session.run(scoped_query)

    assert fake_session.calls == [
        (
            "MATCH (a:Account {tenant_id: $tenant_id}) WHERE a.id = $id RETURN a",
            {"id": "shared-id", "tenant_id": "tenant-a", "_tenant_id": "tenant-a"},
        )
    ]


@pytest.mark.asyncio
async def test_neo4j_tenant_session_denies_broad_match_without_tenant_constraint() -> None:
    from src.api.dependencies_tenant import Neo4jTenantSession

    class FakeSession:
        async def run(self, query, params):  # pragma: no cover
            raise AssertionError("query should have been blocked")

    tenant_session = Neo4jTenantSession(
        object(), tenant_id="tenant-a", session=FakeSession()
    )

    with pytest.raises((ValueError, UnscopedQueryError), match="Denied broad MATCH traversal"):
        await tenant_session.run("MATCH (n) RETURN n LIMIT 1")
