"""Centralized aggregation checks for authentication and authorization guards."""

from tests.security.aggregation_manifest import SECURITY_COVERAGE, existing_references


def test_auth_guard_category_references_existing_security_suites() -> None:
    coverage = SECURITY_COVERAGE["auth_guards"]

    assert coverage["central_file"] == "tests/security/test_auth_guards.py"
    assert len(existing_references("auth_guards")) >= 5
    assert any("test_rbac.py" in reference for reference in coverage["references"])
    assert any(
        "test_auth_boundaries.py" in reference for reference in coverage["references"]
    )


def test_auth_guard_category_documents_fail_closed_controls() -> None:
    description = SECURITY_COVERAGE["auth_guards"]["description"].lower()

    for expected in ("authentication", "authorization", "jwt", "bypass"):
        assert expected in description
