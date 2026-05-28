# Fabric 4L Tenant Management — Phase 3: Self-Service Control Plane

Deliver user-facing APIs for tenant registration, admin dashboard, and usage metrics. Schema-per-tenant remains Phase 4+ consideration. Billing integration deferred until monetization requirements defined.

---

## 1. Objective

Phase 3 delivers the self-service control plane that enables:

1. **Public tenant registration** — Users can sign up and create tenants
2. **Email verification** — Required before provisioning
3. **Tenant admin dashboard API** — User/usage/settings management
4. **Subscription tiers** — Config-based limits (no billing integration)
5. **API key self-service** — Tenant admins manage their own keys

### Design Principles

1. **No billing integration** — Usage metrics collected but no Stripe/payment processing
2. **Config-based tiers** — JSON/YAML tier definitions (not database-driven)
3. **Read-first dashboard** — Analytics before full CRUD
4. **RLS-based isolation** — Continue using hardened RLS from Phase 1
5. **Future-ready** — Architecture supports schema-per-tenant as Phase 4+ option

---

## 2. Current State

### 2.1 Existing Infrastructure

| Component | File | Status |
|-----------|------|--------|
| Tenant Model | `layer4-agents/src/tenants/models/tenant.py` | ✅ With `settings` JSON field |
| Provisioning | `layer4-agents/src/tenants/provisioning.py` | ✅ Phase 2 complete |
| API Key Routes | `layer4-agents/src/tenants/api/routes/api_keys.py` | ✅ Basic CRUD |
| Audit System | `shared/audit/` | ✅ Comprehensive |
| Tier Field | `RequestContext.isolation_tier` | ✅ Supports shared/schema/database |

### 2.2 Required New Components

| Component | Purpose |
|-----------|---------|
| Tier Configuration | JSON-based tier definitions |
| Tier Enforcement | Middleware-based limit checking |
| Usage Tracking | Collect metrics for billing preparation |
| Registration API | Public signup with email verification |
| Admin Dashboard API | Tenant-scoped management endpoints |
| Email Service | Verification and notification emails |

---

## 3. Target Architecture

### 3.1 Registration Flow

```
User Registration                     System Processing
─────────────────                     ─────────────────
POST /tenants/register
  {name, slug, admin_email}
         │
         ▼
┌─────────────────┐
│  Create Tenant  │
│  status=PENDING │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Generate Token │
│  (verification) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Send Email     │────→ User receives verification email
│  (async)        │
└─────────────────┘

User Verification                     System Processing
─────────────────                     ─────────────────
POST /tenants/verify-email
  {token}
         │
         ▼
┌─────────────────┐
│  Validate Token │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Trigger        │────→ Phase 2 provisioning workflow
│  Provisioning   │
└─────────────────┘
```

### 3.2 Admin Dashboard Architecture

```
Tenant Admin                          API Endpoints
────────────                          ─────────────
GET /tenants/{id}/users
  ├─ GET /users (tenant-scoped)
  └─ Response: User list with roles

GET /tenants/{id}/usage
  ├─ Aggregate from usage tracking
  └─ Response: Metrics per resource

GET /tenants/{id}/audit-log
  ├─ Query shared.audit with tenant_id
  └─ Response: Recent tenant events

PATCH /tenants/{id}/settings
  ├─ Update Tenant.settings JSON
  └─ Response: Updated settings
```

---

## 4. Task Breakdown

### Task 3.1: Tier Configuration System
**Estimated Effort:** 4 hours
**Priority:** P1

Create JSON-based tier definitions.

**New File:** `services/layer4-agents/src/tenants/tiers.py`

```python
"""Subscription tier configuration.

Tiers are configuration-based (not database-driven) for Phase 3.
Database-driven tiers with billing integration deferred to Phase 4+.
"""

from dataclasses import dataclass
from typing import Any

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
```

---

### Task 3.2: Tier Enforcement Middleware
**Estimated Effort:** 6 hours
**Priority:** P1

Add middleware to enforce tier limits.

**Modified File:** `packages/shared/src/value_fabric/shared/identity/middleware.py`

```python
from fastapi import HTTPException, status
from layer4_agents.src.tenants.tiers import get_tier_config, check_limit
from layer4_agents.src.tenants.service import TenantService

class TierEnforcementMiddleware:
    """Middleware to enforce tenant tier limits."""

    async def check_user_limit(
        self,
        db: AsyncSession,
        tenant_id: UUID,
    ) -> None:
        """Check if tenant can add another user."""
        service = TenantService(db)
        tenant = await service.get_tenant(tenant_id)
        config = get_tier_config(tenant.tier_id)

        if config.limits.max_users is None:
            return  # Unlimited

        current_users = await service.count_users(tenant_id)
        if current_users >= config.limits.max_users:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User limit reached: {config.limits.max_users}",
            )

    async def check_agent_limit(
        self,
        db: AsyncSession,
        tenant_id: UUID,
    ) -> None:
        """Check if tenant can add another agent."""
        service = TenantService(db)
        tenant = await service.get_tenant(tenant_id)
        config = get_tier_config(tenant.tier_id)

        if config.limits.max_agents is None:
            return

        current_agents = await service.count_agents(tenant_id)
        if current_agents >= config.limits.max_agents:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Agent limit reached: {config.limits.max_agents}",
            )

# Integration in request handling
async def enforce_tier_limits(
    request: Request,
    context: RequestContext,
    db: AsyncSession,
) -> None:
    """Check tier limits for mutating operations."""
    if request.method not in ("POST", "PUT", "PATCH"):
        return  # Skip for read operations

    if not context.tenant_id:
        return  # Skip for non-tenant operations

    # Check specific limits based on endpoint
    path = request.url.path

    if "/users" in path:
        await TierEnforcementMiddleware().check_user_limit(db, context.tenant_id)
    elif "/agents" in path:
        await TierEnforcementMiddleware().check_agent_limit(db, context.tenant_id)
```

---

### Task 3.3: Usage Tracking Service
**Estimated Effort:** 8 hours
**Priority:** P1

Implement usage metrics collection for billing preparation.

**New File:** `services/layer4-agents/src/tenants/usage.py`

```python
"""Tenant usage tracking for metrics and billing preparation."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db_session
from .models.tenant import Tenant

@dataclass
class UsageMetrics:
    """Aggregated usage metrics for a tenant."""
    tenant_id: UUID
    period_start: datetime
    period_end: datetime

    # API usage
    api_calls_total: int
    api_calls_by_endpoint: dict[str, int]

    # Agent usage
    agent_executions: int
    agent_execution_time_ms: int

    # LLM usage
    llm_tokens_input: int
    llm_tokens_output: int
    llm_requests: int

    # Storage
    storage_bytes: int
    neo4j_nodes: int
    postgres_rows: int

    # Compute
    compute_seconds: int

class UsageTrackingService:
    """Service for tracking and querying tenant usage."""

    def __init__(self, db: AsyncSession | None = None) -> None:
        self.db = db
        self._external_db = db is not None

    async def __aenter__(self):
        if not self._external_db:
            self.db = await get_db_session().__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if not self._external_db and self.db:
            await self.db.__aexit__(exc_type, exc_val, exc_tb)

    async def record_api_call(
        self,
        tenant_id: UUID,
        endpoint: str,
        status_code: int,
        duration_ms: int,
    ) -> None:
        """Record an API call for usage tracking.

        Implementation: Write to Redis or time-series DB for aggregation.
        Phase 3: Store in PostgreSQL (simpler, can migrate later).
        """
        from shared.audit import emit_audit_event, AuditAction

        await emit_audit_event(
            action=AuditAction.API_CALL,
            tenant_id=tenant_id,
            details={
                "endpoint": endpoint,
                "status_code": status_code,
                "duration_ms": duration_ms,
            },
        )

    async def record_llm_usage(
        self,
        tenant_id: UUID,
        model: str,
        tokens_input: int,
        tokens_output: int,
        duration_ms: int,
    ) -> None:
        """Record LLM token usage."""
        from shared.audit import emit_audit_event, AuditAction

        await emit_audit_event(
            action=AuditAction.LLM_USAGE,
            tenant_id=tenant_id,
            details={
                "model": model,
                "tokens_input": tokens_input,
                "tokens_output": tokens_output,
                "duration_ms": duration_ms,
            },
        )

    async def record_agent_execution(
        self,
        tenant_id: UUID,
        agent_type: str,
        duration_ms: int,
        success: bool,
    ) -> None:
        """Record agent execution."""
        from shared.audit import emit_audit_event, AuditAction

        await emit_audit_event(
            action=AuditAction.AGENT_EXECUTION,
            tenant_id=tenant_id,
            details={
                "agent_type": agent_type,
                "duration_ms": duration_ms,
                "success": success,
            },
        )

    async def get_usage_summary(
        self,
        tenant_id: UUID,
        days: int = 30,
    ) -> UsageMetrics:
        """Get usage summary for a tenant."""
        end = datetime.now(UTC)
        start = end - timedelta(days=days)

        # Query audit events for the period
        from shared.audit.models import AuditLogEntry

        result = await self.db.execute(
            select(
                AuditLogEntry.action,
                func.count().label("count"),
                func.sum(AuditLogEntry.details["duration_ms"].as_integer()).label("total_duration"),
            )
            .where(AuditLogEntry.tenant_id == tenant_id)
            .where(AuditLogEntry.timestamp >= start)
            .where(AuditLogEntry.timestamp <= end)
            .group_by(AuditLogEntry.action)
        )

        # Aggregate metrics
        rows = result.all()
        metrics = {
            row.action: {"count": row.count, "duration": row.total_duration or 0}
            for row in rows
        }

        return UsageMetrics(
            tenant_id=tenant_id,
            period_start=start,
            period_end=end,
            api_calls_total=metrics.get("api_call", {}).get("count", 0),
            api_calls_by_endpoint={},  # Would need endpoint breakdown
            agent_executions=metrics.get("agent_execution", {}).get("count", 0),
            agent_execution_time_ms=metrics.get("agent_execution", {}).get("duration", 0),
            llm_tokens_input=0,  # Aggregate from LLM usage events
            llm_tokens_output=0,
            llm_requests=metrics.get("llm_usage", {}).get("count", 0),
            storage_bytes=0,  # Would query storage directly
            neo4j_nodes=0,
            postgres_rows=0,
            compute_seconds=0,
        )

    async def get_current_month_usage(
        self,
        tenant_id: UUID,
    ) -> dict[str, Any]:
        """Get current month usage for limit checking."""
        today = datetime.now(UTC)
        start_of_month = today.replace(day=1, hour=0, minute=0, second=0)

        summary = await self.get_usage_summary(
            tenant_id,
            days=(today - start_of_month).days + 1,
        )

        return {
            "api_calls": summary.api_calls_total,
            "llm_tokens": summary.llm_tokens_input + summary.llm_tokens_output,
            "agent_executions": summary.agent_executions,
            "period": "current_month",
        }
```

---

### Task 3.4: Email Verification Service
**Estimated Effort:** 6 hours
**Priority:** P1

Implement email verification for registration.

**New File:** `services/layer4-agents/src/tenants/email_verification.py`

```python
"""Email verification service for tenant registration."""

import os
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import httpx
from pydantic import BaseModel, EmailStr

class EmailConfig(BaseModel):
    """Email service configuration."""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_pass: str = ""
    from_address: str = "noreply@fabric4l.example.com"

    # Or use external service (SendGrid, etc.)
    sendgrid_api_key: str = ""

    @classmethod
    def from_env(cls) -> "EmailConfig":
        return cls(
            smtp_host=os.getenv("SMTP_HOST", ""),
            smtp_port=int(os.getenv("SMTP_PORT", "587")),
            smtp_user=os.getenv("SMTP_USER", ""),
            smtp_pass=os.getenv("SMTP_PASS", ""),
            from_address=os.getenv("EMAIL_FROM", "noreply@fabric4l.example.com"),
            sendgrid_api_key=os.getenv("SENDGRID_API_KEY", ""),
        )

@dataclass
class VerificationToken:
    """Email verification token."""
    tenant_id: UUID
    email: str
    token: str
    expires_at: datetime
    used: bool = False

class EmailVerificationService:
    """Service for email verification."""

    TOKEN_EXPIRY_HOURS = 24

    def __init__(self, redis_client=None) -> None:
        self.redis = redis_client
        self.config = EmailConfig.from_env()

    def generate_token(self, tenant_id: UUID, email: str) -> str:
        """Generate and store verification token."""
        token = secrets.token_urlsafe(32)

        # Store in Redis with expiry
        key = f"email_verification:{token}"
        data = {
            "tenant_id": str(tenant_id),
            "email": email,
            "expires": (datetime.now(UTC) + timedelta(hours=self.TOKEN_EXPIRY_HOURS)).isoformat(),
            "used": False,
        }

        if self.redis:
            self.redis.setex(
                key,
                int(timedelta(hours=self.TOKEN_EXPIRY_HOURS).total_seconds()),
                json.dumps(data),
            )

        return token

    async def verify_token(self, token: str) -> VerificationToken | None:
        """Verify a token and return tenant info."""
        if not self.redis:
            return None

        key = f"email_verification:{token}"
        data = self.redis.get(key)

        if not data:
            return None

        parsed = json.loads(data)

        if parsed["used"]:
            return None

        expires = datetime.fromisoformat(parsed["expires"])
        if datetime.now(UTC) > expires:
            return None

        return VerificationToken(
            tenant_id=UUID(parsed["tenant_id"]),
            email=parsed["email"],
            token=token,
            expires_at=expires,
            used=parsed["used"],
        )

    async def mark_token_used(self, token: str) -> None:
        """Mark token as used after verification."""
        if not self.redis:
            return

        key = f"email_verification:{token}"
        data = json.loads(self.redis.get(key))
        data["used"] = True
        self.redis.setex(key, 3600, json.dumps(data))  # Keep for 1 hour

    async def send_verification_email(
        self,
        to_email: str,
        tenant_name: str,
        verification_token: str,
    ) -> bool:
        """Send verification email."""
        verify_url = f"https://fabric4l.example.com/verify-email?token={verification_token}"

        subject = f"Verify your email for {tenant_name}"
        body = f"""
        Welcome to Fabric 4L!

        Please verify your email by clicking the link below:
        {verify_url}

        This link expires in 24 hours.

        If you didn't request this, please ignore this email.
        """

        if self.config.sendgrid_api_key:
            return await self._send_sendgrid(to_email, subject, body)
        else:
            return await self._send_smtp(to_email, subject, body)

    async def _send_sendgrid(
        self,
        to_email: str,
        subject: str,
        body: str,
    ) -> bool:
        """Send via SendGrid API."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.sendgrid.com/v3/mail/send",
                headers={"Authorization": f"Bearer {self.config.sendgrid_api_key}"},
                json={
                    "personalizations": [{"to": [{"email": to_email}]}],
                    "from": {"email": self.config.from_address},
                    "subject": subject,
                    "content": [{"type": "text/plain", "value": body}],
                },
            )
            return response.status_code == 202

    async def _send_smtp(
        self,
        to_email: str,
        subject: str,
        body: str,
    ) -> bool:
        """Send via SMTP (async wrapper)."""
        import aiosmtplib

        try:
            await aiosmtplib.send(
                sender=self.config.from_address,
                recipients=[to_email],
                subject=subject,
                message=body,
                hostname=self.config.smtp_host,
                port=self.config.smtp_port,
                username=self.config.smtp_user,
                password=self.config.smtp_pass,
                start_tls=True,
            )
            return True
        except Exception:
            return False
```

---

### Task 3.5: Registration API
**Estimated Effort:** 6 hours
**Priority:** P0

Create public registration endpoints.

**New File:** `services/layer4-agents/src/tenants/api/routes/registration.py`

```python
"""Public tenant registration endpoints."""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ...database import get_db_session
from ...email_verification import EmailVerificationService
from ...provisioning import TenantProvisioningService
from ...service import TenantService
from ...tiers import get_public_tiers

router = APIRouter(prefix="/tenants", tags=["Registration"])

class RegisterTenantRequest(BaseModel):
    """Request to register a new tenant."""
    name: str = Field(..., min_length=2, max_length=200)
    slug: str = Field(..., min_length=2, max_length=63, regex=r"^[a-z0-9-]+$")
    admin_email: EmailStr
    tier_id: str = "free"  # Default to free tier

    # Optional
    organization_name: str | None = None
    phone: str | None = None

class VerifyEmailRequest(BaseModel):
    """Request to verify email address."""
    token: str

@router.post("/register", status_code=status.HTTP_202_ACCEPTED)
async def register_tenant(request: RegisterTenantRequest) -> dict:
    """Register a new tenant.

    Process:
    1. Validate slug uniqueness
    2. Validate tier exists and is public
    3. Create tenant (PENDING status)
    4. Generate verification token
    5. Send verification email

    Returns immediately; provisioning happens after email verification.
    """
    async with get_db_session(require_tenant=False) as db:
        # Check slug uniqueness
        service = TenantService(db)
        existing = await service.get_tenant_by_slug(request.slug)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Tenant slug already exists",
            )

        # Validate tier
        try:
            tier = get_tier_config(request.tier_id)
            if not tier.is_public:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid tier selection",
                )
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid tier",
            )

        # Create tenant
        tenant = await service.create_tenant(
            name=request.name,
            slug=request.slug,
            tier_id=request.tier_id,
            settings={
                "admin_email": request.admin_email,
                "organization_name": request.organization_name,
                "phone": request.phone,
            },
            created_by=None,  # Self-registration
        )

        # Generate verification token
        email_service = EmailVerificationService()
        token = email_service.generate_token(tenant.id, request.admin_email)

        # Send verification email
        email_sent = await email_service.send_verification_email(
            request.admin_email,
            request.name,
            token,
        )

        if not email_sent:
            # Log but don't fail — can resend
            logger.warning(f"Failed to send verification email to {request.admin_email}")

        return {
            "message": "Registration received. Check your email to verify.",
            "tenant_id": str(tenant.id),
            "verification_required": True,
        }

@router.post("/verify-email")
async def verify_email(request: VerifyEmailRequest) -> dict:
    """Verify email address and trigger provisioning."""
    email_service = EmailVerificationService()

    # Verify token
    verification = await email_service.verify_token(request.token)
    if not verification:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token",
        )

    # Mark token used
    await email_service.mark_token_used(request.token)

    # Trigger provisioning
    async with get_db_session(require_tenant=False) as db:
        provisioning = TenantProvisioningService(db)
        state = await provisioning.provision_tenant(verification.tenant_id)

        if state.status != "completed":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "message": "Provisioning failed",
                    "error": state.error,
                    "retryable": state.retryable,
                },
            )

    return {
        "message": "Email verified and tenant provisioned successfully",
        "tenant_id": str(verification.tenant_id),
        "status": "active",
    }

@router.get("/validate-slug")
async def validate_slug(slug: str) -> dict:
    """Check if a tenant slug is available."""
    async with get_db_session(require_tenant=False) as db:
        service = TenantService(db)
        existing = await service.get_tenant_by_slug(slug)

        return {
            "slug": slug,
            "available": existing is None,
        }

@router.get("/tiers")
async def list_tiers() -> list[dict]:
    """List available subscription tiers."""
    tiers = get_public_tiers()
    return [
        {
            "id": t.id,
            "name": t.name,
            "description": t.description,
            "limits": {
                "max_users": t.limits.max_users,
                "max_agents": t.limits.max_agents,
                "monthly_api_calls": t.limits.monthly_api_calls,
            },
            "features": {
                "advanced_analytics": t.features.advanced_analytics,
                "custom_branding": t.features.custom_branding,
                "sso_integration": t.features.sso_integration,
            },
        }
        for t in tiers
    ]
```

---

### Task 3.6: Admin Dashboard API
**Estimated Effort:** 8 hours
**Priority:** P1

Create tenant admin endpoints.

**New File:** `services/layer4-agents/src/tenants/api/routes/admin.py`

```python
"""Tenant admin dashboard API."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from shared.audit import get_audit_log_for_tenant
from shared.identity.context import RequestContext
from shared.identity.dependencies import get_request_context, require_tenant_admin
from ...database import get_db_from_context
from ...service import TenantService
from ...usage import UsageTrackingService

router = APIRouter(prefix="/tenants/{tenant_id}", tags=["Tenant Admin"])

class TenantSettingsUpdate(BaseModel):
    """Update tenant settings."""
    name: str | None = None
    settings: dict | None = None

@router.get("/users")
async def list_tenant_users(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db_from_context),
    context: RequestContext = Depends(require_tenant_admin()),
) -> list[dict]:
    """List users in tenant (tenant_admin only)."""
    # Verify tenant access
    if context.tenant_id != tenant_id and not context.is_super_admin():
        raise HTTPException(status_code=403, detail="Access denied")

    service = TenantService(db)
    users = await service.get_tenant_users(tenant_id)

    return [
        {
            "id": str(u.id),
            "email": u.email,
            "role": u.role,
            "created_at": u.created_at.isoformat(),
            "last_login": u.last_login.isoformat() if u.last_login else None,
        }
        for u in users
    ]

@router.get("/usage")
async def get_tenant_usage(
    tenant_id: UUID,
    days: int = 30,
    db: AsyncSession = Depends(get_db_from_context),
    context: RequestContext = Depends(require_tenant_admin()),
) -> dict:
    """Get usage metrics for tenant."""
    if context.tenant_id != tenant_id and not context.is_super_admin():
        raise HTTPException(status_code=403, detail="Access denied")

    usage_service = UsageTrackingService(db)
    summary = await usage_service.get_usage_summary(tenant_id, days)

    return {
        "tenant_id": str(tenant_id),
        "period": {
            "start": summary.period_start.isoformat(),
            "end": summary.period_end.isoformat(),
        },
        "api_calls": {
            "total": summary.api_calls_total,
        },
        "agent_executions": {
            "total": summary.agent_executions,
            "total_time_ms": summary.agent_execution_time_ms,
        },
        "llm_usage": {
            "tokens_input": summary.llm_tokens_input,
            "tokens_output": summary.llm_tokens_output,
            "requests": summary.llm_requests,
        },
    }

@router.get("/audit-log")
async def get_tenant_audit_log(
    tenant_id: UUID,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db_from_context),
    context: RequestContext = Depends(require_tenant_admin()),
) -> dict:
    """Get audit log for tenant."""
    if context.tenant_id != tenant_id and not context.is_super_admin():
        raise HTTPException(status_code=403, detail="Access denied")

    # Query audit log
    events = await get_audit_log_for_tenant(db, tenant_id, limit, offset)

    return {
        "events": [
            {
                "id": str(e.id),
                "action": e.action,
                "timestamp": e.timestamp.isoformat(),
                "actor_id": str(e.actor_id) if e.actor_id else None,
                "details": e.details,
            }
            for e in events
        ],
        "total": len(events),
        "limit": limit,
        "offset": offset,
    }

@router.get("/settings")
async def get_tenant_settings(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db_from_context),
    context: RequestContext = Depends(require_tenant_admin()),
) -> dict:
    """Get tenant settings."""
    if context.tenant_id != tenant_id and not context.is_super_admin():
        raise HTTPException(status_code=403, detail="Access denied")

    service = TenantService(db)
    tenant = await service.get_tenant(tenant_id)

    return {
        "id": str(tenant.id),
        "name": tenant.name,
        "slug": tenant.slug,
        "status": tenant.status,
        "tier_id": tenant.tier_id,
        "settings": tenant.settings,
        "created_at": tenant.created_at.isoformat(),
        "updated_at": tenant.updated_at.isoformat(),
    }

@router.patch("/settings")
async def update_tenant_settings(
    tenant_id: UUID,
    update: TenantSettingsUpdate,
    db: AsyncSession = Depends(get_db_from_context),
    context: RequestContext = Depends(require_tenant_admin()),
) -> dict:
    """Update tenant settings (tenant_admin only)."""
    if context.tenant_id != tenant_id and not context.is_super_admin():
        raise HTTPException(status_code=403, detail="Access denied")

    service = TenantService(db)
    tenant = await service.update_tenant(
        tenant_id,
        name=update.name,
        settings_update=update.settings,
    )

    return {
        "id": str(tenant.id),
        "name": tenant.name,
        "settings": tenant.settings,
        "updated_at": tenant.updated_at.isoformat(),
    }
```

---

### Task 3.7: Enhanced API Key Management
**Estimated Effort:** 4 hours
**Priority:** P2

Extend API key management for tenant self-service.

**Modified File:** `services/layer4-agents/src/tenants/api/routes/api_keys.py`

```python
"""Enhanced API key management with tenant self-service."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from shared.identity.context import RequestContext
from shared.identity.dependencies import get_request_context, require_tenant_admin
from ...database import get_db_from_context
from ...service import TenantService

class CreateApiKeyRequest(BaseModel):
    """Request to create API key."""
    name: str
    expires_in_days: int | None = None  # None = no expiration
    scopes: list[str] = []

class ApiKeyResponse(BaseModel):
    """API key response."""
    id: UUID
    name: str
    key_preview: str  # Last 4 chars only
    scopes: list[str]
    created_at: str
    expires_at: str | None
    last_used_at: str | None

@router.post("")
async def create_api_key(
    tenant_id: UUID,
    request: CreateApiKeyRequest,
    db: AsyncSession = Depends(get_db_from_context),
    context: RequestContext = Depends(require_tenant_admin()),
) -> dict:
    """Create new API key (tenant_admin only)."""
    if context.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")

    service = TenantService(db)

    # Check tier limit
    current_keys = await service.count_api_keys(tenant_id)
    tier_limit = await service.get_tier_api_key_limit(tenant_id)
    if tier_limit and current_keys >= tier_limit:
        raise HTTPException(
            status_code=403,
            detail=f"API key limit reached: {tier_limit}",
        )

    # Create key
    expires_at = None
    if request.expires_in_days:
        expires_at = datetime.now(UTC) + timedelta(days=request.expires_in_days)

    api_key = await service.create_api_key(
        tenant_id=tenant_id,
        name=request.name,
        created_by=context.user_id,
        scopes=request.scopes,
        expires_at=expires_at,
    )

    # Return full key only once
    return {
        "id": str(api_key.id),
        "key": api_key.key,  # Full key — only shown once
        "name": api_key.name,
        "expires_at": expires_at.isoformat() if expires_at else None,
    }

@router.get("")
async def list_api_keys(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db_from_context),
    context: RequestContext = Depends(require_tenant_admin()),
) -> list[ApiKeyResponse]:
    """List API keys (tenant_admin only)."""
    if context.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")

    service = TenantService(db)
    keys = await service.get_tenant_api_keys(tenant_id)

    return [
        ApiKeyResponse(
            id=k.id,
            name=k.name,
            key_preview=f"...{k.key[-4:]}",
            scopes=k.scopes,
            created_at=k.created_at.isoformat(),
            expires_at=k.expires_at.isoformat() if k.expires_at else None,
            last_used_at=k.last_used_at.isoformat() if k.last_used_at else None,
        )
        for k in keys
    ]

@router.delete("/{key_id}")
async def revoke_api_key(
    tenant_id: UUID,
    key_id: UUID,
    db: AsyncSession = Depends(get_db_from_context),
    context: RequestContext = Depends(require_tenant_admin()),
) -> dict:
    """Revoke API key (tenant_admin only)."""
    if context.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")

    service = TenantService(db)
    await service.revoke_api_key(tenant_id, key_id, revoked_by=context.user_id)

    return {"message": "API key revoked"}
```

---

### Task 3.8: E2E Tests
**Estimated Effort:** 6 hours
**Priority:** P1

Create end-to-end tests for control plane.

**New File:** `tests/e2e/test_tenant_control_plane.py`

```python
"""E2E tests for tenant control plane."""

import pytest
from httpx import AsyncClient

@pytest.mark.e2e
async def test_tenant_registration_flow(client: AsyncClient):
    """Test full registration and verification flow."""
    # 1. Register tenant
    response = await client.post(
        "/tenants/register",
        json={
            "name": "E2E Test Tenant",
            "slug": "e2e-test-tenant",
            "admin_email": "admin@example.com",
            "tier_id": "free",
        },
    )
    assert response.status_code == 202
    tenant_id = response.json()["tenant_id"]

    # 2. Verify slug is taken
    response = await client.get("/tenants/validate-slug?slug=e2e-test-tenant")
    assert response.json()["available"] is False

    # 3. Verify email (would need to extract token from email in real test)
    # Skipped in E2E — requires email integration

@pytest.mark.e2e
async def test_tenant_admin_dashboard(
    client: AsyncClient,
    test_tenant: dict,
    tenant_admin_token: str,
):
    """Test tenant admin dashboard endpoints."""
    tenant_id = test_tenant["id"]

    # Get settings
    response = await client.get(
        f"/tenants/{tenant_id}/settings",
        headers={"Authorization": f"Bearer {tenant_admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["id"] == tenant_id

    # Get usage
    response = await client.get(
        f"/tenants/{tenant_id}/usage?days=7",
        headers={"Authorization": f"Bearer {tenant_admin_token}"},
    )
    assert response.status_code == 200
    assert "api_calls" in response.json()

    # Get audit log
    response = await client.get(
        f"/tenants/{tenant_id}/audit-log",
        headers={"Authorization": f"Bearer {tenant_admin_token}"},
    )
    assert response.status_code == 200
    assert "events" in response.json()

    # Update settings
    response = await client.patch(
        f"/tenants/{tenant_id}/settings",
        json={"name": "Updated Name"},
        headers={"Authorization": f"Bearer {tenant_admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Name"

@pytest.mark.e2e
async def test_api_key_self_service(
    client: AsyncClient,
    test_tenant: dict,
    tenant_admin_token: str,
):
    """Test tenant admin API key management."""
    tenant_id = test_tenant["id"]

    # Create key
    response = await client.post(
        f"/tenants/{tenant_id}/api-keys",
        json={"name": "Test Key", "expires_in_days": 30},
        headers={"Authorization": f"Bearer {tenant_admin_token}"},
    )
    assert response.status_code == 201
    key_id = response.json()["id"]
    full_key = response.json()["key"]
    assert len(full_key) > 20  # Reasonable key length

    # List keys
    response = await client.get(
        f"/tenants/{tenant_id}/api-keys",
        headers={"Authorization": f"Bearer {tenant_admin_token}"},
    )
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["key_preview"].startswith("...")

    # Revoke key
    response = await client.delete(
        f"/tenants/{tenant_id}/api-keys/{key_id}",
        headers={"Authorization": f"Bearer {tenant_admin_token}"},
    )
    assert response.status_code == 200
```

---

## 5. Execution Order

| Step | Task | Dependencies |
|------|------|--------------|
| 1 | Task 3.1 | None |
| 2 | Task 3.2 | Task 3.1 |
| 3 | Task 3.4 | None (can parallel with 1-2) |
| 4 | Task 3.3 | Task 3.4 (needs async patterns) |
| 5 | Task 3.5 | Task 3.1, Task 3.4 |
| 6 | Task 3.6 | Task 3.2, Task 3.3 |
| 7 | Task 3.7 | Task 3.2 |
| 8 | Task 3.8 | All above |

---

## 6. Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| Email delivery failures | High | Retry queue; fallback notification in UI |
| Tier enforcement bypass | Critical | Security review; test all limit paths |
| Usage tracking overhead | Medium | Async audit emission; sampling if needed |
| Self-service abuse | Medium | Rate limiting on registration; CAPTCHA |

---

## 7. Acceptance Criteria

1. `POST /tenants/register` creates PENDING tenant, sends verification email
2. `POST /tenants/verify-email` triggers provisioning on valid token
3. `GET /tenants/tiers` returns public tier options
4. Tenant admins can view usage metrics via `/tenants/{id}/usage`
5. Tenant admins can view audit log via `/tenants/{id}/audit-log`
6. Tenant admins can update settings via `PATCH /tenants/{id}/settings`
7. Tenant admins can create/revoke API keys
8. Tier limits enforced (users, agents, API calls)
9. Email verification required before provisioning
10. E2E tests pass for all control plane flows

---

## 8. File Inventory

| Action | File | Description |
|--------|------|-------------|
| **Create** | `layer4-agents/src/tenants/tiers.py` | Tier configuration |
| **Create** | `layer4-agents/src/tenants/usage.py` | Usage tracking |
| **Create** | `layer4-agents/src/tenants/email_verification.py` | Email verification |
| **Create** | `layer4-agents/src/tenants/api/routes/registration.py` | Registration API |
| **Create** | `layer4-agents/src/tenants/api/routes/admin.py` | Admin dashboard API |
| **Create** | `tests/e2e/test_tenant_control_plane.py` | E2E tests |
| **Modify** | `shared/identity/middleware.py` | Add tier enforcement |
| **Modify** | `layer4-agents/src/tenants/api/routes/api_keys.py` | Enhanced key management |
| **Modify** | `shared/audit/` | Add usage tracking actions |

---

## 9. Post-Phase 3 State

After Phase 3 completion:

- ✅ Public tenant registration with email verification
- ✅ Tier-based limits enforced
- ✅ Usage metrics collected for billing preparation
- ✅ Tenant admin dashboard API complete
- ✅ API key self-service
- ✅ RLS-based isolation hardened (from Phase 1)
- ✅ Automated provisioning (from Phase 2)
- ✅ Ready for Phase 4+ schema-per-tenant consideration
- ✅ Billing integration deferred until monetization defined

---

## References

- `layer4-agents/src/tenants/provisioning.py` — Phase 2 provisioning
- `layer4-agents/src/tenants/models/tenant.py` — Tenant with `settings` JSON
- `shared/identity/middleware.py` — Governance middleware
- `shared/audit/` — Audit logging for usage tracking
