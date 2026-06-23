from __future__ import annotations

"""Tenant governance service package."""


# Phase 3: Self-service control plane exports
from .email_verification import EmailVerificationService, send_verification_email
from .service import (
    count_api_keys,
    count_users,
    create_api_key,
    create_tenant,
    deactivate_user,
    delete_tenant,
    get_tenant,
    get_tenant_by_slug,
    get_tenant_settings,
    get_tier_api_key_limit,
    get_user,
    invite_user,
    list_api_keys,
    list_tenants,
    list_users,
    lookup_api_key_by_hash,
    revoke_api_key,
    update_tenant,
    update_user,
)
from .tiers import (
    TierConfig,
    TierFeatures,
    TierLimits,
    check_limit,
    get_public_tiers,
    get_tier_config,
    get_tier_limit,
)
from .usage import (
    UsageMetrics,
    UsageTrackingService,
    record_agent_execution,
    record_api_call,
    record_llm_usage,
)

__all__ = [
    # Core CRUD
    "create_api_key",
    "create_tenant",
    "deactivate_user",
    "delete_tenant",
    "get_tenant",
    "get_tenant_by_slug",
    "get_tenant_settings",  # Task 84: For per-tenant rate limiting
    "get_user",
    "invite_user",
    "list_api_keys",
    "list_tenants",
    "list_users",
    "lookup_api_key_by_hash",
    "revoke_api_key",
    "update_tenant",
    "update_user",
    # Phase 3: Tier limit checking
    "count_api_keys",
    "count_users",
    "get_tier_api_key_limit",
    # Phase 3: Tier configuration
    "TierConfig",
    "TierFeatures",
    "TierLimits",
    "check_limit",
    "get_public_tiers",
    "get_tier_config",
    "get_tier_limit",
    # Phase 3: Usage tracking
    "UsageMetrics",
    "UsageTrackingService",
    "record_agent_execution",
    "record_api_call",
    "record_llm_usage",
    # Phase 3: Email verification
    "EmailVerificationService",
    "send_verification_email",
]
