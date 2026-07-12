"""Architecture tests for service API entrypoints."""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MAX_ENTRYPOINT_BYTES = 35 * 1024
MAX_ROUTE_MODULE_BYTES = 25 * 1024
ENTRYPOINTS = [
    REPO_ROOT / "services/layer3-knowledge/src/api/main.py",
    REPO_ROOT / "services/layer1-ingestion/src/layer1_ingestion/api/main.py",
]
ROUTE_ROOTS = [
    REPO_ROOT / "services/layer3-knowledge/src/api/routes",
    REPO_ROOT / "services/layer1-ingestion/src/api/routes",
]
ROUTE_SIZE_EXCEPTIONS = {
    "services/layer3-knowledge/src/api/routes/value_packs.py": "Existing large route module; planned follow-up split by pack lifecycle/read-model handlers.",
    "services/layer3-knowledge/src/api/routes/formulas.py": "Existing large route module; planned follow-up split by formula evaluation/governance helpers.",
    "services/layer3-knowledge/src/api/routes/formula_governance.py": "Existing large route module; planned follow-up split by governance workflow/read-model handlers.",
    "services/layer3-knowledge/src/api/routes/variables.py": "Existing borderline module; planned follow-up split with formula route cleanup.",
}
ENTRYPOINT_SIZE_EXCEPTIONS = {
    "services/layer1-ingestion/src/layer1_ingestion/api/main.py": "Existing generated Layer 1 app-monolith compatibility entrypoint; planned follow-up split tracked in docs/launch/launch-standard-decision-package.md.",
}
APP_ROUTE_HANDLER_EXCEPTIONS = {
    "services/layer1-ingestion/src/layer1_ingestion/api/main.py:legacy_health_check": "Existing Layer 1 compatibility health route; planned follow-up extraction tracked with the entrypoint split.",
    "services/layer1-ingestion/src/layer1_ingestion/api/main.py:legacy_metrics": "Existing Layer 1 compatibility metrics route; planned follow-up extraction tracked with the entrypoint split.",
}
HTTP_DECORATORS = {"get", "post", "put", "patch", "delete", "options", "head"}


def _has_app_route_decorator(node: ast.AST) -> bool:
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return False

    for decorator in node.decorator_list:
        if not isinstance(decorator, ast.Call):
            continue
        if not isinstance(decorator.func, ast.Attribute):
            continue
        if decorator.func.attr not in HTTP_DECORATORS:
            continue
        owner = decorator.func.value
        if isinstance(owner, ast.Name) and owner.id == "app":
            return True
    return False


def test_service_main_entrypoints_stay_thin() -> None:
    oversized = [
        f"{entrypoint}: {entrypoint.stat().st_size} bytes"
        for entrypoint in ENTRYPOINTS
        if entrypoint.stat().st_size > MAX_ENTRYPOINT_BYTES
        and entrypoint.relative_to(REPO_ROOT).as_posix() not in ENTRYPOINT_SIZE_EXCEPTIONS
    ]

    assert not oversized, "Service API entrypoints must stay <= 35 KiB:\n" + "\n".join(oversized)


def test_service_main_entrypoints_do_not_define_app_route_handlers() -> None:
    violations: list[str] = []

    for entrypoint in ENTRYPOINTS:
        module = ast.parse(entrypoint.read_text(encoding="utf-8"))
        relative = entrypoint.relative_to(REPO_ROOT).as_posix()
        for node in module.body:
            if _has_app_route_decorator(node):
                handler = getattr(node, "name", "<unknown>")
                if f"{relative}:{handler}" in APP_ROUTE_HANDLER_EXCEPTIONS:
                    continue
                violations.append(f"{entrypoint}: {handler}")

    assert not violations, "Route handlers must live outside service api/main.py:\n" + "\n".join(violations)


def test_service_route_modules_respect_size_budget_or_document_exception() -> None:
    violations: list[str] = []

    for root in ROUTE_ROOTS:
        if not root.exists():
            continue
        for route_module in root.rglob("*.py"):
            relative = route_module.relative_to(REPO_ROOT).as_posix()
            if route_module.stat().st_size <= MAX_ROUTE_MODULE_BYTES:
                continue
            if relative in ROUTE_SIZE_EXCEPTIONS:
                continue
            violations.append(f"{relative}: {route_module.stat().st_size} bytes")

    assert not violations, "Route modules must stay <= 25 KiB or document an exception:\n" + "\n".join(violations)
