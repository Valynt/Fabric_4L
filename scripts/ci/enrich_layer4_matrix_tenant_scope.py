#!/usr/bin/env python3
"""Seed ``tenant_scope`` onto Layer 4 route-contract-matrix entries.

Reads every operation from ``contracts/openapi/layer4-agents.json``,
classifies it via :mod:`layer4_tenant_scope`, and writes ``tenant_scope``
into each corresponding ``contracts/layer4-route-contract-matrix.json``
entry. Classification is idempotent: existing ``tenant_scope`` values are
recomputed from the classifier, so the output is deterministic.

Usage:
    python scripts/ci/enrich_layer4_matrix_tenant_scope.py

The regenerator (``regenerate_layer4_route_matrix.py``) preserves the
``tenant_scope`` field on every entry, so running this script followed by a
regeneration keeps the matrix in sync.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
OPENAPI_PATH = REPO_ROOT / "contracts" / "openapi" / "layer4-agents.json"
MATRIX_PATH = REPO_ROOT / "contracts" / "layer4-route-contract-matrix.json"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from layer4_tenant_scope import classify_tenant_scope  # noqa: E402

HTTP_METHODS = frozenset({"get", "post", "put", "patch", "delete", "options", "head", "trace"})


def load_json(path: Path):
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path: Path, data) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(data, indent=2, ensure_ascii=False))
        fh.write("\n")


def main() -> int:
    spec = load_json(OPENAPI_PATH)
    matrix = load_json(MATRIX_PATH)

    if "entries" not in matrix:
        print("ERROR: matrix has no 'entries' key", file=sys.stderr)
        return 1

    # Prefer operation_id (spec-unique); fall back to "{METHOD} {path}"
    # route_id for parity with the regenerator.
    by_operation_id = {e.get("operation_id"): e for e in matrix["entries"]}
    by_route_id = {e.get("route_id"): e for e in matrix["entries"]}

    stamped = 0
    mismatched_paths = 0
    not_in_matrix = []

    paths = spec.get("paths") or {}
    for path, path_item in sorted(paths.items()):
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if method.lower() not in HTTP_METHODS:
                continue
            scope = classify_tenant_scope(method, path)
            op_id = operation.get("operationId")
            entry = by_operation_id.get(op_id) if op_id else None
            if entry is None:
                entry = by_route_id.get(f"{method.upper()} {path}")
            if entry is None:
                not_in_matrix.append(f"{method.upper()} {path} (operationId={op_id or '?'})")
                continue
            entry["tenant_scope"] = scope
            stamped += 1
            if entry.get("openapi_path") != path:
                mismatched_paths += 1
                print(
                    f"WARN: matrix openapi_path {entry.get('openapi_path')!r} != spec path {path!r} "
                    f"for operationId {op_id}",
                    file=sys.stderr,
                )

    # Matrix entries that never appear in the spec at all.
    spec_ids = {
        (path_item.get(method) or {}).get("operationId")
        for path_item in paths.values()
        if isinstance(path_item, dict)
        for method in path_item
        if "operationId" in (path_item.get(method) or {})
    }
    missing_in_spec = [rid for rid in by_operation_id if rid not in spec_ids]

    print(f"Stamped tenant_scope on {stamped} matrix entries.")
    if mismatched_paths:
        print(f"WARN: {mismatched_paths} matrix entries had path mismatch (see above).", file=sys.stderr)
    if not_in_matrix:
        print(f"ERROR: {len(not_in_matrix)} spec operations have no matrix entry:", file=sys.stderr)
        for line in not_in_matrix:
            print(f"  - {line}", file=sys.stderr)
        return 1
    if missing_in_spec:
        print(f"ERROR: {len(missing_in_spec)} matrix entries are absent from the spec:", file=sys.stderr)
        for rid in sorted(missing_in_spec):
            print(f"  - {rid}", file=sys.stderr)
        return 1

    write_json(MATRIX_PATH, matrix)
    print(f"Wrote tenant_scope to {MATRIX_PATH.name} ({len(matrix['entries'])} entries).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
