#!/usr/bin/env python3
"""AST-based enforcement of Layer 4 canonical paths."""

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
L4_SRC = ROOT / "services" / "layer4-agents" / "src"
CANON = L4_SRC / "layer4_agents"
ALLOWED_TOP_LEVEL_DIRS = {
    "adapters", "agents", "api", "config", "contexts", "contracts",
    "engine", "feature_flags", "harness", "integration", "interfaces",
    "messaging", "metrics", "models", "policies", "provenance", "registry",
    "services", "shared", "skills", "startup", "test_support",
}


def _is_star_import_shim(module: ast.Module) -> bool:
    for node in module.body:
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
            continue  # docstring
        if isinstance(node, ast.ImportFrom):
            if node.module and node.module.startswith("layer4_agents."):
                if any(a.name == "*" for a in node.names):
                    return True
    return False


def _has_implementation(module: ast.Module) -> bool:
    for node in ast.walk(module):
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            return True
    return False


def _collect_violations() -> list[str]:
    violations = []

    # 1. Top-level files must be shims if a canonical counterpart exists.
    for path in L4_SRC.glob("*.py"):
        if path.name == "__init__.py":
            continue
        if not (CANON / path.name).exists():
            continue
        module = ast.parse(path.read_text(encoding="utf-8"))
        if not _is_star_import_shim(module):
            violations.append(f"{path}: top-level file with canonical counterpart must be a star-import shim")

    # 2. Top-level directories must remain shims.
    for path in L4_SRC.iterdir():
        if not path.is_dir() or path.name not in ALLOWED_TOP_LEVEL_DIRS:
            continue
        for py_file in path.rglob("*.py"):
            module = ast.parse(py_file.read_text(encoding="utf-8"))
            if _has_implementation(module) and not _is_star_import_shim(module):
                violations.append(f"{py_file}: top-level dir must be a shim")

    # 3. Canonical code must not import from top-level src.* modules.
    for py_file in CANON.rglob("*.py"):
        module = ast.parse(py_file.read_text(encoding="utf-8"))
        for node in ast.walk(module):
            if isinstance(node, ast.ImportFrom):
                if node.module and node.module.startswith("src."):
                    violations.append(f"{py_file}: canonical code imports {node.module}")

    return violations


def main() -> int:
    violations = _collect_violations()
    if violations:
        print("Layer 4 canonical path violations:")
        for v in violations:
            print(f"  - {v}")
        return 1
    print("Layer 4 canonical paths OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
