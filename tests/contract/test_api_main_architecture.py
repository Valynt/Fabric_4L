"""Architecture tests for API entrypoints."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
ENTRYPOINTS = [
    REPO_ROOT / "services/layer2-extraction/src/layer2_extraction/api/main.py",
    REPO_ROOT / "services/layer6-benchmarks/src/api/main.py",
]
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
        value = decorator.func.value
        if isinstance(value, ast.Name) and value.id == "app":
            return True
    return False


@pytest.mark.xfail(
    strict=False,
    reason=(
        "Architectural debt: L2 main.py defines health_check, extract_and_ingest, "
        "get_pipeline_status, stream_job_events inline; L6 main.py defines metrics_endpoint inline. "
        "These must be moved to api/routes/ modules. Tracked as refactor backlog."
    ),
)
def test_main_entrypoints_do_not_define_route_handlers() -> None:
    violations: list[str] = []

    for entrypoint in ENTRYPOINTS:
        module = ast.parse(entrypoint.read_text())
        for node in module.body:
            if _has_app_route_decorator(node):
                violations.append(f"{entrypoint}: {getattr(node, 'name', '<unknown>')}")

    assert not violations, "Route handlers must live in api/routes modules:\n" + "\n".join(violations)
