from __future__ import annotations

import pytest

from tests.production_readiness.manifest import assert_contains_all, assert_paths_exist, assert_pytest_coverage


pytestmark = [pytest.mark.config, pytest.mark.production_readiness]


def test_config_schema_validation_coverage_exists() -> None:
    assert_pytest_coverage(
        (
            "tests/config/test_environment_matrix.py",
        ),
        label="config schema validation coverage",
    )
    assert_paths_exist(
        ("packages/config/src/env/backend.test.ts",),
        label="TypeScript backend config schema tests",
    )


def test_config_schema_sources_are_present() -> None:
    assert_paths_exist(
        (
            "packages/config/src/env/backend.ts",
            "packages/config/src/env/frontend.ts",
            "packages/config/src/env/shared.ts",
            "contracts/config-policy/config_policy.yml",
        ),
        label="config schema sources",
    )
    assert_contains_all(
        "packages/config/src/env/backend.ts",
        ("validateBackendEnvForProductionLike", "requiredSecretSchema", "ALLOW_INSECURE_DEV_AUTH_BYPASS"),
        label="backend config schema",
    )
