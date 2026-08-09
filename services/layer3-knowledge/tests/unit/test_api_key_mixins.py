"""Regression tests for APIKey mixin behavior."""

from datetime import datetime, timedelta

import pytest

from src.auth.api_keys import APIKey, Permission, Role


def _make_key(**overrides):
    """Create a minimal APIKey for mixin tests."""
    defaults = {
        "key_id": "key_test_001",
        "name": "Test Key",
        "key_hash": "deadbeef",
        "prefix": "dead",
        "role": Role.READ_ONLY,
        "permissions": {Permission.READ_HEALTH},
    }
    defaults.update(overrides)
    return APIKey(**defaults)


class TestAPIKeyExpirationMixin:
    def test_not_expired_when_no_expires_at(self):
        key = _make_key()
        assert key.is_expired() is False

    def test_not_expired_when_expires_at_is_future(self):
        key = _make_key(expires_at=datetime.utcnow() + timedelta(hours=1))
        assert key.is_expired() is False

    def test_expired_when_expires_at_is_past(self):
        key = _make_key(expires_at=datetime.utcnow() - timedelta(hours=1))
        assert key.is_expired() is True


class TestAPIKeyIPValidationMixin:
    def test_valid_ip_when_no_allowed_ips(self):
        key = _make_key()
        assert key.is_valid_ip("203.0.113.5") is True

    def test_valid_ip_when_ip_in_allowed_list(self):
        key = _make_key(allowed_ips=["203.0.113.5", "198.51.100.10"])
        assert key.is_valid_ip("203.0.113.5") is True

    def test_invalid_ip_when_ip_not_in_allowed_list(self):
        key = _make_key(allowed_ips=["203.0.113.5"])
        assert key.is_valid_ip("198.51.100.10") is False


class TestAPIKeyPermissionMixin:
    def test_has_permission_when_present(self):
        key = _make_key(permissions={Permission.READ_HEALTH, Permission.READ_METRICS})
        assert key.has_permission(Permission.READ_HEALTH) is True

    def test_has_permission_when_absent(self):
        key = _make_key(permissions={Permission.READ_HEALTH})
        assert key.has_permission(Permission.READ_METRICS) is False


class TestAPIKeyUsageMixin:
    def test_update_usage_sets_last_used_at_and_increments_count(self):
        key = _make_key()
        assert key.usage_count == 0
        assert key.last_used_at is None

        key.update_usage()

        assert key.usage_count == 1
        assert key.last_used_at is not None

    def test_update_usage_called_multiple_times_increments_count(self):
        key = _make_key()
        key.update_usage()
        key.update_usage()
        assert key.usage_count == 2
