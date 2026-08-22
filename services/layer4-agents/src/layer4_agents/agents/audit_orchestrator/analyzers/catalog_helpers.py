"""Helper utilities for filesystem traversal, file reading, and configuration parsing in audit finding checks."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

# Directories that are never traversed by catalog checks.
_EXCLUDED_DIRS: set[str] = {
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "dist",
    "build",
    ".audit_cache",
    "audit_reports",
    ".infisical",
    ".turbo",
    ".next",
    "coverage",
    ".coverage",
    "htmlcov",
}


def _is_excluded(path: Path) -> bool:
    """Return True if any segment of ``path`` matches :data:`_EXCLUDED_DIRS`."""
    return bool(set(path.parts) & _EXCLUDED_DIRS)


def _walk_files(
    repo_path: Path,
    roots: list[Path] | None = None,
    extensions: set[str] | None = None,
) -> list[Path]:
    """Recursively collect file paths under *roots* (or *repo_path*), skipping excluded dirs."""
    targets = roots if roots is not None else [repo_path]
    result: list[Path] = []
    for root in targets:
        if not root.exists():
            continue
        for p in root.rglob("*"):
            if p.is_file() and not _is_excluded(p):
                if extensions is None or p.suffix in extensions:
                    result.append(p)
    return result


def _source_files(repo_path: Path, extensions: set[str]) -> list[Path]:
    """Collect source files within ``services/``, ``apps/``, and ``packages/``."""
    search_roots = [
        repo_path / "services",
        repo_path / "apps",
        repo_path / "packages",
    ]
    return _walk_files(
        repo_path,
        roots=[r for r in search_roots if r.exists()],
        extensions=extensions,
    )


def _py_files(repo_path: Path) -> list[Path]:
    """Collect all Python source files in the repo (skipping excluded dirs)."""
    return _walk_files(repo_path, extensions={".py"})


def _read_lines(file_path: Path) -> list[str]:
    """Read a file and return non-empty stripped lines."""
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
        return [line for line in content.splitlines() if line.strip()]
    except OSError:
        return []


def _line_count(file_path: Path) -> int:
    """Return the total line count for a file."""
    try:
        return len(file_path.read_text(encoding="utf-8", errors="replace").splitlines())
    except OSError:
        return 0


def _match_count(files: list[Path], pattern: re.Pattern[str]) -> tuple[int, list[str]]:
    """Count regex matches across a collection of files, returning total and sample snippets."""
    total = 0
    snippets: list[str] = []
    for file_path in files:
        lines = _read_lines(file_path)
        for i, line in enumerate(lines, start=1):
            if pattern.search(line):
                total += 1
                if len(snippets) < 10:
                    snippets.append(f"{file_path}:{i}: {line.strip()[:80]}")
    return total, snippets


def _load_yaml(path: Path) -> dict[str, Any] | None:
    """Attempt to parse a YAML file, returning a dict or None on error."""
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            data = yaml.safe_load(f)
            return data if isinstance(data, dict) else None
    except Exception:
        return None


def _find_pyprojects(repo_path: Path) -> list[Path]:
    """Find all pyproject.toml files in the repository."""
    return _walk_files(repo_path, extensions={".toml"})


def _pyproject_sections(repo_path: Path, section: str) -> list[tuple[Path, Any]]:
    """Extract a specific ``[tool.<section>]`` config block across all pyproject.toml files."""
    found: list[tuple[Path, Any]] = []
    for pyproject in _find_pyprojects(repo_path):
        if pyproject.name != "pyproject.toml":
            continue
        data = _load_yaml(pyproject)
        if not data:
            continue
        tool = data.get("tool", {})
        if section in tool:
            found.append((pyproject, tool[section]))
    return found
