#!/usr/bin/env python3
"""Validate ``x-tenant-scope`` metadata on the Layer 4 API.

Verifies that:

1. Every entry in ``contracts/layer4-route-contract-matrix.json`` carries a
   ``tenant_scope`` from the canonical enum.
2. Every operation in ``contracts/openapi/layer4-agents.json`` carries an
   ``x-tenant-scope`` from the canonical enum.
3. Matrix ``tenant_scope`` and spec ``x-tenant-scope`` agree for every
   (method, path) pair.
4. Both agree with the canonical classifier in
   ``layer4_tenant_scope.py`` -- a route that should be ``GLOBAL`` /
   ``SYSTEM`` / ``TENANT_AND_BILLING_ACCOUNT`` cannot be silently relabeled
   ``TENANT`` (or vice versa) in one place only.

Emits one line per violation and exits non-zero when anything fails, so
drift in `x-tenant-scope` cannot pass CI.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ci"))

from layer4_tenant_scope import (  # noqa: E402
    classify_tenant_scope,
    is_valid_tenant_scope,
)

MATRIX = REPO_ROOT / "contracts" / "layer4-route-contract-matrix.json"
OPENAPI = REPO_ROOT / "contracts" / "openapi" / "layer4-agents.json"

HTTP_METHODS = frozenset({"get", "post", "put", "patch", "delete", "options", "head", "trace"})


def main() -> int:
    errors: list[str] = []

    matrix = json.loads(MATRIX.read_text(encoding="utf-8"))
    openapi = json.loads(OPENAPI.read_text(encoding="utf-8"))

    matrix_entries: dict[tuple[str, str], dict] = {}
    for entry in matrix.get("entries", []):
        method = str(entry.get("method", "")).upper()
        path = str(entry.get("openapi_path", ""))
        key = (method, path)
        if key in matrix_entries:
            errors.append(f"Duplicate matrix entry for {method} {path}")
        matrix_entries[key] = entry
        scope = entry.get("tenant_scope")
        if scope is None:
            errors.append(f"Matrix entry {method} {path} has no tenant_scope")
        elif not is_valid_tenant_scope(scope):
            errors.append(f"Matrix entry {method} {path} has invalid tenant_scope {scope!r}")

    paths = openapi.get("paths") or {}
    for path, item in sorted(paths.items()):
        if not isinstance(item, dict):
            continue
        for method, operation in item.items():
            if method.lower() not in HTTP_METHODS or method.startswith("x-"):
                continue
            key = (method.upper(), path)
            scope = operation.get("x-tenant-scope")
            if scope is None:
                errors.append(f"OpenAPI operation {method.upper()} {path} has no x-tenant-scope")
                continue
            if not is_valid_tenant_scope(scope):
                errors.append(
                    f"OpenAPI operation {method.upper()} {path} has invalid x-tenant-scope {scope!r}"
                )

            matrix_entry = matrix_entries.get(key)
            expected = classify_tenant_scope(method, path)
            if matrix_entry is None:
                errors.append(f"OpenAPI operation {method.upper()} {path} missing from route matrix")
                continue
            matrix_scope = matrix_entry.get("tenant_scope")
            if matrix_scope != scope:
                errors.append(
                    f"{method.upper()} {path}: matrix tenant_scope {matrix_scope!r} != "
                    f"OpenAPI x-tenant-scope {scope!r}"
                )
            if scope != expected:
                errors.append(
                    f"{method.upper()} {path}: x-tenant-scope {scope!r} diverges from "
                    f"classifier (expected {expected!r})"
                )

    if errors:
        print("\n".join(errors))
        print(f"\n{len(errors)} tenant-scope violation(s) in Layer 4 contract.")
        return 1
    print(
        f"x-tenant-scope check passed: {len(matrix.get('entries', []))} matrix entries, "
        f"{len(paths)} paths."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
