"""Layer 4 clean-architecture import-boundary checks."""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LAYER4_ROOT = REPO_ROOT / "services/layer4-agents/src/layer4_agents"

INNER_RING_PATHS = (
    LAYER4_ROOT / "shared/domain",
    LAYER4_ROOT / "engine/ports.py",
    LAYER4_ROOT / "contracts",
    LAYER4_ROOT / "interfaces",
    LAYER4_ROOT / "policies",
)

APPLICATION_AGENT_PATHS = (
    LAYER4_ROOT / "agents/signal_detection.py",
    LAYER4_ROOT / "agents/taxonomy.py",
)

APPLICATION_SERVICE_PATHS = (
    LAYER4_ROOT / "services/company_knowledge_service.py",
)

ROUTE_ADAPTER_BOUNDARY_PATHS = (
    LAYER4_ROOT / "api/routes/ground_truth_proxy.py",
    LAYER4_ROOT / "api/routes/prospects.py",
    LAYER4_ROOT / "api/routes/signals.py",
)

FORBIDDEN_INFRA_IMPORT_ROOTS = {
    "asyncpg",
    "boto3",
    "celery",
    "fastapi",
    "httpx",
    "langgraph",
    "neo4j",
    "openai",
    "playwright",
    "redis",
    "sqlalchemy",
    "stripe",
    "uvicorn",
}


def _iter_inner_ring_files() -> list[Path]:
    files: list[Path] = []
    for path in INNER_RING_PATHS:
        if path.is_file():
            files.append(path)
        elif path.exists():
            files.extend(sorted(path.rglob("*.py")))
    return files


def _import_root(module_name: str) -> str:
    return module_name.split(".", 1)[0]


def _imported_modules(path: Path) -> list[tuple[int, int, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: list[tuple[int, int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend((node.lineno, 0, alias.name) for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append((node.lineno, node.level, node.module))
    return imports


def test_layer4_inner_ring_modules_do_not_import_infrastructure_packages() -> None:
    violations: list[str] = []
    for path in _iter_inner_ring_files():
        rel_path = path.relative_to(REPO_ROOT).as_posix()
        for lineno, _level, module_name in _imported_modules(path):
            if _import_root(module_name) in FORBIDDEN_INFRA_IMPORT_ROOTS:
                violations.append(f"{rel_path}:{lineno} imports {module_name}")

    assert not violations, (
        "Layer 4 domain, interface, contract, port, and policy modules must not "
        "import infrastructure/framework packages:\n" + "\n".join(violations)
    )


def test_layer4_task_execution_port_does_not_import_scheduler_adapter() -> None:
    path = LAYER4_ROOT / "engine/ports.py"
    violations = []
    for lineno, level, module_name in _imported_modules(path):
        if level == 1 and module_name == "scheduler":
            violations.append(f"{path.relative_to(REPO_ROOT).as_posix()}:{lineno} imports .scheduler")
        if module_name == "layer4_agents.engine.scheduler":
            violations.append(f"{path.relative_to(REPO_ROOT).as_posix()}:{lineno} imports {module_name}")

    assert not violations, (
        "Task execution ports must stay abstract; concrete scheduler adapters "
        "belong under layer4_agents.adapters:\n" + "\n".join(violations)
    )


def test_application_agents_do_not_import_cross_layer_integration_clients() -> None:
    forbidden_modules = {
        "layer4_agents.integration.layer1_client",
        "layer4_agents.integration.layer2_client",
        "layer4_agents.integration.layer3_client",
        "layer4_agents.integration.layer5_client",
    }
    forbidden_relative = {
        "integration.layer1_client",
        "integration.layer2_client",
        "integration.layer3_client",
        "integration.layer5_client",
    }
    violations: list[str] = []
    for path in APPLICATION_AGENT_PATHS:
        rel_path = path.relative_to(REPO_ROOT).as_posix()
        for lineno, level, module_name in _imported_modules(path):
            if module_name in forbidden_modules or (level and module_name in forbidden_relative):
                violations.append(f"{rel_path}:{lineno} imports {module_name}")

    assert not violations, (
        "Application agents must depend on client ports/factories, "
        "not concrete cross-layer integration clients:\n" + "\n".join(violations)
    )


def test_application_services_do_not_import_cross_layer_integration_clients() -> None:
    forbidden_modules = {
        "layer4_agents.integration.layer1_client",
        "layer4_agents.integration.layer2_client",
        "layer4_agents.integration.layer3_client",
        "layer4_agents.integration.layer5_client",
    }
    forbidden_relative = {
        "integration.layer1_client",
        "integration.layer2_client",
        "integration.layer3_client",
        "integration.layer5_client",
    }
    violations: list[str] = []
    for path in APPLICATION_SERVICE_PATHS:
        rel_path = path.relative_to(REPO_ROOT).as_posix()
        for lineno, level, module_name in _imported_modules(path):
            if module_name in forbidden_modules or (level and module_name in forbidden_relative):
                violations.append(f"{rel_path}:{lineno} imports {module_name}")

    assert not violations, (
        "Application services must depend on cross-layer ports, not concrete "
        "integration clients:\n" + "\n".join(violations)
    )


def test_application_agents_do_not_import_adapter_factories() -> None:
    violations: list[str] = []
    for path in APPLICATION_AGENT_PATHS:
        rel_path = path.relative_to(REPO_ROOT).as_posix()
        for lineno, level, module_name in _imported_modules(path):
            if module_name.startswith("layer4_agents.adapters") or (
                level and module_name.startswith("adapters")
            ):
                violations.append(f"{rel_path}:{lineno} imports {module_name}")

    assert not violations, (
        "Application agents must receive adapter factories from composition roots, "
        "not import adapters directly:\n" + "\n".join(violations)
    )


def test_route_modules_do_not_import_cross_layer_integration_clients() -> None:
    forbidden_modules = {
        "layer4_agents.integration.layer1_client",
        "layer4_agents.integration.layer2_client",
        "layer4_agents.integration.layer3_client",
        "layer4_agents.integration.layer5_client",
    }
    forbidden_relative = {
        "integration.layer1_client",
        "integration.layer2_client",
        "integration.layer3_client",
        "integration.layer5_client",
    }
    violations: list[str] = []
    for path in ROUTE_ADAPTER_BOUNDARY_PATHS:
        rel_path = path.relative_to(REPO_ROOT).as_posix()
        for lineno, level, module_name in _imported_modules(path):
            if module_name in forbidden_modules or (level and module_name in forbidden_relative):
                violations.append(f"{rel_path}:{lineno} imports {module_name}")

    assert not violations, (
        "Route modules must depend on route ports/composition, not concrete "
        "cross-layer integration clients:\n" + "\n".join(violations)
    )
