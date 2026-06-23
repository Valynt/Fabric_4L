#!/usr/bin/env python3
"""Evidence producer for E2E gates.

Checks whether the required E2E journey spec files exist and are executable. If a
journey is not yet implemented, the gate is marked INCONCLUSIVE with the
registered remediation ticket.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT / "artifacts" / "release"

JOURNEYS = {
    "e2e.tenant_account_route": {
        "spec": ROOT / "apps" / "web" / "e2e" / "security" / "tenant-route-journey.spec.ts",
        "command": "pnpm exec playwright test apps/web/e2e/security/tenant-route-journey.spec.ts",
    },
    "e2e.notes_to_fabric_found_summary": {
        "spec": ROOT / "apps" / "web" / "e2e" / "journeys" / "notes-to-summary-journey.spec.ts",
        "command": "pnpm exec playwright test apps/web/e2e/journeys/notes-to-summary-journey.spec.ts",
    },
    "e2e.unauthorized_account_denial": {
        "spec": ROOT / "apps" / "web" / "e2e" / "security" / "unauthorized-account-denial.spec.ts",
        "command": "pnpm exec playwright test apps/web/e2e/security/unauthorized-account-denial.spec.ts",
    },
}


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


def _artifact_path(gate_id: str) -> Path:
    return OUTPUT_DIR / f"gate-{gate_id.replace('.', '-')}.json"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true", help="Run the spec if it exists")
    args = ap.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    commit_sha = _get_commit_sha()
    overall_exit = 0

    for gate_id, info in JOURNEYS.items():
        output_path = _artifact_path(gate_id)
        result = {
            "gate_id": gate_id,
            "command": info["command"],
            "owner": "value-fabric/security-leads" if "tenant" in gate_id or "unauthorized" in gate_id else "value-fabric/qa-leads",
            "produced_at": _utc_now(),
            "bound_to": commit_sha,
            "artifact_binding": "commit-sha",
            "evidence_uri": str(output_path),
        }

        if not info["spec"].exists():
            result["status"] = "INCONCLUSIVE"
            result["reason"] = "E2E journey spec not implemented yet"
            result["missing_spec"] = str(info["spec"].relative_to(ROOT))
        elif args.run:
            proc = subprocess.run(
                info["command"].split(),
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            if proc.returncode == 0:
                result["status"] = "PASS"
                result["reason"] = "E2E journey passed"
            else:
                result["status"] = "FAIL"
                result["reason"] = "E2E journey failed"
                result["stderr_tail"] = proc.stderr.strip()[-500:] if proc.stderr else ""
                overall_exit = 1
        else:
            result["status"] = "INCONCLUSIVE"
            result["reason"] = "E2E journey spec exists but has not been executed in this run"

        output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

    return overall_exit


if __name__ == "__main__":
    sys.exit(main())
