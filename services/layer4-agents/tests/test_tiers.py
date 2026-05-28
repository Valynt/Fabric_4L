from __future__ import annotations

"""Tests for tier configuration module (Phase 3)."""


import pytest

from value_fabric.layer4.tenants.tiers import (
    TIERS,
    TierConfig,
    TierFeatures,
    TierLimits,
    check_limit,
    get_public_tiers,
    get_tier_config,
    get_tier_limit,
)


class TestTierLimits:
    """Test TierLimits dataclass."""

    def test_tier_limits_creation(self):
        """Test creating TierLimits instance."""
        limits = TierLimits(
            max_users=10,
            max_agents=5,
            max_storage_mb=1000,
            monthly_api_calls=10000,
            monthly_llm_tokens=100000,
            rate_limit_per_minute=600,
        )
        assert limits.max_users == 10
        assert limits.max_agents == 5
        assert limits.max_storage_mb == 1000

    def test_tier_limits_with_none(self):
        """Test TierLimits with unlimited fields."""
        limits = TierLimits(
            max_users=None,
            max_agents=None,
            max_storage_mb=None,
            monthly_api_calls=None,
            monthly_llm_tokens=None,
            rate_limit_per_minute=None,
        )
        assert limits.max_users is None
        assert limits.max_agents is None


class TestTierFeatures:
    """Test TierFeatures dataclass."""

    def test_tier_features_creation(self):
        """Test creating TierFeatures instance."""
        features = TierFeatures(
            advanced_analytics=True,
            custom_branding=False,
            sso_integration=True,
            audit_export=True,
            priority_support=False,
        )
        assert features.advanced_analytics is True
        assert features.custom_branding is False
        assert features.sso_integration is True


class TestTierConfig:
    """Test TierConfig dataclass."""

    def test_tier_config_creation(self):
        """Test creating TierConfig instance."""
        limits = TierLimits(
            max_users=10,
            max_agents=5,
            max_storage_mb=1000,
            monthly_api_calls=10000,
            monthly_llm_tokens=100000,
            rate_limit_per_minute=600,
        )
        features = TierFeatures(
            advanced_analytics=True,
            custom_branding=False,
            sso_integration=False,
            audit_export=True,
            priority_support=False,
        )
        config = TierConfig(
            id="test",
            name="Test Tier",
            description="A test tier",
            limits=limits,
            features=features,
            is_public=True,
        )
        assert config.id == "test"
        assert config.name == "Test Tier"
        assert config.is_public is True


class TestTierFunctions:
    """Test tier utility functions."""

    def test_get_tier_config_existing(self):
        """Test getting existing tier config."""
        config = get_tier_config("free")
        assert config.id == "free"
        assert config.name == "Free"
        assert config.is_public is True

    def test_get_tier_config_nonexistent(self):
        """Test getting nonexistent tier raises error."""
        with pytest.raises(ValueError, match="Unknown tier"):
            get_tier_config("nonexistent")

    def test_get_public_tiers(self):
        """Test getting only public tiers."""
        public_tiers = get_public_tiers()
        tier_ids = [t.id for t in public_tiers]

        # Should include public tiers
        assert "free" in tier_ids
        assert "basic" in tier_ids
        assert "pro" in tier_ids

        # Should not include enterprise (non-public)
        assert "enterprise" not in tier_ids

    def test_check_limit_within(self):
        """Test check_limit when within limit."""
        # Free tier has max_users=3
        assert check_limit("free", "max_users", 2) is True
        assert check_limit("free", "max_users", 3) is True

    def test_check_limit_exceeded(self):
        """Test check_limit when limit exceeded."""
        # Free tier has max_users=3
        assert check_limit("free", "max_users", 4) is False
        assert check_limit("free", "max_users", 10) is False

    def test_check_limit_unlimited(self):
        """Test check_limit with unlimited tier."""
        # Enterprise tier has no limits (None)
        assert check_limit("enterprise", "max_users", 10000) is True

    def test_get_tier_limit_existing(self):
        """Test getting specific limit value."""
        limit = get_tier_limit("free", "max_users")
        assert limit == 3

    def test_get_tier_limit_unlimited(self):
        """Test getting limit for unlimited tier."""
        limit = get_tier_limit("enterprise", "max_users")
        assert limit is None


class TestPredefinedTiers:
    """Test predefined tier configurations."""

    def test_free_tier_values(self):
        """Test free tier configuration."""
        free = TIERS["free"]
        assert free.limits.max_users == 3
        assert free.limits.max_agents == 2
        assert free.limits.monthly_api_calls == 1000
        assert free.features.advanced_analytics is False
        assert free.features.sso_integration is False

    def test_pro_tier_values(self):
        """Test pro tier configuration."""
        pro = TIERS["pro"]
        assert pro.limits.max_users == 100
        assert pro.limits.max_agents == 50
        assert pro.limits.monthly_api_calls == 100000
        assert pro.features.advanced_analytics is True
        assert pro.features.sso_integration is True

    def test_enterprise_tier_values(self):
        """Test enterprise tier configuration."""
        enterprise = TIERS["enterprise"]
        assert enterprise.limits.max_users is None
        assert enterprise.limits.max_agents is None
        assert enterprise.is_public is False
        assert enterprise.features.priority_support is True
