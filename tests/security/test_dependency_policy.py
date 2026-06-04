"""Centralized aggregation checks for dependency and supply-chain policy coverage."""

import json
from pathlib import Path

from tests.security.aggregation_manifest import (
    REPO_ROOT,
    SECURITY_COVERAGE,
    existing_references,
)


def test_dependency_policy_references_existing_supply_chain_and_package_checks() -> (
    None
):
    coverage = SECURITY_COVERAGE["dependency_policy"]

    assert coverage["central_file"] == "tests/security/test_dependency_policy.py"
    assert len(existing_references("dependency_policy")) >= 4
    assert any(
        "test_supply_chain.py" in reference for reference in coverage["references"]
    )
    assert any(
        "check_package_manager_policy.mjs" in reference
        for reference in coverage["references"]
    )


def test_root_security_script_delegates_to_central_pytest_suite() -> None:
    package_json = json.loads(Path(REPO_ROOT / "package.json").read_text())

    assert "test:security" in package_json["scripts"]
    assert "pytest tests/security/" in package_json["scripts"]["test:security"]
