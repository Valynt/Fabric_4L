"""Centralized aggregation checks for container and deployment security coverage."""

from tests.security.aggregation_manifest import SECURITY_COVERAGE, existing_references


def test_container_policy_references_existing_runtime_policy_inputs() -> None:
    coverage = SECURITY_COVERAGE["container_policy"]

    assert coverage["central_file"] == "tests/security/test_container_policy.py"
    assert len(existing_references("container_policy")) >= 3
    assert any("docker-compose" in reference for reference in coverage["references"])
    assert any(reference == "k8s" for reference in coverage["references"])


def test_container_policy_category_documents_production_safety_scope() -> None:
    description = SECURITY_COVERAGE["container_policy"]["description"].lower()

    for expected in ("container", "deployment", "production"):
        assert expected in description
