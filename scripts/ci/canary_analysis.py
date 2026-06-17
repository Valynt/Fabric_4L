#!/usr/bin/env python3
"""Poll Argo Rollouts and Prometheus during a production canary analysis."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Wait for Argo Rollouts to reach a healthy state and optionally gate on Prometheus metrics."
    )
    parser.add_argument("--namespace", required=True, help="Kubernetes namespace containing the rollouts.")
    parser.add_argument(
        "--rollouts",
        required=True,
        help="Comma-separated list of rollout resource names.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=1800,
        help="Maximum time to wait for all rollouts to become healthy.",
    )
    parser.add_argument(
        "--poll-interval-seconds",
        type=int,
        default=30,
        help="Seconds to sleep between rollout status polls.",
    )
    parser.add_argument(
        "--prometheus-url",
        default="",
        help="Optional Prometheus base URL. If unset, metric queries are skipped.",
    )
    return parser.parse_args()


def get_rollout(namespace: str, name: str) -> dict[str, Any] | None:
    cmd = [
        "kubectl",
        "argo",
        "rollouts",
        "get",
        "rollout",
        name,
        "-n",
        namespace,
        "-o",
        "json",
    ]
    try:
        result = subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        print(f"Warning: kubectl failed for rollout/{name}: {exc.stderr.strip()}")
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        print(f"Warning: could not parse rollout/{name} JSON: {exc}")
        return None


def is_rollout_healthy(rollout: dict[str, Any]) -> bool:
    status = rollout.get("status", {})
    if status.get("abort"):
        return False
    if status.get("phase") == "Degraded":
        return False
    if status.get("phase") != "Healthy":
        return False
    replicas = status.get("replicas", 0)
    updated_replicas = status.get("updatedReplicas", 0)
    ready_replicas = status.get("readyReplicas", 0)
    return updated_replicas == replicas and ready_replicas == replicas and replicas > 0


def check_rollout_failures(rollout: dict[str, Any], name: str) -> None:
    status = rollout.get("status", {})
    if status.get("abort"):
        print(f"Error: rollout/{name} was aborted (status.abort=true).")
        sys.exit(1)
    if status.get("phase") == "Degraded":
        print(f"Error: rollout/{name} is Degraded.")
        sys.exit(1)


def query_prometheus(base_url: str, query: str) -> float | None:
    encoded_query = urllib.parse.quote(query)
    url = f"{base_url.rstrip('/')}/api/v1/query?query={encoded_query}"
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        print(f"Warning: Prometheus query failed: {exc}")
        return None
    except json.JSONDecodeError as exc:
        print(f"Warning: could not parse Prometheus response: {exc}")
        return None

    if data.get("status") != "success":
        print(f"Warning: Prometheus returned non-success status: {data.get('status')}")
        return None

    results = data.get("data", {}).get("result", [])
    if not results:
        return 0.0

    value = results[0].get("value", [])
    if len(value) < 2:
        return None
    try:
        return float(value[1])
    except (TypeError, ValueError):
        return None


def check_prometheus_metrics(prometheus_url: str) -> None:
    if not prometheus_url:
        return

    error_rate = query_prometheus(
        prometheus_url,
        'rate(http_requests_total{status=~"5.."}[1m])',
    )
    if error_rate is not None and error_rate > 0.01:
        print(f"Error: 5xx error rate {error_rate:.4f} exceeds threshold 0.01.")
        sys.exit(1)

    p99_latency_seconds = query_prometheus(
        prometheus_url,
        "histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[1m]))",
    )
    if p99_latency_seconds is not None and p99_latency_seconds * 1000 > 1000:
        print(
            f"Error: p99 latency {p99_latency_seconds * 1000:.2f} ms exceeds threshold 1000 ms."
        )
        sys.exit(1)


def main() -> int:
    args = parse_args()
    rollout_names = [name.strip() for name in args.rollouts.split(",") if name.strip()]
    if not rollout_names:
        print("Error: --rollouts must contain at least one rollout name.")
        return 1

    deadline = time.monotonic() + args.timeout_seconds
    healthy: set[str] = set()

    while time.monotonic() < deadline:
        for name in rollout_names:
            if name in healthy:
                continue
            rollout = get_rollout(args.namespace, name)
            if rollout is None:
                continue
            check_rollout_failures(rollout, name)
            if is_rollout_healthy(rollout):
                print(f"rollout/{name} is healthy.")
                healthy.add(name)

        if len(healthy) == len(rollout_names):
            print("All rollouts are healthy.")
            check_prometheus_metrics(args.prometheus_url)
            return 0

        check_prometheus_metrics(args.prometheus_url)

        remaining = int(deadline - time.monotonic())
        if remaining <= 0:
            break
        print(f"Waiting for rollouts... ({remaining}s remaining)")
        time.sleep(args.poll_interval_seconds)

    unhealthy = [name for name in rollout_names if name not in healthy]
    print(f"Error: timed out waiting for rollouts: {', '.join(unhealthy)}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
