"""Release checks for fail-closed feature flag defaults."""

from __future__ import annotations

import json
from pathlib import Path

POLICY = Path("config/production-readiness/feature_flag_rollout_policy.json")


def _policy() -> dict[str, object]:
    return json.loads(POLICY.read_text(encoding="utf-8"))


def test_feature_flag_policy_exists_and_is_active() -> None:
    data = _policy()
    assert data["version"]
    assert "tenant-safe feature flag policy" in str(data["purpose"]).lower()


def test_feature_flag_default_behavior_denies_unsafe_contexts() -> None:
    defaults = _policy()["defaultBehavior"]
    assert defaults == {
        "unknownFlag": "deny",
        "missingTenantContext": "deny",
        "missingEnvironmentContext": "deny",
        "evaluationFailure": "deny",
    }


def test_feature_flag_records_require_rollback_metadata() -> None:
    required_fields = set(_policy()["requiredFlagFields"])
    for field in (
        "key",
        "owner",
        "default_state",
        "allowed_environments",
        "tenant_allow_list",
        "expires_at",
        "rollback_plan",
    ):
        assert field in required_fields


def test_agent_capability_flags_require_kill_switch_and_audit() -> None:
    controls = _policy()["agentCapabilityControls"]
    assert controls["requiresHumanApprovalForAutonomousActions"] is True
    assert controls["killSwitchRequired"] is True
    assert controls["auditEveryEvaluationForHighRiskFlags"] is True
