#!/usr/bin/env python3
"""Generate gate result evidence for all gates in the registry.

Runs each registered evidence producer and writes the output as a canonical
`artifacts/release/gate-{gate_id}.json` file. Gates without real producers are
recorded as INCONCLUSIVE with the registered command and owner.
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
GATE_REGISTRY = ROOT / ".fabric" / "gate-engineering" / "gate-registry.json"
DEFAULT_ARTIFACT_DIR = ROOT / "artifacts" / "release"


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


def _artifact_path(artifact_dir: Path, gate_id: str) -> Path:
    return artifact_dir / f"gate-{gate_id.replace('.', '-')}.json"


def _run_command(command: str) -> tuple[int, str, str]:
    try:
        result = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
            shell=True,
        )
        return result.returncode, result.stdout, result.stderr
    except Exception as exc:
        return 1, "", str(exc)


DEDICATED_PRODUCERS: dict[str, Path] = {
    "contract.l1_target_schema": ROOT / "scripts" / "ci" / "check_l1_target_schema.py",
    "contract.targets_stats_named_schema": ROOT / "scripts" / "ci" / "check_targets_stats_named_schema.py",
    "contract.l4_jsonvalue_compiles": ROOT / "scripts" / "ci" / "check_l4_generated_jsonvalue.py",
    "contract.generated_clients_current": ROOT / "scripts" / "ci" / "check_generated_client_reproducibility.py",
    "build.generated_client_reproducible": ROOT / "scripts" / "ci" / "check_generated_client_reproducibility.py",
    "contract.clerk_tenant_mapping_tested": ROOT / "scripts" / "ci" / "check_clerk_tenant_mapping_tested.py",
    "e2e.tenant_account_route": ROOT / "scripts" / "ci" / "check_e2e_gate_readiness.py",
    "e2e.notes_to_fabric_found_summary": ROOT / "scripts" / "ci" / "check_e2e_gate_readiness.py",
    "e2e.unauthorized_account_denial": ROOT / "scripts" / "ci" / "check_e2e_gate_readiness.py",
}


def _generate_for_gate(
    gate: dict[str, Any],
    artifact_dir: Path,
    commit_sha: str,
    run_real_producers: bool,
    fast: bool,
) -> dict[str, Any]:
    gate_id = gate["gate_id"]
    producer = gate.get("evidence_producer")
    artifact_path = _artifact_path(artifact_dir, gate_id)

    result: dict[str, Any] = {
        "gate_id": gate_id,
        "owner": gate["owner"],
        "produced_at": _utc_now(),
        "bound_to": commit_sha,
        "artifact_binding": producer["artifact_binding"] if producer else "commit-sha",
        "evidence_uri": str(artifact_path),
    }

    if producer:
        result["command"] = producer["command"]

    if not run_real_producers or not producer:
        result["status"] = "INCONCLUSIVE"
        result["reason"] = "evidence producer not executed in this run" if producer else "no evidence producer registered"
        return result

    if fast and gate_id not in DEDICATED_PRODUCERS:
        result["status"] = "INCONCLUSIVE"
        result["reason"] = "heavy evidence producer skipped in fast mode"
        return result

    if gate_id in DEDICATED_PRODUCERS:
        script = DEDICATED_PRODUCERS[gate_id]
        if script.exists():
            code = subprocess.run(
                [sys.executable, str(script)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            ).returncode
            # Read the dedicated script's output file if it exists and merge.
            dedicated_output = _read_dedicated_output(gate_id)
            if dedicated_output:
                result.update(dedicated_output)
                return result
            result["status"] = "PASS" if code == 0 else "FAIL"
            result["reason"] = "dedicated producer returned" + (" success" if code == 0 else " failure")
            return result

    # Generic producer: run the command and infer status from exit code.
    code, stdout, stderr = _run_command(producer["command"])
    result["status"] = "PASS" if code == 0 else "FAIL"
    result["reason"] = "producer exited successfully" if code == 0 else "producer exited with failure"
    if code != 0:
        result["stderr_tail"] = (stderr or "").strip()[-500:]
        result["stdout_tail"] = (stdout or "").strip()[-500:]
    return result


def _read_dedicated_output(gate_id: str) -> dict[str, Any] | None:
    mapping: dict[str, Path] = {
        "contract.l1_target_schema": ROOT / "artifacts" / "contract" / "l1-target-schema-check.json",
        "contract.targets_stats_named_schema": ROOT / "artifacts" / "contract" / "targets-stats-schema-check.json",
        "contract.l4_jsonvalue_compiles": ROOT / "artifacts" / "contract" / "l4-jsonvalue-check.json",
        "contract.generated_clients_current": ROOT / "artifacts" / "contract" / "generated-client-reproducibility.json",
        "build.generated_client_reproducible": ROOT / "artifacts" / "contract" / "generated-client-reproducibility.json",
        "contract.clerk_tenant_mapping_tested": ROOT / "artifacts" / "security" / "clerk-tenant-mapping-test-report.json",
        "e2e.tenant_account_route": ROOT / "artifacts" / "e2e" / "e2e-tenant_account_route-report.json",
        "e2e.notes_to_fabric_found_summary": ROOT / "artifacts" / "e2e" / "e2e-notes_to_fabric_found_summary-report.json",
        "e2e.unauthorized_account_denial": ROOT / "artifacts" / "e2e" / "e2e-unauthorized_account_denial-report.json",
    }
    path = mapping.get(gate_id)
    if path and path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--artifact-dir", type=Path, default=DEFAULT_ARTIFACT_DIR)
    ap.add_argument(
        "--artifact-digest",
        default="synthetic-digest",
        help="Artifact digest to bind artifact-bound evidence to",
    )
    ap.add_argument(
        "--run-real-producers",
        action="store_true",
        help="Execute real evidence producers; otherwise emit INCONCLUSIVE for all gates",
    )
    ap.add_argument(
        "--fast",
        action="store_true",
        help="Run only lightweight dedicated producers; mark heavy producers INCONCLUSIVE",
    )
    args = ap.parse_args()

    args.artifact_dir.mkdir(parents=True, exist_ok=True)
    registry = json.loads(GATE_REGISTRY.read_text(encoding="utf-8"))
    commit_sha = _get_commit_sha()
    artifact_digest = args.artifact_digest
    overall_exit = 0

    for gate in registry["gates"]:
        producer = gate.get("evidence_producer")
        bound_to = artifact_digest if producer and producer["artifact_binding"] in ("container-image-digest", "artifact-digest") else commit_sha
        result = _generate_for_gate(
            gate,
            args.artifact_dir,
            bound_to,
            run_real_producers=args.run_real_producers,
            fast=args.fast,
        )
        _artifact_path(args.artifact_dir, gate["gate_id"]).write_text(
            json.dumps(result, indent=2), encoding="utf-8"
        )
        if result["status"] == "FAIL" and gate["criticality"] == "blocking":
            overall_exit = 1

    print(f"Generated {len(registry['gates'])} gate result files in {args.artifact_dir}")
    return overall_exit


if __name__ == "__main__":
    sys.exit(main())
