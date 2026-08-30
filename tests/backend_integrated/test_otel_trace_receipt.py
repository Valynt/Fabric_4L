"""P0-007: Runtime smoke test for OpenTelemetry trace receipt.

Requires:
  - Running OpenTelemetry Collector (or local collector via docker-compose)
  - Running services: billing, layer2-5-signal-refinery
  - Jaeger or OTLP backend accessible for trace verification

This test is gated behind the ``service_required`` marker and only runs in
staging or backend-integrated pipelines.
"""

from __future__ import annotations

import os
import time
import urllib.request
from typing import Any

import pytest

# Service endpoints (overridable via environment)
BILLING_URL = os.getenv("BILLING_URL", "http://localhost:8000")
LAYER25_URL = os.getenv("LAYER25_URL", "http://localhost:8007")
JAEGER_URL = os.getenv("JAEGER_URL", "http://localhost:16686")


def _get_json(url: str, timeout: float = 5.0) -> dict[str, Any] | None:
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as response:
            import json
            return json.loads(response.read().decode("utf-8"))
    except Exception:
        return None


@pytest.mark.backend_integrated
@pytest.mark.service_required
def test_billing_service_emits_traces() -> None:
    """Send a request to billing service and verify traces appear in Jaeger."""
    # 1. Health check to ensure service is up
    health = _get_json(f"{BILLING_URL}/health")
    assert health is not None, f"Billing service not available at {BILLING_URL}"

    # 2. Send a request that generates a trace
    _get_json(f"{BILLING_URL}/health")

    # 3. Allow traces to propagate
    time.sleep(2)

    # 4. Query Jaeger for traces
    # Note: Jaeger query API v3 uses /api/traces?service=<service_name>
    traces = _get_json(f"{JAEGER_URL}/api/traces?service=billing&limit=1")
    assert traces is not None, "Jaeger not accessible - cannot verify trace receipt"
    data = traces.get("data", [])
    assert len(data) > 0, "No traces found for service 'billing' in Jaeger"


@pytest.mark.backend_integrated
@pytest.mark.service_required
def test_layer25_service_emits_traces() -> None:
    """Send a request to layer2-5-signal-refinery and verify traces."""
    health = _get_json(f"{LAYER25_URL}/health")
    assert health is not None, f"Layer2.5 service not available at {LAYER25_URL}"

    _get_json(f"{LAYER25_URL}/health")
    time.sleep(2)

    traces = _get_json(f"{JAEGER_URL}/api/traces?service=layer2-5-signal-refinery&limit=1")
    assert traces is not None, "Jaeger not accessible"
    data = traces.get("data", [])
    assert len(data) > 0, "No traces found for service 'layer2-5-signal-refinery'"
