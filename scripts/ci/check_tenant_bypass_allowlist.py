#!/usr/bin/env python3
"""Tenant bypass allowlist enforcement gate.

Scans Layer 1 source code for require_tenant=False usages and fails
if any usage is found outside the explicit allowlist.  All bypass
usage must be documented, reviewed, and tracked in this gate.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

# Roots to scan
SCAN_ROOTS = (
    Path("services/layer1-ingestion/src"),
    Path("value_fabric/layer1"),
)

# Allowlisted bypass usages.
# Each entry is (relative_path, function_or_method_name, reason).
# The function name is matched against the enclosing function/class scope.
ALLOWLIST: tuple[tuple[str, str | None, str], ...] = (
    # robots_checker.py: global public metadata cache for robots.txt.
    # The cache stores only public robots.txt data; tenant_id column is legacy/system-owned.
    ("compliance/robots_checker.py", "_get_cached_robots_txt", "global public robots.txt cache read"),
    ("compliance/robots_checker.py", "_cache_robots_txt", "global public robots.txt cache write"),
    # database.py: fail-safe session helper itself emits metric on bypass.
    ("shared/database.py", "get_db_session", "session helper definition with metric emission"),
    # tasks.py: system maintenance reads from tenant_registry (explicit system table, no RLS).
    ("shared/tasks.py", "cleanup_old_content", "system maintenance reads tenant_registry (system table)"),
)


def _enclosing_scope(node: ast.AST) -> str | None:
    """Walk up the AST to find the nearest function/class name."""
    current: ast.AST | None = node
    while current is not None:
        if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return current.name
        if isinstance(current, ast.ClassDef):
            return current.name
        current = getattr(current, "parent", None)
    return None


def _set_parents(tree: ast.AST) -> None:
    """Set parent references on all nodes for scope walking."""
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            setattr(child, "parent", node)


def _find_require_tenant_false_usages(source: str, path: Path) -> list[tuple[int, str | None, str]]:
    """Return list of (line_no, scope_name, line_text) for each bypass usage."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    _set_parents(tree)
    usages: list[tuple[int, str | None, str]] = []
    lines = source.splitlines()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            for kw in node.keywords:
                if kw.arg == "require_tenant" and isinstance(kw.value, ast.Constant) and kw.value.value is False:
                    scope = _enclosing_scope(node)
                    usages.append((node.lineno, scope, lines[node.lineno - 1].strip() if node.lineno <= len(lines) else ""))
    return usages


def main() -> int:
    errors: list[str] = []
    for root in SCAN_ROOTS:
        if not root.exists():
            continue
        for py_file in sorted(root.rglob("*.py")):
            if "__pycache__" in str(py_file):
                continue
            rel = py_file.relative_to(root)
            source = py_file.read_text(encoding="utf-8")
            usages = _find_require_tenant_false_usages(source, py_file)
            for line_no, scope, line_text in usages:
                rel_posix = rel.as_posix()
                allowed = any(
                    rel_posix.endswith(allow_path) and (allow_scope is None or allow_scope == scope)
                    for allow_path, allow_scope, _reason in ALLOWLIST
                )
                if not allowed:
                    errors.append(
                        f"{py_file}:{line_no}  scope={scope}  require_tenant=False not in allowlist\n"
                        f"    {line_text}"
                    )

    if errors:
        print("ERROR: Tenant bypass allowlist check failed.\n")
        for error in errors:
            print(f" - {error}")
        print(
            "\nAll require_tenant=False usages must be documented in "
            "scripts/ci/check_tenant_bypass_allowlist.py ALLOWLIST."
        )
        return 1

    print("Tenant bypass allowlist check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
