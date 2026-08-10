from __future__ import annotations

import pytest
from tests.tenancy._invariant_manifest import TenantInvariant, assert_tenancy_invariants

pytestmark = [pytest.mark.tenancy, pytest.mark.tenant_boundary, pytest.mark.production_readiness]


def test_file_storage_tenant_scope_coverage_exists() -> None:
    assert_tenancy_invariants(
        (
            "packages/shared/src/value_fabric/shared/storage/tests/test_tenant_scoping.py",
            "services/layer4-agents/tests/security/test_file_tool_tenant_fallback.py",
            "tests/security/test_export_tenant_access.py",
        ),
        label="file storage tenant scope coverage",
        invariants=(
            TenantInvariant(
                key="tenant_scoped_object_keys",
                description="object storage keys or local paths include tenant-safe scoping",
                evidence=(("tenant-scoped normalized key", "export_storage_key_includes_tenant_id", "tenant directories are isolated"),),
            ),
            TenantInvariant(
                key="path_traversal_denied",
                description="file operations cannot escape the tenant storage boundary",
                evidence=(("path escaping tenant dir", "path traversal", "../tenant-b"),),
            ),
            TenantInvariant(
                key="same_logical_key_is_partitioned",
                description="the same logical key maps to different storage paths for different tenants",
                evidence=(("different tenants cannot access same key", "key_tenant_a != key_tenant_b"),),
            ),
            TenantInvariant(
                key="missing_tenant_fails_closed",
                description="file operations fail closed without tenant context",
                evidence=(("without context raises", "never falls back", "default tenant directory must never be created"),),
            ),
        ),
    )
