from __future__ import annotations

from value_fabric.shared.error_handling.exceptions import NotFoundError

"""Feature flags API routes.

GET    /v1/feature-flags            — list flags (tenant-scoped)
GET    /v1/feature-flags/{key}      — get flag details
PUT    /v1/feature-flags/{key}      — upsert flag (tenant_admin)
DELETE /v1/feature-flags/{key}      — delete flag (tenant_admin)
GET    /v1/feature-flags/{key}/evaluate — evaluate for current user
"""


from typing import Any
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_tenant_admin
from value_fabric.shared.models.typed_dict import TypedDictModel

from ...database import get_db_from_context
from ..service import FeatureFlagService


class evaluate_feature_flagResult(TypedDictModel):
    enabled: Any
    flag_key: Any
    tenant_id: Any
    user_id: Any

router = APIRouter(prefix="/feature-flags", tags=["Feature Flags"])


class FeatureFlagResponse(BaseModel):
    """Feature flag read model."""

    id: UUID
    tenant_id: UUID | None
    flag_key: str
    enabled: bool
    rollout_percentage: int = Field(..., ge=0, le=100)
    description: str | None
    metadata: dict[str, Any]
    created_at: str
    updated_at: str
    updated_by: UUID | None

    model_config = ConfigDict(from_attributes=True)


class FeatureFlagUpsertRequest(BaseModel):
    """Payload to create or update a feature flag."""

    enabled: bool
    rollout_percentage: int = Field(..., ge=0, le=100)
    description: str | None = None
    metadata: dict[str, Any] | None = Field(default_factory=dict)


@router.get("", response_model=list[FeatureFlagResponse])
async def list_feature_flags(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    ctx: RequestContext = Depends(require_tenant_admin),
    db: AsyncSession = Depends(get_db_from_context),
) -> list[FeatureFlagResponse]:
    """List feature flags for the caller's tenant."""
    # super_admin can list platform-wide flags if they omit tenant context,
    # but for simplicity we always scope to the resolved tenant.
    flags = await FeatureFlagService.list_flags(
        db, tenant_id=ctx.tenant_id, limit=limit, offset=offset
    )
    return [
        FeatureFlagResponse(
            id=f.id,
            tenant_id=f.tenant_id,
            flag_key=f.flag_key,
            enabled=f.enabled,
            rollout_percentage=f.rollout_percentage,
            description=f.description,
            metadata=f.metadata_ or {},
            created_at=f.created_at.isoformat(),
            updated_at=f.updated_at.isoformat(),
            updated_by=f.updated_by,
        )
        for f in flags
    ]


@router.get("/{flag_key}", response_model=FeatureFlagResponse)
async def get_feature_flag(
    flag_key: str,
    ctx: RequestContext = Depends(require_tenant_admin),
    db: AsyncSession = Depends(get_db_from_context),
) -> FeatureFlagResponse:
    """Get a single feature flag by key."""
    flag = await FeatureFlagService.get_flag(db, flag_key, tenant_id=ctx.tenant_id)
    if flag is None:
        raise NotFoundError(message = str(f"Feature flag '{flag_key}' not found"))
    return FeatureFlagResponse(
        id=flag.id,
        tenant_id=flag.tenant_id,
        flag_key=flag.flag_key,
        enabled=flag.enabled,
        rollout_percentage=flag.rollout_percentage,
        description=flag.description,
        metadata=flag.metadata_ or {},
        created_at=flag.created_at.isoformat(),
        updated_at=flag.updated_at.isoformat(),
        updated_by=flag.updated_by,
    )


@router.put("/{flag_key}", response_model=FeatureFlagResponse)
async def upsert_feature_flag(
    flag_key: str,
    request: FeatureFlagUpsertRequest,
    background_tasks: BackgroundTasks,
    ctx: RequestContext = Depends(require_tenant_admin),
    db: AsyncSession = Depends(get_db_from_context),
) -> FeatureFlagResponse:
    """Create or update a feature flag."""
    updated_by = UUID(ctx.user_id) if ctx.user_id else None
    flag = await FeatureFlagService.upsert_flag(
        db=db,
        flag_key=flag_key,
        tenant_id=ctx.tenant_id,
        enabled=request.enabled,
        rollout_percentage=request.rollout_percentage,
        description=request.description,
        metadata=request.metadata,
        updated_by=updated_by,
        background_tasks=background_tasks,
        ctx=ctx,
    )
    return FeatureFlagResponse(
        id=flag.id,
        tenant_id=flag.tenant_id,
        flag_key=flag.flag_key,
        enabled=flag.enabled,
        rollout_percentage=flag.rollout_percentage,
        description=flag.description,
        metadata=flag.metadata_ or {},
        created_at=flag.created_at.isoformat(),
        updated_at=flag.updated_at.isoformat(),
        updated_by=flag.updated_by,
    )


@router.delete("/{flag_key}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_feature_flag(
    flag_key: str,
    background_tasks: BackgroundTasks,
    ctx: RequestContext = Depends(require_tenant_admin),
    db: AsyncSession = Depends(get_db_from_context),
) -> None:
    """Delete a feature flag."""
    deleted = await FeatureFlagService.delete_flag(
        db=db,
        flag_key=flag_key,
        tenant_id=ctx.tenant_id,
        background_tasks=background_tasks,
        ctx=ctx,
    )
    if not deleted:
        raise NotFoundError(message = str(f"Feature flag '{flag_key}' not found"))


@router.get("/{flag_key}/evaluate")
async def evaluate_feature_flag(
    flag_key: str,
    ctx: RequestContext = Depends(require_tenant_admin),
) -> dict[str, Any]:
    """Evaluate a feature flag for the current user context."""
    result = await FeatureFlagService.evaluate_flag(
        flag_key=flag_key,
        tenant_id=ctx.tenant_id,
        user_id=ctx.user_id,
    )
    return evaluate_feature_flagResult.model_validate({
        "flag_key": flag_key,
        "tenant_id": str(ctx.tenant_id),
        "user_id": ctx.user_id,
        "enabled": result,
    })


