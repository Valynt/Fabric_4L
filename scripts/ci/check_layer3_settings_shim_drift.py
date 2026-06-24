#!/usr/bin/env python3
"""Validate Layer 3 settings canonical coverage and service-wrapper shim discipline.

Per ADR-027, the canonical settings module is:
  services/layer3-knowledge/src/config/settings.py

The historical service-local compat shim path is:
  services/layer3-knowledge/src/config.py
  (must remain either a thin re-export or an inert docstring-only marker)
"""

from __future__ import annotations

import ast
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
# Canonical settings per ADR-027 (services/ is the authoritative tree)
CANONICAL = ROOT / "services/layer3-knowledge/src/config/settings.py"
# Service-local compat shim (re-exports from canonical via value_fabric.layer3.config)
SHIM = ROOT / "services/layer3-knowledge/src/config.py"

REQUIRED_FIELDS = {
    "API_PORT",
    "NEO4J_URI",
    "NEO4J_USER",
    "NEO4J_PASSWORD",
    "NEO4J_DATABASE",
    "RATE_LIMIT_ENABLED",
    "RATE_LIMIT_REQUESTS_PER_MINUTE",
    "RATE_LIMIT_BURST_SIZE",
    "METRICS_ENABLED",
    "METRICS_PATH",
    "CORS_ORIGINS",
    "JWT_SECRET",
}


def _extract_aliases(module: ast.Module) -> set[str]:
    aliases: set[str] = set()
    for node in ast.walk(module):
        if isinstance(node, ast.AnnAssign) and isinstance(node.value, ast.Call):
            call = node.value
            if isinstance(call.func, ast.Name) and call.func.id == "Field":
                for kw in call.keywords:
                    if kw.arg == "alias" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                        aliases.add(kw.value.value)
    return aliases


def _is_inert_marker_shim(module: ast.Module) -> bool:
    """Return true for the intentionally shadowed docstring-only config.py marker."""
    docstring = ast.get_docstring(module) or ""
    body_after_docstring = module.body[1:] if module.body and isinstance(module.body[0], ast.Expr) else module.body
    return (
        not body_after_docstring
        and "config/ package" in docstring
        and "never imported" in docstring
    )


def _validate_shim(module: ast.Module) -> list[str]:
    """Shim must be a thin re-export or inert marker; no local logic allowed."""
    errors: list[str] = []
    class_defs = [node.name for node in module.body if isinstance(node, ast.ClassDef)]
    if class_defs:
        errors.append(f"Shim must not define classes, found: {', '.join(class_defs)}")

    fn_defs = [node.name for node in module.body if isinstance(node, ast.FunctionDef)]
    if fn_defs:
        errors.append(f"Shim must not define functions, found: {', '.join(fn_defs)}")

    if errors:
        return errors

    if _is_inert_marker_shim(module):
        return []

    # Accept wildcard re-export from any value_fabric.layer3.config* path
    has_wildcard_reexport = any(
        isinstance(node, ast.ImportFrom)
        and node.module is not None
        and node.module.startswith("value_fabric.layer3.config")
        and any(alias.name == "*" for alias in node.names)
        for node in module.body
    )
    if not has_wildcard_reexport:
        errors.append(
            "Shim must re-export via wildcard from value_fabric.layer3.config "
            "(or submodule), or be the documented docstring-only inert marker"
        )
    return errors


def main() -> int:
    if not CANONICAL.exists():
        print(f"ERROR: Canonical settings not found at {CANONICAL}", file=sys.stderr)
        return 1

    canonical_ast = ast.parse(CANONICAL.read_text(encoding="utf-8"))

    errors: list[str] = []

    if SHIM.exists():
        shim_ast = ast.parse(SHIM.read_text(encoding="utf-8"))
        errors.extend(_validate_shim(shim_ast))

    aliases = _extract_aliases(canonical_ast)
    missing = sorted(REQUIRED_FIELDS - aliases)
    if missing:
        errors.append(f"Canonical settings is missing required operational aliases: {', '.join(missing)}")

    if errors:
        print("Layer 3 settings shim drift detected:")
        for error in errors:
            print(f" - {error}")
        return 1

    print("Layer 3 settings shim drift check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
