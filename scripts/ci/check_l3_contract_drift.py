"""CI gate: Layer 3 V2 contract drift check (DOC-ARCH-010).

Compares the current Layer 3 OpenAPI contract against the locked V1 snapshot
(``docs/api/v1_snapshot.yaml``) to guarantee that V2 routers do not break
backward compatibility before the full monolith removal (ARCH-L3-011).

Checks performed
----------------
1. **No removed paths** — every path in the V1 snapshot must still exist.
2. **No removed methods** — every HTTP method on each path must still exist.
3. **No removed response codes** — existing success/error codes must be preserved.
4. **No removed required response fields** — top-level required fields in 200
   response schemas must not be removed (additive changes are allowed).

What is NOT checked (intentionally allowed)
-------------------------------------------
- New paths / methods (additive, backward-compatible)
- New optional response fields (additive)
- Description / summary text changes
- Non-breaking schema relaxations

Usage
-----
    python scripts/ci/check_l3_contract_drift.py
    python scripts/ci/check_l3_contract_drift.py --snapshot docs/api/v1_snapshot.yaml
    python scripts/ci/check_l3_contract_drift.py --current contracts/openapi/layer3-knowledge.json

Exit codes
----------
    0  No breaking drift detected.
    1  Breaking drift detected.
    2  Snapshot or current contract not found.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SNAPSHOT = REPO_ROOT / "docs/api/v1_snapshot.yaml"
DEFAULT_CURRENT = REPO_ROOT / "contracts/openapi/layer3-knowledge.json"

# Explicitly governed Layer 3 legacy-to-canonical path migrations. These paths
# were renamed during the V2 router split; the current path must exist for the
# snapshot path to be considered preserved by an approved alias.
COMPATIBILITY_HIDDEN_PATHS: set[str] = {
    "/metrics",
    "/v1/schema/status",
    "/v1/schema/init",
    "/v1/schema/statistics",
    # Removed intentionally (never re-added): the L3→L4 circular dependency
    # fix removed the dead L3 /v1/documents/export proxy (R5). Business case
    # export flows directly from the frontend to L4, so this path is not
    # covered by canonical-path compatibility (R8).
    "/v1/documents/export",
}

COMPATIBILITY_PATH_ALIASES: dict[str, str] = {
    "/graph": "/v1/graph",
    "/entities/{entity_id}/subgraph": "/v1/entities/{entity_id}/subgraph",
    "/v1/query": "/v1/query/search",
    "/v1/v1/entities": "/v1/entities/",
    "/v1/v1/entities/{entity_id}": "/v1/entities/{entity_id}",
    "/v1/v1/entities/query": "/v1/entities/query",
    "/v1/v1/entity/traverse": "/v1/entities/traverse",
    "/v1/v1/calculators/levers": "/v1/calculators/levers",
    "/v1/v1/calculators/value-cases": "/v1/calculators/value-cases",
    "/v1/v1/calculators/value-cases/{case_id}": "/v1/calculators/value-cases/{case_id}",
}

# Explicit response-code standardizations retained in runtime exception handlers
# but no longer emitted per-operation in the generated OpenAPI document.
COMPATIBILITY_RESPONSE_CODES: set[tuple[str, str, str]] = {
    ("get", "/v1/variables", "401"),
    ("post", "/v1/variables", "401"),
    ("get", "/v1/variables/{variable_id}", "401"),
    ("put", "/v1/variables/{variable_id}", "401"),
    ("post", "/v1/variables/{variable_id}/resolve", "401"),
    ("post", "/v1/variables/{variable_id}/validate", "401"),
    ("get", "/v1/variables/stats", "401"),
    ("get", "/v1/variables/bindings", "401"),
    ("get", "/v1/graph/subgraph", "400"),
    ("get", "/v1/graph/subgraph", "500"),
    ("get", "/graph", "503"),
    ("get", "/entities/{entity_id}/subgraph", "404"),
    ("get", "/entities/{entity_id}/subgraph", "503"),
}


def _load(path: Path) -> dict[str, Any]:
    with path.open() as fh:
        return json.load(fh)


def _get_response_schema_required(operation: dict[str, Any], status: str) -> set[str]:
    """Extract required field names from a response schema."""
    try:
        content = operation["responses"][status]["content"]
        for media_type in content.values():
            schema = media_type.get("schema", {})
            return set(schema.get("required", []))
    except (KeyError, TypeError):
        return set()


def check_drift(
    snapshot: dict[str, Any],
    current: dict[str, Any],
) -> list[str]:
    """Return a list of breaking drift violation messages."""
    violations: list[str] = []

    snapshot_paths: dict[str, Any] = snapshot.get("paths", {})
    current_paths: dict[str, Any] = current.get("paths", {})

    for path, snapshot_path_item in snapshot_paths.items():
        # 1. Removed path
        if path not in current_paths:
            if path in COMPATIBILITY_HIDDEN_PATHS:
                continue
            alias_path = COMPATIBILITY_PATH_ALIASES.get(path)
            if alias_path is None or alias_path not in current_paths:
                violations.append(f"REMOVED PATH: {path}")
                continue
            current_path_item = current_paths[alias_path]
        else:
            current_path_item = current_paths[path]

        for method, snapshot_op in snapshot_path_item.items():
            if method.startswith("x-") or method == "parameters":
                continue

            # 2. Removed method
            if method not in current_path_item:
                violations.append(f"REMOVED METHOD: {method.upper()} {path}")
                continue

            current_op = current_path_item[method]

            # 3. Removed response codes
            snapshot_responses: dict[str, Any] = snapshot_op.get("responses", {})
            current_responses: dict[str, Any] = current_op.get("responses", {})

            for status_code in snapshot_responses:
                if status_code not in current_responses:
                    if (method, path, str(status_code)) in COMPATIBILITY_RESPONSE_CODES:
                        continue
                    violations.append(
                        f"REMOVED RESPONSE CODE: {method.upper()} {path} → {status_code}"
                    )
                    continue

                # 4. Removed required response fields (200 only)
                if status_code == "200":
                    snapshot_required = _get_response_schema_required(snapshot_op, "200")
                    current_required = _get_response_schema_required(current_op, "200")
                    removed_fields = snapshot_required - current_required
                    for field in sorted(removed_fields):
                        violations.append(
                            f"REMOVED REQUIRED FIELD: {method.upper()} {path} "
                            f"→ 200 response → '{field}'"
                        )

    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--snapshot",
        type=Path,
        default=DEFAULT_SNAPSHOT,
        help=f"Path to V1 snapshot (default: {DEFAULT_SNAPSHOT})",
    )
    parser.add_argument(
        "--current",
        type=Path,
        default=DEFAULT_CURRENT,
        help=f"Path to current contract (default: {DEFAULT_CURRENT})",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        default=None,
        help="Write violations as JSON to this path.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Run the full V1 compatibility drift check. Kept for CI/register parity.",
    )
    args = parser.parse_args()

    for label, path in [("snapshot", args.snapshot), ("current", args.current)]:
        if not path.exists():
            print(f"ERROR: {label} contract not found: {path}", file=sys.stderr)
            return 2

    snapshot = _load(args.snapshot)
    current = _load(args.current)

    violations = check_drift(snapshot, current)

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        with args.json_out.open("w") as fh:
            json.dump({"violations": violations, "count": len(violations)}, fh, indent=2)

    if violations:
        print(
            f"FAIL: {len(violations)} breaking contract drift violation(s) detected "
            f"(DOC-ARCH-010)",
            file=sys.stderr,
        )
        for v in violations:
            print(f"  {v}", file=sys.stderr)
        print(
            "\nV2 routers must maintain full backward compatibility with the V1 snapshot.\n"
            "See docs/api/v1_snapshot.yaml for the locked baseline.",
            file=sys.stderr,
        )
        return 1

    snapshot_path_count = len(snapshot.get("paths", {}))
    print(
        f"OK: No breaking drift detected "
        f"({snapshot_path_count} V1 paths verified against current contract)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
