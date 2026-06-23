from __future__ import annotations

import pytest

from tests.production_readiness.manifest import assert_pytest_coverage


pytestmark = [pytest.mark.audit, pytest.mark.production_readiness]


def test_permission_change_audit_coverage_exists() -> None:
    assert_pytest_coverage(
        (
            "services/layer4-agents/tests/test_case_permissions_and_audit.py",
            "services/layer5-ground-truth/tests/unit/test_policy_enforcement.py",
            "tests/security/test_rbac.py",
        ),
        label="permission change audit coverage",
    )

