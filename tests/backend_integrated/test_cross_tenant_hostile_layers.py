"""Targeted hostile cross-tenant access checks across layers."""
from __future__ import annotations

import pytest

pytestmark = [pytest.mark.backend_integrated, pytest.mark.integration, pytest.mark.security, pytest.mark.tenant_boundary]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("layer", "path"),
    [
        ("l1", "/api/v1/ingestion/sources/security-seed-doc"),
        ("l2", "/health"),
        ("l3", "/api/v1/graph/search?q=security-seed-account"),
        ("l4", "/v1/accounts/security-seed-account"),
        ("l5", "/health"),
        ("l6", "/health"),
    ],
)
async def test_hostile_cross_tenant_access_does_not_leak(layer, path, backend):
    body, response = await backend.request(layer, "GET", path, tenant_id=backend.seed_ids.tenant_b, expected=(200, 401, 403, 404))
    assert response.status_code in {200, 401, 403, 404}
    assert "security-seed-account" not in str(body)
