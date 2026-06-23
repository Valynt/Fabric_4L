from __future__ import annotations

"""High-value Layer 3 regression gates for mutation, determinism, tenant traversal, and observability."""


import ast
import importlib.util
import itertools
import sys
from pathlib import Path

import pytest

from src.metrics.prometheus_metrics import MetricsConfig, PrometheusMetrics
from src.schema.entity_resolution import EntityResolutionRequest, ResolutionStrategy
from src.services.entity_resolution import EntityResolutionService

ROUTES_DIR = Path(__file__).resolve().parents[1] / "src" / "api" / "routes"
REPO_ROOT = Path(__file__).resolve().parents[3]
AUDITED_WRITE_SCRIPT = REPO_ROOT / "scripts" / "ci" / "check_layer3_audited_relationship_writes.py"

SPEC = importlib.util.spec_from_file_location("check_layer3_audited_relationship_writes", AUDITED_WRITE_SCRIPT)
assert SPEC is not None and SPEC.loader is not None
audited_write_check = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = audited_write_check
SPEC.loader.exec_module(audited_write_check)


def _iter_route_files() -> list[Path]:
    return sorted(ROUTES_DIR.glob("*.py"))


def _decorator_name(node: ast.AST) -> str | None:
    if not isinstance(node, ast.Call):
        return None
    if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
        return f"{node.func.value.id}.{node.func.attr}"
    return None


def _is_write_endpoint(node: ast.AsyncFunctionDef | ast.FunctionDef) -> bool:
    writes = {"router.post", "router.put", "router.patch", "router.delete"}
    return any(_decorator_name(d) in writes for d in node.decorator_list)


class TestMutationPathCompleteness:
    def test_relationship_mutation_routes_reference_audited_gateway(self) -> None:
        violations: list[str] = []
        for route_file in _iter_route_files():
            source = route_file.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(route_file))
            visitor = audited_write_check.ScanVisitor(route_file)
            visitor.visit(tree)
            violations.extend(f"{route_file.name}:{item.function}:{item.line}" for item in visitor.violations)
        assert not violations, "Relationship mutation endpoints must route writes through AuditedGraphMutation gateway"


class TestDeterministicEntityResolutionProperties:
    @pytest.mark.asyncio
    async def test_order_perturbation_preserves_canonical_link_set_and_explanations(self) -> None:
        corpus = [
            {"id": "p-1", "properties": {"id": "p-1", "name": "Acme Platform", "category": "SaaS"}},
            {"id": "p-2", "properties": {"id": "p-2", "name": "Acme Platform", "category": "SaaS"}},
            {"id": "p-3", "properties": {"id": "p-3", "name": "Acme Platform X", "category": "SaaS"}},
        ]

        service = EntityResolutionService(driver=object())
        request = EntityResolutionRequest(
            entity_type="Product",
            tenant_id="tenant-1",
            query_attributes={"name": "Acme Platform", "category": "SaaS"},
            strategy=ResolutionStrategy.EXACT,
        )

        canonical = None
        for permutation in itertools.permutations(corpus):
            response = await service._score_candidates(request, list(permutation))
            projection = {(c.entity_id, c.explanation) for c in response}
            if canonical is None:
                canonical = projection
            assert projection == canonical


class TestAccountScopeHostileTraversal:
    def test_entities_detail_relationship_traversal_is_tenant_scoped(self) -> None:
        source = (ROUTES_DIR / "entities.py").read_text(encoding="utf-8")
        # Hostile traversal protection: both anchors must remain tenant constrained.
        assert "(e:Entity {id: $entity_id, tenant_id: $tenant_id})-[r]-(other:Entity {tenant_id: $tenant_id})" in source


class TestPaginationAbuseGates:
    def test_search_endpoints_define_hard_limit_upper_bounds(self) -> None:
        violations: list[str] = []
        for route_file in _iter_route_files():
            text = route_file.read_text(encoding="utf-8")
            if "limit:" in text and "Query(" in text and "le=" not in text:
                violations.append(route_file.name)
        assert not violations, "Pagination limit parameters must define hard le= upper bound"


class TestObservabilityContractCoverage:
    def test_metrics_and_alert_primitives_cover_mutation_and_traversal_failures(self) -> None:
        metrics = PrometheusMetrics(MetricsConfig(enabled=True))

        assert "graph_mutation_rate" in metrics._metrics
        assert "graph_mutations_total" in metrics._metrics
        assert "unauthorized_traversals_total" in metrics._metrics

        # Constraint/index failures surface as mutation failures via error_type label.
        metrics.increment_mutation_failure("constraint_violation")
        metrics.increment_mutation_failure("index_failure")
        metrics.increment_unauthorized_traversal(
            category="account_scope",
            route="entities.detail",
            violation_type="hostile_traversal",
        )
