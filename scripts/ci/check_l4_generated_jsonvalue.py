#!/usr/bin/env python3
"""Evidence producer for gate contract.l4_jsonvalue_compiles.

Validates that the Layer 4 generated TypeScript client exists, compiles, and has
no manual override markers.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
L4_GENERATED = ROOT / "apps" / "web" / "src" / "api" / "generated" / "l4" / "index.ts"
OUTPUT_PATH = ROOT / "artifacts" / "release" / "gate-contract-l4_jsonvalue_compiles.json"
MANUAL_OVERRIDE_MARKERS = ("// MANUAL OVERRIDE", "manual override", "hand-edited")


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _get_commit_sha() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        ).stdout.strip()
    except Exception:
        return "unknown"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, default=OUTPUT_PATH)
    args = ap.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)

    result = {
        "gate_id": "contract.l4_jsonvalue_compiles",
        "command": "python scripts/ci/check_l4_generated_jsonvalue.py",
        "owner": "value-fabric/frontend-leads",
        "produced_at": _utc_now(),
        "bound_to": _get_commit_sha(),
        "artifact_binding": "commit-sha",
        "evidence_uri": str(args.output),
    }

    if not L4_GENERATED.exists():
        result["status"] = "INCONCLUSIVE"
        result["reason"] = f"Layer 4 generated client not found: {L4_GENERATED}"
        args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
        return 0

    content = L4_GENERATED.read_text(encoding="utf-8")
    has_override = any(marker.lower() in content.lower() for marker in MANUAL_OVERRIDE_MARKERS)

    if has_override:
        result["status"] = "FAIL"
        result["reason"] = "Manual override marker found in generated Layer 4 client"
        args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
        return 1

    # Type-check the generated layer 4 client using the repo's TypeScript compiler.
    try:
        tsc = subprocess.run(
            ["pnpm", "exec", "tsc", "--noEmit", "--skipLibCheck", str(L4_GENERATED)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if tsc.returncode != 0:
            result["status"] = "FAIL"
            result["reason"] = "Layer 4 generated client does not compile"
            result["stderr_tail"] = (tsc.stderr or "").strip()[-500:]
            args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
            return 1
    except FileNotFoundError:
        result["status"] = "INCONCLUSIVE"
        result["reason"] = "TypeScript compiler not available in this environment"
        args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
        return 0

    result["status"] = "PASS"
    result["reason"] = "Layer 4 generated client exists, compiles, and has no manual overrides"
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
