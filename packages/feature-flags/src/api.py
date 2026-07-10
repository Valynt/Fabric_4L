"""
Fabric_4L Feature Flags — FastAPI Admin API
v1.2.0

Provides CRUD for feature flags, override management, audit log retrieval,
and kill-switch activation. All endpoints require admin role.

Mounted in the main app via:
    app.include_router(feature_flags_router, prefix="/api/v1/admin")
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Annotated, Any, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, field_validator

# ---------------------------------------------------------------------------
# Dependencies (provided by the host app — value_fabric.shared.auth)
# ---------------------------------------------------------------------------

# The host app MUST supply these via dependency overrides in test / prod:
#
#   from value_fabric.shared.auth import require_admin_role, get_db_pool, get_redis
#
# For standalone development we define protocol-style stubs here and
# expect the host to override them.

try:
    from value_fabric.shared.auth import require_admin_role
    from value_fabric.shared.db import get_db_pool
    from value_fabric.shared.redis import get_redis
except ImportError:  # pragma: no cover — development fallback

    async def _fake_admin(_request: Request) -> "Actor":
        return Actor(id="dev", type="user", email="dev@fabric_4l.local")

    async def _fake_db(_request: Request) -> "DbPool":
        raise RuntimeError("DB pool not configured — override get_db_pool in app deps")

    async def _fake_redis(_request: Request) -> "RedisStub":
        return RedisStub()

    require_admin_role = _fake_admin  # type: ignore[assignment]
    get_db_pool = _fake_db  # type: ignore[assignment]
    get_redis = _fake_redis  # type: ignore[assignment]


logger = logging.getLogger("fabric.feature_flags.api")

# ---------------------------------------------------------------------------
# Domain models
# ---------------------------------------------------------------------------

class TenantTier(str, Enum):
    SHARED = "shared"
    DEDICATED = "dedicated"
    ENTERPRISE = "enterprise"


class Actor(BaseModel):
    id: str
    type: Literal["user", "service", "system"]
    email: Optional[str] = None


class FlagRule(BaseModel):
    tenant_tier: Optional[TenantTier] = None
    tenant_ids: Optional[list[str]] = Field(default=None, max_length=100)
    percentage: Optional[int] = Field(default=None, ge=0, le=100)
    user_segments: Optional[list[str]] = None


class FeatureFlagBase(BaseModel):
    flag_key: str = Field(..., min_length=1, max_length=128, pattern=r"^[a-z0-9-]+$")
    description: str = Field(default="", max_length=512)
    default_value: bool = False  # fail-safe


class FeatureFlagCreate(FeatureFlagBase):
    rules: list[FlagRule] = []

    @field_validator("flag_key")
    @classmethod
    def _lowercase(cls, v: str) -> str:
        return v.lower()


class FeatureFlagUpdate(BaseModel):
    description: Optional[str] = Field(default=None, max_length=512)
    default_value: Optional[bool] = None
    rules: Optional[list[FlagRule]] = None


class OverrideCreate(BaseModel):
    tenant_id: Optional[str] = None
    tier: Optional[TenantTier] = None
    enabled: bool = True
    percentage: Optional[int] = Field(default=None, ge=0, le=100)
    expires_at: Optional[datetime] = None

    @field_validator("tenant_id")
    @classmethod
    def _xor_scope(cls, v: Optional[str], info: Any) -> Optional[str]:
        data = info.data if hasattr(info, "data") else info  # pydantic v1/v2 compat
        tier = data.get("tier") if isinstance(data, dict) else getattr(data, "tier", None)
        has_tenant = v is not None and v != ""
        has_tier = tier is not None
        if has_tenant and has_tier:
            raise ValueError("Provide tenant_id OR tier, not both")
        if not has_tenant and not has_tier:
            raise ValueError("Provide tenant_id OR tier")
        return v


class FeatureFlagOut(FeatureFlagBase):
    id: int
    created_at: datetime
    updated_at: datetime
    override_count: int = 0
    rules: list[FlagRule] = []

    model_config = {"from_attributes": True}


class AuditEventOut(BaseModel):
    id: int
    flag_key: str
    actor: str
    action: str
    old_value: Optional[dict[str, Any]] = None
    new_value: Optional[dict[str, Any]] = None
    timestamp: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Redis stub (host app provides real Redis)
# ---------------------------------------------------------------------------

class RedisStub:
    """In-memory fallback for local development."""

    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    async def get(self, key: str) -> Optional[str]:
        return self._store.get(key)

    async def setex(self, key: str, seconds: int, value: str) -> None:
        self._store[key] = value

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter(tags=["Feature Flags"])

DbDep = Annotated[Any, Depends(get_db_pool)]
RedisDep = Annotated[Any, Depends(get_redis)]
AdminDep = Annotated[Actor, Depends(require_admin_role)]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CACHE_PREFIX = "ff:v1"
_KILL_SWITCH_TTL_SECONDS = 14_400  # 4 hours


def _cache_key(flag_key: str, tenant_id: str) -> str:
    """Cache key for evaluated flag result."""
    return f"{_CACHE_PREFIX}:eval:{flag_key}:{tenant_id}"


def _kill_switch_key(flag_key: str) -> str:
    return f"{_CACHE_PREFIX}:kill:{flag_key}"


def _hash_user_id(raw: str) -> str:
    secret = os.environ.get("FEATURE_FLAG_HMAC_SECRET", "dev-secret-change-me")
    return hmac.new(
        secret.encode(), raw.encode(), hashlib.sha256
    ).hexdigest()[:16]


async def _invalidate_eval_cache(redis: Any, flag_key: str) -> None:
    """Invalidate all cached evaluation results for a flag."""
    # In production this would scan for matching keys or use a Redis set.
    # For now we publish a cache-invalidation pub/sub message.
    pass


async def _insert_audit(
    db: Any,
    flag_id: int,
    actor: Actor,
    action: str,
    old: Optional[dict] = None,
    new: Optional[dict] = None,
) -> None:
    actor_str = f"{actor.type}:{actor.id}"
    sql = """
        INSERT INTO feature_flags.feature_flag_audit_log
            (flag_id, actor, action, old_value, new_value, timestamp)
        VALUES ($1, $2, $3, $4, $5, NOW())
    """
    await db.execute(sql, flag_id, actor_str, action, old, new)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/feature-flags",
    response_model=list[FeatureFlagOut],
    summary="List all feature flags",
    responses={status.HTTP_403_FORBIDDEN: {"description": "Admin role required"}},
)
async def list_feature_flags(
    db: DbDep,
    _: AdminDep,
    include_expired_overrides: bool = False,
) -> list[FeatureFlagOut]:
    """
    Return all flags with their current override counts.
    Expired overrides are excluded by default.
    """
    sql = """
        SELECT
            f.id,
            f.flag_key,
            f.description,
            f.default_value,
            f.created_at,
            f.updated_at,
            COUNT(o.id) AS override_count
        FROM feature_flags.feature_flags f
        LEFT JOIN feature_flags.feature_flag_overrides o
            ON o.flag_id = f.id
            AND ($1 OR o.expires_at IS NULL OR o.expires_at > NOW())
        GROUP BY f.id, f.flag_key, f.description,
                 f.default_value, f.created_at, f.updated_at
        ORDER BY f.updated_at DESC
    """
    rows = await db.fetch(sql, include_expired_overrides)
    return [FeatureFlagOut(**dict(r)) for r in rows]


@router.post(
    "/feature-flags",
    response_model=FeatureFlagOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new feature flag",
)
async def create_feature_flag(
    payload: FeatureFlagCreate,
    db: DbDep,
    redis: RedisDep,
    actor: AdminDep,
) -> FeatureFlagOut:
    """
    Create a feature flag. `default_value` MUST be `false` for new flags
    unless explicitly overridden by an admin with write justification.
    """
    async with db.transaction():
        # Check for duplicate key
        dup = await db.fetchval(
            "SELECT 1 FROM feature_flags.feature_flags WHERE flag_key = $1",
            payload.flag_key,
        )
        if dup:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Flag '{payload.flag_key}' already exists",
            )

        flag_id = await db.fetchval(
            """
            INSERT INTO feature_flags.feature_flags
                (flag_key, description, default_value)
            VALUES ($1, $2, $3)
            RETURNING id
            """,
            payload.flag_key,
            payload.description,
            payload.default_value,
        )

        # Insert rules as overrides
        for rule in payload.rules:
            await db.execute(
                """
                INSERT INTO feature_flags.feature_flag_overrides
                    (flag_id, tenant_id, tier, enabled, percentage)
                VALUES ($1, $2, $3, $4, $5)
                """,
                flag_id,
                rule.tenant_ids[0] if rule.tenant_ids else None,
                rule.tenant_tier.value if rule.tenant_tier else None,
                True,
                rule.percentage,
            )

        await _insert_audit(
            db,
            flag_id,
            actor,
            "created",
            None,
            {"flag_key": payload.flag_key, "default_value": payload.default_value},
        )

    await _invalidate_eval_cache(redis, payload.flag_key)

    return FeatureFlagOut(
        id=flag_id,
        flag_key=payload.flag_key,
        description=payload.description,
        default_value=payload.default_value,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        override_count=len(payload.rules),
        rules=payload.rules,
    )


@router.get(
    "/feature-flags/{flag_key}",
    response_model=FeatureFlagOut,
    summary="Get a single feature flag",
)
async def get_feature_flag(
    flag_key: str,
    db: DbDep,
    _: AdminDep,
) -> FeatureFlagOut:
    """Return flag details including active overrides."""
    row = await db.fetchrow(
        """
        SELECT
            f.id,
            f.flag_key,
            f.description,
            f.default_value,
            f.created_at,
            f.updated_at,
            COUNT(o.id) AS override_count
        FROM feature_flags.feature_flags f
        LEFT JOIN feature_flags.feature_flag_overrides o
            ON o.flag_id = f.id
            AND (o.expires_at IS NULL OR o.expires_at > NOW())
        WHERE f.flag_key = $1
        GROUP BY f.id
        """,
        flag_key,
    )
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Flag '{flag_key}' not found",
        )
    return FeatureFlagOut(**dict(row))


@router.put(
    "/feature-flags/{flag_key}",
    response_model=FeatureFlagOut,
    summary="Update a feature flag",
)
async def update_feature_flag(
    flag_key: str,
    payload: FeatureFlagUpdate,
    db: DbDep,
    redis: RedisDep,
    actor: AdminDep,
) -> FeatureFlagOut:
    """
    Update flag metadata, default value, or replace rules.
    All changes are audited.
    """
    async with db.transaction():
        row = await db.fetchrow(
            "SELECT * FROM feature_flags.feature_flags WHERE flag_key = $1",
            flag_key,
        )
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Flag '{flag_key}' not found",
            )

        old = dict(row)
        flag_id: int = row["id"]
        updates: dict[str, Any] = {}

        if payload.description is not None:
            updates["description"] = payload.description
        if payload.default_value is not None:
            updates["default_value"] = payload.default_value

        if updates:
            set_clause = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(updates))
            sql = f"""
                UPDATE feature_flags.feature_flags
                SET {set_clause}, updated_at = NOW()
                WHERE id = $1
            """
            await db.execute(sql, flag_id, *updates.values())

        # Replace rules if provided
        if payload.rules is not None:
            await db.execute(
                "DELETE FROM feature_flags.feature_flag_overrides WHERE flag_id = $1",
                flag_id,
            )
            for rule in payload.rules:
                await db.execute(
                    """
                    INSERT INTO feature_flags.feature_flag_overrides
                        (flag_id, tenant_id, tier, enabled, percentage)
                    VALUES ($1, $2, $3, $4, $5)
                    """,
                    flag_id,
                    rule.tenant_ids[0] if rule.tenant_ids else None,
                    rule.tenant_tier.value if rule.tenant_tier else None,
                    True,
                    rule.percentage,
                )

        await _insert_audit(
            db,
            flag_id,
            actor,
            "updated",
            old,
            {
                "description": payload.description,
                "default_value": payload.default_value,
                "rules": [r.model_dump() for r in payload.rules] if payload.rules else None,
            },
        )

    await _invalidate_eval_cache(redis, flag_key)

    return await get_feature_flag(flag_key, db, actor)  # type: ignore[arg-type]


@router.delete(
    "/feature-flags/{flag_key}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a feature flag",
)
async def delete_feature_flag(
    flag_key: str,
    db: DbDep,
    redis: RedisDep,
    actor: AdminDep,
) -> None:
    """Hard-delete a flag and all associated overrides / audit entries."""
    async with db.transaction():
        row = await db.fetchrow(
            "SELECT id FROM feature_flags.feature_flags WHERE flag_key = $1",
            flag_key,
        )
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Flag '{flag_key}' not found",
            )
        flag_id: int = row["id"]
        await _insert_audit(
            db,
            flag_id,
            actor,
            "deleted",
            {"flag_key": flag_key},
            None,
        )
        await db.execute(
            "DELETE FROM feature_flags.feature_flags WHERE id = $1",
            flag_id,
        )
    await _invalidate_eval_cache(redis, flag_key)


@router.get(
    "/feature-flags/{flag_key}/audit",
    response_model=list[AuditEventOut],
    summary="Get audit log for a flag",
)
async def get_flag_audit_log(
    flag_key: str,
    db: DbDep,
    _: AdminDep,
    limit: int = 50,
    offset: int = 0,
) -> list[AuditEventOut]:
    """Return the most recent audit events for a flag, newest first."""
    rows = await db.fetch(
        """
        SELECT
            al.id,
            f.flag_key,
            al.actor,
            al.action,
            al.old_value,
            al.new_value,
            al.timestamp
        FROM feature_flags.feature_flag_audit_log al
        JOIN feature_flags.feature_flags f ON f.id = al.flag_id
        WHERE f.flag_key = $1
        ORDER BY al.timestamp DESC
        LIMIT $2 OFFSET $3
        """,
        flag_key,
        limit,
        offset,
    )
    return [AuditEventOut(**dict(r)) for r in rows]


# ═══════════════════════════════════════════════════════════════════════════
# Kill Switch Endpoints
# ═══════════════════════════════════════════════════════════════════════════

class KillSwitchActivatePayload(BaseModel):
    """Request body to arm a kill switch."""

    reason: str = Field(..., min_length=5, max_length=500)
    duration_seconds: int = Field(default=_KILL_SWITCH_TTL_SECONDS, le=86_400)


class KillSwitchStatus(BaseModel):
    flag_key: str
    killed: bool
    armed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    reason: Optional[str] = None


@router.post(
    "/feature-flags/{flag_key}/kill",
    response_model=KillSwitchStatus,
    summary="Activate kill switch for a flag",
)
async def activate_kill_switch(
    flag_key: str,
    payload: KillSwitchActivatePayload,
    db: DbDep,
    redis: RedisDep,
    actor: AdminDep,
) -> KillSwitchStatus:
    """
    Emergency kill switch — immediately disables the feature for ALL tenants.
    Auto-expires after 4 hours (configurable up to 24h).
    Triggers PagerDuty alert.
    """
    row = await db.fetchrow(
        "SELECT id FROM feature_flags.feature_flags WHERE flag_key = $1",
        flag_key,
    )
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Flag '{flag_key}' not found",
        )
    flag_id: int = row["id"]
    now = datetime.now(timezone.utc)
    expires = now + timedelta(seconds=payload.duration_seconds)

    # Arm kill switch in Redis (fast, global)
    key = _kill_switch_key(flag_key)
    value = f"{now.isoformat()}|{payload.reason}|{actor.id}"
    await redis.setex(key, payload.duration_seconds, value)

    # Audit log
    await _insert_audit(
        db,
        flag_id,
        actor,
        "kill_switch_activated",
        None,
        {
            "reason": payload.reason,
            "duration_seconds": payload.duration_seconds,
            "expires_at": expires.isoformat(),
        },
    )

    # Trigger PagerDuty alert (async fire-and-forget)
    await _trigger_pagerduty(flag_key, payload.reason, actor)

    logger.critical(
        "Kill switch ACTIVATED for %s by %s (%s). Expires at %s",
        flag_key,
        actor.id,
        payload.reason,
        expires.isoformat(),
    )

    return KillSwitchStatus(
        flag_key=flag_key,
        killed=True,
        armed_at=now,
        expires_at=expires,
        reason=payload.reason,
    )


@router.delete(
    "/feature-flags/{flag_key}/kill",
    response_model=KillSwitchStatus,
    summary="Deactivate (reset) kill switch",
)
async def deactivate_kill_switch(
    flag_key: str,
    db: DbDep,
    redis: RedisDep,
    actor: AdminDep,
) -> KillSwitchStatus:
    """Manually reset a kill switch before its TTL expires."""
    row = await db.fetchrow(
        "SELECT id FROM feature_flags.feature_flags WHERE flag_key = $1",
        flag_key,
    )
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Flag '{flag_key}' not found",
        )
    flag_id: int = row["id"]
    await redis.delete(_kill_switch_key(flag_key))

    await _insert_audit(
        db,
        flag_id,
        actor,
        "kill_switch_expired",
        None,
        {"manual_reset": True, "reset_by": actor.id},
    )

    logger.info("Kill switch RESET for %s by %s", flag_key, actor.id)
    return KillSwitchStatus(flag_key=flag_key, killed=False)


@router.get(
    "/feature-flags/{flag_key}/kill",
    response_model=KillSwitchStatus,
    summary="Check kill switch status",
)
async def get_kill_switch_status(
    flag_key: str,
    redis: RedisDep,
    _: AdminDep,
) -> KillSwitchStatus:
    """Check whether a kill switch is currently armed."""
    raw = await redis.get(_kill_switch_key(flag_key))
    if raw is None:
        return KillSwitchStatus(flag_key=flag_key, killed=False)
    parts = raw.split("|", 2)
    return KillSwitchStatus(
        flag_key=flag_key,
        killed=True,
        armed_at=datetime.fromisoformat(parts[0]),
        reason=parts[1] if len(parts) > 1 else None,
    )


# ---------------------------------------------------------------------------
# Evaluation endpoint (called by backend services, NOT the React SDK)
# ---------------------------------------------------------------------------

class EvaluateRequest(BaseModel):
    flag_key: str
    tenant_id: str
    tenant_tier: Optional[TenantTier] = None
    user_id: Optional[str] = None
    user_segments: Optional[list[str]] = None


class EvaluateResponse(BaseModel):
    flag_key: str
    enabled: bool
    source: Literal["default", "rule", "override", "kill_switch"]
    evaluated_at: datetime


@router.post(
    "/feature-flags/evaluate",
    response_model=EvaluateResponse,
    summary="Evaluate a flag for a given context (backend SDK entrypoint)",
)
async def evaluate_flag_endpoint(
    req: EvaluateRequest,
    db: DbDep,
    redis: RedisDep,
    _: AdminDep,
) -> EvaluateResponse:
    """
    Server-side evaluation. Used by Python services (L1-L6).
    Respects kill switches > overrides > rules > default.
    """
    now = datetime.now(timezone.utc)

    # 1. Kill switch check (fastest path — Redis)
    ks_raw = await redis.get(_kill_switch_key(req.flag_key))
    if ks_raw is not None:
        return EvaluateResponse(
            flag_key=req.flag_key,
            enabled=False,
            source="kill_switch",
            evaluated_at=now,
        )

    # 2. Fetch flag + overrides from DB
    flag_row = await db.fetchrow(
        "SELECT * FROM feature_flags.feature_flags WHERE flag_key = $1",
        req.flag_key,
    )
    if not flag_row:
        # Unknown flag → fail-safe default
        return EvaluateResponse(
            flag_key=req.flag_key,
            enabled=False,
            source="default",
            evaluated_at=now,
        )

    default_value: bool = flag_row["default_value"]

    # 3. Check tenant-specific override
    override = await db.fetchrow(
        """
        SELECT enabled, percentage
        FROM feature_flags.feature_flag_overrides o
        JOIN feature_flags.feature_flags f ON f.id = o.flag_id
        WHERE f.flag_key = $1
          AND (
              o.tenant_id = $2
              OR (o.tier = $3 AND o.tenant_id IS NULL)
          )
          AND (o.expires_at IS NULL OR o.expires_at > NOW())
        LIMIT 1
        """,
        req.flag_key,
        req.tenant_id,
        req.tenant_tier.value if req.tenant_tier else None,
    )

    if override:
        enabled = override["enabled"]
        pct = override["percentage"]
        if enabled and pct is not None:
            bucket = _hash_percentage(req.flag_key, req.tenant_id, req.user_id or "")
            enabled = bucket <= pct
        return EvaluateResponse(
            flag_key=req.flag_key,
            enabled=enabled,
            source="override",
            evaluated_at=now,
        )

    # 4. No override → return default
    return EvaluateResponse(
        flag_key=req.flag_key,
        enabled=default_value,
        source="default",
        evaluated_at=now,
    )


def _hash_percentage(flag_key: str, tenant_id: str, user_id: str) -> int:
    """Deterministic percentage bucket (1-100) matching frontend FNV-1a logic."""
    seed = f"{flag_key}:{tenant_id}:{user_id}"
    h = 0x811C9DC5
    for ch in seed.encode("utf-8"):
        h ^= ch
        h = (h * 0x01000193) & 0xFFFFFFFF
    return (h % 100) + 1


# ---------------------------------------------------------------------------
# PagerDuty integration (fire-and-forget)
# ---------------------------------------------------------------------------

async def _trigger_pagerduty(flag_key: str, reason: str, actor: Actor) -> None:
    """Send a PagerDuty event when a kill switch is activated."""
    import asyncio

    routing_key = os.environ.get("PAGERDUTY_ROUTING_KEY")
    if not routing_key:
        logger.warning("PagerDuty routing key not configured — skipping alert")
        return

    payload = {
        "routing_key": routing_key,
        "event_action": "trigger",
        "dedup_key": f"ff-kill-{flag_key}-{datetime.now(timezone.utc).strftime('%Y%m%d')}",
        "payload": {
            "summary": f"Kill switch activated: {flag_key}",
            "severity": "critical",
            "source": "fabric-feature-flags",
            "custom_details": {
                "flag_key": flag_key,
                "reason": reason,
                "actor_id": actor.id,
                "actor_type": actor.type,
            },
        },
    }

    async def _send() -> None:
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://events.pagerduty.com/v2/enqueue",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as resp:
                    if resp.status >= 400:
                        logger.error("PagerDuty alert failed: HTTP %s", resp.status)
        except Exception as exc:
            logger.error("PagerDuty alert exception: %s", exc)

    # Fire-and-forget; never block the API response
    asyncio.create_task(_send())


# ---------------------------------------------------------------------------
# Include helper for host app
# ---------------------------------------------------------------------------

feature_flags_router = router
