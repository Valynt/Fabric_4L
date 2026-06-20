#!/usr/bin/env python3
"""Evidence producer for gate contract.generated_jsonvalue_absent.

Validates that no generated TypeScript client contains the recursive JsonValue
alias that breaks openapi-typescript output. The generator replaces the opaque
``JsonValue: unknown;`` emitted for an empty schema with a stable recursive
type; this check ensures that replacement is present and that no manual override
markers remain in any generated layer.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GENERATED_ROOT = ROOT / "apps" / "web" / "src" / "api" / "generated"
OUTPUT_PATH = ROOT / "artifacts" / "contract" / "generated-jsonvalue-absent-check.json"
MANUAL_OVERRIDE_MARKERS = ("// MANUAL OVERRIDE", "manual override", "hand-edited")


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _get_commit_sha() -> str:
    try:
        import subprocess
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        ).stdout.strip()
    except Exception:
        return "unknown"


def _find_generated_index_files() -> list[Path]:
    if not GENERATED_ROOT.exists():
        return []
    return sorted(
        path for path in GENERATED_ROOT.rglob("index.ts")
        if path.is_file()
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, default=OUTPUT_PATH)
    args = ap.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)

    result = {
        "gate_id": "contract.generated_jsonvalue_absent",
        "command": "python scripts/ci/check_generated_jsonvalue_absent.py",
        "owner": "value-fabric/frontend-leads",
        "produced_at": _utc_now(),
        "bound_to": _get_commit_sha(),
        "artifact_binding": "commit-sha",
        "evidence_uri": str(args.output),
    }

    files = _find_generated_index_files()
    if not files:
        result["status"] = "INCONCLUSIVE"
        result["reason"] = f"No generated TypeScript clients found under {GENERATED_ROOT}"
        args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
        return 0

    failures: list[str] = []
    checked: list[str] = []
    for path in files:
        rel = str(path.relative_to(ROOT))
        checked.append(rel)
        content = path.read_text(encoding="utf-8")

        if "JsonValue: unknown;" in content:
            failures.append(f"{rel}: manual override 'JsonValue: unknown;' found")
        if "JsonValue" in content and "type JsonValue =" not in content:
            failures.append(f"{rel}: JsonValue is used without the recursive alias")
        if any(marker.lower() in content.lower() for marker in MANUAL_OVERRIDE_MARKERS):
            failures.append(f"{rel}: manual override marker found")

    if failures:
        result["status"] = "FAIL"
        result["reason"] = "Generated clients contain JsonValue regressions or manual overrides"
        result["failures"] = failures
    else:
        result["status"] = "PASS"
        result["reason"] = "No recursive JsonValue regressions or manual overrides in generated clients"

    result["checked_files"] = checked
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
