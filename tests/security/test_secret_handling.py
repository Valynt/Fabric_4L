"""Centralized aggregation checks for secret handling security coverage."""

from tests.security.aggregation_manifest import SECURITY_COVERAGE, existing_references


def test_secret_handling_references_existing_secret_and_bypass_checks() -> None:
    coverage = SECURITY_COVERAGE["secret_handling"]

    assert coverage["central_file"] == "tests/security/test_secret_handling.py"
    assert len(existing_references("secret_handling")) >= 5
    assert any(
        "test_secrets_protection.py" in reference
        for reference in coverage["references"]
    )
    assert any(
        "check_keycloak_realm_seed_security.py" in reference
        for reference in coverage["references"]
    )


def test_secret_handling_category_documents_production_guardrails() -> None:
    description = SECURITY_COVERAGE["secret_handling"]["description"].lower()

    for expected in ("secret", "production", "bypass"):
        assert expected in description
