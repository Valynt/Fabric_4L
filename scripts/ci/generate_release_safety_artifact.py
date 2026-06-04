#!/usr/bin/env python3
"""Generate the static release-safety artifact used by release gates."""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = REPO_ROOT / "artifacts/release/release-safety.json"


def _git_sha() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        return result.stdout.strip()
    return "unknown"


def _package_version() -> str:
    package_json = REPO_ROOT / "package.json"
    data = json.loads(package_json.read_text(encoding="utf-8"))
    return str(data["version"])


def _read_gate_decision() -> str:
    gate_result = REPO_ROOT / "artifacts/release/gate-result.json"
    if not gate_result.exists():
        return "DRY_RUN"
    try:
        data = json.loads(gate_result.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return "DRY_RUN"
    return str(data.get("decision") or "DRY_RUN")


def build_payload(environment: str, profile: str) -> dict[str, object]:
    return {
        "version": _package_version(),
        "commit_sha": _git_sha(),
        "build_timestamp": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "environment": environment,
        "profile": profile,
        "gate_decision": _read_gate_decision(),
        "canary_gates": {
            "source": "k8s/gitops/rollouts + k8s/feature-flags",
            "required_checks": ["health", "error_rate", "latency"],
            "promotion_policy": "block promotion until health, error-rate, and latency analysis gates pass",
        },
        "rollback_readiness": {
            "runbooks": [
                "docs/runbooks/deployment/rollback-production-release.md",
                "docs/runbooks/deployment/failed-deployment.md",
                "docs/operations/runbooks/database-migration-rollback.md",
            ],
            "verification": "pnpm release:rollback:verify",
            "failed_deployment_blocks_promotion": True,
        },
        "migration_rollback_policy": {
            "strategy": "forward-only or rollback-safe with documented production approval for unsupported downgrades",
            "verification": "python scripts/ci/check_migration_rollback_policy.py",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--environment", default="release-candidate")
    parser.add_argument("--profile", default="release-candidate")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    payload = build_payload(environment=args.environment, profile=args.profile)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote release safety artifact: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
