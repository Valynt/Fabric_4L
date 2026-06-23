"""Small helpers for centralized production-readiness selector suites."""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]


def repo_path(relative_path: str) -> Path:
    return REPO_ROOT / relative_path


def read_text(relative_path: str) -> str:
    return repo_path(relative_path).read_text(encoding="utf-8")


def read_json(relative_path: str) -> dict:
    return json.loads(read_text(relative_path))


def assert_paths_exist(paths: Iterable[str], *, label: str) -> None:
    missing = [path for path in paths if not repo_path(path).exists()]
    assert not missing, f"{label} references missing paths: {missing}"


def assert_pytest_coverage(paths: Iterable[str], *, label: str) -> None:
    paths = tuple(paths)
    assert paths, f"{label} must reference at least one pytest file"
    assert_paths_exist(paths, label=label)
    without_tests = [path for path in paths if repo_path(path).is_file() and not _has_discoverable_tests(repo_path(path))]
    assert not without_tests, f"{label} references pytest files with no discoverable tests: {without_tests}"


def assert_contains_all(relative_path: str, tokens: Iterable[str], *, label: str | None = None) -> None:
    path = repo_path(relative_path)
    source = path.read_text(encoding="utf-8")
    missing = [token for token in tokens if token not in source]
    assert not missing, f"{label or relative_path} is missing required tokens: {missing}"


def assert_readme_has_sections(relative_path: str = "tests/README.md") -> None:
    source = read_text(relative_path)
    required = (
        "## What This Suite Validates",
        "## Production Risks Covered",
        "## Existing Coverage Aggregated",
        "## Known Gaps",
        "## How To Run",
        "## CI Artifact",
    )
    missing = [section for section in required if section not in source]
    assert not missing, f"{relative_path} is missing production-readiness README sections: {missing}"


def assert_readme_documents_gap(relative_path: str, gap_token: str) -> None:
    source = read_text(relative_path)
    assert "## Known Gaps" in source, f"{relative_path} must document known gaps"
    assert gap_token in source, f"{relative_path} must document gap token {gap_token!r}"


def _has_discoverable_tests(path: Path) -> bool:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
            return True
        if isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
            return True
    return False

