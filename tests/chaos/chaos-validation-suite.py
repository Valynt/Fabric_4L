#!/usr/bin/env python3
"""Post-chaos validation suite.

Validates system recovery after chaos experiments and emits a JSON report.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def run_kubectl(namespace: str, args: list[str]) -> tuple[int, str, str]:
    try:
        result = subprocess.run(
            ["kubectl", "-n", namespace, *args],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        return result.returncode, result.stdout, result.stderr
    except FileNotFoundError:
        return 127, "", "kubectl not found in PATH"
    except subprocess.TimeoutExpired as exc:
        return 124, "", f"kubectl timed out: {exc}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Post-chaos validation suite")
    parser.add_argument("--namespace", required=True, help="target Kubernetes namespace")
    parser.add_argument("--output", required=True, help="path to write the JSON validation report")
    args = parser.parse_args(argv)

    report_path = Path(args.output)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    pod_rc, pod_out, pod_err = run_kubectl(args.namespace, ["get", "pods", "-o", "json"])
    deployment_rc, deploy_out, deploy_err = run_kubectl(
        args.namespace, ["get", "deployments", "-o", "json"]
    )

    healthy = pod_rc == 0 and deployment_rc == 0
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "namespace": args.namespace,
        "healthy": healthy,
        "checks": {
            "pods_accessible": pod_rc == 0,
            "deployments_accessible": deployment_rc == 0,
        },
        "details": {
            "pods": {"returncode": pod_rc, "stderr": pod_err.strip()},
            "deployments": {"returncode": deployment_rc, "stderr": deploy_err.strip()},
        },
    }

    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote chaos validation report to {report_path}")
    return 0 if healthy else 1


if __name__ == "__main__":
    raise SystemExit(main())
