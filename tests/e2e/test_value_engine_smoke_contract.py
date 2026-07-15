"""Deterministic smoke contract for the Value Engine workflow.

The live workflow tests in ``test_value_engine_workflow.py`` still exercise a running
stack when ``RUN_E2E=1`` is supplied. This file is the release-gate smoke subset:
it validates that the workflow contract, endpoint surface, tenant/header behavior,
and demo data shape are present without relying on external services or skip valves.
"""

from __future__ import annotations

from pathlib import Path

from tests.e2e.test_value_engine_workflow import (
    DEMO_PROSPECT,
    DEMO_TENANT,
    DEMO_USER,
    ValueEngineE2EClient,
)

EXPECTED_METHODS = [
    "signup",
    "login",
    "create_prospect",
    "enrich_prospect",
    "get_prospect_context",
    "run_intelligence_workflow",
    "get_workflow_status",
    "get_intelligence_findings",
    "create_hypothesis",
    "get_hypotheses",
    "create_driver_tree",
    "get_driver_tree",
    "get_evidence",
    "attach_evidence",
    "create_scenario",
    "calculate_scenario",
    "get_scenario",
    "create_value_case",
    "get_value_case",
    "get_value_case_preview",
]


class TestValueEngineSmokeContract:
    """Release-safe smoke checks for the seven-step Value Engine path."""

    def test_demo_identity_and_prospect_contract_is_complete(self) -> None:
        assert DEMO_TENANT["slug"]
        assert DEMO_TENANT["name"]
        assert DEMO_USER["email"].endswith("@acmerobotics.com")
        assert len(DEMO_USER["password"]) >= 8
        assert DEMO_USER["role"] in {"admin", "seller", "ae"}
        assert DEMO_PROSPECT["company_name"]
        assert "." in DEMO_PROSPECT["domain"]
        assert DEMO_PROSPECT["objective"] in {"cost_reduction", "growth", "risk_reduction", "efficiency"}

    def test_client_has_every_required_workflow_operation(self) -> None:
        missing = [name for name in EXPECTED_METHODS if not callable(getattr(ValueEngineE2EClient, name, None))]
        assert not missing, f"Missing Value Engine E2E client operations: {missing}"

    def test_client_headers_preserve_auth_and_tenant_context(self) -> None:
        client = ValueEngineE2EClient("https://fabric.example.test", api_key="test-api-key")
        assert client.base_url == "https://fabric.example.test"
        assert client._headers()["X-API-Key"] == "test-api-key"

        client.token = "jwt-token"
        client.tenant_id = "tenant-123"
        headers = client._headers()
        assert headers["Authorization"] == "Bearer jwt-token"
        assert "X-API-Key" not in headers, "Bearer auth must take precedence over API key fallback"
        assert headers["X-Tenant-ID"] == "tenant-123"
        assert headers["Content-Type"] == "application/json"

    def test_workflow_source_references_all_seven_release_steps(self) -> None:
        source = Path("tests/e2e/test_value_engine_workflow.py").read_text(encoding="utf-8")
        for step in [
            "Step 1: Prospect Setup",
            "Step 2: Intelligence",
            "Step 3: Hypothesis",
            "Step 4: Driver Tree",
            "Step 5: Evidence",
            "Step 6: ROI",
            "Step 7: Value Case",
        ]:
            assert step in source, f"Workflow source is missing {step}"

    def test_endpoint_surface_is_scoped_to_versioned_api(self) -> None:
        source = Path("tests/e2e/test_value_engine_workflow.py").read_text(encoding="utf-8")
        expected_paths = [
            "/v1/auth/signup",
            "/v1/auth/login",
            "/v1/prospects",
            "/v1/workflows/intelligence",
            "/v1/intelligence/findings",
            "/v1/intelligence/hypotheses",
            "/v1/value-engine/driver-tree",
            "/v1/value-engine/scenarios",
            "/v1/value-engine/cases",
        ]
        missing = [path for path in expected_paths if path not in source]
        assert not missing, f"Missing versioned Value Engine API paths: {missing}"
