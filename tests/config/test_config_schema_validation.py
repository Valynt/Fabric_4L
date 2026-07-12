from __future__ import annotations

import pytest
from tests.config._helpers import package_scripts, read_yaml
from tests.production_readiness.manifest import (
    assert_contains_all,
    assert_paths_exist,
    assert_pytest_coverage,
)

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


def test_config_policy_schema_is_versioned() -> None:
    policy = read_yaml("contracts/config-policy/config_policy.yml")
    assert policy["schema_version"] == "1.0.0"
    assert policy["policy_version"]
    assert isinstance(policy["scan_paths"], list) and policy["scan_paths"]
    assert isinstance(policy["rules"], list) and policy["rules"]


def test_config_validation_package_script_runs_config_suite() -> None:
    scripts = package_scripts()
    assert scripts["config:validate"] == "python -m pytest tests/config/ -v --tb=short"
    assert scripts["test:config"] == "python -m pytest tests/config/ -v --tb=short"


def test_backend_typescript_schema_has_production_required_controls() -> None:
    assert_contains_all(
        "packages/config/src/env/backend.ts",
        (
            "DATABASE_URL",
            "REDIS_URL",
            "JWT_SECRET",
            "API_KEY_HMAC_SECRET",
            "SERVICE_AUTH_SECRET",
            "CREDENTIALS_MASTER_KEY",
            "CORS_ORIGINS",
            "DEFAULT_TENANT_ID",
            "MULTI_TENANT_MODE",
            "LLM_PROVIDER",
            "DEBUG",
            "SEED_DEMO_DATA",
            "validateBackendEnvForProductionLike",
        ),
        label="backend production config schema controls",
    )
