from __future__ import annotations

import pytest

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

