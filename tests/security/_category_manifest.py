"""Helpers for security category aggregation tests."""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def assert_security_category_manifest(category: str, paths: tuple[str, ...]) -> None:
    """Assert a security category references existing, discoverable tests."""
    assert paths, f"{category} security category must reference at least one test file"

    missing: list[str] = []
    undiscoverable: list[str] = []
    for relative_path in paths:
        path = REPO_ROOT / relative_path
        if not path.is_file():
            missing.append(relative_path)
            continue
        if not _has_discoverable_tests(path):
            undiscoverable.append(relative_path)

    assert not missing, f"{category} security category references missing files: {missing}"
    assert not undiscoverable, (
        f"{category} security category references files with no pytest-discoverable tests: "
        f"{undiscoverable}"
    )


def _has_discoverable_tests(path: Path) -> bool:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
            return True
        if isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
            return True
    return False
