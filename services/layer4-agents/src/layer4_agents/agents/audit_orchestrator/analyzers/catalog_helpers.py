"""Helper utilities for filesystem traversal, file reading, and configuration parsing in audit finding checks."""

from __future__ import annotations

import os
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
    """Return True if any path component should be skipped."""
    return any(part in _EXCLUDED_DIRS for part in path.parts)


def _walk_files(
    repo_path: Path,
    roots: list[Path] | None = None,
    extensions: set[str] | None = None,
) -> list[Path]:
    """Walk configured roots while pruning excluded directories.

    This avoids descending into ``node_modules``, ``.venv``, ``.git``, etc.,
    which keeps large repository scans fast.
    """
    results: list[Path] = []
    search_roots = roots or [repo_path]
    for root in search_roots:
        if not root.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(str(root), topdown=True):
            # Prune excluded directories in-place so os.walk does not descend.
            dirnames[:] = [d for d in dirnames if d not in _EXCLUDED_DIRS]
            for filename in filenames:
                file_path = Path(dirpath) / filename
                if extensions is None or file_path.suffix.lower() in extensions:
                    results.append(file_path)
    return results


def _source_files(repo_path: Path, extensions: set[str]) -> list[Path]:
    """Yield non-excluded source files with the given extensions."""
    return _walk_files(repo_path, extensions=extensions)


def _py_files(repo_path: Path) -> list[Path]:
    """Collect all Python source files in the repo (skipping excluded dirs)."""
    return _source_files(repo_path, {".py"})


def _read_lines(path: Path) -> list[str]:
    """Read a text file, returning a list of physical lines.

    Errors are ignored so that binary or malformed files do not abort a run.
    Caching is intentionally avoided here: a process-wide cache would retain
    stale file contents across audit runs and across different repositories.
    """
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as fh:
            return fh.readlines()
    except (OSError, UnicodeDecodeError):
        return []


def _line_count(path: Path) -> int:
    """Return the total line count for a file."""
    return len(_read_lines(path))


def _match_count(files: list[Path], pattern: re.Pattern[str]) -> tuple[int, list[str]]:
    """Count regex matches across a collection of files, returning total and sample snippets."""
    total = 0
    snippets: list[str] = []
    for file_path in files:
        try:
            for i, line in enumerate(_read_lines(file_path), start=1):
                if pattern.search(line):
                    total += 1
                    if len(snippets) < 10:
                        snippets.append(f"{file_path}:{i}: {line.strip()[:80]}")
        except Exception:
            continue
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
