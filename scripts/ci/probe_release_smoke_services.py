#!/usr/bin/env python3
"""Probe the Fabric_4L release-smoke L1–L6 service stack.

The probe is deliberately small and dependency-free so it can run in CI before
pytest collection. It fails closed when any layer has no reachable health
endpoint and writes a machine-readable evidence file for release artifacts.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SERVICE_URLS = {
    "l1": os.getenv("LAYER1_API_URL", "http://localhost:8001").rstrip("/"),
    "l2": os.getenv("LAYER2_API_URL", "http://localhost:8002").rstrip("/"),
    "l3": os.getenv("LAYER3_API_URL", "http://localhost:8003").rstrip("/"),
    "l4": os.getenv("LAYER4_API_URL", "http://localhost:8004").rstrip("/"),
    "l5": os.getenv("LAYER5_API_URL", "http://localhost:8005").rstrip("/"),
    "l6": os.getenv("LAYER6_API_URL", "http://localhost:8006").rstrip("/"),
}

HEALTH_PATHS = {
    "l1": ("/health", "/api/v1/health"),
    "l2": ("/health", "/api/v1/health"),
    "l3": ("/health", "/api/v1/health"),
    "l4": ("/health", "/v1/health", "/v1/health/detailed"),
    "l5": ("/health", "/api/v1/health"),
    "l6": ("/health", "/v1/health"),
}


def _request_json(url: str, timeout: float) -> tuple[int, Any]:
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - local release-smoke URLs only
        body = response.read(64_000)
        content_type = response.headers.get("content-type", "")
        if "json" in content_type and body:
            return response.status, json.loads(body.decode("utf-8"))
        return response.status, body.decode("utf-8", errors="replace")


def _probe_layer(layer: str, timeout: float) -> dict[str, Any] | None:
    base_url = SERVICE_URLS[layer]
    errors: list[str] = []
    for path in HEALTH_PATHS[layer]:
        url = f"{base_url}{path}"
        try:
            status, body = _request_json(url, timeout)
        except (TimeoutError, urllib.error.URLError, urllib.error.HTTPError, OSError, json.JSONDecodeError) as exc:
            errors.append(f"{url}: {type(exc).__name__}: {exc}")
            continue
        if status in {200, 204}:
            return {
                "layer": layer,
                "base_url": base_url,
                "health_path": path,
                "status": status,
                "body": body,
            }
        errors.append(f"{url}: unexpected status {status}")
    return {
        "layer": layer,
        "base_url": base_url,
        "health_path": None,
        "status": "unhealthy",
        "errors": errors,
    }


def main() -> int:
    deadline_seconds = float(os.getenv("RELEASE_SMOKE_READINESS_TIMEOUT", "180"))
    interval_seconds = float(os.getenv("RELEASE_SMOKE_READINESS_INTERVAL", "5"))
    request_timeout = float(os.getenv("BACKEND_VALIDATION_HTTP_TIMEOUT", "3"))
    evidence_path = Path(os.getenv("RELEASE_SMOKE_EVIDENCE", "artifacts/release_smoke/service_readiness.json"))
    evidence_path.parent.mkdir(parents=True, exist_ok=True)

    started = time.monotonic()
    last_results: dict[str, dict[str, Any]] = {}
    while time.monotonic() - started <= deadline_seconds:
        last_results = {layer: _probe_layer(layer, request_timeout) or {} for layer in SERVICE_URLS}
        if all(result.get("health_path") for result in last_results.values()):
            payload = {
                "status": "ready",
                "checked_at": datetime.now(timezone.utc).isoformat(),
                "elapsed_seconds": round(time.monotonic() - started, 3),
                "services": last_results,
            }
            evidence_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            print(f"release-smoke services ready; evidence={evidence_path}")
            return 0
        time.sleep(interval_seconds)

    payload = {
        "status": "unhealthy",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "services": last_results,
    }
    evidence_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"release-smoke services failed readiness; evidence={evidence_path}", file=sys.stderr)
    print(json.dumps(payload, indent=2, sort_keys=True), file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
