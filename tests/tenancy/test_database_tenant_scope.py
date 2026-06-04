from __future__ import annotations

import pytest

from tests.production_readiness.manifest import assert_pytest_coverage


pytestmark = [pytest.mark.tenancy, pytest.mark.production_readiness]


def test_database_tenant_scope_coverage_exists() -> None:
    assert_pytest_coverage(
        (
            "tests/production_readiness/test_postgres_production_invariants.py",
            "tests/security/test_rls_enforcement.py",
            "tests/security/test_tenant_repository_filter_presence.py",
            "services/api/app/tests/test_database_tenant_boundary.py",
            "services/layer4-agents/tests/test_database_session_tenant_enforcement.py",
            "services/layer5-ground-truth/tests/test_database_optional_tenant_security.py",
        ),
        label="database tenant scope coverage",
    )

