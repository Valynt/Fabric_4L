from __future__ import annotations

import asyncio

from value_fabric.shared.error_handling.exceptions import AuthorizationError

"""Tier enforcement for tenant resource limits.

Provides FastAPI dependency functions that check tenant tier limits
before allowing resource creation. Used as Depends() in route handlers
rather than as global middleware — this gives fine-grained control over
which endpoints enforce which limits.

Design Principles (Phase 3):
- Config-based tiers from tiers.py (no billing integration)
- Fail-closed: unknown tier → deny
- JSON error responses with limit details
- Audit event emission on limit exceeded
"""


import logging
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from value_fabric.shared.models.typed_dict import TypedDictModel

from .tiers import TierConfig, get_tier_config


class TierEnforcement_get_usage_summaryResult(TypedDictModel):
    features: dict[str, Any]
    limits: dict[str, Any]
    tier: Any
    tier_name: Any

logger = logging.getLogger(__name__)

# Default API key limits per tier (configurable via environment in future)
DEFAULT_API_KEY_LIMITS = {
    "free": 2,
    "basic": 10,
    "pro": 50,
    "enterprise": 500,
}

# Audit integration (optional — graceful degradation)
try:
    from value_fabric.shared.audit import AuditAction, emit_audit_event

    AUDIT_AVAILABLE = True
except ImportError:
    AUDIT_AVAILABLE = False
    emit_audit_event = None  # type: ignore
    AuditAction = None  # type: ignore


class TierLimitExceeded(HTTPException):
    """Raised when a tenant exceeds a tier limit."""

    def __init__(
        self,
        limit_name: str,
        current_value: int,
        max_value: int,
        tier_id: str,
    ) -> None:
        detail = {
            "error": "tier_limit_exceeded",
            "limit": limit_name,
            "current": current_value,
            "max": max_value,
            "tier": tier_id,
            "message": (
                f"{limit_name} limit reached: {current_value}/{max_value}. "
                f"Upgrade from '{tier_id}' tier to increase limits."
            ),
        }
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )


class TierEnforcement:
    """Service for checking and enforcing tenant tier limits.

    Usage in route handlers:

        enforcer = TierEnforcement(db)
        await enforcer.check_user_limit(tenant_id, tier_id)
        # ... proceed to create user
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _count_rows(self, model_class: Any, tenant_id: UUID) -> int:
        """Count rows in a table filtered by tenant_id."""
        result = await self.db.execute(
            select(func.count()).select_from(model_class).where(
                model_class.tenant_id == str(tenant_id)
            )
        )
        return result.scalar_one()

    async def check_user_limit(
        self,
        tenant_id: UUID,
        tier_id: str,
    ) -> None:
        """Check if tenant can add another user.

        Raises TierLimitExceeded if at or over limit.
        """
        config = get_tier_config(tier_id)
        if config.limits.max_users is None:
            return  # Unlimited

        # Lazy import to avoid circular dependencies
        from .models.user import User

        current = await self._count_rows(User, tenant_id)
        if current >= config.limits.max_users:
            await self._emit_limit_exceeded(tenant_id, "max_users", current, config)
            raise TierLimitExceeded(
                limit_name="max_users",
                current_value=current,
                max_value=config.limits.max_users,
                tier_id=tier_id,
            )

    async def check_agent_limit(
        self,
        tenant_id: UUID,
        tier_id: str,
    ) -> None:
        """Check if tenant can create another agent.

        Raises TierLimitExceeded if at or over limit.
        """
        config = get_tier_config(tier_id)
        if config.limits.max_agents is None:
            return

        # Lazy import — agent model may live in a different module
        try:
            from ..models.agent import Agent

            current = await self._count_rows(Agent, tenant_id)
        except ImportError:
            logger.warning("Agent model not available for limit check")
            return

        if current >= config.limits.max_agents:
            await self._emit_limit_exceeded(tenant_id, "max_agents", current, config)
            raise TierLimitExceeded(
                limit_name="max_agents",
                current_value=current,
                max_value=config.limits.max_agents,
                tier_id=tier_id,
            )

    async def check_api_key_limit(
        self,
        tenant_id: UUID,
        tier_id: str,
        max_keys_per_tier: dict[str, int] | None = None,
    ) -> None:
        """Check if tenant can create another API key.

        API key limits are not in TierLimits (they're a platform concern),
        so we use a configurable mapping with sensible defaults.
        """
        limits = max_keys_per_tier or DEFAULT_API_KEY_LIMITS
        max_keys = limits.get(tier_id)

        if max_keys is None:
            return  # Unknown tier or unlimited

        try:
            from .models.api_key import APIKey

            current = await self._count_rows(APIKey, tenant_id)
        except ImportError:
            logger.warning("APIKey model not available for limit check")
            return

        if current >= max_keys:
            await self._emit_limit_exceeded(
                tenant_id, "max_api_keys", current,
                get_tier_config(tier_id),
            )
            raise TierLimitExceeded(
                limit_name="max_api_keys",
                current_value=current,
                max_value=max_keys,
                tier_id=tier_id,
            )

    async def check_monthly_api_calls(
        self,
        tenant_id: UUID,
        tier_id: str,
        current_month_calls: int,
    ) -> None:
        """Check if tenant has exceeded monthly API call limit.

        Unlike user/agent limits, this takes the current count as a parameter
        because it's tracked externally (usage tracking service).
        """
        config = get_tier_config(tier_id)
        if config.limits.monthly_api_calls is None:
            return

        if current_month_calls >= config.limits.monthly_api_calls:
            await self._emit_limit_exceeded(
                tenant_id, "monthly_api_calls", current_month_calls, config,
            )
            raise TierLimitExceeded(
                limit_name="monthly_api_calls",
                current_value=current_month_calls,
                max_value=config.limits.monthly_api_calls,
                tier_id=tier_id,
            )

    async def check_monthly_llm_tokens(
        self,
        tenant_id: UUID,
        tier_id: str,
        current_month_tokens: int,
    ) -> None:
        """Check if tenant has exceeded monthly LLM token limit."""
        config = get_tier_config(tier_id)
        if config.limits.monthly_llm_tokens is None:
            return

        if current_month_tokens >= config.limits.monthly_llm_tokens:
            await self._emit_limit_exceeded(
                tenant_id, "monthly_llm_tokens", current_month_tokens, config,
            )
            raise TierLimitExceeded(
                limit_name="monthly_llm_tokens",
                current_value=current_month_tokens,
                max_value=config.limits.monthly_llm_tokens,
                tier_id=tier_id,
            )

    async def check_storage_limit(
        self,
        tenant_id: UUID,
        tier_id: str,
        current_storage_mb: int,
    ) -> None:
        """Check if tenant has exceeded storage limit."""
        config = get_tier_config(tier_id)
        if config.limits.max_storage_mb is None:
            return

        if current_storage_mb >= config.limits.max_storage_mb:
            await self._emit_limit_exceeded(
                tenant_id, "max_storage_mb", current_storage_mb, config,
            )
            raise TierLimitExceeded(
                limit_name="max_storage_mb",
                current_value=current_storage_mb,
                max_value=config.limits.max_storage_mb,
                tier_id=tier_id,
            )

    def check_feature(self, tier_id: str, feature_name: str) -> bool:
        """Check if a feature is enabled for the given tier.

        Returns True if enabled, False if not.
        Does not raise — callers decide how to handle disabled features.
        """
        config = get_tier_config(tier_id)
        return getattr(config.features, feature_name, False)

    def require_feature(self, tier_id: str, feature_name: str) -> None:
        """Require a feature to be enabled, raising 403 if not.

        Usage:
            enforcer.require_feature(tier_id, "sso_integration")
        """
        if not self.check_feature(tier_id, feature_name):
            raise AuthorizationError(message = "Request failed", details = {
                    "error": "feature_not_available",
                    "feature": feature_name,
                    "tier": tier_id,
                    "message": (
                        f"Feature '{feature_name}' is not available on the "
                        f"'{tier_id}' tier. Please upgrade to access this feature."
                    ),
                })

    async def get_usage_summary(
        self,
        tenant_id: UUID,
        tier_id: str,
    ) -> dict[str, Any]:
        """Get a summary of current usage vs. tier limits.

        Useful for dashboard display.
        """
        config = get_tier_config(tier_id)

        # Count resources where models are available
        user_count = 0
        agent_count = 0
        api_key_count = 0

        try:
            from .models.user import User
            user_count = await self._count_rows(User, tenant_id)
        except ImportError:
            pass

        try:
            from ..models.agent import Agent
            agent_count = await self._count_rows(Agent, tenant_id)
        except ImportError:
            pass

        try:
            from .models.api_key import APIKey
            api_key_count = await self._count_rows(APIKey, tenant_id)
        except ImportError:
            pass

        return TierEnforcement_get_usage_summaryResult.model_validate({
            "tier": tier_id,
            "tier_name": config.name,
            "limits": {
                "users": {
                    "current": user_count,
                    "max": config.limits.max_users,
                    "unlimited": config.limits.max_users is None,
                },
                "agents": {
                    "current": agent_count,
                    "max": config.limits.max_agents,
                    "unlimited": config.limits.max_agents is None,
                },
                "api_keys": {
                    "current": api_key_count,
                    "max": DEFAULT_API_KEY_LIMITS.get(tier_id),
                },
                "storage_mb": {
                    "max": config.limits.max_storage_mb,
                    "unlimited": config.limits.max_storage_mb is None,
                },
                "monthly_api_calls": {
                    "max": config.limits.monthly_api_calls,
                    "unlimited": config.limits.monthly_api_calls is None,
                },
                "monthly_llm_tokens": {
                    "max": config.limits.monthly_llm_tokens,
                    "unlimited": config.limits.monthly_llm_tokens is None,
                },
            },
            "features": {
                "advanced_analytics": config.features.advanced_analytics,
                "custom_branding": config.features.custom_branding,
                "sso_integration": config.features.sso_integration,
                "audit_export": config.features.audit_export,
                "priority_support": config.features.priority_support,
            },
        })


    async def _emit_limit_exceeded(
        self,
        tenant_id: UUID,
        limit_name: str,
        current_value: int,
        config: TierConfig,
    ) -> None:
        """Emit an audit event when a tier limit is exceeded."""
        if not AUDIT_AVAILABLE or emit_audit_event is None:
            return

        try:
            await emit_audit_event(
                action=AuditAction.TENANT_STATUS_CHANGED,
                tenant_id=str(tenant_id),
                details={
                    "event": "tier_limit_exceeded",
                    "limit": limit_name,
                    "current": current_value,
                    "max": getattr(config.limits, limit_name, None),
                    "tier": config.id,
                },
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.warning(
                "Failed to emit tier limit exceeded audit event",
                exc_info=True,
            )
