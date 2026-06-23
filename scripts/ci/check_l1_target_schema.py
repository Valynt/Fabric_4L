#!/usr/bin/env python3
"""Evidence producer for gate contract.l1_target_schema.

Validates that contracts/openapi/layer1-ingestion.json contains required target
paths and fields.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC_PATH = ROOT / "contracts" / "openapi" / "layer1-ingestion.json"
OUTPUT_PATH = ROOT / "artifacts" / "release" / "gate-contract-l1_target_schema.json"

REQUIRED_PATHS = (
    "/api/v1/ingestion/targets",
    "/api/v1/ingestion/targets/{target_id}",
    "/api/v1/ingestion/targets/stats",
    "/api/v1/ingestion/jobs/batch",
)
REQUIRED_TARGET_FIELDS = ("id", "domain", "status", "pages_crawled")
REQUIRED_TARGET_SCHEMAS = (
    "ScrapingTargetSummary",
    "ScrapingTargetDetail",
)
REQUIRED_TARGET_SCHEMA_FIELDS = (
    "id",
    "name",
    "url",
    "target_type",
    "source_category",
    "status",
)


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
        "gate_id": "contract.l1_target_schema",
        "command": "python scripts/ci/check_l1_target_schema.py",
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

    missing_paths = [p for p in REQUIRED_PATHS if p not in paths]
    missing_fields: list[str] = []
    target_schema = components.get("Target", {})
    if target_schema.get("type") == "object":
        props = target_schema.get("properties", {})
        missing_fields = [f for f in REQUIRED_TARGET_FIELDS if f not in props]

    missing_schema_fields: dict[str, list[str]] = {}
    for schema_name in REQUIRED_TARGET_SCHEMAS:
        schema = components.get(schema_name, {})
        props = schema.get("properties", {})
        absent = [f for f in REQUIRED_TARGET_SCHEMA_FIELDS if f not in props]
        if absent:
            missing_schema_fields[schema_name] = absent

    failures = []
    if missing_paths:
        failures.append(f"missing_paths: {missing_paths}")
    if missing_fields:
        failures.append(f"missing_fields in Target: {missing_fields}")
    if missing_schema_fields:
        failures.append(f"missing_schema_fields: {missing_schema_fields}")

    if failures:
        result["status"] = "FAIL"
        result["reason"] = "Missing required OpenAPI contract elements"
        result["missing_paths"] = missing_paths
        result["missing_fields"] = missing_fields
        result["missing_schema_fields"] = missing_schema_fields
    else:
        result["status"] = "PASS"
        result["reason"] = "Required target paths and fields are present"

    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
