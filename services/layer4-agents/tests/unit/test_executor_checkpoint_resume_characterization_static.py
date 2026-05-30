from __future__ import annotations

import ast
from pathlib import Path

ENGINE_DIR = Path(__file__).resolve().parents[2] / "src" / "layer4_agents" / "engine"
EXECUTOR = ENGINE_DIR / "executor.py"
HELPER = ENGINE_DIR / "checkpoint_replay.py"


def _class_node(tree: ast.AST, name: str) -> ast.ClassDef:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == name:
            return node
    raise AssertionError(f"missing class {name}")


def _method_names(cls: ast.ClassDef) -> set[str]:
    return {
        node.name
        for node in cls.body
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    }


def test_orchestration_controller_preserves_public_resume_methods() -> None:
    tree = ast.parse(EXECUTOR.read_text())
    controller = _class_node(tree, "OrchestrationController")

    assert {"resume_workflow", "resume_from_checkpoint"} <= _method_names(controller)


def test_checkpoint_replay_helpers_are_extracted_and_executor_delegates() -> None:
    helper_tree = ast.parse(HELPER.read_text())
    helper_functions = {
        node.name
        for node in helper_tree.body
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    }
    assert {
        "compute_state_hash",
        "resolve_resume_policy",
        "get_latest_persisted_checkpoint_hash",
    } <= helper_functions

    executor_tree = ast.parse(EXECUTOR.read_text())
    calls = {
        node.func.id
        for node in ast.walk(executor_tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert {
        "compute_state_hash",
        "resolve_resume_policy",
        "get_latest_persisted_checkpoint_hash",
    } <= calls
