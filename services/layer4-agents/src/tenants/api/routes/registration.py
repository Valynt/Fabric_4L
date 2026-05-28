from __future__ import annotations

from value_fabric.shared.error_handling.exceptions import ValidationError
"""Public tenant registration endpoints."""


import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

# SECURITY: Registration endpoints are pre-authentication flows.
# New tenants/users don't have JWTs yet, so get_db (no tenant context)
# is intentional. Tenant isolation begins AFTER registration completes.
from ....database import get_db_from_context
from ...email_verification import EmailVerificationService
from ...models.tenant import IsolationTier
from ...provisioning import ProvisioningStatus, TenantProvisioningService
from ...service import create_tenant, get_tenant_by_slug
from ...tiers import get_public_tiers, get_tier_config

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tenants", tags=["Registration"])


class RegisterTenantRequest(BaseModel):
    """Request to register a new tenant."""

    name: str = Field(..., min_length=2, max_length=200)
    slug: str = Field(..., min_length=2, max_length=63)
    admin_email: EmailStr
    tier_id: str = "free"  # Default to free tier

    # Optional
    organization_name: str | None = None
    phone: str | None = None

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        """Validate slug format."""
        if not v.replace("-", "").replace("_", "").isalnum():
            raise ValueError("Slug must contain only lowercase letters, numbers, hyphens")
        if not v[0].isalnum():
            raise ValueError("Slug must start with alphanumeric character")
        return v.lower()


class VerifyEmailRequest(BaseModel):
    """Request to verify email address."""

    token: str


class RegisterTenantResponse(BaseModel):
    """Response from tenant registration."""

    message: str
    tenant_id: str
    verification_required: bool


class VerifyEmailResponse(BaseModel):
    """Response from email verification."""

    message: str
    tenant_id: str
    status: str


class ValidateSlugResponse(BaseModel):
    """Response for slug validation."""

    slug: str
    available: bool


class TierInfo(BaseModel):
    """Tier information for public listing."""

    id: str
    name: str
    description: str
    limits: dict
    features: dict


@router.post("/register", status_code=status.HTTP_202_ACCEPTED, response_model=RegisterTenantResponse)
async def register_tenant(
    request: RegisterTenantRequest,
    db: AsyncSession = Depends(get_db_from_context),
) -> RegisterTenantResponse:
    """Register a new tenant.

    Process:
    1. Validate slug uniqueness
    2. Validate tier exists and is public
    3. Create tenant (PENDING status)
    4. Generate verification token
    5. Send verification email

    Returns immediately; provisioning happens after email verification.
    """
    # Check slug uniqueness
    existing = await get_tenant_by_slug(db, request.slug)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tenant slug already exists",
        )

    # Validate tier
    try:
        tier = get_tier_config(request.tier_id)
        if not tier.is_public:
            raise ValidationError(message = "Invalid tier selection")
    except ValueError:
        raise ValidationError(message = "Invalid tier")

    # Create tenant
    from value_fabric.shared.identity.models import TenantCreateRequest

    create_request = TenantCreateRequest(
        name=request.name,
        slug=request.slug,
        settings={
            "isolation_tier": IsolationTier.SHARED.value,
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
        # Log but don't fail — can resend
        logger.warning(f"Failed to send verification email to {request.admin_email}")

    return RegisterTenantResponse(
        message="Registration received. Check your email to verify.",
        tenant_id=tenant.id,
        verification_required=True,
    )


@router.post("/verify-email", response_model=VerifyEmailResponse)
async def verify_email(
    request: VerifyEmailRequest,
    db: AsyncSession = Depends(get_db_from_context),
) -> VerifyEmailResponse:
    """Verify email address and trigger provisioning workflow."""
    email_service = EmailVerificationService()

    # Verify token
    verification = await email_service.verify_token(request.token)
    if not verification:
        raise ValidationError(message = "Invalid or expired verification token")

    # Mark token used
    await email_service.mark_token_used(request.token)

    # Trigger provisioning workflow
    provisioning_service = TenantProvisioningService(db)
    state = await provisioning_service.provision_tenant(verification.tenant_id)

    if state.status != ProvisioningStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Provisioning failed",
                "error": state.error,
                "retryable": state.retryable,
            },
        )

    logger.info("Email verified and tenant %s provisioned successfully", verification.tenant_id)

    return VerifyEmailResponse(
        message="Email verified and tenant provisioned successfully",
        tenant_id=str(verification.tenant_id),
        status="active",
    )


@router.get("/validate-slug", response_model=ValidateSlugResponse)
async def validate_slug(
    slug: str,
    db: AsyncSession = Depends(get_db_from_context),
) -> ValidateSlugResponse:
    """Check if a tenant slug is available."""
    existing = await get_tenant_by_slug(db, slug)

    return ValidateSlugResponse(
        slug=slug,
        available=existing is None,
    )


@router.get("/tiers", response_model=list[TierInfo])
async def list_tiers() -> list[TierInfo]:
    """List available subscription tiers."""
    tiers = get_public_tiers()
    return [
        TierInfo(
            id=t.id,
            name=t.name,
            description=t.description,
            limits={
                "max_users": t.limits.max_users,
                "max_agents": t.limits.max_agents,
                "monthly_api_calls": t.limits.monthly_api_calls,
            },
            features={
                "advanced_analytics": t.features.advanced_analytics,
                "custom_branding": t.features.custom_branding,
                "sso_integration": t.features.sso_integration,
            },
        )
        for t in tiers
    ]
