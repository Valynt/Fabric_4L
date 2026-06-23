#!/usr/bin/env python3
"""Fail if the legacy Layer 1 api.main entrypoint regains implementation logic."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CANONICAL = ROOT / "services/layer1-ingestion/src/layer1_ingestion/api/main.py"
SHIM = ROOT / "services/layer1-ingestion/src/api/main.py"
CANONICAL_IMPORT = "layer1_ingestion.api"
CANONICAL_MODULE_ATTR = "main"


def _call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    if isinstance(node, ast.Call):
        return _call_name(node.func)
    return None


def _imports_canonical_main(tree: ast.Module) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            imports_canonical = node.module == CANONICAL_IMPORT and any(
                alias.name == CANONICAL_MODULE_ATTR for alias in node.names
            )
            if imports_canonical:
                return True
        if isinstance(node, ast.Import):
            imports_canonical = any(
                alias.name == f"{CANONICAL_IMPORT}.{CANONICAL_MODULE_ATTR}"
                for alias in node.names
            )
            if imports_canonical:
                return True
    return False


def _implementation_nodes(tree: ast.Module) -> list[tuple[int, str]]:
    findings: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            findings.append((node.lineno, type(node).__name__))
        elif isinstance(node, ast.Call) and _call_name(node.func) in {
            "FastAPI",
            "APIRouter",
            "create_fabric_app",
        }:
            findings.append((node.lineno, f"call:{_call_name(node.func)}"))
    return sorted(findings)


def main() -> int:
    if not CANONICAL.exists():
        print(f"FAIL: canonical Layer 1 API main file is missing: {CANONICAL.relative_to(ROOT)}")
        return 1
    if not SHIM.exists():
        print(f"FAIL: legacy Layer 1 API main shim is missing: {SHIM.relative_to(ROOT)}")
        return 1

    shim_tree = ast.parse(SHIM.read_text(encoding="utf-8"), filename=str(SHIM))
    if not _imports_canonical_main(shim_tree):
        print(
            "FAIL: legacy Layer 1 api.main must import/re-export "
            f"{CANONICAL_IMPORT}.{CANONICAL_MODULE_ATTR}."
        )
        return 1

    implementation_nodes = _implementation_nodes(shim_tree)
    if implementation_nodes:
        print("FAIL: legacy Layer 1 api.main contains independent implementation logic:")
        for lineno, kind in implementation_nodes:
            print(f" - {SHIM.relative_to(ROOT)}:{lineno} ({kind})")
        print(
            f"Move implementation logic to {CANONICAL.relative_to(ROOT)} "
            "and keep the legacy file a shim."
        )
        return 1

    print("Layer 1 API main shim drift check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
