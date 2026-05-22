"""Consumer-side Pact contract tests for Layer 4 Agents API.

These tests define the contract that the frontend (consumer) expects from the
Layer 4 Agents API (provider).  Each interaction is recorded by the Pact mock
provider and written to ``pacts/value-fabric-frontend-layer4-agents-api.json``.

Run locally:
    pip install -r tests/requirements.txt
    pytest tests/pact/test_l4_consumer_contract.py -v

The generated pact file can be published to a Pact Broker in CI:
    pact-broker publish pacts/ \
        --consumer-app-version=$(git rev-parse HEAD) \
        --broker-base-url=$PACT_BROKER_URL \
        --broker-token=$PACT_BROKER_TOKEN
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest
import requests

pytestmark = [pytest.mark.pact, pytest.mark.contract_static]


@pytest.fixture
def consumer_pact(pact_dir: Path) -> Any:
    """Build a Pact between the frontend consumer and Layer 4 provider."""
    # Deferred import so collection doesn't fail when pact-python isn't installed
    pytest.importorskip("pact")
    from pact import Consumer, Provider

    pact = Consumer("value-fabric-frontend").has_pact_with(
        Provider("layer4-agents-api"),
        pact_dir=str(pact_dir),
        log_dir=str(pact_dir / "logs"),
    )
    return pact


class TestL4RootEndpoint:
    """Pact contract for the root / endpoint."""

    def test_root_returns_service_metadata(self, consumer_pact: Any) -> None:
        """Consumer expects the root endpoint to expose service metadata."""
        expected_body = {
            "service": "Layer 4: Agentic Workflow Engine",
            "version": "0.2.0",
            "documentation": "/docs",
            "health": "/health",
            "metrics": "/metrics",
        }

        (
            consumer_pact.given("service is running")
            .upon_receiving("a request for service metadata")
            .with_request("GET", "/", headers={"Accept": "application/json"})
            .will_respond_with(200, body=expected_body)
        )

        with consumer_pact:
            result = requests.get(
                f"{consumer_pact.uri}/",
                headers={"Accept": "application/json"},
                timeout=5,
            )
            assert result.status_code == 200
            assert result.json()["service"] == "Layer 4: Agentic Workflow Engine"
            assert "/health" in result.json()["health"]


class TestL4BillingPlanLimits:
    """Pact contract for GET /billing/plans/{plan_id}/limits."""

    def test_plan_limits_returns_usage_configuration(self, consumer_pact: Any) -> None:
        """Consumer expects plan limits to expose usage configuration."""
        expected_body = {
            "api_calls": {
                "included_amount": 50000,
                "period": "monthly",
                "overage_rate": 0.001,
                "hard_limit": False,
                "warning_threshold": 80.0,
            },
            "tokens": {
                "included_amount": 5000000,
                "period": "monthly",
                "overage_rate": 0.00002,
                "hard_limit": False,
                "warning_threshold": 80.0,
            },
            "storage_gb": {
                "included_amount": 50.0,
                "period": "monthly",
                "overage_rate": 0.1,
                "hard_limit": False,
                "warning_threshold": 80.0,
            },
        }

        (
            consumer_pact.given("pro plan exists")
            .upon_receiving("a request for pro plan limits")
            .with_request("GET", "/billing/plans/pro/limits", headers={"Accept": "application/json"})
            .will_respond_with(200, body=expected_body)
        )

        with consumer_pact:
            result = requests.get(
                f"{consumer_pact.uri}/billing/plans/pro/limits",
                headers={"Accept": "application/json"},
                timeout=5,
            )
            assert result.status_code == 200
            data = result.json()
            assert "api_calls" in data
            assert data["api_calls"]["included_amount"] == 50000
            assert data["api_calls"]["hard_limit"] is False

    def test_plan_limits_404_for_unknown_plan(self, consumer_pact: Any) -> None:
        """Consumer expects 404 for non-existent plans."""
        (
            consumer_pact.given("unknown plan requested")
            .upon_receiving("a request for an unknown plan")
            .with_request("GET", "/billing/plans/unknown-plan/limits", headers={"Accept": "application/json"})
            .will_respond_with(404, body={"detail": "Plan not found: unknown-plan"})
        )

        with consumer_pact:
            result = requests.get(
                f"{consumer_pact.uri}/billing/plans/unknown-plan/limits",
                headers={"Accept": "application/json"},
                timeout=5,
            )
            assert result.status_code == 404
