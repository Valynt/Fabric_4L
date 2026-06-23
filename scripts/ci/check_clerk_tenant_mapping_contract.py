#!/usr/bin/env python3
"""Evidence producer for gate contract.clerk_tenant_mapping.

Validates that the Clerk org → Fabric tenant mapping contract is present in the
OpenAPI spec and that the required regression tests exist.
"""
from __future__ import annotations

import argparse
import ast
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC_PATH = ROOT / "contracts" / "openapi" / "fabric-4l-api.json"
OUTPUT_PATH = ROOT / "artifacts" / "release" / "gate-contract-clerk_tenant_mapping.json"

REQUIRED_PATH = "/v1/auth/clerk/tenant"
REQUIRED_SCHEMAS = ("ClerkTenantResponse",)
REQUIRED_FRONTEND_TEST_FILES = (
    ROOT / "apps" / "web" / "src" / "hooks" / "useResolvedTenant.test.ts",
    ROOT / "apps" / "web" / "src" / "hooks" / "useResolvedTenant.test.tsx",
    ROOT / "apps" / "web" / "src" / "components" / "routing" / "RequireClerkAuth.test.tsx",
)
REQUIRED_BACKEND_TEST_FILES = (
    ROOT / "services" / "api" / "tests" / "test_clerk_auth_router.py",
)
REQUIRED_BACKEND_TESTS = (
    "test_clerk_tenant_missing_token_returns_401",
    "test_clerk_tenant_invalid_token_returns_401",
    "test_clerk_tenant_wrong_org_cannot_resolve_other_tenant",
    "test_clerk_tenant_response_does_not_leak_unauthorized_metadata",
)


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


def _collect_tests(source: Path) -> set[str]:
    """Collect top-level test function names from a Python file."""
    try:
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
    except Exception:
        return set()
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, default=OUTPUT_PATH)
    args = ap.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)

    result = {
        "gate_id": "contract.clerk_tenant_mapping",
        "command": "python scripts/ci/check_clerk_tenant_mapping_contract.py",
        "owner": "value-fabric/security-leads",
        "produced_at": _utc_now(),
        "bound_to": _get_commit_sha(),
        "artifact_binding": "commit-sha",
        "evidence_uri": str(args.output),
    }

    failures: list[str] = []

    if not SPEC_PATH.exists():
        failures.append(f"OpenAPI spec not found: {SPEC_PATH}")
    else:
        spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
        paths = spec.get("paths", {})
        components = spec.get("components", {}).get("schemas", {})

        if REQUIRED_PATH not in paths:
            failures.append(f"missing path: {REQUIRED_PATH}")
        else:
            methods = paths[REQUIRED_PATH]
            if "get" not in methods:
                failures.append(f"GET method missing on {REQUIRED_PATH}")

        for schema_name in REQUIRED_SCHEMAS:
            if schema_name not in components:
                failures.append(f"missing schema: {schema_name}")

    for test_file in REQUIRED_FRONTEND_TEST_FILES:
        if not test_file.exists():
            failures.append(f"missing frontend test file: {test_file}")

    for test_file in REQUIRED_BACKEND_TEST_FILES:
        if not test_file.exists():
            failures.append(f"missing backend test file: {test_file}")
        else:
            available_tests = _collect_tests(test_file)
            missing = [t for t in REQUIRED_BACKEND_TESTS if t not in available_tests]
            if missing:
                failures.append(f"missing backend tests in {test_file}: {missing}")

    if failures:
        result["status"] = "FAIL"
        result["reason"] = "Clerk tenant-mapping contract is incomplete"
        result["failures"] = failures
    else:
        result["status"] = "PASS"
        result["reason"] = "Clerk tenant-mapping contract and regression tests are present"

    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
