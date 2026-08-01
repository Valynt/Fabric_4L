"""Cross-tenant adversarial contract tests for Layer 4 streaming/checkpoint endpoints."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = [pytest.mark.security, pytest.mark.tenant_boundary]

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_LAYER4_ROUTES = _PROJECT_ROOT / "services" / "layer4-agents" / "src" / "layer4_agents" / "api" / "routes"
_WORKFLOWS_FILE = _LAYER4_ROUTES / "workflows.py"
_CHECKPOINTS_FILE = _LAYER4_ROUTES / "checkpoints.py"
_AGENT_STREAM_FILE = _LAYER4_ROUTES / "agent_stream.py"
_C1_FILE = _LAYER4_ROUTES / "c1.py"


def _function_node(filepath: Path, func_name: str) -> ast.FunctionDef | ast.AsyncFunctionDef:
    tree = ast.parse(filepath.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == func_name:
            return node
    raise AssertionError(f"Function {func_name} not found in {filepath}")


def _uses_depends(func_node: ast.FunctionDef | ast.AsyncFunctionDef, dependency_name: str) -> bool:
    for default in list(func_node.args.defaults) + [d for d in func_node.args.kw_defaults if d is not None]:
        if isinstance(default, ast.Call) and isinstance(default.func, ast.Name) and default.func.id == "Depends":
            for arg in default.args:
                if isinstance(arg, ast.Name) and arg.id == dependency_name:
                    return True
    return False


def _has_request_tenant_override(func_node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    source = ast.unparse(func_node).lower()
    return "x-tenant-id" in source or "tenant_id:" in source and "header(" in source


class TestLayer4StreamEndpointsAuthContract:
    """Fail-closed and auth-derived tenant requirements for stream-producing endpoints."""

    @pytest.mark.parametrize(
        "filepath,func_name",
        [
            (_WORKFLOWS_FILE, "get_workflow_events"),
            (_WORKFLOWS_FILE, "resume_workflow"),
            (_CHECKPOINTS_FILE, "list_checkpoints"),
            (_CHECKPOINTS_FILE, "get_checkpoint_state"),
            (_CHECKPOINTS_FILE, "resume_from_checkpoint"),
            (_AGENT_STREAM_FILE, "agent_stream_chat_sse"),
            (_C1_FILE, "stream_c1"),
        ],
    )
    def test_stream_and_checkpoint_endpoints_require_authenticated_context(self, filepath: Path, func_name: str):
        node = _function_node(filepath, func_name)
        assert _uses_depends(node, "require_authenticated"), (
            f"{filepath.name}::{func_name} must require authenticated context so tenant is derived "
            "from JWT/session claims only and fails closed when missing."
        )

    @pytest.mark.parametrize(
        "filepath,func_name",
        [
            (_WORKFLOWS_FILE, "get_workflow_events"),
            (_WORKFLOWS_FILE, "resume_workflow"),
            (_CHECKPOINTS_FILE, "list_checkpoints"),
            (_CHECKPOINTS_FILE, "get_checkpoint_state"),
            (_CHECKPOINTS_FILE, "resume_from_checkpoint"),
            (_AGENT_STREAM_FILE, "agent_stream_chat_sse"),
            (_C1_FILE, "stream_c1"),
        ],
    )
    def test_stream_and_checkpoint_endpoints_do_not_accept_tenant_override_headers(self, filepath: Path, func_name: str):
        node = _function_node(filepath, func_name)
        assert not _has_request_tenant_override(node), (
            f"{filepath.name}::{func_name} appears to accept tenant override input. "
            "Tenant identity must come only from authenticated context."
        )
