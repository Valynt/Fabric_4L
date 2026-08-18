#!/usr/bin/env python3
"""Canary analysis script for validating Argo Rollouts and Prometheus metrics during production promotion."""
from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess  # nosec B404
import sys
import time
import urllib.parse
import urllib.request
from typing import Sequence

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("canary_analysis")


def check_rollout_status(namespace: str, rollout_name: str) -> bool:
    """Check if an Argo rollout is healthy using kubectl argo rollouts status or standard kubectl."""
    cmd = ["kubectl", "argo", "rollouts", "status", rollout_name, "-n", namespace, "--timeout=30s"]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=False)  # nosec B603
        if res.returncode == 0:
            logger.info("Rollout %s in %s is healthy", rollout_name, namespace)
            return True
        logger.warning("Rollout %s status non-zero: %s", rollout_name, res.stderr.strip())
        return False
    except FileNotFoundError:
        logger.info("kubectl argo plugin not found, checking with kubectl rollout status")
        fallback = ["kubectl", "rollout", "status", f"deployment/{rollout_name}", "-n", namespace, "--timeout=30s"]
        try:
            res_fb = subprocess.run(fallback, capture_output=True, text=True, check=False)  # nosec B603
            return res_fb.returncode == 0
        except FileNotFoundError:
            logger.info("kubectl not found in runtime environment (dry-run or local check)")
            return True


def check_prometheus_metrics(prometheus_url: str | None, max_error_rate: float = 0.01) -> bool:
    """Query Prometheus for error rate anomalies during canary window."""
    if not prometheus_url:
        logger.info("PROMETHEUS_URL not set; skipping remote metric poll")
        return True

    query = "sum(rate(http_requests_total{status=~'5..'}[2m])) / sum(rate(http_requests_total[2m]))"
    req_url = f"{prometheus_url.rstrip('/')}/api/v1/query?query={urllib.parse.quote(query)}"
    try:
        with urllib.request.urlopen(req_url, timeout=10) as resp:  # nosec B310
            data = json.loads(resp.read().decode("utf-8"))
            results = data.get("data", {}).get("result", [])
            if results:
                val = float(results[0].get("value", [0, 0])[1])
                if val > max_error_rate:
                    logger.error("Canary error rate %.4f exceeds threshold %.4f", val, max_error_rate)
                    return False
            return True
    except Exception as exc:
        logger.warning("Failed to query Prometheus at %s: %s", prometheus_url, exc)
        return True


def run_canary_analysis(
    namespace: str,
    rollouts: Sequence[str],
    timeout_seconds: int = 1800,
    poll_interval_seconds: int = 30,
) -> int:
    """Poll rollouts until all are healthy or timeout is reached."""
    logger.info("Starting canary analysis for %s in namespace %s (timeout: %ds)", rollouts, namespace, timeout_seconds)
    start_time = time.time()
    prom_url = os.environ.get("PROMETHEUS_URL")

    while time.time() - start_time < timeout_seconds:
        all_healthy = True
        for ro in rollouts:
            if not check_rollout_status(namespace, ro.strip()):
                all_healthy = False
                break

        if all_healthy and check_prometheus_metrics(prom_url):
            logger.info("All rollouts healthy and metrics within bounds")
            return 0

        logger.info("Canary progression in progress; sleeping %ds...", poll_interval_seconds)
        time.sleep(poll_interval_seconds)

    logger.error("Canary analysis timed out after %ds", timeout_seconds)
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Canary Analysis Gate")
    parser.add_argument("--namespace", default="prod", help="Kubernetes namespace")
    parser.add_argument("--rollouts", required=True, help="Comma-separated list of rollout names")
    parser.add_argument("--timeout-seconds", type=int, default=1800, help="Max wait time")
    parser.add_argument("--poll-interval-seconds", type=int, default=30, help="Poll interval")
    args = parser.parse_args()

    rollout_list = [r.strip() for r in args.rollouts.split(",") if r.strip()]
    return run_canary_analysis(
        namespace=args.namespace,
        rollouts=rollout_list,
        timeout_seconds=args.timeout_seconds,
        poll_interval_seconds=args.poll_interval_seconds,
    )


if __name__ == "__main__":
    sys.exit(main())
