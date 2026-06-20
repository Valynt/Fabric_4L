#!/usr/bin/env python3
"""Evidence producer for gate contract.clerk_tenant_mapping_tested.

Checks for the existence of and runs Clerk org → Fabric tenant mapping tests.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUTPUT_PATH = ROOT / "artifacts" / "security" / "clerk-tenant-mapping-test-report.json"
BACKEND_TEST = ROOT / "tests" / "security" / "test_clerk_tenant_mapping.py"
FRONTEND_TEST = ROOT / "apps" / "web" / "e2e" / "security" / "tenant-mapping.spec.ts"


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
        "gate_id": "contract.clerk_tenant_mapping_tested",
        "command": "python -m pytest tests/security/test_clerk_tenant_mapping.py && pnpm exec playwright test apps/web/e2e/security/tenant-mapping.spec.ts",
        "owner": "value-fabric/security-leads",
        "produced_at": _utc_now(),
        "bound_to": _get_commit_sha(),
        "artifact_binding": "commit-sha",
        "evidence_uri": str(args.output),
    }

    missing = []
    if not BACKEND_TEST.exists():
        missing.append(str(BACKEND_TEST.relative_to(ROOT)))
    if not FRONTEND_TEST.exists():
        missing.append(str(FRONTEND_TEST.relative_to(ROOT)))

    if missing:
        result["status"] = "INCONCLUSIVE"
        result["reason"] = "Required Clerk tenant mapping tests do not exist yet"
        result["missing_files"] = missing
        args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
        return 0

    backend_ok = True
    backend_proc = subprocess.run(
        ["python", "-m", "pytest", str(BACKEND_TEST), "-q", "--maxfail=1"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    backend_ok = backend_proc.returncode == 0

    frontend_ok = True
    frontend_proc = subprocess.run(
        ["pnpm", "exec", "playwright", "test", str(FRONTEND_TEST)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    frontend_ok = frontend_proc.returncode == 0

    if backend_ok and frontend_ok:
        result["status"] = "PASS"
        result["reason"] = "Clerk tenant mapping tests pass"
    else:
        result["status"] = "FAIL"
        result["reason"] = "Clerk tenant mapping tests failed"
        result["backend_stderr"] = backend_proc.stderr.strip()[-500:] if backend_proc.stderr else ""
        result["frontend_stderr"] = frontend_proc.stderr.strip()[-500:] if frontend_proc.stderr else ""

    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
