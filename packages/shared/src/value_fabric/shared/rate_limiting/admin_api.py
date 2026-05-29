"""
Admin API for tenant rate limit quota management (Task 5).

Provides endpoints for:
- Viewing tenant quotas and usage
- Setting custom limits
- Resetting rate limits
- Monitoring and alerting
"""

import logging
from typing import Any, Protocol
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
try:
    from neo4j import AsyncDriver
except ImportError:  # pragma: no cover - optional dependency for test/runtime variants
    AsyncDriver = Any  # type: ignore[misc,assignment]
from pydantic import BaseModel, Field

from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_privileged_access
from .tenant_rate_limiter import (
    TenantRateLimiter,
    TenantTier,
    RateLimitConfig,
)
from value_fabric.shared.models.typed_dict import TypedDictModel

class list_rate_limit_tiersResult(TypedDictModel):
    tiers: Any

class set_custom_limitsResult(TypedDictModel):
    limits: dict[str, Any]
    message: str

class reset_tenant_limitsResult(TypedDictModel):
    keys_deleted: Any
    message: str

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/admin/rate-limits", tags=["Admin - Rate Limits"])


# ═══════════════════════════════════════════════════════════════════════════
# Request/Response Models
# ═══════════════════════════════════════════════════════════════════════════

class RateLimitConfigRequest(BaseModel):
    """Request to set custom rate limit."""
    
    requests_per_minute: int = Field(..., gt=0, description="Requests per minute")
    requests_per_hour: int = Field(..., gt=0, description="Requests per hour")
    requests_per_day: int = Field(..., gt=0, description="Requests per day")
    burst_allowance: int = Field(0, ge=0, description="Burst allowance")
    
    class Config:
        json_schema_extra = {
            "example": {
                "requests_per_minute": 1000,
                "requests_per_hour": 50000,
                "requests_per_day": 1000000,
                "burst_allowance": 200,
            }
        }


class TenantQuotaResponse(BaseModel):
    """Response with tenant quota status."""
    
    tenant_id: str
    tier: str
    limits: dict
    usage: dict
    custom_limits: bool


class TenantUsageResponse(BaseModel):
    """Response with tenant usage statistics."""
    
    tenant_id: str
    timestamp: str
    windows: dict


# ═══════════════════════════════════════════════════════════════════════════
# Dependency Injection
# ═══════════════════════════════════════════════════════════════════════════

async def get_rate_limiter(request: Request) -> TenantRateLimiter:
    """Get configured rate limiter from FastAPI application state."""
    rate_limiter = getattr(request.app.state, "tenant_rate_limiter", None)
    if isinstance(rate_limiter, TenantRateLimiter):
        return rate_limiter
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail={
            "code": "RATE_LIMITER_UNAVAILABLE",
            "message": "Tenant rate limiter is not configured on application state.",
            "remediation": (
                "Set app.state.tenant_rate_limiter to a configured TenantRateLimiter "
                "instance during startup, or disable admin rate-limit endpoints."
            ),
        },
    )


# ═══════════════════════════════════════════════════════════════════════════
# Helper Functions
# ═══════════════════════════════════════════════════════════════════════════

class TenantMetadataProvider(Protocol):
    """Provider for authoritative tenant metadata lookups."""

    async def get_tenant_tier(self, tenant_id: UUID) -> TenantTier | None:
        """Return tenant tier for tenant_id, or None if not found."""


class Neo4jTenantMetadataProvider:
    """Tenant metadata provider backed by Neo4j."""

    async def get_tenant_tier(self, tenant_id: UUID) -> TenantTier | None:
        return await _get_tenant_tier_from_db(tenant_id)


async def get_tenant_metadata_provider() -> TenantMetadataProvider:
    """Get tenant metadata provider dependency."""
    return Neo4jTenantMetadataProvider()


async def _get_tenant_tier_from_db(
    tenant_id: UUID,
    driver_factory: Any | None = None,
) -> TenantTier | None:
    """Fetch tenant tier from authoritative database source.

    Queries Neo4j Tenant node for tier/isolation_tier property.
    Falls back to SHARED only if tenant not found or DB unavailable,
    with appropriate warning logs.

    Args:
        tenant_id: Tenant UUID
        driver_factory: Optional callable that returns an AsyncDriver.
            If not provided, attempts a runtime import from the Layer 3
            driver module (soft dependency to preserve shared-layer boundary).

    Returns:
        TenantTier enum value from database, or None if tenant not found
    """
    if driver_factory is None:
        try:
            from db.driver import get_driver as _get_driver  # noqa: PLC0415
            driver_factory = _get_driver  # type: ignore[assignment]
        except ImportError:
            pass

    if driver_factory is None:
        logger.warning(
            "Neo4j driver not available for tenant tier lookup, "
            "falling back to SHARED for tenant_id=%s",
            tenant_id,
        )
        return None

    try:
        driver = await driver_factory()
        async with driver.session() as session:
            # Query Tenant node for tier - check both tier and isolation_tier properties
            result = await session.run(
                """
                MATCH (t:Tenant {id: $tenant_id})
                RETURN t.tier as tier, t.isolation_tier as isolation_tier
                """,
                tenant_id=str(tenant_id),
            )
            record = await result.single()

            if not record:
                logger.warning(
                    "Tenant %s not found in database, falling back to SHARED tier",
                    tenant_id,
                )
                return None

            # Check tier property first, then isolation_tier
            tier_value = record.get("tier") or record.get("isolation_tier")
            if not tier_value:
                logger.warning(
                    "Tenant %s has no tier/isolation_tier property, "
                    "falling back to SHARED",
                    tenant_id,
                )
                return None

            # Normalize to lowercase and map to TenantTier
            tier_str = str(tier_value).lower()
            tier_mapping = {
                "shared": TenantTier.SHARED,
                "dedicated": TenantTier.DEDICATED,
                "enterprise": TenantTier.ENTERPRISE,
                # Also accept isolation tier values
                "standard": TenantTier.SHARED,
                "isolated": TenantTier.DEDICATED,
            }

            tier = tier_mapping.get(tier_str)
            if tier is None:
                logger.warning(
                    "Unknown tier value '%s' for tenant %s, falling back to SHARED",
                    tier_value,
                    tenant_id,
                )
                raise ValueError(f"Unknown tenant tier value: {tier_value}")

            logger.debug(
                "Resolved tenant %s to tier %s from database",
                tenant_id,
                tier.value,
            )
            return tier

    except Exception as e:
        logger.error(
            "Failed to query tenant tier from database for %s: %s. "
            "Falling back to SHARED",
            tenant_id,
            e,
        )
        return None


# ═══════════════════════════════════════════════════════════════════════════
# Endpoints
# ═══════════════════════════════════════════════════════════════════════════

@router.get(
    "/tenants/{tenant_id}/quota",
    response_model=TenantQuotaResponse,
    summary="Get tenant quota status",
    description="""
    Get current quota status for a tenant including:
    - Rate limits (per minute/hour/day)
    - Current usage across all windows
    - Whether custom limits are applied
    
    **Requires:** super_admin role
    """,
)
async def get_tenant_quota(
    tenant_id: UUID,
    context: RequestContext = Depends(require_privileged_access()),
    rate_limiter: TenantRateLimiter = Depends(get_rate_limiter),
    tenant_metadata_provider: TenantMetadataProvider = Depends(get_tenant_metadata_provider),
) -> TenantQuotaResponse:
    """Get quota status for tenant.
    
    Args:
        tenant_id: Tenant UUID
        context: Request context (super-admin required)
        rate_limiter: Rate limiter instance
        
    Returns:
        TenantQuotaResponse with quota and usage
    """
    try:
        tenant_tier = await tenant_metadata_provider.get_tenant_tier(tenant_id)
        if tenant_tier is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant {tenant_id} not found",
            )

        logger.info(
            "Admin quota request",
            extra={
                "tenant_id": str(tenant_id),
                "tenant_tier": tenant_tier.value,
                "admin_user_id": str(context.user_id),
            },
        )

        status_data = await rate_limiter.get_tenant_quota_status(
            tenant_id=tenant_id,
            tenant_tier=tenant_tier,
        )
        status_data["tier"] = tenant_tier.value

        return TenantQuotaResponse(**status_data)
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.warning("Invalid tenant quota request: %s", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid quota request",
        ) from e
    except Exception as e:
        logger.error(f"Failed to get tenant quota: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve quota status",
        ) from e


@router.get(
    "/tenants/{tenant_id}/usage",
    response_model=TenantUsageResponse,
    summary="Get tenant usage statistics",
    description="""
    Get current usage statistics for a tenant across all rate limit windows.
    
    **Requires:** super_admin role
    """,
)
async def get_tenant_usage(
    tenant_id: UUID,
    endpoint: str | None = None,
    context: RequestContext = Depends(require_privileged_access()),
    rate_limiter: TenantRateLimiter = Depends(get_rate_limiter),
) -> TenantUsageResponse:
    """Get usage statistics for tenant.
    
    Args:
        tenant_id: Tenant UUID
        endpoint: Optional endpoint filter
        context: Request context (super-admin required)
        rate_limiter: Rate limiter instance
        
    Returns:
        TenantUsageResponse with usage data
    """
    try:
        usage_data = await rate_limiter.get_tenant_usage(
            tenant_id=tenant_id,
            endpoint=endpoint,
        )
        
        return TenantUsageResponse(**usage_data)
        
    except Exception as e:
        logger.error(f"Failed to get tenant usage: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve usage statistics: {e!r}",
        )


@router.put(
    "/tenants/{tenant_id}/limits",
    status_code=status.HTTP_200_OK,
    summary="Set custom rate limits",
    description="""
    Set custom rate limits for a specific tenant.
    Overrides tier-based defaults.
    
    **Requires:** super_admin role + X-Privileged-Reason header
    """,
)
async def set_custom_limits(
    tenant_id: UUID,
    config: RateLimitConfigRequest,
    context: RequestContext = Depends(require_privileged_access()),
    rate_limiter: TenantRateLimiter = Depends(get_rate_limiter),
) -> dict:
    """Set custom rate limits for tenant.
    
    Args:
        tenant_id: Tenant UUID
        config: Custom rate limit configuration
        context: Request context (super-admin required)
        rate_limiter: Rate limiter instance
        
    Returns:
        Success message
    """
    try:
        rate_limit_config = RateLimitConfig(
            requests_per_minute=config.requests_per_minute,
            requests_per_hour=config.requests_per_hour,
            requests_per_day=config.requests_per_day,
            burst_allowance=config.burst_allowance,
        )
        
        await rate_limiter.set_custom_limit(
            tenant_id=tenant_id,
            config=rate_limit_config,
        )
        
        logger.info(
            f"Super-admin {context.user_id} set custom rate limits for tenant {tenant_id}"
        )
        
        return set_custom_limitsResult.model_validate({
            "message": f"Custom rate limits set for tenant {tenant_id}",
            "limits": {
                "requests_per_minute": config.requests_per_minute,
                "requests_per_hour": config.requests_per_hour,
                "requests_per_day": config.requests_per_day,
                "burst_allowance": config.burst_allowance,
            },
        })


        
    except Exception as e:
        logger.error(f"Failed to set custom limits: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set custom limits: {e!r}",
        )


@router.post(
    "/tenants/{tenant_id}/reset",
    status_code=status.HTTP_200_OK,
    summary="Reset tenant rate limits",
    description="""
    Reset all rate limit counters for a tenant.
    Use with caution - this clears all usage tracking.
    
    **Requires:** super_admin role + X-Privileged-Reason header
    """,
)
async def reset_tenant_limits(
    tenant_id: UUID,
    context: RequestContext = Depends(require_privileged_access()),
    rate_limiter: TenantRateLimiter = Depends(get_rate_limiter),
) -> dict:
    """Reset rate limits for tenant.
    
    Args:
        tenant_id: Tenant UUID
        context: Request context (super-admin required)
        rate_limiter: Rate limiter instance
        
    Returns:
        Number of keys deleted
    """
    try:
        deleted_count = await rate_limiter.reset_tenant_limits(tenant_id)
        
        logger.warning(
            f"Super-admin {context.user_id} reset rate limits for tenant {tenant_id} "
            f"({deleted_count} keys deleted)"
        )
        
        return reset_tenant_limitsResult.model_validate({
            "message": f"Rate limits reset for tenant {tenant_id}",
            "keys_deleted": deleted_count,
        })


        
    except Exception as e:
        logger.error(f"Failed to reset tenant limits: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset rate limits: {e!r}",
        )


@router.get(
    "/tiers",
    summary="List rate limit tiers",
    description="""
    List all available rate limit tiers with their default quotas.
    
    **Requires:** super_admin role
    """,
)
async def list_rate_limit_tiers(
    context: RequestContext = Depends(require_privileged_access()),
) -> dict:
    """List rate limit tiers and their quotas.
    
    Args:
        context: Request context (super-admin required)
        
    Returns:
        Dictionary of tiers and their limits
    """
    from .tenant_rate_limiter import DEFAULT_TENANT_LIMITS
    
    tiers = {}
    for tier, config in DEFAULT_TENANT_LIMITS.items():
        tiers[tier.value] = {
            "requests_per_minute": config.requests_per_minute,
            "requests_per_hour": config.requests_per_hour,
            "requests_per_day": config.requests_per_day,
            "burst_allowance": config.burst_allowance,
        }
    
    return list_rate_limit_tiersResult.model_validate({"tiers": tiers})
