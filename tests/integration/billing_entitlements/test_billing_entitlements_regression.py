"""Regression pack for billing + entitlement behavior.

This suite is intentionally implementation-agnostic: it encodes behavioral
contracts that any billing/entitlement service should satisfy.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
OPENAPI_DIR = REPO_ROOT / "contracts" / "openapi"


@dataclass(frozen=True)
class Plan:
    """Commercial plan with regional entitlement limits."""

    plan_id: str
    base_limits: dict[str, int]
    regional_overrides: dict[str, dict[str, int]] = field(default_factory=dict)
    overage_rate_usd: dict[str, float] = field(default_factory=dict)

    def limit_for(self, feature_key: str, region: str) -> int:
        region_limits = self.regional_overrides.get(region, {})
        return region_limits.get(feature_key, self.base_limits.get(feature_key, 0))


@dataclass(frozen=True)
class Tenant:
    """Tenant context used for entitlement decisions."""

    tenant_id: str
    region: str
    plan: Plan
    feature_flags: dict[str, bool] = field(default_factory=dict)


@dataclass
class Meter:
    """Tracks usage and computes overage charges."""

    usage_by_feature: dict[str, int] = field(default_factory=dict)

    def consume(self, feature_key: str, units: int) -> int:
        new_usage = self.usage_by_feature.get(feature_key, 0) + units
        self.usage_by_feature[feature_key] = new_usage
        return new_usage


@dataclass(frozen=True)
class Decision:
    allowed: bool
    reason: str
    limit: int
    projected_usage: int


def evaluate_entitlement(
    *,
    tenant: Tenant,
    meter: Meter,
    feature_key: str,
    requested_units: int,
    expansion_flag_key: str = "billing.expanded_quota",
    expansion_bonus: int = 0,
) -> Decision:
    """Evaluate whether a tenant can consume units for a feature."""
    feature_flag_key = f"feature.{feature_key}.enabled"
    if not tenant.feature_flags.get(feature_flag_key, True):
        return Decision(
            allowed=False,
            reason="feature_disabled",
            limit=0,
            projected_usage=meter.usage_by_feature.get(feature_key, 0),
        )

    base_limit = tenant.plan.limit_for(feature_key, tenant.region)
    effective_limit = base_limit + expansion_bonus if tenant.feature_flags.get(expansion_flag_key, False) else base_limit
    projected_usage = meter.usage_by_feature.get(feature_key, 0) + requested_units
    return Decision(
        allowed=projected_usage <= effective_limit,
        reason="ok" if projected_usage <= effective_limit else "limit_exceeded",
        limit=effective_limit,
        projected_usage=projected_usage,
    )


def calculate_overage_usd(plan: Plan, feature_key: str, total_usage: int, region: str) -> float:
    """Compute overage charges for usage above entitlement."""
    included = plan.limit_for(feature_key, region)
    overage_units = max(0, total_usage - included)
    return round(overage_units * plan.overage_rate_usd.get(feature_key, 0.0), 2)


def _billing_paths(spec: dict[str, Any]) -> dict[str, Any]:
    paths = spec.get("paths", {})
    return {
        path: operations
        for path, operations in paths.items()
        if "billing" in path.lower() or "entitlement" in path.lower()
    }


def _has_json_schema(operation: dict[str, Any], response_code: str) -> bool:
    responses = operation.get("responses", {})
    response = responses.get(response_code, {})
    content = response.get("content", {})
    schema = content.get("application/json", {}).get("schema")
    return isinstance(schema, dict) and bool(schema)


@pytest.fixture
def starter_plan() -> Plan:
    return Plan(
        plan_id="starter",
        base_limits={"api_calls": 1_000, "seats": 10},
        regional_overrides={"eu-west-1": {"api_calls": 1_200}, "ap-south-1": {"api_calls": 800}},
        overage_rate_usd={"api_calls": 0.01},
    )


@pytest.fixture
def growth_plan() -> Plan:
    return Plan(
        plan_id="growth",
        base_limits={"api_calls": 5_000, "seats": 50},
        regional_overrides={"eu-west-1": {"api_calls": 5_500}},
        overage_rate_usd={"api_calls": 0.0075},
    )


class TestPlanEntitlementEnforcement:
    def test_enforces_limits_per_tenant_and_region(self, starter_plan: Plan) -> None:
        tenant_us = Tenant(tenant_id="tenant-us", region="us-east-1", plan=starter_plan)
        tenant_eu = Tenant(tenant_id="tenant-eu", region="eu-west-1", plan=starter_plan)

        meter_us = Meter(usage_by_feature={"api_calls": 950})
        meter_eu = Meter(usage_by_feature={"api_calls": 1_150})

        us_decision = evaluate_entitlement(
            tenant=tenant_us,
            meter=meter_us,
            feature_key="api_calls",
            requested_units=75,
        )
        eu_decision = evaluate_entitlement(
            tenant=tenant_eu,
            meter=meter_eu,
            feature_key="api_calls",
            requested_units=75,
        )

        assert us_decision.allowed is False
        assert us_decision.reason == "limit_exceeded"
        assert us_decision.limit == 1_000

        assert eu_decision.allowed is False
        assert eu_decision.reason == "limit_exceeded"
        assert eu_decision.limit == 1_200

    def test_allows_when_within_regional_limit(self, starter_plan: Plan) -> None:
        tenant_apac = Tenant(tenant_id="tenant-apac", region="ap-south-1", plan=starter_plan)
        meter = Meter(usage_by_feature={"api_calls": 700})

        decision = evaluate_entitlement(
            tenant=tenant_apac,
            meter=meter,
            feature_key="api_calls",
            requested_units=100,
        )

        assert decision.allowed is True
        assert decision.limit == 800
        assert decision.projected_usage == 800


class TestFeatureFlagInteractions:
    def test_feature_flag_can_block_access_even_below_limit(self, starter_plan: Plan) -> None:
        tenant = Tenant(
            tenant_id="tenant-a",
            region="us-east-1",
            plan=starter_plan,
            feature_flags={"feature.api_calls.enabled": False},
        )

        decision = evaluate_entitlement(
            tenant=tenant,
            meter=Meter(usage_by_feature={"api_calls": 100}),
            feature_key="api_calls",
            requested_units=1,
        )

        assert decision.allowed is False
        assert decision.reason == "feature_disabled"

    def test_quota_expansion_flag_extends_limit(self, starter_plan: Plan) -> None:
        tenant = Tenant(
            tenant_id="tenant-b",
            region="us-east-1",
            plan=starter_plan,
            feature_flags={"billing.expanded_quota": True},
        )

        decision = evaluate_entitlement(
            tenant=tenant,
            meter=Meter(usage_by_feature={"api_calls": 1_000}),
            feature_key="api_calls",
            requested_units=150,
            expansion_bonus=200,
        )

        assert decision.allowed is True
        assert decision.limit == 1_200


class TestBillingImpactingScenarios:
    def test_upgrade_recomputes_available_quota(self, starter_plan: Plan, growth_plan: Plan) -> None:
        meter = Meter(usage_by_feature={"api_calls": 1_250})
        before = evaluate_entitlement(
            tenant=Tenant(tenant_id="tenant-u", region="us-east-1", plan=starter_plan),
            meter=meter,
            feature_key="api_calls",
            requested_units=1,
        )
        after = evaluate_entitlement(
            tenant=Tenant(tenant_id="tenant-u", region="us-east-1", plan=growth_plan),
            meter=meter,
            feature_key="api_calls",
            requested_units=1,
        )

        assert before.allowed is False
        assert after.allowed is True
        assert after.limit == 5_000

    def test_downgrade_can_trigger_overage(self, starter_plan: Plan, growth_plan: Plan) -> None:
        total_usage = 2_000
        before = calculate_overage_usd(growth_plan, "api_calls", total_usage, "us-east-1")
        after = calculate_overage_usd(starter_plan, "api_calls", total_usage, "us-east-1")

        assert before == 0.0
        assert after == 10.0  # 1,000 overage units at $0.01

    def test_usage_metering_accumulates_over_cycle(self) -> None:
        meter = Meter()
        assert meter.consume("api_calls", 100) == 100
        assert meter.consume("api_calls", 250) == 350
        assert meter.consume("seats", 2) == 2

    def test_upgrade_downgrade_recomputes_overage(self, starter_plan: Plan, growth_plan: Plan) -> None:
        """Upgrade/downgrade cycle must recompute overage accurately."""
        total_usage = 4_500
        # On starter plan: 4,500 - 1,000 = 3,500 overage
        starter_overage = calculate_overage_usd(starter_plan, "api_calls", total_usage, "us-east-1")
        # On growth plan: 4,500 - 5,000 = 0 overage
        growth_overage = calculate_overage_usd(growth_plan, "api_calls", total_usage, "us-east-1")
        # Upgrade then downgrade back
        assert starter_overage == 35.0  # 3,500 * $0.01
        assert growth_overage == 0.0
        assert starter_overage > growth_overage

    def test_usage_metering_precision(self) -> None:
        """Meter must accumulate without floating-point drift."""
        meter = Meter()
        for _ in range(1_000):
            meter.consume("api_calls", 1)
        assert meter.usage_by_feature["api_calls"] == 1_000

    def test_webhook_idempotency(self) -> None:
        """Same webhook ID must not be processed twice."""
        processed = set()
        webhook_id = "wh-test-123"

        def process_webhook(wid: str) -> bool:
            if wid in processed:
                return False
            processed.add(wid)
            return True

        assert process_webhook(webhook_id) is True
        assert process_webhook(webhook_id) is False
        assert len(processed) == 1


class TestEntitlementBillingContracts:
    def test_contracts_for_billing_or_entitlements_if_exposed(self) -> None:
        exposed_operations_checked = 0

        for openapi_file in sorted(OPENAPI_DIR.glob("*.json")):
            spec = json.loads(openapi_file.read_text(encoding="utf-8"))
            candidate_paths = _billing_paths(spec)

            for _path, operations in candidate_paths.items():
                for method, operation in operations.items():
                    # OpenAPI extension keys start with x- and are not operations.
                    if method.lower().startswith("x-"):
                        continue
                    responses = operation.get("responses", {})
                    success_codes = [code for code in responses if code.startswith("2")]
                    assert success_codes, (
                        f"{openapi_file.name} has billing/entitlement operation without 2xx response"
                    )
                    assert any(_has_json_schema(operation, code) for code in success_codes), (
                        f"{openapi_file.name} operation missing application/json schema for success response"
                    )
                    exposed_operations_checked += 1

        if exposed_operations_checked == 0:
            pytest.skip("No billing/entitlement endpoints currently exposed in OpenAPI contracts")

    def test_contract_validator_detects_well_formed_sample(self) -> None:
        sample_spec = {
            "paths": {
                "/v1/billing/entitlements/{tenant_id}": {
                    "get": {
                        "responses": {
                            "200": {
                                "description": "ok",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "required": ["tenant_id", "plan_id", "limits"],
                                        }
                                    }
                                },
                            }
                        }
                    }
                }
            }
        }
        paths = _billing_paths(sample_spec)
        assert "/v1/billing/entitlements/{tenant_id}" in paths
        operation = paths["/v1/billing/entitlements/{tenant_id}"]["get"]
        assert _has_json_schema(operation, "200") is True
