from __future__ import annotations

import pytest

from tests.production_readiness.manifest import assert_contains_all, assert_pytest_coverage
from tests.config._helpers import env_example_keys, read_text


pytestmark = [pytest.mark.config, pytest.mark.production_readiness]


PRODUCTION_REQUIRED_KEYS = {
    "DATABASE_URL",
    "REDIS_URL",
    "JWT_SECRET",
    "API_KEY_HMAC_SECRET",
    "SERVICE_AUTH_SECRET",
    "CREDENTIALS_MASTER_KEY",
    "CORS_ORIGINS",
    "DEFAULT_TENANT_ID",
    "NEO4J_URI",
    "NEO4J_USER",
    "NEO4J_PASSWORD",
}

LAYER_EXTERNAL_SECRET_RESOURCES = (
    "../../external-secrets/layer1-secrets.yaml",
    "../../external-secrets/layer2-secrets.yaml",
    "../../external-secrets/layer2-5-secrets.yaml",
    "../../external-secrets/layer3-secrets.yaml",
    "../../external-secrets/layer4-secrets.yaml",
    "../../external-secrets/layer5-secrets.yaml",
    "../../external-secrets/layer6-secrets.yaml",
)


def test_environment_parity_coverage_exists() -> None:
    assert_pytest_coverage(
        (
            "tests/config/test_environment_matrix.py",
            "tests/ci/test_env_contract_validator_i01.py",
            "tests/ci/test_bunnyshell_environment_contract.py",
        ),
        label="environment parity coverage",
    )


def test_production_readiness_policy_matrix_is_validated() -> None:
    assert_contains_all(
        "scripts/ci/validate_policy_enforcement_matrix.py",
        ("POLICY_DIR", "config/production-readiness", "matrix covers"),
        label="production readiness policy matrix validator",
    )


def test_env_example_covers_production_required_keys() -> None:
    missing = sorted(PRODUCTION_REQUIRED_KEYS - env_example_keys())
    assert not missing, f".env.example is missing production-required keys: {missing}"


def test_production_compose_uses_required_substitution_for_critical_secrets() -> None:
    source = read_text("docker-compose.full.yml")
    for key in ("POSTGRES_USER", "POSTGRES_PASSWORD", "JWT_SECRET", "API_KEY_HMAC_SECRET", "SERVICE_AUTH_SECRET"):
        assert f"${{{key}:?" in source, f"docker-compose.full.yml must fail when {key} is missing"


def test_prod_kustomization_references_all_layer_secret_sources() -> None:
    source = read_text("k8s/envs/prod/kustomization.yaml")
    missing = [resource for resource in LAYER_EXTERNAL_SECRET_RESOURCES if resource not in source]
    assert not missing, f"prod kustomization is missing ExternalSecret resources: {missing}"
