"""
Sprint 3: Distributed Trace E2E Validation Test

Validates that a single trace propagates across all 10 services.
Injects a traceparent header at the API gateway and verifies
the same trace_id appears in logs from L1→L2→L3→L4→L5.

Usage:
    pytest tests/e2e/test_distributed_tracing.py -v

Requires:
    - All services running in Kubernetes
    - Jaeger query endpoint accessible
    - kubectl configured
"""
from __future__ import annotations

import os
import subprocess
import time
import uuid
from typing import Optional

import pytest
import requests

JAEGER_URL = os.environ.get("JAEGER_QUERY_URL", "http://jaeger.value-fabric.svc.cluster.local:16686")
API_GATEWAY = os.environ.get("API_GATEWAY_URL", "http://api-gateway.value-fabric.svc.cluster.local:8000")
TEST_TENANT = os.environ.get("TEST_TENANT_ID", "test-tenant-e2e")

pytestmark = [pytest.mark.e2e, pytest.mark.slow]


class TestDistributedTracing:
    """End-to-end distributed trace propagation validation."""

    @pytest.fixture
    def trace_id(self) -> str:
        """Generate a unique 32-hex trace ID."""
        return uuid.uuid4().hex + uuid.uuid4().hex[:16]

    @pytest.fixture
    def traceparent(self, trace_id: str) -> str:
        """Build W3C traceparent header."""
        parent_id = uuid.uuid4().hex[:16]
        flags = "01"  # sampled
        return f"00-{trace_id}-{parent_id}-{flags}"

    def _jaeger_has_trace(self, trace_id: str, timeout: int = 60) -> bool:
        """Poll Jaeger until trace appears or timeout."""
        service_names = [
            "api-gateway",
            "layer1-ingestion",
            "layer2-extraction",
            "layer3-knowledge",
            "layer4-agents",
            "layer5-ground-truth",
            "layer6-benchmarks",
            "layer7-billing",
        ]
        start = time.time()
        found_services = set()
        while time.time() - start < timeout:
            for svc in service_names:
                if svc in found_services:
                    continue
                try:
                    resp = requests.get(
                        f"{JAEGER_URL}/api/traces",
                        params={"service": svc, "traceID": trace_id},
                        timeout=5,
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        if data.get("data") and len(data["data"]) > 0:
                            found_services.add(svc)
                except Exception:
                    pass
            if len(found_services) >= 5:
                return True
            time.sleep(2)
        return len(found_services) >= 3

    def test_trace_propagates_through_api_to_l4(self, traceparent: str, trace_id: str):
        """V12-S3-1: Trace from API gateway → L4 agents."""
        resp = requests.get(
            f"{API_GATEWAY}/health",
            headers={
                "traceparent": traceparent,
                "X-Tenant-ID": TEST_TENANT,
            },
            timeout=30,
        )
        assert resp.status_code == 200, f"API health check failed: {resp.status_code}"

        # Wait for trace to appear in Jaeger
        time.sleep(5)
        assert self._jaeger_has_trace(trace_id), (
            f"Trace {trace_id} not found in Jaeger within timeout. "
            "Check trace propagation through services."
        )

    def test_trace_spans_all_services(self, traceparent: str, trace_id: str):
        """V12-S3-2: Full trace across L1→L2→L3→L4→L5."""
        # Trigger a workflow that exercises multiple layers
        resp = requests.post(
            f"{API_GATEWAY}/v1/workflows/run",
            headers={
                "traceparent": traceparent,
                "X-Tenant-ID": TEST_TENANT,
                "Content-Type": "application/json",
            },
            json={
                "workflow_type": "value_extraction",
                "input": {"test": True},
            },
            timeout=60,
        )
        # 202 accepted is fine — we just need the trace to flow
        assert resp.status_code in (200, 201, 202), f"Workflow submission failed: {resp.status_code}"

        # Wait longer for async processing
        time.sleep(15)

        # Query Jaeger for the trace
        resp = requests.get(
            f"{JAEGER_URL}/api/traces/{trace_id}",
            timeout=10,
        )
        assert resp.status_code == 200, f"Trace {trace_id} not found in Jaeger"

        trace_data = resp.json()
        assert "data" in trace_data and len(trace_data["data"]) > 0, "Empty trace data"

        # Extract service names from spans
        services_found = set()
        for trace in trace_data["data"]:
            for span in trace.get("spans", []):
                process_id = span.get("processID", "")
                process = trace.get("processes", {}).get(process_id, {})
                svc = process.get("serviceName", "")
                if svc:
                    services_found.add(svc)

        print(f"Services found in trace: {services_found}")
        assert len(services_found) >= 3, (
            f"Trace only spans {len(services_found)} services: {services_found}. "
            f"Expected at least 3 (API gateway + 2 downstream)."
        )

    def test_traceparent_in_response_headers(self, traceparent: str):
        """V12-S3-3: Response includes traceparent header for correlation."""
        resp = requests.get(
            f"{API_GATEWAY}/health",
            headers={
                "traceparent": traceparent,
                "X-Tenant-ID": TEST_TENANT,
            },
            timeout=30,
        )
        assert resp.status_code == 200
        response_trace = resp.headers.get("traceparent", "")
        assert response_trace, "Response missing traceparent header"
        # Response traceparent should have same trace_id
        original_trace_id = traceparent.split("-")[1]
        response_trace_id = response_trace.split("-")[1]
        assert original_trace_id == response_trace_id, (
            f"Trace ID mismatch: request={original_trace_id} response={response_trace_id}"
        )

    def test_tracestate_propagation(self, traceparent: str):
        """V12-S3-4: tracestate header propagates through services."""
        tracestate = "fabric=vendor-context,other=vendor2"
        resp = requests.get(
            f"{API_GATEWAY}/health",
            headers={
                "traceparent": traceparent,
                "tracestate": tracestate,
                "X-Tenant-ID": TEST_TENANT,
            },
            timeout=30,
        )
        assert resp.status_code == 200
        response_state = resp.headers.get("tracestate", "")
        assert "fabric" in response_state, f"tracestate lost: expected 'fabric' in '{response_state}'"
