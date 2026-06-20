#!/usr/bin/env python3
"""Evidence producer for gate contract.clerk_tenant_response_exported.

Validates that the API gateway contract (fabric-4l-api.json) exports the
ClerkTenantResponse schema and exposes the GET /v1/auth/clerk/tenant endpoint.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC_PATH = ROOT / "contracts" / "openapi" / "fabric-4l-api.json"
OUTPUT_PATH = ROOT / "artifacts" / "contract" / "clerk-tenant-response-check.json"
EXPECTED_SCHEMA_NAME = "ClerkTenantResponse"
EXPECTED_ENDPOINT = "/v1/auth/clerk/tenant"
EXPECTED_METHOD = "get"
REQUIRED_FIELDS = (
    "fabric_tenant_id",
    "tenant_slug",
    "clerk_org_id",
    "status",
    "roles",
    "permissions",
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
        "gate_id": "contract.clerk_tenant_response_exported",
        "command": "python scripts/ci/check_clerk_tenant_response_exported.py",
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

    endpoint = paths.get(EXPECTED_ENDPOINT, {})
    method = endpoint.get(EXPECTED_METHOD, {})

    missing = []
    if not method:
        missing.append(f"missing endpoint: {EXPECTED_METHOD.upper()} {EXPECTED_ENDPOINT}")

    schema = components.get(EXPECTED_SCHEMA_NAME)
    if schema is None:
        missing.append(f"missing schema: {EXPECTED_SCHEMA_NAME}")
    else:
        props = schema.get("properties", {})
        absent_fields = [f for f in REQUIRED_FIELDS if f not in props]
        if absent_fields:
            missing.append(f"{EXPECTED_SCHEMA_NAME} missing fields: {absent_fields}")

    if missing:
        result["status"] = "FAIL"
        result["reason"] = "Clerk tenant mapping contract is incomplete"
        result["missing"] = missing
    else:
        result["status"] = "PASS"
        result["reason"] = (
            f"{EXPECTED_SCHEMA_NAME} exported and {EXPECTED_METHOD.upper()} {EXPECTED_ENDPOINT} is present"
        )

    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
