from __future__ import annotations

"""Tenant context propagation guardrails for layer4-agents.

These tests prove that the Layer 4 tenant context API extracts tenant identity
from the canonical shared request context and fails closed when context is missing.
"""

import uuid

from value_fabric.shared.identity.context import RequestContext, set_request_context

from layer4_agents.tenant.context import TenantContext, get_current_tenant


def test_get_current_tenant_extracts_from_shared_request_context():
    tenant_id = uuid.uuid4()
    ctx = RequestContext(tenant_id=tenant_id, user_id="user-1", roles=["admin"])
    token = set_request_context(ctx)
    try:
        tenant = get_current_tenant()
        assert isinstance(tenant, TenantContext)
        assert tenant.tenant_id == str(tenant_id)
        assert tenant.user_id == "user-1"
        assert tenant.roles == ["admin"]
    finally:
        set_request_context(None)


def test_get_current_tenant_returns_none_without_context():
    set_request_context(None)
    assert get_current_tenant() is None


def test_get_current_tenant_returns_none_with_empty_tenant_id():
    ctx = RequestContext(tenant_id="", user_id="user-1")
    token = set_request_context(ctx)
    try:
        assert get_current_tenant() is None
    finally:
        set_request_context(None)


def test_tenant_context_round_trip_preserves_identity():
    tenant = TenantContext(tenant_id="tenant-a", user_id="user-1", roles=["admin"], metadata={"key": "value"})
    data = tenant.to_dict()
    restored = TenantContext.from_dict(data)

    assert restored.tenant_id == "tenant-a"
    assert restored.user_id == "user-1"
    assert restored.roles == ["admin"]
    assert restored.metadata == {"key": "value"}
