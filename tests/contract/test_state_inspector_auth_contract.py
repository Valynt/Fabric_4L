"""Auth dependency contract tests for state inspector routes.

Uses AST parsing to verify the auth dependency contract without importing
Layer 4 modules. A full runtime import of ``value_fabric.layer4`` requires
the complete service dependency stack (redis, sqlalchemy, celery, etc.) which
is not available in the test environment without all service deps installed.

The AST approach is intentional and sufficient for this contract: it verifies
the source-level auth wiring (``Depends(require_authenticated)``) without
needing a running service. This should be replaced with a runtime import test
once the full service dep stack is available in CI.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest


def _get_analyze_errors_ast_node():
    src = (
        Path(__file__).resolve().parents[2]
        / "services"
        / "layer4-agents"
        / "src"
        / "layer4_agents"
        / "api"
        / "routes"
        / "state_inspector.py"
    )
    tree = ast.parse(src.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "analyze_errors":
            return node
    pytest.fail("analyze_errors not found in state_inspector.py")


def test_analyze_errors_requires_authenticated_dependency() -> None:
    """Error inspection route must require authenticated context."""

    func = _get_analyze_errors_ast_node()

    ctx_param = None
    for arg in func.args.args + func.args.kwonlyargs:
        if arg.arg == "_ctx":
            ctx_param = arg
            break

    assert ctx_param is not None, "Missing _ctx parameter"

    # Find the default value for _ctx
    if func.args.kwonlyargs and ctx_param in func.args.kwonlyargs:
        kw_index = func.args.kwonlyargs.index(ctx_param)
        default_node = func.args.kw_defaults[kw_index] if kw_index < len(func.args.kw_defaults) else None
    else:
        pos_index = func.args.args.index(ctx_param)
        defaults_start = len(func.args.args) - len(func.args.defaults)
        if pos_index >= defaults_start:
            default_node = func.args.defaults[pos_index - defaults_start]
        else:
            default_node = None

    assert default_node is not None, "_ctx has no default value"
    assert isinstance(default_node, ast.Call), "_ctx default is not a call"
    # Check it's Depends(require_authenticated)
    assert isinstance(default_node.func, ast.Name), "_ctx default is not Depends(...)"
    assert default_node.func.id == "Depends", "_ctx default is not Depends"
    assert len(default_node.args) == 1, "Depends() should have one argument"
    assert isinstance(default_node.args[0], ast.Name), "Depends argument is not a name"
    assert default_node.args[0].id == "require_authenticated", "Depends argument is not require_authenticated"
