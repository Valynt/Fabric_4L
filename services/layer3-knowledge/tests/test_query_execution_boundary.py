"""Regression tests for the Layer 3 approved Neo4j execution boundary."""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

import pytest

from db.query_execution import TenantQueryValidationError, run_validated_query


REPO_ROOT = Path(__file__).resolve().parents[3]
HIGH_RISK_RUNTIME_ROOTS = (
    REPO_ROOT / "services" / "layer3-knowledge" / "src" / "api" / "routes",
    REPO_ROOT / "services" / "layer3-knowledge" / "src" / "services",
    REPO_ROOT / "services" / "layer3-knowledge" / "src" / "agents",
    REPO_ROOT / "services" / "layer3-knowledge" / "src" / "analytics",
)
SCANNER = REPO_ROOT / "scripts" / "check_layer3_cypher_scope.py"
ALLOWED_SYSTEM_SCOPED_PATH_FRAGMENTS = (
    "services/layer3-knowledge/src/schema/",
    "services/layer3-knowledge/src/migrations/",
    "services/layer3-knowledge/src/bootstrap/",
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
        if isinstance(func, ast.Attribute) and func.attr == "run":
            owner = self._owner_name(func.value)
            if owner in {"session", "raw_session", "tx", "transaction"}:
                self.violations.append((node.lineno, node.col_offset))
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
            "services/layer3-knowledge/src/api/routes",
            "services/layer3-knowledge/src/services",
            "services/layer3-knowledge/src/agents",
            "services/layer3-knowledge/src/analytics",
            "--warnings-as-errors",
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + "\n" + result.stderr


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "query",
    [
        "MATCH (e:Entity) RETURN e",
        "MATCH (p:Product {id: $id}) RETURN p",
        "MATCH (e:Evidence)-[:SUPPORTS]->(d:ValueDriver {tenant_id: $tenant_id}) RETURN e, d",
        "CREATE (e:Evidence {id: $id}) RETURN e",
    ],
)
async def test_tenant_owned_label_queries_fail_closed_without_tenant_predicates(query: str) -> None:
    """Tenant-owned labels require explicit tenant predicates before execution."""

    class FakeSession:
        async def run(self, query, params):  # pragma: no cover - must not execute
            raise AssertionError(f"unsafe query unexpectedly executed: {query} {params}")

    with pytest.raises(TenantQueryValidationError, match="missing tenant scoping"):
        await run_validated_query(FakeSession(), query, {"id": "shared-id", "tenant_id": "tenant-a"})


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

    result = await run_validated_query(fake, query, {"tenant_id": "spoofed"}, tenant_id="tenant-a")

    assert result == ["ok"]
    assert fake.calls == [(query, {"tenant_id": "tenant-a", "_tenant_id": "tenant-a"})]
