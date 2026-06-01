"""
P2-009: Pact contract tests for L5 Ground Truth, L6 Benchmarks, L7 Billing
Expands consumer/provider coverage beyond L1-L4.
"""
import pytest
import requests
from pathlib import Path

pytestmark = [pytest.mark.contract, pytest.mark.pact]

PACT_DIR = Path(__file__).parent.parent.parent / "pacts"


class TestL5GroundTruthContracts:
    """Pact consumer tests for L5 Ground Truth service."""

    @pytest.fixture
    def pact(self):
        pytest.importorskip("pact")
        from pact import Consumer, Provider

        return Consumer("l5-ground-truth").has_pact_with(
            Provider("api-gateway"),
            pact_dir=str(PACT_DIR),
        )

    def test_get_ground_truth_items(self, pact):
        expected = {
            "items": [{"id": "gt_001", "tenant_id": "tenant_123", "status": "validated", "confidence": 0.95}],
            "total": 1, "has_more": False,
        }
        (pact.given("ground truth items exist")
         .upon_receiving("a request for ground truth items")
         .with_request("GET", "/v1/ground-truth/items", query={"limit": "10"})
         .will_respond_with(200, body=expected))
        with pact:
            # TODO: replace interim requests call with real consumer client
            result = requests.get(
                f"{pact.uri}/v1/ground-truth/items",
                params={"limit": "10"},
                timeout=5,
            )
            assert result.status_code == 200
            assert result.json() == expected

    def test_submit_validation(self, pact):
        request_body = {"item_id": "gt_001", "validation": "approved", "validator_notes": "Correct"}
        expected = {"id": "val_001", "status": "submitted"}
        (pact.given("ground truth item exists")
         .upon_receiving("a validation submission")
         .with_request("POST", "/v1/ground-truth/validations", body=request_body)
         .will_respond_with(201, body=expected))
        with pact:
            # TODO: replace interim requests call with real consumer client
            result = requests.post(
                f"{pact.uri}/v1/ground-truth/validations",
                json=request_body,
                timeout=5,
            )
            assert result.status_code == 201
            assert result.json() == expected


class TestL6BenchmarksContracts:
    @pytest.fixture
    def pact(self):
        pytest.importorskip("pact")
        from pact import Consumer, Provider

        return Consumer("l6-benchmarks").has_pact_with(
            Provider("api-gateway"), pact_dir=str(PACT_DIR))

    def test_run_benchmark(self, pact):
        request_body = {"benchmark_type": "extraction_accuracy", "dataset_id": "ds_001"}
        expected = {"run_id": "run_001", "status": "queued"}
        (pact.given("benchmark dataset exists")
         .upon_receiving("a benchmark run request")
         .with_request("POST", "/v1/benchmarks/run", body=request_body)
         .will_respond_with(202, body=expected))
        with pact:
            # TODO: replace interim requests call with real consumer client
            result = requests.post(
                f"{pact.uri}/v1/benchmarks/run",
                json=request_body,
                timeout=5,
            )
            assert result.status_code == 202
            assert result.json() == expected

    def test_get_benchmark_results(self, pact):
        expected = {"run_id": "run_001", "status": "completed",
             "metrics": {"accuracy": 0.94, "precision": 0.92, "recall": 0.96}}
        (pact.given("benchmark run completed")
         .upon_receiving("a request for benchmark results")
         .with_request("GET", "/v1/benchmarks/results/run_001")
         .will_respond_with(200, body=expected))
        with pact:
            # TODO: replace interim requests call with real consumer client
            result = requests.get(
                f"{pact.uri}/v1/benchmarks/results/run_001",
                timeout=5,
            )
            assert result.status_code == 200
            assert result.json() == expected


class TestL7BillingContracts:
    @pytest.fixture
    def pact(self):
        pytest.importorskip("pact")
        from pact import Consumer, Provider

        return Consumer("l7-billing").has_pact_with(
            Provider("api-gateway"), pact_dir=str(PACT_DIR))

    def test_get_subscription(self, pact):
        expected = {"id": "sub_001", "plan": "enterprise", "status": "active",
             "seats": 25, "features": ["ai_extraction", "knowledge_graph", "api_access"]}
        (pact.given("active subscription exists")
         .upon_receiving("a request for subscription details")
         .with_request("GET", "/v1/billing/subscription")
         .will_respond_with(200, body=expected))
        with pact:
            # TODO: replace interim requests call with real consumer client
            result = requests.get(
                f"{pact.uri}/v1/billing/subscription",
                timeout=5,
            )
            assert result.status_code == 200
            assert result.json() == expected

    def test_report_usage(self, pact):
        request_body = {"resource_type": "api_call", "quantity": 1500, "tenant_id": "tenant_123"}
        expected = {"usage_id": "use_001", "status": "recorded"}
        (pact.given("metered billing is configured")
         .upon_receiving("a usage report")
         .with_request("POST", "/v1/billing/usage", body=request_body)
         .will_respond_with(202, body=expected))
        with pact:
            # TODO: replace interim requests call with real consumer client
            result = requests.post(
                f"{pact.uri}/v1/billing/usage",
                json=request_body,
                timeout=5,
            )
            assert result.status_code == 202
            assert result.json() == expected
