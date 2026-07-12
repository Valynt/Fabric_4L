from __future__ import annotations

import pytest
from tests.config._helpers import read_text, read_yaml
from tests.production_readiness.manifest import assert_contains_all, assert_pytest_coverage

pytestmark = [pytest.mark.config, pytest.mark.production_readiness]


UNSAFE_PRODUCTION_ASSIGNMENTS = (
    "DEV_AUTH_BYPASS=true",
    "ALLOW_DEV_AUTH_BYPASS=true",
    "AUTH_BYPASS_ENABLED=true",
    "ALLOW_INSECURE_DEV_AUTH_BYPASS=true",
    "JWT_FALLBACK_TO_QUERY_PARAM=true",
    "DEBUG=true",
    "MOCK_PERSISTENCE=true",
    "ALLOW_MOCK_LLM=true",
    "SEED_DEMO_DATA=true",
    "MULTI_TENANT_MODE=false",
    "VITE_USE_MOCKS=true",
    "VITE_ENABLE_MOCK_FALLBACK=true",
)


def test_production_default_guardrails_are_covered() -> None:
    assert_pytest_coverage(
        (
            "tests/config/test_environment_matrix.py",
            "tests/config/test_database_tls_validation.py",
            "tests/security/test_production_bypass_guardrails.py",
            "tests/security/test_dev_bypass.py",
        ),
        label="production default guardrail coverage",
    )


def test_config_policy_blocks_dev_bypass_flags_in_production() -> None:
    assert_contains_all(
        "contracts/config-policy/config_policy.yml",
        (
            "DEV_AUTH_BYPASS",
            "ALLOW_DEV_AUTH_BYPASS",
            "required_scope_markers",
            "environment: development",
            "dev_only_allowlist",
        ),
        label="config policy production bypass controls",
    )


def test_config_policy_has_version_and_scoped_rules() -> None:
    policy = read_yaml("contracts/config-policy/config_policy.yml")
    assert policy["schema_version"] == "1.0.0"
    assert policy["policy_version"]
    assert policy["scan_paths"]
    assert policy["rules"]

    rules_by_flag = {rule["flag"]: rule for rule in policy["rules"]}
    for flag in ("DEV_AUTH_BYPASS", "ALLOW_DEV_AUTH_BYPASS", "AUTH_BYPASS_ENABLED"):
        assert flag in rules_by_flag
        assert rules_by_flag[flag]["dev_only_allowlist"] == []


def test_production_compose_requires_secret_injection_for_core_secrets() -> None:
    source = read_text("infra/compose/docker-compose.full.yml")
    for env_var in (
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "LAYER4_DATABASE_URL",
        "JWT_SECRET",
        "API_KEY_HMAC_SECRET",
        "SERVICE_AUTH_SECRET",
    ):
        assert f"${{{env_var}:?" in source, f"{env_var} must use required compose substitution"


def test_production_manifests_do_not_enable_dev_or_mock_defaults() -> None:
    production_sources = (
        "infra/compose/docker-compose.full.yml",
        "infra/compose/docker-compose.prod.yml",
        "k8s/envs/prod/kustomization.yaml",
    )
    violations: list[str] = []
    for path in production_sources:
        source = read_text(path)
        for assignment in UNSAFE_PRODUCTION_ASSIGNMENTS:
            if assignment in source:
                violations.append(f"{path}: {assignment}")

    assert not violations, f"Unsafe production defaults found: {violations}"
