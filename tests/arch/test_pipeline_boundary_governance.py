"""Architecture guardrails for the six-layer core pipeline boundary."""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

CORE_LAYER_NUMBERS = ("1", "2", "3", "4", "5", "6")

SERVICE_ROOTS: dict[str, tuple[Path, str]] = {
    "layer1-ingestion": (
        REPO_ROOT / "services" / "layer1-ingestion" / "src",
        "layer1_ingestion",
    ),
    "layer2-extraction": (
        REPO_ROOT / "services" / "layer2-extraction" / "src",
        "layer2_extraction",
    ),
    "layer2-5-signal-refinery": (
        REPO_ROOT / "services" / "layer2-5-signal-refinery" / "src",
        "layer2_5_signal_refinery",
    ),
    "layer4-agents": (
        REPO_ROOT / "services" / "layer4-agents" / "src",
        "layer4_agents",
    ),
    "layer5-ground-truth": (
        REPO_ROOT / "services" / "layer5-ground-truth" / "src",
        "layer5_ground_truth",
    ),
    "layer6-benchmarks": (
        REPO_ROOT / "services" / "layer6-benchmarks" / "src",
        "layer6_benchmarks",
    ),
}

SERVICE_IMPORT_PREFIXES = {
    service_prefix: service_name
    for service_name, (_, service_prefix) in SERVICE_ROOTS.items()
}

SKIP_DIR_NAMES = {".venv", "venv", "__pycache__", "tests", "migrations"}


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def _python_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return [
        path
        for path in root.rglob("*.py")
        if not any(part in SKIP_DIR_NAMES for part in path.relative_to(REPO_ROOT).parts)
    ]


def _imported_roots(path: Path) -> list[tuple[int, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imported: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend((node.lineno, alias.name.split(".", 1)[0]) for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append((node.lineno, node.module.split(".", 1)[0]))
    return imported


def test_architecture_authority_keeps_core_pipeline_to_six_layers() -> None:
    architecture = _read("ARCHITECTURE.md")

    assert "six-layer core microservices architecture" in architecture
    assert "Adjacent Deployable Capabilities" in architecture
    assert "| 2.5 |" not in architecture
    assert "| 7 |" not in architecture
    for layer_number in CORE_LAYER_NUMBERS:
        assert f"| {layer_number} |" in architecture


def test_runtime_path_governance_tracks_adjacent_services_outside_layer_matrix() -> None:
    governance = _read("docs/reference/layer-runtime-path-governance.md")

    assert "Adjacent service path matrix" in governance
    assert "not additional" in governance
    assert "services/layer2-5-signal-refinery/src/layer2_5_signal_refinery/" in governance
    assert "services/layer4-agents/src/layer4_agents/services/billing_service.py" in governance
    assert "Legacy `services/billing/` removed 2026-08-27 (COMPAT-BILL-001)" in governance


def test_behavior_contract_distinguishes_core_layers_from_adjacent_services() -> None:
    contract = _read("contracts/behavior-contract.yaml")

    assert "Every core endpoint family (L1-L6)" in contract
    assert "Signal Refinery and Billing" in contract
    assert "L1-L7" not in contract


def test_runtime_services_do_not_import_other_service_runtime_packages_directly() -> None:
    violations: list[str] = []

    for service_name, (root, own_prefix) in SERVICE_ROOTS.items():
        for path in _python_files(root):
            rel_path = path.relative_to(REPO_ROOT).as_posix()
            for line_number, imported_root in _imported_roots(path):
                imported_service = SERVICE_IMPORT_PREFIXES.get(imported_root)
                if imported_service is None or imported_root == own_prefix:
                    continue
                violations.append(
                    f"{rel_path}:{line_number} imports {imported_root} "
                    f"from {imported_service}; use a contracted client boundary from {service_name}"
                )

    assert not violations, "\n".join(violations)


def test_value_fabric_layer_shims_do_not_grow_local_logic() -> None:
    violations: list[str] = []
    for layer_number in CORE_LAYER_NUMBERS:
        root = REPO_ROOT / "value_fabric" / f"layer{layer_number}"
        for path in _python_files(root):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in tree.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    rel_path = path.relative_to(REPO_ROOT).as_posix()
                    violations.append(
                        f"{rel_path}:{node.lineno} defines local runtime logic; "
                        "compatibility shims must re-export or delegate only"
                    )

    assert not violations, "\n".join(violations)


def test_layer3_entity_routes_do_not_return_raw_neo4j_objects() -> None:
    path = REPO_ROOT / "services" / "layer3-knowledge" / "src" / "api" / "routes" / "entities.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    raw_object_names = {
        "neo4j",
        "session",
        "transaction",
        "tx",
        "driver",
        "record",
        "result",
        "entity_node",
        "center_node",
    }
    violations: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Name):
            if node.value.id in raw_object_names:
                violations.append(
                    f"{path.relative_to(REPO_ROOT).as_posix()}:{node.lineno} "
                    f"returns raw backend object '{node.value.id}'"
                )

    assert not violations, "\n".join(violations)


def test_billing_api_does_not_call_external_provider_sdks_in_request_handlers() -> None:
    violations: list[str] = []
    forbidden_import_roots = {"stripe", "requests", "httpx", "aiohttp", "urllib"}
    routes_root = (
        REPO_ROOT
        / "services"
        / "layer4-agents"
        / "src"
        / "layer4_agents"
        / "api"
        / "routes"
    )
    billing_route_files = [p for p in _python_files(routes_root) if p.name.startswith("billing")]

    for path in billing_route_files:
        rel_path = path.relative_to(REPO_ROOT).as_posix()
        for line_number, imported_root in _imported_roots(path):
            if imported_root in forbidden_import_roots:
                violations.append(
                    f"{rel_path}:{line_number} imports external provider/client '{imported_root}'; "
                    "billing request paths must use approved adapters, verified webhooks, or idempotent callbacks"
                )

    assert not violations, "\n".join(violations)
