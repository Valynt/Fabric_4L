from __future__ import annotations

from uuid import UUID

import pytest

from layer4_agents.shared.security import enforce_tenant_context
from layer4_agents.tools.registry import TenantSpoofingError

TENANT_A_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
TENANT_B_ID = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")


def test_enforce_tenant_context_accepts_matching_tenant():
    """A payload tenant_id that matches the authenticated context must not raise."""
    enforce_tenant_context(payload_tenant_id=TENANT_A_ID, authenticated_tenant_id=TENANT_A_ID)


def test_enforce_tenant_context_accepts_missing_tenant_id():
    """A missing/None payload tenant_id is allowed (query is tenant-scoped anyway)."""
    enforce_tenant_context(payload_tenant_id=None, authenticated_tenant_id=TENANT_A_ID)


def test_enforce_tenant_context_rejects_spoofed_tenant_id():
    """A mismatched payload tenant_id must raise TenantSpoofingError with the stable message."""
    with pytest.raises(TenantSpoofingError, match="Tenant spoofing detected: payload tenant_id does not match authenticated context"):
        enforce_tenant_context(
            payload_tenant_id=TENANT_B_ID, authenticated_tenant_id=TENANT_A_ID
        )


def test_enforce_tenant_context_compares_strings():
    """UUID str form must equal string form (string comparison is intentional)."""
    enforce_tenant_context(
        payload_tenant_id=str(TENANT_A_ID), authenticated_tenant_id=TENANT_A_ID
    )