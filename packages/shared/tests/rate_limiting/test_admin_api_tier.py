"""Tests for tenant tier lookup helpers in the admin API."""

from uuid import uuid4

import pytest

from value_fabric.shared.rate_limiting.admin_api import (
    _map_tier_value,
    _resolve_driver_factory,
)
from value_fabric.shared.rate_limiting.tenant_rate_limiter import TenantTier


def test_resolve_driver_factory_uses_injected_factory():
    def fake_factory():
        return None

    assert _resolve_driver_factory(fake_factory) is fake_factory


def test_resolve_driver_factory_returns_none_without_driver():
    # When no driver_factory is provided and the optional db.driver module is
    # unavailable, the helper should return None to trigger the soft fallback.
    assert _resolve_driver_factory(None) is None


def test_map_tier_value_maps_known_tiers():
    tenant_id = uuid4()
    assert _map_tier_value("shared", tenant_id) == TenantTier.SHARED
    assert _map_tier_value("standard", tenant_id) == TenantTier.SHARED
    assert _map_tier_value("dedicated", tenant_id) == TenantTier.DEDICATED
    assert _map_tier_value("isolated", tenant_id) == TenantTier.DEDICATED
    assert _map_tier_value("enterprise", tenant_id) == TenantTier.ENTERPRISE


def test_map_tier_value_is_case_insensitive():
    tenant_id = uuid4()
    assert _map_tier_value("Dedicated", tenant_id) == TenantTier.DEDICATED
    assert _map_tier_value("SHARED", tenant_id) == TenantTier.SHARED


def test_map_tier_value_rejects_unknown_tier():
    tenant_id = uuid4()
    with pytest.raises(ValueError, match="Unknown tenant tier value"):
        _map_tier_value("platinum", tenant_id)
