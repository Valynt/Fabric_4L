from __future__ import annotations

"""Regression tests for the Layer 3 approved Neo4j execution boundary."""


import ast
import subprocess
import sys
from pathlib import Path

import pytest

from src.db.query_execution import TenantQueryValidationError, run_validated_query


REPO_ROOT = Path(__file__).resolve().parents[3]
HIGH_RISK_RUNTIME_ROOTS = (
    REPO_ROOT / "services" / "layer3-knowledge" / "src" / "api",
    REPO_ROOT / "services" / "layer3-knowledge" / "src" / "ingestion",
    REPO_ROOT / "services" / "layer3-knowledge" / "src" / "analytics",
    REPO_ROOT / "services" / "layer3-knowledge" / "src" / "agents",
)
SCANNER = REPO_ROOT / "scripts" / "check_layer3_cypher_scope.py"
QUERY_ENTRYPOINT_SCANNER = REPO_ROOT / "scripts" / "ci" / "check_layer3_query_entrypoints.py"
ALLOWED_SYSTEM_SCOPED_PATH_FRAGMENTS = (
    "services/layer3-knowledge/src/schema/",
    "services/layer3-knowledge/src/migrations/",
    "services/layer3-knowledge/src/bootstrap/",
)
TENANT_GATEWAY_TARGETS = (
    REPO_ROOT / "services" / "layer3-knowledge" / "src" / "api" / "routes" / "analytics.py",
    REPO_ROOT / "services" / "layer3-knowledge" / "src" / "api" / "routes" / "evidence.py",
    REPO_ROOT / "services" / "layer3-knowledge" / "src" / "api" / "routes" / "value_packs.py",
    REPO_ROOT / "services" / "layer3-knowledge" / "src" / "agents" / "provenance_tracking.py",
    REPO_ROOT / "services" / "layer3-knowledge" / "src" / "agents" / "roi_calculation.py",
    REPO_ROOT / "services" / "layer3-knowledge" / "src" / "agents" / "value_tree_projection.py",
    REPO_ROOT / "services" / "layer3-knowledge" / "src" / "agents" / "whitespace_analysis.py",
    REPO_ROOT / "services" / "layer3-knowledge" / "src" / "analytics" / "centrality.py",
    REPO_ROOT / "services" / "layer3-knowledge" / "src" / "analytics" / "communities.py",
    REPO_ROOT / "services" / "layer3-knowledge" / "src" / "db" / "audited_mutation.py",
    REPO_ROOT / "services" / "layer3-knowledge" / "src" / "ingestion" / "sync_manager.py",
    REPO_ROOT / "services" / "layer3-knowledge" / "src" / "services" / "case_study_service.py",
    REPO_ROOT / "services" / "layer3-knowledge" / "src" / "services" / "competitive_intel_service.py",
    REPO_ROOT / "services" / "layer3-knowledge" / "src" / "services" / "entity_resolution.py",
    REPO_ROOT / "services" / "layer3-knowledge" / "src" / "services" / "evidence_search.py",
    REPO_ROOT / "services" / "layer3-knowledge" / "src" / "services" / "product_service.py",
    REPO_ROOT / "services" / "layer3-knowledge" / "src" / "services" / "roi_calculator_service.py",
    REPO_ROOT / "services" / "layer3-knowledge" / "src" / "services" / "signal_persistence.py",
    REPO_ROOT / "services" / "layer3-knowledge" / "src" / "services" / "signal_quantification.py",
)


class _DirectNeo4jRunVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.violations: list[tuple[int, int]] = []

    @staticmethod
    def _owner_name(node: ast.AST) -> str | None:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return node.attr
        return None

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802 - ast visitor hook
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr in {"run", "execute_query"}:
            owner = self._owner_name(func.value)
            if owner in {"session", "raw_session", "tx", "transaction"}:
                self.violations.append((node.lineno, node.col_offset))
        self.generic_visit(node)


class _RunValidatedQueryVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.violations: list[tuple[int, int, str]] = []

    @staticmethod
    def _is_run_validated_query(node: ast.Call) -> bool:
        func = node.func
        return (
            isinstance(func, ast.Name)
            and func.id == "run_validated_query"
            or isinstance(func, ast.Attribute)
            and func.attr == "run_validated_query"
        )

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802 - ast visitor hook
        if not self._is_run_validated_query(node):
            self.generic_visit(node)
            return

        keywords = {kw.arg for kw in node.keywords if kw.arg is not None}
        if "allow_system_query" in keywords:
            if "query_name" not in keywords:
                self.violations.append(
                    (node.lineno, node.col_offset, "system query missing query_name")
                )
            self.generic_visit(node)
            return

        if "tenant_id" not in keywords:
            self.violations.append((node.lineno, node.col_offset, "missing tenant_id kwarg"))
        if "require_explicit_tenant_id" not in keywords:
            self.violations.append(
                (node.lineno, node.col_offset, "missing require_explicit_tenant_id marker")
            )
        if "query_name" not in keywords:
            self.violations.append((node.lineno, node.col_offset, "missing query_name"))
        self.generic_visit(node)


def test_high_risk_runtime_modules_do_not_call_neo4j_run_directly() -> None:
    """Runtime modules must enter Neo4j through approved execution wrappers."""

    violations: list[str] = []
    for root in HIGH_RISK_RUNTIME_ROOTS:
        for path in root.rglob("*.py"):
            rel = path.relative_to(REPO_ROOT).as_posix()
            if any(rel.startswith(fragment) for fragment in ALLOWED_SYSTEM_SCOPED_PATH_FRAGMENTS):
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            visitor = _DirectNeo4jRunVisitor()
            visitor.visit(tree)
            for line, col in visitor.violations:
                violations.append(f"{rel}:{line}:{col}")

    assert not violations, "direct Neo4j run calls found:\n" + "\n".join(violations)


def test_layer3_tenant_gateway_targets_forward_authenticated_tenant_explicitly() -> None:
    """Audited route/ingestion reads must not rely on tenant_id embedded in params only."""

    violations: list[str] = []
    for path in TENANT_GATEWAY_TARGETS:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        visitor = _RunValidatedQueryVisitor()
        visitor.visit(tree)
        rel = path.relative_to(REPO_ROOT).as_posix()
        for line, col, reason in visitor.violations:
            violations.append(f"{rel}:{line}:{col}: {reason}")

    assert not violations, "tenant gateway calls missing explicit audit context:\n" + "\n".join(violations)


@pytest.mark.mandatory
def test_layer3_scanner_blocks_direct_session_run_in_high_risk_runtime() -> None:
    """Static scanner must fail CI if high-risk runtime modules call session.run directly."""

    result = subprocess.run(
        [
            sys.executable,
            str(SCANNER),
            "--root",
            str(REPO_ROOT),
            "--paths",
            "services/layer3-knowledge/src/api",
            "services/layer3-knowledge/src/ingestion",
            "services/layer3-knowledge/src/analytics",
            "services/layer3-knowledge/src/agents",
            "--warnings-as-errors",
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + "\n" + result.stderr




@pytest.mark.mandatory
def test_layer3_query_entrypoint_matrix_blocks_direct_session_run_in_runtime() -> None:
    """CI entrypoint matrix must fail if L3 runtime code calls session.run directly."""

    result = subprocess.run(
        [
            sys.executable,
            str(QUERY_ENTRYPOINT_SCANNER),
            "services/layer3-knowledge/src/api",
            "services/layer3-knowledge/src/ingestion",
            "services/layer3-knowledge/src/analytics",
            "services/layer3-knowledge/src/agents",
            "--report-json",
            "artifacts/test-layer3-query-entrypoint-matrix.json",
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + "\n" + result.stderr


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("query", "expected_error"),
    [
        ("MATCH (e:Entity) RETURN e", "missing tenant scoping"),
        ("MATCH (p:Product {id: $id}) RETURN p", "missing tenant scoping"),
        (
            "MATCH (e:Evidence)-[:SUPPORTS]->(d:ValueDriver {tenant_id: $tenant_id}) RETURN e, d",
            "missing tenant scoping",
        ),
        ("CREATE (e:Evidence {id: $id}) RETURN e", "Direct CREATE"),
    ],
)
async def test_tenant_owned_label_queries_fail_closed_without_tenant_predicates(
    query: str, expected_error: str
) -> None:
    """Tenant-owned labels require explicit tenant predicates before execution."""

    class FakeSession:
        async def run(self, query, params):  # pragma: no cover - must not execute
            raise AssertionError(f"unsafe query unexpectedly executed: {query} {params}")

    with pytest.raises(TenantQueryValidationError, match=expected_error):
        await run_validated_query(
            FakeSession(),
            query,
            {"id": "shared-id"},
            tenant_id="tenant-a",
        )


@pytest.mark.asyncio
async def test_tenant_owned_label_queries_fail_closed_without_tenant_context() -> None:
    """Tenant predicates alone are insufficient without an execution tenant."""

    class FakeSession:
        async def run(self, query, params):  # pragma: no cover - must not execute
            raise AssertionError(f"tenantless query unexpectedly executed: {query} {params}")

    with pytest.raises(TenantQueryValidationError, match="Tenant context is required"):
        await run_validated_query(
            FakeSession(),
            "MATCH (e:Entity {tenant_id: $tenant_id}) RETURN e",
            {},
        )


@pytest.mark.asyncio
async def test_tenant_owned_label_queries_ignore_caller_supplied_tenant_params() -> None:
    """Strict callers must not treat params as authenticated execution tenant context."""

    class FakeSession:
        async def run(self, query, params):  # pragma: no cover - must not execute
            raise AssertionError(f"spoofed tenant query unexpectedly executed: {query} {params}")

    with pytest.raises(TenantQueryValidationError, match="Tenant context is required"):
        await run_validated_query(
            FakeSession(),
            "MATCH (e:Entity {tenant_id: $tenant_id}) RETURN e",
            {"tenant_id": "tenant-from-payload", "_tenant_id": "tenant-from-payload"},
        )


@pytest.mark.asyncio
async def test_parameter_tenant_context_is_not_treated_as_authenticated_context() -> None:
    """Parameter-only tenant context is not sufficient for tenant-owned Cypher."""

    class FakeSession:
        def __init__(self) -> None:
            self.calls: list[tuple[str, dict]] = []

        async def run(self, query, params):
            self.calls.append((query, params))
            return ["ok"]

    fake = FakeSession()
    query = "MATCH (e:Entity {tenant_id: $tenant_id}) RETURN e"

    with pytest.raises(TenantQueryValidationError, match="Tenant context is required"):
        await run_validated_query(fake, query, {"tenant_id": "tenant-a"})

    assert fake.calls == []


@pytest.mark.asyncio
async def test_tenant_owned_label_query_executes_when_every_label_is_scoped() -> None:
    """Scoped tenant-owned label queries are delegated with forced tenant params."""

    class FakeSession:
        def __init__(self) -> None:
            self.calls: list[tuple[str, dict]] = []

        async def run(self, query, params):
            self.calls.append((query, params))
            return ["ok"]

    fake = FakeSession()
    query = """
    MATCH (e:Entity {tenant_id: $tenant_id})-[:SUPPORTS]->(d:ValueDriver)
    WHERE d.tenant_id = $tenant_id
    RETURN e, d
    """

    result = await run_validated_query(
        fake,
        query,
        {"tenant_id": "spoofed"},
        tenant_id="tenant-a",
    )

    assert result == ["ok"]
    assert fake.calls == [(query, {"tenant_id": "tenant-a", "_tenant_id": "tenant-a"})]
