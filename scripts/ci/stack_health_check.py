#!/usr/bin/env python3
"""Unified stack health probe for Fabric_4L backend-integrated validation.

Polls L1-L6 health endpoints with retry and emits a JSON evidence artifact.
Designed to run both locally and in CI.

Usage:
    python scripts/ci/stack_health_check.py [--timeout 300] [--output stack-health.json]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.request
from datetime import UTC, datetime

DEFAULT_ENDPOINTS: dict[str, tuple[str, ...]] = {
    "layer1": ("http://localhost:8001/health",),
    "layer2": ("http://localhost:8002/ready", "http://localhost:8002/health"),
    "layer3": ("http://localhost:8003/health",),
    "layer4": ("http://localhost:8004/health",),
    "layer5": ("http://localhost:8005/api/v1/health", "http://localhost:8005/health"),
    "layer6": ("http://localhost:8006/ready", "http://localhost:8006/health"),
}


def _probe(url: str, timeout: int = 10) -> dict[str, object]:
    """Return {ok: bool, status: int, latency_ms: float, error: str | None}."""
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            return {
                "ok": 200 <= resp.status < 300,
                "status": resp.status,
                "latency_ms": latency_ms,
                "error": None,
            }
    except Exception as exc:
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        return {
            "ok": False,
            "status": None,
            "latency_ms": latency_ms,
            "error": type(exc).__name__ + ": " + str(exc),
        }


def _probe_any(urls: tuple[str, ...], timeout: int = 10) -> dict[str, object]:
    errors: list[dict[str, object]] = []
    for url in urls:
        result = _probe(url, timeout=timeout)
        result["url"] = url
        if result["ok"]:
            return result
        errors.append(result)
    last = errors[-1] if errors else {"ok": False, "status": None, "latency_ms": 0, "error": "no endpoints"}
    last["attempted_urls"] = list(urls)
    return last


def _capture_logs(compose_file: str | None) -> str:
    """Best-effort capture of container logs to surface one-off failures like migrations."""
    cmd = ["docker", "compose"]
    if compose_file:
        cmd.extend(["-f", compose_file])
    cmd.extend(["logs", "--no-color", "--tail", "200"])
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, check=False)
        return result.stdout + result.stderr
    except Exception as exc:
        return f"Could not capture container logs: {type(exc).__name__}: {exc}"


def check_all(
    endpoints: dict[str, tuple[str, ...]],
    *,
    overall_timeout: int = 300,
    per_service_timeout: int = 10,
    retry_interval: int = 5,
    compose_file: str | None = None,
) -> dict[str, object]:
    """Poll every endpoint until all pass or overall_timeout is reached."""
    deadline = time.time() + overall_timeout
    results: dict[str, object] = {name: {"ok": False} for name in endpoints}

    while time.time() < deadline:
        all_ok = True
        for name, url in endpoints.items():
            if not results[name].get("ok"):
                results[name] = _probe_any(url, timeout=per_service_timeout)
            if not results[name]["ok"]:
                all_ok = False
        if all_ok:
            break
        time.sleep(retry_interval)

    report: dict[str, object] = {
        "timestamp": datetime.now(UTC).isoformat(),
        "overall_timeout_seconds": overall_timeout,
        "retry_interval_seconds": retry_interval,
        "all_healthy": all(r.get("ok") for r in results.values()),
        "services": results,
    }
    if not report["all_healthy"]:
        report["container_logs"] = _capture_logs(compose_file)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Fabric_4L stack health probe")
    parser.add_argument("--timeout", type=int, default=300, help="Overall timeout in seconds")
    parser.add_argument("--output", type=str, default="stack-health.json", help="Output JSON path")
    parser.add_argument("--format", choices=["json", "gha"], default="json", help="Output format")
    parser.add_argument("--compose-file", type=str, default="infra/compose/docker-compose.backend-integrated.yml", help="Docker Compose file for log capture on failure")
    args = parser.parse_args()

    report = check_all(
        DEFAULT_ENDPOINTS,
        overall_timeout=args.timeout,
        compose_file=args.compose_file,
    )

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    if args.format == "gha":
        # GitHub Actions step summary format
        print("## Stack Health Check")
        for name, result in report["services"].items():
            icon = "PASS" if result["ok"] else "FAIL"
            print(f"- {icon} **{name}**: {result.get('status') or result.get('error')}")
        if report["all_healthy"]:
            print("\n🟢 **All services healthy**")
        else:
            print("\n🔴 **Some services unhealthy**")

    return 0 if report["all_healthy"] else 1


if __name__ == "__main__":
    sys.exit(main())
