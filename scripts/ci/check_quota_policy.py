#!/usr/bin/env python3
"""Validate abuse-prevention quota and cost-control policy foundations."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config" / "production-readiness" / "tenant_quota_policy.json"

REQUIRED_DIMENSIONS = (
    "api_requests_per_minute",
    "workflow_starts_per_hour",
    "agent_actions_per_hour",
    "llm_tokens_per_day",
    "ingestion_pages_per_day",
    "benchmark_runs_per_day",
)
REQUIRED_TIERS = ("free", "pro", "enterprise")
REQUIRED_ENFORCEMENT = {
    "rateLimitHeadersRequired": True,
    "quotaExceededAuditEventRequired": True,
    "tenantOverrideRequiresApproval": True,
    "serviceBypassAllowed": False,
    "testModeRequiresExplicitEnvironment": True,
}
REQUIRED_EVIDENCE_TOKENS = ("isolated", "429", "headers", "Noisy-tenant", "audit")


def _load_policy() -> dict[str, Any]:
    try:
        data = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"missing policy: {POLICY_PATH.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {POLICY_PATH.relative_to(ROOT)}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("tenant quota policy must be a JSON object")
    return data


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate_policy(policy: dict[str, Any]) -> None:
    _require(policy.get("scopeRequired") == "tenant", "quota scope must be tenant")
    _require(policy.get("denyWhenTenantMissing") is True, "missing tenant context must fail closed")

    dimensions = policy.get("policyDimensions")
    _require(isinstance(dimensions, list), "policyDimensions must be a list")
    missing_dimensions = [dimension for dimension in REQUIRED_DIMENSIONS if dimension not in dimensions]
    _require(not missing_dimensions, f"missing quota dimensions: {missing_dimensions}")

    tiers = policy.get("defaultTiers")
    _require(isinstance(tiers, dict), "defaultTiers must be an object")
    for tier in REQUIRED_TIERS:
        tier_limits = tiers.get(tier)
        _require(isinstance(tier_limits, dict), f"defaultTiers.{tier} must be an object")
        for dimension in REQUIRED_DIMENSIONS:
            value = tier_limits.get(dimension)
            _require(
                isinstance(value, int) and value > 0,
                f"defaultTiers.{tier}.{dimension} must be a positive integer",
            )

    for lower, upper in zip(REQUIRED_TIERS, REQUIRED_TIERS[1:]):
        for dimension in REQUIRED_DIMENSIONS:
            _require(
                tiers[lower][dimension] <= tiers[upper][dimension],
                f"{dimension} must not decrease from {lower} to {upper}",
            )

    enforcement = policy.get("enforcementRequirements")
    _require(isinstance(enforcement, dict), "enforcementRequirements must be an object")
    for key, expected in REQUIRED_ENFORCEMENT.items():
        _require(enforcement.get(key) is expected, f"enforcementRequirements.{key} must be {expected!r}")

    evidence = policy.get("productionEvidenceRequired")
    _require(isinstance(evidence, list) and evidence, "productionEvidenceRequired must be a non-empty list")
    evidence_text = "\n".join(str(item) for item in evidence)
    missing_tokens = [token for token in REQUIRED_EVIDENCE_TOKENS if token not in evidence_text]
    _require(not missing_tokens, f"productionEvidenceRequired missing quota evidence tokens: {missing_tokens}")


def main() -> int:
    try:
        validate_policy(_load_policy())
    except ValueError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print("PASS: tenant quota policy covers tenant scope, hard limits, headers, audit, and evidence")
    return 0


if __name__ == "__main__":
    sys.exit(main())
