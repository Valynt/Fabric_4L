from __future__ import annotations

from pathlib import Path

import pytest
from tests.config._helpers import REPO_ROOT, read_text, read_yaml_documents
from tests.production_readiness.manifest import (
    assert_contains_all,
    assert_paths_exist,
    assert_pytest_coverage,
)

pytestmark = [pytest.mark.config, pytest.mark.production_readiness]


EXTERNAL_SECRET_MANIFESTS = (
    "k8s/external-secrets/layer1-secrets.yaml",
    "k8s/external-secrets/layer2-secrets.yaml",
    "k8s/external-secrets/layer3-secrets.yaml",
    "k8s/external-secrets/layer4-secrets.yaml",
    "k8s/external-secrets/layer5-secrets.yaml",
    "k8s/external-secrets/layer6-secrets.yaml",
)

SENSITIVE_KEY_TOKENS = (
    "SECRET",
    "PASSWORD",
    "API_KEY",
    "TOKEN",
    "PRIVATE_KEY",
    "DATABASE_URL",
    "REDIS_URL",
)


def test_secret_reference_policy_coverage_exists() -> None:
    assert_pytest_coverage(
        (
            "tests/shared/secrets/test_infisical_bootstrap.py",
            "tests/security/test_secret_handling.py",
            "tests/security/test_secrets_protection.py",
            "tests/release/test_secret_policy.py",
        ),
        label="secret reference coverage",
    )


def test_external_secret_manifests_are_present_for_runtime_layers() -> None:
    assert_paths_exist(
        EXTERNAL_SECRET_MANIFESTS
        + (
            "k8s/external-secrets/cluster-secret-store.yaml",
        ),
        label="external secret manifests",
    )


def test_env_example_points_to_secret_manager_bootstrap() -> None:
    assert_contains_all(
        ".env.example",
        ("INFISICAL_CLIENT_ID=", "INFISICAL_PROJECT_ID=", "INFISICAL_ENVIRONMENT=", "INFISICAL_HOST="),
        label="Infisical env reference",
    )


def test_production_kustomization_uses_external_secret_manifests() -> None:
    source = read_text("k8s/envs/prod/kustomization.yaml")
    for manifest in EXTERNAL_SECRET_MANIFESTS:
        assert manifest.replace("k8s/", "../../") in source


def test_external_secrets_reference_secret_manager_remote_keys() -> None:
    missing_remote_refs: list[str] = []
    for manifest in EXTERNAL_SECRET_MANIFESTS:
        for document in read_yaml_documents(manifest):
            if document.get("kind") != "ExternalSecret":
                continue
            name = document.get("metadata", {}).get("name", manifest)
            for entry in document.get("spec", {}).get("data", []):
                remote_ref = entry.get("remoteRef") or {}
                if not remote_ref.get("key") or not remote_ref.get("property"):
                    missing_remote_refs.append(f"{manifest}:{name}:{entry.get('secretKey')}")

    assert not missing_remote_refs, (
        "Every production ExternalSecret data entry must map to a secret "
        f"manager key/property: {missing_remote_refs}"
    )


def test_sensitive_external_secret_templates_do_not_commit_literal_values() -> None:
    literal_values: list[str] = []
    for manifest in EXTERNAL_SECRET_MANIFESTS:
        for document in read_yaml_documents(manifest):
            if document.get("kind") != "ExternalSecret":
                continue
            template_data = (
                document.get("spec", {})
                .get("target", {})
                .get("template", {})
                .get("data", {})
            )
            for key, value in template_data.items():
                if not any(token in key.upper() for token in SENSITIVE_KEY_TOKENS):
                    continue
                if "{{" not in str(value):
                    literal_values.append(f"{manifest}:{key}")

    assert not literal_values, (
        "Sensitive ExternalSecret template values must be templated from "
        f"remote secret references, not committed literals: {literal_values}"
    )


def test_unrendered_k8s_secret_templates_are_templates_only() -> None:
    secret_templates = sorted(Path(REPO_ROOT / "k8s").glob("**/*secret*.template"))
    secret_templates += sorted(Path(REPO_ROOT / "k8s").glob("**/*secrets.yml.template"))
    assert secret_templates, "Expected committed Kubernetes secret templates to be explicitly templated"
    for path in secret_templates:
        source = path.read_text(encoding="utf-8")
        assert "REPLACE_" in source or "<" in source, f"{path} must not contain usable committed secrets"
