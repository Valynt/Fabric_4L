#!/usr/bin/env python3
"""Fail-safe health gate used before and after blue-green traffic switching."""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request


def fetch_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=10) as resp:  # nosec B310 - controlled operator input
        return json.loads(resp.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--health-url", required=True)
    parser.add_argument("--metrics-url", required=True)
    parser.add_argument("--max-error-rate", type=float, default=0.02)
    parser.add_argument("--max-p95-latency-ms", type=int, default=1200)
    args = parser.parse_args()

    health = fetch_json(args.health_url)
    metrics = fetch_json(args.metrics_url)

    ready = bool(health.get("ready", False))
    error_rate = float(metrics.get("error_rate", 1.0))
    p95_latency_ms = float(metrics.get("p95_latency_ms", 999999))

    gate_ok = ready and error_rate <= args.max_error_rate and p95_latency_ms <= args.max_p95_latency_ms
    if gate_ok:
        print("health gate passed")
        return 0

    print(
        "health gate failed: "
        f"ready={ready}, error_rate={error_rate}, p95_latency_ms={p95_latency_ms}, "
        f"thresholds=({args.max_error_rate}, {args.max_p95_latency_ms})"
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
