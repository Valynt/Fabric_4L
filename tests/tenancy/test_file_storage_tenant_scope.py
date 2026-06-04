from __future__ import annotations

import pytest

from tests.production_readiness.manifest import assert_pytest_coverage


pytestmark = [pytest.mark.tenancy, pytest.mark.production_readiness]


def test_file_storage_tenant_scope_coverage_exists() -> None:
    assert_pytest_coverage(
        (
            "packages/shared/src/value_fabric/shared/storage/tests/test_tenant_scoping.py",
            "services/layer4-agents/tests/security/test_file_tool_tenant_fallback.py",
            "tests/security/test_export_tenant_access.py",
        ),
        label="file storage tenant scope coverage",
    )

