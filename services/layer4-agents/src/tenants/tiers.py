from __future__ import annotations

"""Subscription tier configuration.

Tiers are configuration-based (not database-driven) for Phase 3.
Database-driven tiers with billing integration deferred to Phase 4+.
"""


from dataclasses import dataclass


@dataclass(frozen=True)
class TierLimits:
    """Resource limits for a tier."""

    max_users: int | None  # None = unlimited
    max_agents: int | None
    max_storage_mb: int | None
    monthly_api_calls: int | None
    monthly_llm_tokens: int | None
    rate_limit_per_minute: int | None


@dataclass(frozen=True)
class TierFeatures:
    """Feature flags for a tier."""

    advanced_analytics: bool
    custom_branding: bool
    sso_integration: bool
    audit_export: bool
    priority_support: bool


@dataclass(frozen=True)
class TierConfig:
    """Complete tier configuration."""

    id: str
    name: str
    description: str
    limits: TierLimits
    features: TierFeatures
    is_public: bool  # Show in registration


# Tier definitions
TIERS: dict[str, TierConfig] = {
    "free": TierConfig(
        id="free",
        name="Free",
        description="For individuals and small teams",
        limits=TierLimits(
            max_users=3,
            max_agents=2,
            max_storage_mb=100,
            monthly_api_calls=1000,
            monthly_llm_tokens=10000,
            rate_limit_per_minute=60,
        ),
        features=TierFeatures(
            advanced_analytics=False,
            custom_branding=False,
            sso_integration=False,
            audit_export=False,
            priority_support=False,
        ),
        is_public=True,
    ),
    "basic": TierConfig(
        id="basic",
        name="Basic",
        description="For growing teams",
        limits=TierLimits(
            max_users=20,
            max_agents=10,
            max_storage_mb=1000,
            monthly_api_calls=10000,
            monthly_llm_tokens=100000,
            rate_limit_per_minute=300,
        ),
        features=TierFeatures(
            advanced_analytics=True,
            custom_branding=False,
            sso_integration=False,
            audit_export=True,
            priority_support=False,
        ),
        is_public=True,
    ),
    "pro": TierConfig(
        id="pro",
        name="Professional",
        description="For organizations",
        limits=TierLimits(
            max_users=100,
            max_agents=50,
            max_storage_mb=10000,
            monthly_api_calls=100000,
            monthly_llm_tokens=1000000,
            rate_limit_per_minute=1000,
        ),
        features=TierFeatures(
            advanced_analytics=True,
            custom_branding=True,
            sso_integration=True,
            audit_export=True,
            priority_support=True,
        ),
        is_public=True,
    ),
    "enterprise": TierConfig(
        id="enterprise",
        name="Enterprise",
        description="Custom solutions",
        limits=TierLimits(
            max_users=None,
            max_agents=None,
            max_storage_mb=None,
            monthly_api_calls=None,
            monthly_llm_tokens=None,
            rate_limit_per_minute=None,
        ),
        features=TierFeatures(
            advanced_analytics=True,
            custom_branding=True,
            sso_integration=True,
            audit_export=True,
            priority_support=True,
        ),
        is_public=False,  # Contact sales
    ),
}


def get_tier_config(tier_id: str) -> TierConfig:
    """Get tier configuration by ID."""
    if tier_id not in TIERS:
        raise ValueError(f"Unknown tier: {tier_id}")
    return TIERS[tier_id]


def get_public_tiers() -> list[TierConfig]:
    """Get tiers available for public registration."""
    return [t for t in TIERS.values() if t.is_public]


def check_limit(tier_id: str, limit_name: str, current_value: int) -> bool:
    """Check if current value is within tier limit.

    Returns True if within limit, False if exceeded.
    """
    tier = get_tier_config(tier_id)
    limit = getattr(tier.limits, limit_name)

    if limit is None:  # Unlimited
        return True
    return current_value <= limit


def get_tier_limit(tier_id: str, limit_name: str) -> int | None:
    """Get specific limit value for a tier.

    Returns None for unlimited tiers.
    """
    tier = get_tier_config(tier_id)
    return getattr(tier.limits, limit_name)
