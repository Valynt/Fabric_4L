"""Regression tests for P1-14: SecurityMiddleware skip lists.

These tests intentionally inspect source configuration instead of importing
service entrypoints. Importing the full apps requires optional service
dependencies and can silently skip security coverage in constrained CI/local
environments.
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LAYER_CONFIG_SOURCES = {
    "l1": REPO_ROOT / "services" / "layer1-ingestion" / "src" / "layer1_ingestion" / "api" / "main.py",
    "l2": REPO_ROOT / "services" / "layer2-extraction" / "src" / "layer2_extraction" / "api" / "main.py",
    "l3": REPO_ROOT / "services" / "layer3-knowledge" / "src" / "api" / "main.py",
    "l4": REPO_ROOT / "services" / "layer4-agents" / "src" / "layer4_agents" / "api" / "middleware.py",
}
LAYER_CONFIG_TARGETS = {
    "l1": "_security_config_l1",
    "l2": "_TENANT_CONTEXT_EXEMPT_PATHS",
    "l3": "_security_config_l3",
    "l4": "security_config",
}


def _literal_string_set(node: ast.AST) -> set[str]:
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "frozenset":
        return _literal_string_set(node.args[0])
    if isinstance(node, (ast.Set, ast.List, ast.Tuple)):
        values = ast.literal_eval(node)
        return {str(value) for value in values}
    raise AssertionError(f"Unsupported skip_validation_paths expression: {ast.dump(node)}")


def _security_config_call(layer: str) -> ast.Call:
    source = LAYER_CONFIG_SOURCES[layer]
    tree = ast.parse(source.read_text(encoding="utf-8"))
    target_name = LAYER_CONFIG_TARGETS[layer]

    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == target_name for target in node.targets):
            continue
        if isinstance(node.value, ast.Call):
            return node.value

    raise AssertionError(f"{target_name} assignment not found in {source}")


def _assignment_value(layer: str) -> ast.AST:
    source = LAYER_CONFIG_SOURCES[layer]
    tree = ast.parse(source.read_text(encoding="utf-8"))
    target_name = LAYER_CONFIG_TARGETS[layer]

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == target_name
            for target in node.targets
        ):
            return node.value
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == target_name
            and node.value is not None
        ):
            return node.value

    raise AssertionError(f"{target_name} assignment not found in {source}")


def _security_config_keyword(layer: str, keyword_name: str) -> ast.AST:
    call = _security_config_call(layer)
    for keyword in call.keywords:
        if keyword.arg == keyword_name:
            return keyword.value
    raise AssertionError(f"{keyword_name} not configured for {layer}")


def _skip_paths(layer: str) -> set[str]:
    if layer == "l2":
        return _literal_string_set(_assignment_value(layer))
    return _literal_string_set(_security_config_keyword(layer, "skip_validation_paths"))


def _strict_mode(layer: str) -> bool:
    if layer == "l2":
        source = LAYER_CONFIG_SOURCES[layer].read_text(encoding="utf-8")
        return "tenant_enforcement=EnforcementControlConfig(mode=EnforcementMode.ENFORCE)" in source
    value = ast.literal_eval(_security_config_keyword(layer, "strict_mode"))
    assert isinstance(value, bool)
    return value


class TestSecurityMiddlewareCoverage:
    """Test that SecurityMiddleware validates all untrusted input paths."""

    def test_layer1_no_ingest_in_skip_list(self):
        """L1: /v1/ingest paths must NOT be in skip_validation_paths."""
        skip_paths = _skip_paths("l1")

        # These paths must be validated (NOT in skip list)
        assert "/v1/ingest" not in skip_paths, "/v1/ingest must be validated"
        assert "/v1/ingest/batch" not in skip_paths, "/v1/ingest/batch must be validated"
        assert "/v1/batch/ingest" not in skip_paths, "/v1/batch/ingest must be validated"

        # These paths are OK to skip
        assert "/health" in skip_paths
        assert "/metrics" in skip_paths

    def test_layer2_no_extract_in_skip_list(self):
        """L2: /v1/extract paths must NOT be in skip_validation_paths."""
        skip_paths = _skip_paths("l2")

        # These paths must be validated
        assert "/v1/extract" not in skip_paths, "/v1/extract must be validated"
        assert "/v1/extract/batch" not in skip_paths, "/v1/extract/batch must be validated"
        assert "/v1/nl-query" not in skip_paths, "/v1/nl-query must be validated"

        # These paths are OK to skip
        assert "/health" in skip_paths
        # Layer 2 protects metrics with verify_metrics_access instead of
        # opting the route out of tenant enforcement.

    def test_layer3_no_query_in_skip_list(self):
        """L3: /v1/query paths must NOT be in skip_validation_paths."""
        skip_paths = _skip_paths("l3")

        # These paths must be validated
        assert "/v1/query" not in skip_paths, "/v1/query must be validated"
        assert "/v1/query/graph" not in skip_paths, "/v1/query/graph must be validated"
        assert "/v1/graph/query" not in skip_paths, "/v1/graph/query must be validated"

        # These paths are OK to skip
        assert "/health" in skip_paths
        assert "/metrics" in skip_paths

    def test_layer4_no_agent_in_skip_list(self):
        """L4: /agents/v1 paths must NOT be in skip_validation_paths."""
        skip_paths = _skip_paths("l4")

        # These paths must be validated
        assert "/agents/v1/workflows" not in skip_paths, "/agents/v1/workflows must be validated"
        assert "/agents/v1/skills" not in skip_paths, "/agents/v1/skills must be validated"
        assert "/agents/v1/analyze" not in skip_paths, "/agents/v1/analyze must be validated"

        # These paths are OK to skip
        assert "/health" in skip_paths
        assert "/metrics" in skip_paths

    def test_security_middleware_has_strict_mode(self):
        """All layers must have strict_mode=True."""
        for layer in ("l1", "l2", "l3", "l4"):
            assert _strict_mode(layer) is True
