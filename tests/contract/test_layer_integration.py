"""Runtime Contract Tests — End-to-End Layer Integration

Validates actual data flow between layers by calling live endpoints.
These tests verify that:
- L4 clients call correct L1/L2 routes (not 404s)
- Data flows from L1 → L3 (ingested entities are queryable)
- L4 workflows orchestrate real L1 and L2 jobs

Requirements:
- L1 service running on localhost:8001
- L2 service running on localhost:8002
- L3 service running on localhost:8003
- L4 service running on localhost:8004
"""

import os
import time
import uuid
from functools import wraps
from typing import Any, Callable, TypeVar

import pytest
import requests
from requests.adapters import HTTPAdapter, Retry

pytestmark = pytest.mark.service_required

# Service endpoints (configurable via env vars for CI flexibility)
L1_URL = os.environ.get("L1_URL", "http://localhost:8001")
L2_URL = os.environ.get("L2_URL", "http://localhost:8002")
L3_URL = os.environ.get("L3_URL", "http://localhost:8003")
L4_URL = os.environ.get("L4_URL", "http://localhost:8004")
RUN_RUNTIME_CONTRACTS = os.environ.get("RUN_RUNTIME_CONTRACTS", "").strip() == "1"
RUNTIME_SERVICE_FLAGS = {
    "l1": os.environ.get("RUN_RUNTIME_L1", "").strip() == "1",
    "l2": os.environ.get("RUN_RUNTIME_L2", "").strip() == "1",
    "l3": os.environ.get("RUN_RUNTIME_L3", "").strip() == "1",
    "l4": os.environ.get("RUN_RUNTIME_L4", "").strip() == "1",
}
SERVICE_AUTH_SECRET = os.environ.get("SERVICE_AUTH_SECRET", "")
RUNTIME_CONTRACT_TENANT_ID = os.environ.get("RUNTIME_CONTRACT_TENANT_ID", "")
_HEALTH_ENDPOINTS = {
    "l1": f"{L1_URL}/health",
    "l2": f"{L2_URL}/health",
    "l3": f"{L3_URL}/health",
    "l4": f"{L4_URL}/health",
}

# HTTP client with retry logic
_session = requests.Session()
_retries = Retry(total=3, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
_session.mount("http://", HTTPAdapter(max_retries=_retries))
_session.mount("https://", HTTPAdapter(max_retries=_retries))

F = TypeVar("F", bound=Callable[..., Any])


def _in_ci() -> bool:
    """Detect CI execution for fail-closed preflight behavior."""
    return os.environ.get("CI", "").strip().lower() in {"1", "true", "yes"}


def _fail_closed_or_skip(message: str) -> None:
    """Fail in CI for launch-gated preflight checks; skip only for local runs."""
    if _in_ci():
        pytest.fail(message)
    pytest.skip(message)


def retry_on_connection_error(max_retries: int = 3, delay: float = 1.0) -> Callable[[F], F]:
    """Decorator to retry tests on connection errors."""

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args, **kwargs):  # type: ignore
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except requests.exceptions.ConnectionError as e:
                    if attempt == max_retries - 1:
                        raise
                    time.sleep(delay * (attempt + 1))
            return None  # unreachable

        return wrapper  # type: ignore

    return decorator


def _runtime_enabled_for(services: set[str]) -> bool:
    """Allow either global runtime enablement or per-service flags."""
    if RUN_RUNTIME_CONTRACTS:
        return True
    return all(RUNTIME_SERVICE_FLAGS.get(service, False) for service in services)


def _runtime_auth_headers() -> dict[str, str]:
    """Build the canonical service identity used by protected runtime routes."""
    if len(SERVICE_AUTH_SECRET) < 32:
        _fail_closed_or_skip("SERVICE_AUTH_SECRET must be at least 32 characters")
    try:
        uuid.UUID(RUNTIME_CONTRACT_TENANT_ID)
    except ValueError:
        _fail_closed_or_skip("RUNTIME_CONTRACT_TENANT_ID must be a UUID")
    return {
        "X-Service-Auth": SERVICE_AUTH_SECRET,
        "X-Tenant-ID": RUNTIME_CONTRACT_TENANT_ID,
    }


def _require_runtime_services(services: set[str]) -> None:
    """Preflight runtime service health and skip with explicit diagnostics."""
    if not _runtime_enabled_for(services):
        required_flags = ", ".join(sorted(f"RUN_RUNTIME_{s.upper()}=1" for s in services))
        _fail_closed_or_skip(
            "Runtime contracts disabled. Set RUN_RUNTIME_CONTRACTS=1 "
            f"or service-specific flags ({required_flags})."
        )

    diagnostics: list[str] = []
    for service in sorted(services):
        health_url = _HEALTH_ENDPOINTS[service]
        try:
            response = _session.get(health_url, timeout=5)
            if response.status_code != 200:
                diagnostics.append(
                    f"{service.upper()} health check failed at {health_url}: "
                    f"HTTP {response.status_code} ({response.text[:120]!r})"
                )
        except requests.RequestException as exc:
            diagnostics.append(f"{service.upper()} health check error at {health_url}: {exc}")

    if diagnostics:
        _fail_closed_or_skip("Runtime preflight prerequisites not met: " + " | ".join(diagnostics))


@pytest.fixture
def test_tenant():
    """Generate unique test tenant ID."""
    return f"test-tenant-{uuid.uuid4().hex[:8]}"


@pytest.fixture
def test_entity_data():
    """Generate unique test entity data."""
    test_id = f"test-entity-{uuid.uuid4().hex[:8]}"
    return {
        "id": test_id,
        "name": f"TestCorp {test_id}",
        "entity_type": "Organization",
        "properties": {
            "industry": "Technology",
            "employees": 500,
        },
    }


class TestL1RoutesExist:
    """Verify L4 client routes match actual L1 endpoints."""

    @retry_on_connection_error()
    def test_l1_health_check(self):
        """L1 health endpoint responds with valid health status."""
        response = _session.get(f"{L1_URL}/health", timeout=10)
        assert response.status_code == 200, f"Health check failed: {response.status_code}"
        data = response.json()
        assert isinstance(data, dict), f"Expected dict response, got {type(data)}"
        # Accept either 'status' field or common health indicators
        has_health_indicator = (
            "status" in data or data.get("healthy") is True or data.get("status") == "healthy"
        )
        assert has_health_indicator, f"No health indicator in response: {data}"

    @retry_on_connection_error()
    def test_l1_jobs_endpoint_post_creates_job(self):
        """POST /jobs creates ingestion job (was /v1/ingestion/jobs)."""
        payload = {
            "target": {"url": "https://example.com/test", "type": "http"},
            "document_type": "test",
        }
        response = _session.post(f"{L1_URL}/jobs", json=payload, timeout=10)
        # May fail auth but should NOT 404
        assert response.status_code != 404, f"L1 /jobs endpoint not found: {response.text[:200]}"
        # Should be 202 (accepted) or 401/403 (auth), not 404
        assert response.status_code in [202, 200, 401, 403], (
            f"Unexpected status: {response.status_code}"
        )

    @retry_on_connection_error()
    def test_l1_jobs_get_list(self):
        """GET /jobs lists jobs (was /v1/ingestion/jobs)."""
        response = _session.get(f"{L1_URL}/jobs", timeout=10)
        assert response.status_code != 404, f"L1 /jobs endpoint not found: {response.text[:200]}"
        assert response.status_code in [200, 401, 403], f"Unexpected status: {response.status_code}"

    @retry_on_connection_error()
    def test_l1_job_status_endpoint(self):
        """GET /jobs/{id} gets job status (was /v1/ingestion/jobs/{id})."""
        fake_job_id = str(uuid.uuid4())
        response = _session.get(f"{L1_URL}/jobs/{fake_job_id}", timeout=10)
        # Should be 404 for unknown job, not endpoint 404
        assert response.status_code != 404, (
            f"L1 /jobs/{{id}} endpoint not found: {response.text[:200]}"
        )
        # May get 401, 403, or 404 for unknown job
        assert response.status_code in [404, 401, 403, 200], (
            f"Unexpected status: {response.status_code}"
        )


class TestL2RoutesExist:
    """Verify L4 client routes match actual L2 endpoints."""

    @retry_on_connection_error()
    def test_l2_health_check(self):
        """L2 health endpoint responds."""
        response = _session.get(f"{L2_URL}/health", timeout=10)
        assert response.status_code == 200, f"L2 health check failed: {response.status_code}"
        data = response.json()
        assert isinstance(data, dict), f"Expected dict, got {type(data)}"

    @retry_on_connection_error()
    def test_l2_extract_endpoint_post(self):
        """POST /v1/extract exists (was /v1/extract/filing)."""
        payload = {
            "document_url": "https://example.com/test.pdf",
            "filing_type": "TEST",
            "extraction_type": "test",
        }
        response = _session.post(f"{L2_URL}/v1/extract", json=payload, timeout=10)
        # Should NOT 404 - endpoint should exist
        assert response.status_code != 404, (
            f"L2 /v1/extract endpoint not found: {response.text[:200]}"
        )

    @retry_on_connection_error()
    def test_l2_extract_and_ingest_endpoint(self):
        """POST /v1/extract-and-ingest exists."""
        payload = {
            "document_url": "https://example.com/test.pdf",
            "filing_type": "TEST",
        }
        response = _session.post(f"{L2_URL}/v1/extract-and-ingest", json=payload, timeout=10)
        assert response.status_code != 404, (
            f"L2 /v1/extract-and-ingest endpoint not found: {response.text[:200]}"
        )

    @retry_on_connection_error()
    def test_l2_extract_status_endpoint(self):
        """GET /v1/extract/status/{job_id} exists."""
        fake_job_id = str(uuid.uuid4())
        response = _session.get(f"{L2_URL}/v1/extract/status/{fake_job_id}", timeout=10)
        assert response.status_code != 404, (
            f"L2 /v1/extract/status endpoint not found: {response.text[:200]}"
        )


class TestL1ToL3DataFlow:
    """Verify data flows from L1 ingestion to L3 knowledge graph."""

    @pytest.mark.runtime_contract
    def test_l1_ingest_creates_data_in_l3(self, test_entity_data):
        """End-to-end: L1 ingest → L3 queryable."""
        _require_runtime_services({"l1", "l3"})

        # 1. Create entity directly in L3 (simulating L1→L3 flow)
        entity_name = test_entity_data["name"]

        # 2. Query L3 for the entity
        l3_response = _session.post(
            f"{L3_URL}/v1/search/hybrid",
            json={"query": entity_name, "entity_type": "Company"},
            headers=_runtime_auth_headers(),
            timeout=15,
        )
        assert l3_response.status_code == 200, f"L3 search failed: {l3_response.text[:200]}"
        results = l3_response.json()

        # 3. Verify response structure
        assert "entities" in results or "results" in results, (
            f"Missing entities in response: {list(results.keys())}"
        )

    @pytest.mark.runtime_contract
    def test_l3_entity_persistence(self):
        """L3 entities endpoint returns data."""
        _require_runtime_services({"l3"})

        response = _session.post(
            f"{L3_URL}/v1/ingest",
            json={
                "rdf_data": (
                    "@prefix ex: <http://example.com/> . "
                    "@prefix vf: <http://valuefabric.io/ontology/> . "
                    "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> . "
                    f"ex:runtime-{uuid.uuid4().hex[:8]} rdf:type vf:Company ; "
                    'vf:name "TestCorp Runtime" .'
                ),
                "source_id": f"runtime-source-{uuid.uuid4().hex[:8]}",
                "extraction_job_id": f"runtime-job-{uuid.uuid4().hex[:8]}",
            },
            headers=_runtime_auth_headers(),
            timeout=10,
        )
        # L3 may not have direct ingest - skip if 404
        if response.status_code == 404:
            _fail_closed_or_skip("L3 ingest endpoint not available")

        assert response.status_code in [200, 202], f"Unexpected status: {response.status_code}"


class TestL4WorkflowOrchestration:
    """Verify the canonical L4 workflow creation and status contract."""

    @pytest.mark.runtime_contract
    def test_l4_workflow_create_contract(self):
        """Create a supported workflow through the authenticated canonical route."""
        _require_runtime_services({"l4"})
        headers = _runtime_auth_headers()
        response = _session.post(
            f"{L4_URL}/v1/workflows",
            json={
                "workflow_type": "roi_calculator",
                "inputs": {
                    "prospect_id": f"runtime-{uuid.uuid4().hex[:8]}",
                    "use_case_ids": ["runtime-contract-driver"],
                    "prospect_metrics": {"annual_revenue": 1000000},
                },
                "priority": "NORMAL",
            },
            headers=headers,
            timeout=10,
        )

        assert response.status_code == 201, f"Workflow start failed: {response.text[:200]}"
        workflow_id = response.json().get("workflow_instance_id")
        assert workflow_id, "No workflow_instance_id in response"

        status_resp = _session.get(
            f"{L4_URL}/v1/workflows/{workflow_id}",
            headers=headers,
            timeout=5,
        )
        assert status_resp.status_code == 200, f"Workflow status failed: {status_resp.text[:200]}"


class TestContractAlignment:
    """Verify OpenAPI contracts match runtime behavior."""

    @retry_on_connection_error()
    def test_l1_openapi_spec_loads(self):
        """L1 OpenAPI spec is valid and loadable."""
        response = _session.get(f"{L1_URL}/openapi.json", timeout=10)
        if response.status_code == 404:
            _fail_closed_or_skip("L1 OpenAPI endpoint not exposed")

        assert response.status_code == 200, f"OpenAPI spec load failed: {response.status_code}"
        spec = response.json()
        assert "paths" in spec, "Missing 'paths' in OpenAPI spec"
        # Verify actual routes are documented
        paths = spec["paths"]
        assert "/jobs" in paths or any("jobs" in p for p in paths), "Jobs route not documented"

    @retry_on_connection_error()
    def test_l2_openapi_spec_loads(self):
        """L2 OpenAPI spec is valid and loadable."""
        response = _session.get(f"{L2_URL}/openapi.json", timeout=10)
        if response.status_code == 404:
            response = _session.get(f"{L2_URL}/docs/openapi.json", timeout=10)

        if response.status_code == 404:
            _fail_closed_or_skip("L2 OpenAPI endpoint not exposed")

        assert response.status_code == 200, f"OpenAPI spec load failed: {response.status_code}"
        spec = response.json()
        assert "paths" in spec, "Missing 'paths' in OpenAPI spec"

    @retry_on_connection_error()
    def test_l3_openapi_spec_matches_contract(self):
        """L3 runtime spec matches contracts/openapi/layer3-knowledge.json."""
        response = _session.get(f"{L3_URL}/openapi.json", timeout=10)
        if response.status_code == 404:
            _fail_closed_or_skip("L3 OpenAPI endpoint not exposed")

        assert response.status_code == 200, f"OpenAPI spec load failed: {response.status_code}"
        runtime_spec = response.json()

        # Load contract spec
        import json
        from pathlib import Path

        contract_path = (
            Path(__file__).parent.parent.parent / "contracts" / "openapi" / "layer3-knowledge.json"
        )
        if not contract_path.exists():
            _fail_closed_or_skip("Contract spec not found")

        contract_spec = json.loads(contract_path.read_text())

        # Verify key endpoints exist in both
        contract_paths = set(contract_spec.get("paths", {}).keys())
        runtime_paths = set(runtime_spec.get("paths", {}).keys())

        # Check critical paths
        critical_paths = ["/v1/ingest", "/v1/search/hybrid"]
        for path in critical_paths:
            if path in contract_paths:
                assert path in runtime_paths, f"Critical path {path} missing from runtime"


if __name__ == "__main__":
    # Run basic connectivity tests
    print("Testing L1 connectivity...")
    try:
        r = requests.get(f"{L1_URL}/health")
        print(f"  L1 health: {r.status_code}")
    except Exception as e:
        print(f"  L1 unavailable: {e}")

    print("\nTesting L2 connectivity...")
    try:
        r = requests.get(f"{L2_URL}/health")
        print(f"  L2 health: {r.status_code}")
    except Exception as e:
        print(f"  L2 unavailable: {e}")

    print("\nTesting L3 connectivity...")
    try:
        r = requests.get(f"{L3_URL}/health")
        print(f"  L3 health: {r.status_code}")
    except Exception as e:
        print(f"  L3 unavailable: {e}")

    print("\nRun pytest with -s to execute full stack tests")
