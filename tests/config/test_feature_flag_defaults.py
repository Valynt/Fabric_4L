from __future__ import annotations

from datetime import date

import pytest
from tests.config._helpers import read_json, read_text
from tests.production_readiness.manifest import assert_contains_all, assert_pytest_coverage

pytestmark = [pytest.mark.config, pytest.mark.production_readiness]


def test_feature_flag_default_behavior_reuses_release_gate() -> None:
    assert_pytest_coverage(
        (
            "tests/release/test_feature_flag_defaults.py",
            "services/layer4-agents/tests/test_feature_flags.py",
        ),
        label="feature flag default coverage",
    )


def test_rollout_policy_requires_tenant_and_environment_controls() -> None:
    assert_contains_all(
        "config/production-readiness/feature_flag_rollout_policy.json",
        (
            "Tenant-safe feature flag policy",
            "allowed_environments",
            "Kill switch disables feature without redeploy",
        ),
        label="feature flag rollout policy",
    )


def test_feature_flag_policy_defaults_fail_closed() -> None:
    policy = read_json("config/production-readiness/feature_flag_rollout_policy.json")
    assert policy["version"]
    assert date.fromisoformat(str(policy["version"]))
    assert policy["defaultBehavior"] == {
        "unknownFlag": "deny",
        "missingTenantContext": "deny",
        "missingEnvironmentContext": "deny",
        "evaluationFailure": "deny",
    }


def test_feature_flag_policy_requires_owner_expiry_and_safe_default_metadata() -> None:
    policy = read_json("config/production-readiness/feature_flag_rollout_policy.json")
    required_fields = set(policy["requiredFlagFields"])
    assert {
        "key",
        "owner",
        "description",
        "default_state",
        "allowed_environments",
        "tenant_allow_list",
        "expires_at",
        "rollback_plan",
    }.issubset(required_fields)


def test_feature_flag_api_exposes_metadata_for_policy_required_fields() -> None:
    route_source = read_text("services/layer4-agents/src/layer4_agents/feature_flags/api/routes.py")
    service_source = read_text("services/layer4-agents/src/layer4_agents/feature_flags/service.py")
    model_source = read_text("services/layer4-agents/src/layer4_agents/feature_flags/models.py")

    assert "metadata: dict[str, Any]" in route_source
    assert "metadata: dict[str, Any] | None" in route_source
    assert "metadata=request.metadata" in route_source
    assert "metadata_" in service_source
    assert '"metadata"' in model_source


def test_feature_flag_package_script_is_registered() -> None:
    package_source = read_text("package.json")
    assert '"flags:lint"' in package_source
    assert "tests/config/test_feature_flag_defaults.py" in package_source
