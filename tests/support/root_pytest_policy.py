"""Repository-level pytest dependency and marker policy."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import TYPE_CHECKING

from tests.support.root_pytest_bootstrap import REPO_ROOT

if TYPE_CHECKING:
    from _pytest.config import Config, Parser
    from _pytest.nodes import Item

MANDATORY_DEPS: dict[str, str] = {
    "respx": "pip install 'respx>=0.21'  (layer1-ingestion[dev] or tests/requirements-test.txt)",
    "aiohttp": "pip install 'aiohttp>=3.9'  (tests/requirements-test.txt)",
    "trafilatura": "pip install 'trafilatura>=1.6'  (layer1-ingestion dependency)",
    "defusedxml": "pip install 'defusedxml>=0.7'  (layer1-ingestion dependency)",
    "pymupdf4llm": "pip install 'pymupdf4llm>=0.0.17'  (layer1-ingestion dependency)",
    "pytesseract": "pip install 'pytesseract>=0.3.13'  (layer1-ingestion dependency)",
    "selectolax": "pip install 'selectolax>=0.3'  (layer1-ingestion dependency)",
    "rdflib": "pip install 'rdflib>=7.0'  (layer3-knowledge dependency)",
    "neo4j": "pip install 'neo4j>=5.15'  (layer3-knowledge dependency)",
    "psycopg": "pip install 'psycopg[binary]>=3.1'  (layer4-agents[dev])",
    "email_validator": "pip install 'email-validator>=2.1'  (layer4-agents[dev])",
    "langgraph": "pip install 'langgraph>=0.2'  (layer4-agents dependency)",
    "jose": "pip install 'python-jose[cryptography]>=3.3'  (layer4-agents dependency)",
    "jsonschema": "pip install 'jsonschema>=4.23'  (tests/requirements-test.txt)",
}

TENANT_ISOLATION_ALIASES = frozenset({"tenant_boundary", "tenant_matrix", "cross_tenant_write"})
TENANT_ISOLATION_TARGETS = frozenset(
    {
        "tests/security/test_cross_layer_tenant_isolation_matrix.py",
        "tests/security/test_tenant_boundary_fails_closed.py",
        "tests/security/test_tenant_repository_filter_presence.py",
        "services/layer1-ingestion/tests/security/test_rls_enforcement_postgres.py",
        "services/layer1-ingestion/tests/security/test_celery_tenant_isolation_postgres.py",
        "services/layer1-ingestion/tests/security/test_targets_tenant_isolation.py",
        "services/layer1-ingestion/tests/test_api_tenant_propagation.py",
        "services/layer1-ingestion/tests/test_cross_tenant_hostile.py",
        "services/layer2-extraction/tests/test_api_tenant_propagation.py",
        "services/layer2-extraction/tests/test_cross_tenant_hostile.py",
        "services/layer2-extraction/tests/test_missing_tenant_context_hostile.py",
        "services/layer2-extraction/tests/test_job_store.py",
        "services/layer2-extraction/tests/test_extraction_cache.py",
        "tests/security/test_graph_tenant_hostile_regression.py",
        "tests/security/test_neo4j_tenant_write_enforcement.py",
        "tests/security/test_neo4j_cross_tenant_write_isolation.py",
        "services/layer3-knowledge/tests/test_api_tenant_propagation.py",
        "services/layer3-knowledge/tests/test_cross_tenant_hostile.py",
        "services/layer3-knowledge/tests/test_tenant_isolation.py",
        "services/layer4-agents/tests/test_api_tenant_propagation.py",
        "services/layer4-agents/tests/test_cross_tenant_hostile.py",
        "services/layer4-agents/tests/test_agent_tenant_isolation.py",
        "services/layer4-agents/tests/test_workflow_tenant_isolation.py",
        "services/layer4-agents/tests/test_checkpoint_tenant_isolation.py",
        "services/layer5-ground-truth/tests/test_tenant_id_consistency.py",
        "services/layer5-ground-truth/tests/test_cross_tenant_hostile.py",
        "services/layer5-ground-truth/tests/unit/test_truth_service_and_api_tenant_boundaries.py",
        "services/layer6-benchmarks/tests/test_api_tenant_propagation.py",
        "services/layer6-benchmarks/tests/test_repository_tenant_isolation.py",
        "services/layer6-benchmarks/tests/test_cross_tenant_hostile.py",
        "services/layer7-billing/tests/test_api_tenant_propagation.py",
        "services/layer7-billing/tests/test_cross_tenant_hostile.py",
        "services/layer7-billing/tests/test_tenant_isolation.py",
        "tests/cache/test_redis_tenant_isolation.py",
        "tests/shared/identity/test_api_key_cache.py",
        "services/api/app/tests/test_distributed_session_store.py",
    }
)
TENANT_ISOLATION_NODEIDS = frozenset(
    {"services/layer5-ground-truth/tests/test_api.py::TestGetTruth::test_org_isolation"}
)
MANDATORY_MARKERS = frozenset({"unit", "contract", "security", "tenant_boundary", "tenant_isolation"})
MANDATORY_EXCLUSION_MARKERS = frozenset(
    {
        "slow",
        "requires_postgres",
        "requires_redis",
        "requires_neo4j",
        "requires_docker",
        "requires_openai",
        "e2e",
        "integration",
        "performance",
        "flaky",
        "quarantine",
    }
)


def add_root_pytest_options(parser: "Parser") -> None:
    parser.addoption(
        "--no-mandatory-dep-check",
        action="store_true",
        default=False,
        dest="no_mandatory_dep_check",
        help="Skip mandatory dependency enforcement (for --collect-only dry runs).",
    )


def enforce_mandatory_dependencies(config: "Config") -> None:
    if _skip_mandatory_dep_check(config):
        return
    missing = [(name, hint) for name, hint in MANDATORY_DEPS.items() if importlib.util.find_spec(name) is None]
    if missing:
        raise SystemExit(_missing_dependency_message(missing))


def apply_collection_markers(items: list["Item"]) -> None:
    for item in items:
        item_markers = _item_marker_names(item)
        _apply_tenant_isolation_marker(item, item_markers)
        if _should_mark_mandatory(item_markers):
            item.add_marker("mandatory")


def _skip_mandatory_dep_check(config: "Config") -> bool:
    return (
        getattr(config.option, "no_mandatory_dep_check", False)
        or getattr(config.option, "collectonly", False)
        or _is_central_security_aggregation_run(config)
    )


def _is_central_security_aggregation_run(config: "Config") -> bool:
    args = [str(arg).rstrip("/") for arg in getattr(config, "args", ())]
    if not args:
        return False
    security_dir = str(REPO_ROOT / "tests" / "security")
    return all(arg in {"tests/security", security_dir} for arg in args)


def _missing_dependency_message(missing: list[tuple[str, str]]) -> str:
    lines = ["", "Mandatory test dependencies are missing.", ""]
    for name, hint in missing:
        lines.append(f"  \u2717 {name}")
        lines.append(f"    \u2192 {hint}")
    lines += [
        "",
        "Install all mandatory deps for the full mandatory profile:",
        "  pip install -r tests/requirements-test.txt",
        "",
        "To skip this check (e.g. for a dry-run collection audit):",
        "  pytest --no-mandatory-dep-check --collect-only",
        "",
    ]
    return "\n".join(lines)


def _item_marker_names(item: "Item") -> set[str]:
    return {marker.name for marker in item.iter_markers()}


def _item_repo_path(item: "Item") -> str:
    return Path(str(item.fspath)).resolve().relative_to(REPO_ROOT).as_posix()


def _is_tenant_isolation_target(item: "Item", item_markers: set[str]) -> bool:
    item_path = _item_repo_path(item)
    item_nodeid = item.nodeid.replace("\\", "/")
    return (
        item_path in TENANT_ISOLATION_TARGETS
        or item_nodeid in TENANT_ISOLATION_NODEIDS
        or bool(item_markers & TENANT_ISOLATION_ALIASES)
    )


def _apply_tenant_isolation_marker(item: "Item", item_markers: set[str]) -> None:
    if not _is_tenant_isolation_target(item, item_markers):
        return
    if "tenant_isolation" in item_markers:
        return
    item.add_marker("tenant_isolation")
    item_markers.add("tenant_isolation")


def _should_mark_mandatory(item_markers: set[str]) -> bool:
    if "mandatory" in item_markers:
        return False
    if item_markers & MANDATORY_EXCLUSION_MARKERS:
        return False
    return bool(item_markers & MANDATORY_MARKERS)
