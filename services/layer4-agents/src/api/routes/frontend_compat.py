from __future__ import annotations

from value_fabric.shared.error_handling.exceptions import NotFoundError, ValidationError
"""Frontend compatibility aliases for path mismatches.

These routes provide backward-compatible paths that the frontend expects,
mapping to canonical backend handlers.

ROUTE LIFECYCLE DOCUMENTATION
------------------------------
Canonical API routes (do NOT delete without frontend coordination):
  GET  /tenant/settings     -> current tenant settings (auth required)
  PATCH /tenant/settings    -> update current tenant settings (auth required)

Temporary frontend compatibility routes (plan migration to canonical paths):
  POST /auth/register       -> alias for /v1/tenants/register
    - FRONTEND CALLER: frontend/client/src/api/auth.ts
    - MIGRATION PLAN: update frontend to call /v1/tenants/register directly
    - REVIEW DATE: 2026-06-01

Deprecated aliases (should be removed once frontend stops using them):
  None currently.

NOTES
-----
- This router is mounted at prefix="/v1" in src/api/main.py.
- All aliases should enforce the same auth/tenant isolation as canonical routes.
- When adding a new alias, document it above and update the contract map.
"""


from uuid import UUID

from fastapi import APIRouter, Cookie, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_authenticated

from ...database import get_db_from_context
from ...tenants.email_verification import EmailVerificationService
from ...tenants.service import get_tenant, update_tenant_settings
from ...tenants.tiers import get_tier_config
from ..security.csrf import CSRF_COOKIE_NAME, validate_double_submit

router = APIRouter(tags=["Frontend Compatibility"])


class TenantSettingsResponse(BaseModel):
    """Tenant settings response."""

    id: str
    name: str
    slug: str
    status: str
    tier_id: str
    settings: dict
    created_at: str


class TenantSettingsUpdate(BaseModel):
    """Update tenant settings."""

    settings: dict | None = None


class TenantSettingsUpdateResponse(BaseModel):
    """Tenant settings update response."""

    id: str
    name: str
    settings: dict
    updated_at: str


class RegisterTenantRequest(BaseModel):
    """Request to register a new tenant."""

    name: str
    slug: str
    admin_email: str
    tier_id: str = "free"
    organization_name: str | None = None
    phone: str | None = None


class RegisterTenantResponse(BaseModel):
    """Response from tenant registration."""

    message: str
    tenant_id: str
    verification_required: bool


class AuthSessionResponse(BaseModel):
    """Minimal authenticated session profile for compatibility smoke checks."""

    authenticated: bool
    user_id: str
    tenant_id: str
    roles: list[str]
    permissions: list[str]


@router.get("/auth/session", response_model=AuthSessionResponse)
async def get_auth_session_frontend_alias(
    ctx: RequestContext = Depends(require_authenticated),
) -> AuthSessionResponse:
    """Compatibility alias exposing the current request context as a session profile."""
    return AuthSessionResponse(
        authenticated=True,
        user_id=str(ctx.user_id),
        tenant_id=str(ctx.tenant_id),
        roles=[getattr(role, "value", str(role)) for role in ctx.roles],
        permissions=[getattr(permission, "value", str(permission)) for permission in ctx.permissions],
    )


@router.get("/tenant/settings", response_model=TenantSettingsResponse, deprecated=True, openapi_extra={"x-deprecated-removal-date": "2026-08-01", "x-canonical-path": "/v1/tenants/current/settings"})
async def get_current_tenant_settings(
    db: AsyncSession = Depends(get_db_from_context),
    ctx: RequestContext = Depends(require_authenticated),
) -> TenantSettingsResponse:
    """DEPRECATED alias for GET /v1/tenants/current/settings. Planned removal: 2026-08-01."""
    tenant = await get_tenant(db, ctx.tenant_id)
    if not tenant:
        raise NotFoundError(message = "Tenant not found")

    settings = tenant.settings or {}
    tier_id = settings.get("tier_id", "free")

    return TenantSettingsResponse(
        id=str(tenant.id),
        name=tenant.name,
        slug=tenant.slug,
        status=tenant.status,
        tier_id=tier_id,
        settings=settings,
        created_at=tenant.created_at.isoformat() if tenant.created_at else "",
    )


@router.patch("/tenant/settings", response_model=TenantSettingsUpdateResponse, deprecated=True, openapi_extra={"x-deprecated-removal-date": "2026-08-01", "x-canonical-path": "/v1/tenants/current/settings"})
async def update_current_tenant_settings(
    update: TenantSettingsUpdate,
    db: AsyncSession = Depends(get_db_from_context),
    ctx: RequestContext = Depends(require_authenticated),
    _csrf_cookie: str | None = Cookie(default=None, alias=CSRF_COOKIE_NAME),
    _csrf_ok: None = Depends(validate_double_submit),
) -> TenantSettingsUpdateResponse:
    """DEPRECATED alias for PATCH /v1/tenants/current/settings. Planned removal: 2026-08-01."""
    tenant = await get_tenant(db, ctx.tenant_id)
    if not tenant:
        raise NotFoundError(message = "Tenant not found")

    current_settings = tenant.settings or {}
    if update.settings:
        allowed_fields = {
            "custom_branding",
            "notification_preferences",
            "webhook_url",
            "security",
            "feature_flags",
            "limits",
            "retention",
            "integrations_summary",
        }
        for key, value in update.settings.items():
            if key in allowed_fields:
                current_settings[key] = value
        tenant.settings = current_settings

    updated = await update_tenant_settings(
        db,
        ctx.tenant_id,
        settings_update=current_settings,
    )
    if not updated:
        raise HTTPException(status_code=500, detail="Failed to update tenant settings")

    return TenantSettingsUpdateResponse(
        id=str(updated.id),
        name=updated.name,
        settings=updated.settings or {},
        updated_at=updated.updated_at.isoformat() if updated.updated_at else "",
    )


@router.post("/auth/register", status_code=202, response_model=RegisterTenantResponse, deprecated=True, openapi_extra={"x-deprecated-removal-date": "2026-07-01", "x-canonical-path": "/v1/tenants/register"})
async def register_tenant_frontend_alias(
    request: RegisterTenantRequest,
    db: AsyncSession = Depends(get_db_from_context),
    _csrf_cookie: str | None = Cookie(default=None, alias=CSRF_COOKIE_NAME),
    _csrf_ok: None = Depends(validate_double_submit),
) -> RegisterTenantResponse:
    """DEPRECATED alias for POST /v1/tenants/register. Planned removal: 2026-07-01."""
    from value_fabric.shared.identity.models import TenantCreateRequest

    from ...service import create_tenant, get_tenant_by_slug

    # Check slug uniqueness
    existing = await get_tenant_by_slug(db, request.slug)
    if existing:
        raise HTTPException(status_code=409, detail="Tenant slug already exists")

    # Validate tier
    try:
        tier = get_tier_config(request.tier_id)
        if not tier.is_public:
            raise ValidationError(message = "Invalid tier selection")
    except ValueError:
        raise ValidationError(message = "Invalid tier")

    # Create tenant
    create_request = TenantCreateRequest(
        name=request.name,
        slug=request.slug,
        settings={
            "isolation_tier": "shared",
            "admin_email": request.admin_email,
            "organization_name": request.organization_name,
            "phone": request.phone,
            "tier_id": request.tier_id,
            "registration_pending": True,
        },
    )

    tenant = await create_tenant(db, create_request)

    # Generate verification token
    email_service = EmailVerificationService()
    token = email_service.generate_token(UUID(tenant.id), request.admin_email)

    # Send verification email
    email_sent = await email_service.send_verification_email(
        request.admin_email,
        request.name,
        token,
    )

    if not email_sent:
        import logging

        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to send verification email to {request.admin_email}")

    return RegisterTenantResponse(
        message="Registration received. Check your email to verify.",
        tenant_id=tenant.id,
        verification_required=True,
    )
