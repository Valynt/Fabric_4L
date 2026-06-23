"""Parity guardrails between canonical runtime modules and maintained service wrappers."""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


LAYER_PARITY_RULES: dict[str, dict[str, object]] = {
    "layer1": {
        "canonical_routes": REPO_ROOT / "services/layer1-ingestion/src/api/routes/__init__.py",
        "service_routes": REPO_ROOT / "services/layer1-ingestion/src/api/routes/__init__.py",
        "service_main": REPO_ROOT / "services/layer1-ingestion/src/layer1_ingestion/api/main.py",
        "canonical_import": "layer1_ingestion.api.routes",
        "service_interface": REPO_ROOT / "services/layer1-ingestion/src/layer1_ingestion/api/main.py",
        "repository_interface": REPO_ROOT / "services/layer1-ingestion/src/crawler/decision_store.py",
        "middleware_anchor": REPO_ROOT / "services/layer1-ingestion/src/layer1_ingestion/api/main.py",
    },
    "layer2": {
        "canonical_routes": REPO_ROOT / "services/layer2-extraction/src/layer2_extraction/api/routes/__init__.py",
        "service_routes": REPO_ROOT / "services/layer2-extraction/src/layer2_extraction/api/routes/__init__.py",
        "service_main": REPO_ROOT / "services/layer2-extraction/src/layer2_extraction/api/main.py",
        "canonical_import": "layer2_extraction.api.routes",
        "service_interface": REPO_ROOT / "services/layer2-extraction/src/layer2_extraction/services/signal_lifecycle_service.py",
        "repository_interface": REPO_ROOT / "services/layer2-extraction/src/layer2_extraction/repositories/__init__.py",
        "middleware_anchor": REPO_ROOT / "services/layer2-extraction/src/layer2_extraction/api/main.py",
    },
    "layer3": {
        "canonical_routes": REPO_ROOT / "services/layer3-knowledge/src/api/routes/__init__.py",
        "service_routes": REPO_ROOT / "services/layer3-knowledge/src/api/routes/__init__.py",
        "service_main": REPO_ROOT / "services/layer3-knowledge/src/api/main.py",
        "canonical_import": "api.routes",
        "service_interface": REPO_ROOT / "services/layer3-knowledge/src/services/product_service.py",
        "repository_interface": REPO_ROOT / "services/layer3-knowledge/src/graph/query_guards.py",
        "middleware_anchor": REPO_ROOT / "services/layer3-knowledge/src/api/main.py",
    },
    "layer4": {
        "canonical_routes": REPO_ROOT / "services/layer4-agents/src/api/routes/__init__.py",
        "service_routes": REPO_ROOT / "services/layer4-agents/src/api/routes/__init__.py",
        "service_main": REPO_ROOT / "services/layer4-agents/src/api/main.py",
        "canonical_import": "api.routes",
        "service_interface": REPO_ROOT / "services/layer4-agents/src/services/business_case_service.py",
        "repository_interface": REPO_ROOT / "services/layer4-agents/src/database.py",
        "middleware_anchor": REPO_ROOT / "services/layer4-agents/src/api/main.py",
    },
    "layer5": {
        "canonical_routes": REPO_ROOT / "services/layer5-ground-truth/src/layer5_ground_truth/api/router.py",
        "service_routes": REPO_ROOT / "services/layer5-ground-truth/src/layer5_ground_truth/api/router.py",
        "service_main": REPO_ROOT / "services/layer5-ground-truth/src/layer5_ground_truth/api/main.py",
        "canonical_import": "layer5_ground_truth.api.router",
        "service_interface": REPO_ROOT / "services/layer5-ground-truth/src/layer5_ground_truth/services/truth_service.py",
        "repository_interface": REPO_ROOT / "services/layer5-ground-truth/src/layer5_ground_truth/database.py",
        "middleware_anchor": REPO_ROOT / "services/layer5-ground-truth/src/layer5_ground_truth/api/main.py",
    },
    "layer6": {
        "canonical_routes": REPO_ROOT / "services/layer6-benchmarks/src/layer6_benchmarks/api/routes/__init__.py",
        "service_routes": REPO_ROOT / "services/layer6-benchmarks/src/layer6_benchmarks/api/routes/__init__.py",
        "service_main": REPO_ROOT / "services/layer6-benchmarks/src/layer6_benchmarks/api/main.py",
        "canonical_import": "layer6_benchmarks.api.routes",
        "service_interface": REPO_ROOT / "services/layer6-benchmarks/src/layer6_benchmarks/api/routes/benchmarks.py",
        "repository_interface": REPO_ROOT / "services/layer6-benchmarks/src/layer6_benchmarks/repositories/benchmark_repository.py",
        "middleware_anchor": REPO_ROOT / "services/layer6-benchmarks/src/layer6_benchmarks/api/main.py",
    },
}


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"))


def _star_imports(path: Path) -> set[str]:
    module = _parse(path)
    imports: set[str] = set()
    for node in module.body:
        if isinstance(node, ast.ImportFrom) and any(alias.name == "*" for alias in node.names):
            if node.module:
                imports.add(node.module)
    return imports


def test_layer_parity_rules_cover_all_layers() -> None:
    assert set(LAYER_PARITY_RULES.keys()) == {"layer1", "layer2", "layer3", "layer4", "layer5", "layer6"}


def test_service_route_modules_reexport_canonical_exports() -> None:
    for layer, rule in LAYER_PARITY_RULES.items():
        # Fully migrated layers have no separate shim; service_routes == canonical_routes
        if rule["service_routes"] == rule["canonical_routes"]:
            continue
        imports = _star_imports(rule["service_routes"])
        expected = {rule["canonical_import"]}
        assert expected.issubset(imports), f"{layer} service route module must star-import canonical route module"


def test_service_main_modules_reexport_or_bind_canonical_app() -> None:
    for layer, rule in LAYER_PARITY_RULES.items():
        source = rule["service_main"].read_text(encoding="utf-8")
        assert "app" in source, f"{layer} service main entrypoint must expose app"


def test_parity_rules_define_required_checkpoints() -> None:
    for layer, rule in LAYER_PARITY_RULES.items():
        for field in ("canonical_routes", "service_routes", "service_main", "service_interface", "repository_interface", "middleware_anchor"):
            target = rule[field]
            assert isinstance(target, Path)
            assert target.exists(), f"{layer}: missing parity checkpoint path for {field}: {target}"
