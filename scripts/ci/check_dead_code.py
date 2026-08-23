#!/usr/bin/env python3
"""Detect unused top-level functions, classes, and imports in tracked Python.

Conservative dead-code guard. Only flags module-level ``def``/``class`` and
``import`` symbols that are unreferenced anywhere in the tracked tree.
Symbols that are referenced only through dynamic patterns (string constants,
attribute access, decorators, getattr-style dispatch) are never flagged, and
an explicit allowlist in ``config/ci/dead_code_allowlist.txt`` suppresses
future-reserved or intentionally exported names.

Scope rules:

* Only top-level functions, classes, and imports are scanned. Module-level
  variables and constants are intentionally not flagged.
* ``_``-private names are skipped (test helpers, module internals).
* Decorated definitions are assumed live (FastAPI routes, registration
  callbacks, dynamic dispatch) and skipped.
* ``if TYPE_CHECKING`` imports and ``__future__`` imports are skipped.
* ``__init__.py`` barrel files are reference providers, never flagged.
* Test files (paths whose segments match test conventions) are never flagged.

Exit code 0 = clean; 1 = findings found.
"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path.cwd()
ALLOWLIST_PATH = REPO_ROOT / "config" / "ci" / "dead_code_allowlist.txt"

# Trees scanned for unused symbols. Everything else (scripts/ci, docs,
# tools, tests/test files) still contributes references, so dynamic/direct
# usage is always honored without flagging tooling internals.
SCAN_PREFIXES = ("services/", "packages/")

TEST_SEGMENTS = ("tests", "test", "tests_unit", "test_")


def _is_test_relpath(rel: str) -> bool:
    """True if any path segment looks like a test directory."""
    for part in rel.split("/"):
        if part in TEST_SEGMENTS or part.endswith("_tests") or part.endswith("_test"):
            return True
    return False


class _ModuleInfo:
    """Collect top-level bindings and reference names for one module."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.bindings: list[tuple[int, str, str]] = []  # (lineno, kind, name)

    @staticmethod
    def _collect_references(tree: ast.Module) -> set[str]:
        refs: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                refs.add(node.id)
            elif isinstance(node, ast.Attribute):
                refs.add(node.attr)
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                refs.add(node.value)
        # `__all__ = [...]` marks an intentional public export surface even if
        # nothing in-tree references the name directly.
        for node in tree.body:
            if (
                isinstance(node, ast.Assign)
                and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id == "__all__"
                and isinstance(node.value, (ast.List, ast.Tuple))
            ):
                for elt in node.value.elts:
                    if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                        refs.add(elt.value)
        return refs

    def collect(self, text: str) -> set[str]:
        """Populate bindings and return the set of all referenced names."""
        tree = ast.parse(text, filename=str(self.path))
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._record_def(node.name, node.lineno, node.decorator_list)
            elif isinstance(node, ast.ClassDef):
                self._record_def(node.name, node.lineno, node.decorator_list)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "__future__":
                        continue
                    name = alias.asname or alias.name.split(".")[0]
                    self.bindings.append((node.lineno, "import", name))
            elif isinstance(node, ast.ImportFrom):
                if node.module == "__future__":
                    continue
                for alias in node.names:
                    if alias.name == "*":
                        continue
                    name = alias.asname or alias.name
                    self.bindings.append((node.lineno, "import", name))
        return self._collect_references(tree)

    def _record_def(
        self,
        name: str,
        lineno: int,
        decorators: list[ast.expr],
    ) -> None:
        if name.startswith("_") or decorators:
            return
        self.bindings.append((lineno, "def", name))


def _tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files"], check=True, capture_output=True, text=True
    )
    return [REPO_ROOT / line for line in result.stdout.splitlines() if line.strip()]


def _load_allowlist() -> set[tuple[str, str]]:
    """Load {path}|{symbol} allowances; bare symbols are global allowances."""
    if not ALLOWLIST_PATH.exists():
        return set()
    entries: set[tuple[str, str]] = set()
    for line in ALLOWLIST_PATH.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "|" in stripped:
            entries.add(tuple(part.strip() for part in stripped.split("|", 1)))
        else:
            entries.add(("*", stripped))
    return entries


def _is_test_path(rel: str) -> bool:
    """True for pytest convention paths: test directories, ``test_*.py``,
    ``*_test.py``, and ``conftest.py``. Never flagged as dead."""
    name = Path(rel).name
    if name == "conftest.py":
        return True
    if name.startswith("test_") or name.endswith("_test.py"):
        return True
    for part in rel.split("/"):
        if part in TEST_SEGMENTS or part.endswith("_tests") or part.endswith("_test"):
            return True
    return False


def _is_scanned(path: Path) -> bool:
    rel = str(path.relative_to(REPO_ROOT)).replace("\\", "/")
    if not (rel.endswith(".py") and rel.startswith(SCAN_PREFIXES)):
        return False
    if Path(rel).name == "__init__.py":
        return False
    if _is_test_path(rel):
        return False
    return True


def _main() -> int:
    allowlist = _load_allowlist()
    files = _tracked_files()

    scanned: list[_ModuleInfo] = []
    global_refs: set[str] = set()

    for path in files:
        if not path.is_file() or path.suffix != ".py":
            continue
        try:
            text = path.read_text(encoding="utf-8")
            tree = ast.parse(text, filename=str(path))
        except (OSError, UnicodeDecodeError, SyntaxError):
            continue
        global_refs.update(_ModuleInfo._collect_references(tree))
        # Every `from X import name` is a directional reference to X, so alias
        # renames like `from .routes import register_routes as rr` still count.
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name != "*":
                        global_refs.add(alias.name)
        if not _is_scanned(path):
            continue
        info = _ModuleInfo(path)
        refs = info.collect(text)
        scanned.append(info)
        global_refs.update(refs)

    findings: list[str] = []
    for info in scanned:
        for lineno, kind, name in info.bindings:
            if name in global_refs:
                continue
            rel = str(info.path.relative_to(REPO_ROOT)).replace("\\", "/")
            if (rel, name) in allowlist or ("*", name) in allowlist:
                continue
            findings.append(f"{rel}::{lineno}  {kind} {name}")

    if findings:
        print("ERROR: Dead-code guard failed - unreferenced top-level symbols:")
        for finding in sorted(findings):
            print(f"  {finding}")
        print("")
        print(
            "If a symbol is used dynamically or reserved for future use, add "
            f"'{ALLOWLIST_PATH}' entry as 'PATH|SYMBOL' or bare 'SYMBOL'."
        )
        return 1

    print(
        "OK: Dead-code guard passed - no unreferenced top-level symbols "
        "outside the allowlist."
    )
    return 0


if __name__ == "__main__":
    sys.exit(_main())
