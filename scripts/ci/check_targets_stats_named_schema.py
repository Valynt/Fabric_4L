#!/usr/bin/env python3
"""Evidence producer for gate contract.targets_stats_named_schema.

Validates that /api/v1/ingestion/targets/stats returns a named schema reference.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC_PATH = ROOT / "contracts" / "openapi" / "layer1-ingestion.json"
OUTPUT_PATH = ROOT / "artifacts" / "release" / "gate-contract-targets_stats_named_schema.json"
EXPECTED_SCHEMA_NAME = "TargetStatsResponse"


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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, default=OUTPUT_PATH)
    args = ap.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)

    result = {
        "gate_id": "contract.targets_stats_named_schema",
        "command": "python scripts/ci/check_targets_stats_named_schema.py",
        "owner": "value-fabric/backend-leads",
        "produced_at": _utc_now(),
        "bound_to": _get_commit_sha(),
        "artifact_binding": "commit-sha",
        "evidence_uri": str(args.output),
    }

    if not SPEC_PATH.exists():
        result["status"] = "FAIL"
        result["reason"] = f"OpenAPI spec not found: {SPEC_PATH}"
        args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
        return 1

    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    paths = spec.get("paths", {})
    components = spec.get("components", {}).get("schemas", {})

    stats_path = paths.get("/api/v1/ingestion/targets/stats", {})
    get_op = stats_path.get("get", {})
    responses = get_op.get("responses", {})
    ok_response = responses.get("200", {})
    content = ok_response.get("content", {})
    json_content = content.get("application/json", {})
    schema = json_content.get("schema", {})

    ref = schema.get("$ref", "")
    named_match = re.match(r"^#/components/schemas/(.+)$", ref)

    if named_match:
        named_name = named_match.group(1)
        if named_name != EXPECTED_SCHEMA_NAME:
            result["status"] = "FAIL"
            result["reason"] = (
                f"Stats response named schema is {named_name!r}, expected {EXPECTED_SCHEMA_NAME!r}"
            )
            result["named_schema"] = named_name
        elif named_name not in components:
            result["status"] = "FAIL"
            result["reason"] = f"Named schema reference missing from components: {named_name}"
            result["named_schema"] = named_name
        else:
            result["status"] = "PASS"
            result["reason"] = f"Response uses named schema: {named_name}"
            result["named_schema"] = named_name
    else:
        result["status"] = "FAIL"
        result["reason"] = "Response is not a $ref to a named schema"
        result["schema_kind"] = "inline" if schema else "missing"

    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
