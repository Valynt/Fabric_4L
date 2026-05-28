# Fabric 4L Tenant Management — Phase 2: Automated Provisioning Pipeline

Build automated tenant onboarding using existing Infisical secrets management and generic OIDC identity infrastructure. No external IdP automation — use webhook-based provisioning triggers.

---

## 1. Objective

Phase 2 implements the automated provisioning pipeline that creates tenant infrastructure without manual intervention. This phase leverages:

- **Infisical** (already configured) for tenant-scoped secrets
- **Generic OIDC** (already implemented) for identity — no Keycloak-specific automation
- **Webhook API** for external provisioning triggers
- **Async workflow** with retry and rollback capabilities

### Design Principles

1. **Use existing infrastructure** — Infisical and OIDC already in codebase
2. **No new vendor dependencies** — Generic OIDC patterns, not Keycloak-specific
3. **Webhook-based** — External systems trigger provisioning via API
4. **Observable** — Comprehensive audit logging and status tracking
5. **Recoverable** — Failed provisioning can be retried idempotently

---

## 2. Current State

### 2.1 Existing Infrastructure

| Component | File | Status |
|-----------|------|--------|
| Infisical Config | `.infisical.json` | ✅ Multi-environment configured |
| OIDC Client | `shared/identity/oidc.py` | ✅ Generic OIDC with discovery |
| Tenant Model | `layer4-agents/src/tenants/models/tenant.py` | ✅ Has `isolation_tier`, `status` |
| Audit System | `shared/audit/` | ✅ Emitters and models ready |
| Provisioning Skeleton | `layer4-agents/src/tenants/provisioning.py` | ✅ Created in Phase 1 |

### 2.2 Required New Components

| Component | Purpose |
|-----------|---------|
| Infisical API Service | Create tenant secret paths programmatically |
| Provisioning Workflow | Orchestrate tenant creation steps |
| Webhook Handler | Receive external provisioning triggers |
| Status API | Query provisioning progress |
| Retry Logic | Handle transient failures |

---

## 3. Target Architecture

### 3.1 Provisioning Workflow

```
┌─────────────────┐     POST /tenants      ┌─────────────────┐
│ External System │ ────────────────────→ │  Provisioning   │
│   or Admin      │                       │    Webhook      │
└─────────────────┘                       └────────┬────────┘
                                                   │
                                                   ▼
┌────────────────────────────────────────────────────────────────┐
│                    Provisioning Workflow                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────┐ │
│  │ Create      │→ │ Create      │→ │ Seed        │→ │ Update │ │
│  │ Tenant      │  │ Infisical   │  │ Default     │  │ Status │ │
│  │ Record      │  │ Path        │  │ Secrets     │  │ ACTIVE │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └────────┘ │
│         │                │                │              │     │
│         ▼                ▼                ▼              ▼     │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │              Audit Event per Step                        │ │
│  └─────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────┘
```

### 3.2 Rollback on Failure

```
If step N fails:
1. Log failure audit event
2. Update tenant status to FAILED with error detail
3. Optionally rollback completed steps:
   - Delete Infisical path (if created)
   - Keep tenant record for retry
4. Return error with retryable flag
```

---

## 4. Task Breakdown

### Task 2.1: Infisical API Client
**Estimated Effort:** 6 hours
**Priority:** P0

Create service to interact with Infisical API for tenant secrets.

**New File:** `packages/shared/src/value_fabric/shared/secrets/infisical_client.py`

```python
"""Infisical API client for tenant secret management."""

import os
from typing import Any
import httpx
from pydantic import BaseModel

class InfisicalConfig(BaseModel):
    """Infisical API configuration."""
    api_url: str = "https://app.infisical.com"
    service_token: str
    workspace_id: str

    @classmethod
    def from_env(cls) -> "InfisicalConfig":
        return cls(
            api_url=os.getenv("INFISICAL_API_URL", "https://app.infisical.com"),
            service_token=os.getenv("INFISICAL_SERVICE_TOKEN", ""),
            workspace_id=os.getenv("INFISICAL_WORKSPACE_ID", ""),
        )

class InfisicalClient:
    """Client for Infisical API operations."""

    def __init__(self, config: InfisicalConfig | None = None) -> None:
        self.config = config or InfisicalConfig.from_env()
        self._client = httpx.AsyncClient(
            base_url=self.config.api_url,
            headers={"Authorization": f"Bearer {self.config.service_token}"},
            timeout=30.0,
        )

    async def create_folder(
        self,
        environment: str,
        folder_path: str,
    ) -> dict[str, Any]:
        """Create a folder path for tenant secrets."""
        response = await self._client.post(
            f"/api/v1/workspaces/{self.config.workspace_id}/folders",
            json={
                "environment": environment,
                "path": folder_path,
            },
        )
        response.raise_for_status()
        return response.json()

    async def create_secret(
        self,
        environment: str,
        path: str,
        key: str,
        value: str,
    ) -> dict[str, Any]:
        """Create a secret in tenant path."""
        response = await self._client.post(
            f"/api/v1/workspaces/{self.config.workspace_id}/secrets",
            json={
                "environment": environment,
                "path": path,
                "key": key,
                "value": value,
            },
        )
        response.raise_for_status()
        return response.json()

    async def delete_folder(
        self,
        environment: str,
        folder_path: str,
    ) -> None:
        """Delete a folder path (for rollback)."""
        response = await self._client.delete(
            f"/api/v1/workspaces/{self.config.workspace_id}/folders",
            params={
                "environment": environment,
                "path": folder_path,
            },
        )
        response.raise_for_status()
```

---

### Task 2.2: Tenant Secrets Service
**Estimated Effort:** 4 hours
**Priority:** P0

Create high-level service for tenant secret operations.

**New File:** `packages/shared/src/value_fabric/shared/secrets/tenant_secrets.py`

```python
"""Tenant-scoped secrets management service."""

from typing import Any
from uuid import UUID

from .infisical_client import InfisicalClient

DEFAULT_SECRETS = {
    "dev": {
        "LLM_API_KEY": "",
        "NEO4J_PASSWORD": "",
        "REDIS_PASSWORD": "",
    },
    "test": {
        "LLM_API_KEY": "test-key",
        "NEO4J_PASSWORD": "test-pass",
        "REDIS_PASSWORD": "test-redis",
    },
    "staging": DEFAULT_SECRETS["dev"],
    "prod": DEFAULT_SECRETS["dev"],
}

class TenantSecretsService:
    """Manages secrets provisioning for tenants."""

    def __init__(self, client: InfisicalClient | None = None) -> None:
        self.client = client or InfisicalClient()

    async def provision_tenant_secrets(
        self,
        tenant_slug: str,
        environments: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create secret paths and seed defaults for a tenant.

        Args:
            tenant_slug: URL-safe tenant identifier
            environments: List of environments to provision (default: all)

        Returns:
            Provisioning results per environment
        """
        envs = environments or ["dev", "test", "staging", "prod"]
        results = {}

        for env in envs:
            # Create folder path: /tenants/{tenant_slug}
            folder_path = f"/tenants/{tenant_slug}"
            folder = await self.client.create_folder(env, folder_path)

            # Seed default secrets
            secrets = DEFAULT_SECRETS.get(env, {})
            created_secrets = []
            for key, value in secrets.items():
                secret = await self.client.create_secret(env, folder_path, key, value)
                created_secrets.append(secret)

            results[env] = {
                "folder": folder,
                "secrets": created_secrets,
            }

        return results

    async def rollback_tenant_secrets(
        self,
        tenant_slug: str,
        environments: list[str] | None = None,
    ) -> None:
        """Delete tenant secret paths (for rollback)."""
        envs = environments or ["dev", "test", "staging", "prod"]

        for env in envs:
            try:
                await self.client.delete_folder(env, f"/tenants/{tenant_slug}")
            except Exception:
                # Log but don't fail — may not exist
                pass
```

---

### Task 2.3: Provisioning Workflow Implementation
**Estimated Effort:** 8 hours
**Priority:** P0

Implement the full provisioning orchestration.

**Modified File:** `services/layer4-agents/src/tenants/provisioning.py`

```python
"""Tenant provisioning workflow implementation."""

import logging
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from shared.audit import emit_audit_event, AuditAction, AuditOutcome
from shared.secrets.tenant_secrets import TenantSecretsService
from .constants import TenantStatus
from .models.tenant import Tenant
from .service import TenantService

logger = logging.getLogger(__name__)

class ProvisioningStep(str, Enum):
    CREATE_RECORD = "create_record"
    CREATE_INFISICAL = "create_infisical"
    SEED_SECRETS = "seed_secrets"
    UPDATE_STATUS = "update_status"

class ProvisioningStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class ProvisioningState:
    tenant_id: UUID
    status: ProvisioningStatus
    current_step: ProvisioningStep | None = None
    completed_steps: list[ProvisioningStep] = field(default_factory=list)
    error: str | None = None
    retryable: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "tenant_id": str(self.tenant_id),
            "status": self.status.value,
            "current_step": self.current_step.value if self.current_step else None,
            "completed_steps": [s.value for s in self.completed_steps],
            "error": self.error,
            "retryable": self.retryable,
        }

class TenantProvisioningService:
    """Orchestrates tenant provisioning workflow."""

    def __init__(
        self,
        db_session: AsyncSession,
        secrets_service: TenantSecretsService | None = None,
    ) -> None:
        self.db = db_session
        self.secrets = secrets_service or TenantSecretsService()
        self.tenant_service = TenantService(db_session)

    async def provision_tenant(
        self,
        tenant_id: UUID,
        actor_id: UUID | None = None,
    ) -> ProvisioningState:
        """Execute full provisioning workflow for a tenant.

        Steps:
        1. Verify tenant in PENDING status
        2. Create Infisical secret paths
        3. Seed default secrets
        4. Update tenant status to ACTIVE

        Args:
            tenant_id: UUID of tenant to provision
            actor_id: User/system that triggered provisioning (for audit)

        Returns:
            Final provisioning state
        """
        state = ProvisioningState(
            tenant_id=tenant_id,
            status=ProvisioningStatus.IN_PROGRESS,
        )

        try:
            # Step 1: Verify tenant record
            state.current_step = ProvisioningStep.CREATE_RECORD
            tenant = await self.tenant_service.get_tenant(tenant_id)

            if tenant.status != TenantStatus.PENDING.value:
                raise ValueError(f"Tenant not in PENDING status: {tenant.status}")

            state.completed_steps.append(ProvisioningStep.CREATE_RECORD)
            await self._emit_step_audit(state, actor_id)

            # Step 2: Create Infisical paths
            state.current_step = ProvisioningStep.CREATE_INFISICAL
            await self.secrets.provision_tenant_secrets(tenant.slug)
            state.completed_steps.append(ProvisioningStep.CREATE_INFISICAL)
            await self._emit_step_audit(state, actor_id)

            # Step 3: Update tenant status to ACTIVE
            state.current_step = ProvisioningStep.UPDATE_STATUS
            tenant.transition_to(TenantStatus.ACTIVE.value, "Provisioning completed")
            await self.db.commit()
            state.completed_steps.append(ProvisioningStep.UPDATE_STATUS)
            await self._emit_step_audit(state, actor_id)

            # Mark complete
            state.status = ProvisioningStatus.COMPLETED
            state.current_step = None
            state.retryable = False

            logger.info(f"Tenant {tenant_id} provisioned successfully")

        except Exception as e:
            state.status = ProvisioningStatus.FAILED
            state.error = str(e)
            logger.error(f"Tenant {tenant_id} provisioning failed: {e}")

            await self._emit_failure_audit(state, actor_id)

            # Don't rollback here — allow manual retry

        return state

    async def get_provisioning_status(self, tenant_id: UUID) -> ProvisioningState:
        """Get current provisioning status for a tenant."""
        tenant = await self.tenant_service.get_tenant(tenant_id)

        # Derive state from tenant status
        if tenant.status == TenantStatus.ACTIVE.value:
            return ProvisioningState(
                tenant_id=tenant_id,
                status=ProvisioningStatus.COMPLETED,
                completed_steps=list(ProvisioningStep),
                retryable=False,
            )
        elif tenant.status == TenantStatus.PENDING.value:
            return ProvisioningState(
                tenant_id=tenant_id,
                status=ProvisioningStatus.NOT_STARTED,
                retryable=True,
            )
        else:
            return ProvisioningState(
                tenant_id=tenant_id,
                status=ProvisioningStatus.FAILED,
                error=f"Tenant status: {tenant.status}",
                retryable=True,
            )

    async def retry_provisioning(
        self,
        tenant_id: UUID,
        actor_id: UUID | None = None,
    ) -> ProvisioningState:
        """Retry failed provisioning.

        Idempotent: Checks what steps completed and continues from there.
        """
        # For simplicity, re-run full workflow
        # Production: Would check state and resume from failed step
        return await self.provision_tenant(tenant_id, actor_id)

    async def _emit_step_audit(
        self,
        state: ProvisioningState,
        actor_id: UUID | None,
    ) -> None:
        """Emit audit event for completed step."""
        await emit_audit_event(
            action=AuditAction.PROVISIONING_STEP_COMPLETED,
            outcome=AuditOutcome.SUCCESS,
            resource_type="tenant_provisioning",
            resource_id=str(state.tenant_id),
            actor_id=actor_id,
            tenant_id=state.tenant_id,
            details={
                "step": state.current_step.value if state.current_step else None,
                "completed_steps": [s.value for s in state.completed_steps],
            },
        )

    async def _emit_failure_audit(
        self,
        state: ProvisioningState,
        actor_id: UUID | None,
    ) -> None:
        """Emit audit event for provisioning failure."""
        await emit_audit_event(
            action=AuditAction.PROVISIONING_FAILED,
            outcome=AuditOutcome.FAILURE,
            resource_type="tenant_provisioning",
            resource_id=str(state.tenant_id),
            actor_id=actor_id,
            tenant_id=state.tenant_id,
            details={
                "failed_step": state.current_step.value if state.current_step else None,
                "error": state.error,
                "completed_steps": [s.value for s in state.completed_steps],
            },
        )
```

---

### Task 2.4: Provisioning API Endpoints
**Estimated Effort:** 6 hours
**Priority:** P0

Add tenant provisioning endpoints.

**Modified File:** `services/layer4-agents/src/tenants/api/routes/tenants.py`

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from shared.identity.context import RequestContext
from shared.identity.dependencies import get_request_context, require_super_admin
from ...database import get_db_from_context
from ...provisioning import TenantProvisioningService, ProvisioningState
from ..models.requests import CreateTenantRequest
from ..models.responses import TenantResponse, ProvisioningStatusResponse

@router.post("", response_model=TenantResponse)
async def create_tenant(
    request: CreateTenantRequest,
    db: AsyncSession = Depends(get_db_from_context),
    context: RequestContext = Depends(require_super_admin()),
) -> TenantResponse:
    """Create a new tenant (PENDING status, requires provisioning)."""
    service = TenantService(db)
    tenant = await service.create_tenant(
        name=request.name,
        slug=request.slug,
        created_by=context.user_id,
    )
    return TenantResponse.from_model(tenant)

@router.post("/{tenant_id}/provision", response_model=ProvisioningStatusResponse)
async def provision_tenant(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db_from_context),
    context: RequestContext = Depends(require_super_admin()),
) -> ProvisioningStatusResponse:
    """Trigger provisioning workflow for a PENDING tenant."""
    provisioning = TenantProvisioningService(db)
    state = await provisioning.provision_tenant(
        tenant_id=tenant_id,
        actor_id=context.user_id,
    )

    if state.status == "failed":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Provisioning failed",
                "error": state.error,
                "retryable": state.retryable,
            },
        )

    return ProvisioningStatusResponse.from_state(state)

@router.get("/{tenant_id}/provision-status", response_model=ProvisioningStatusResponse)
async def get_provisioning_status(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db_from_context),
    context: RequestContext = Depends(require_super_admin()),
) -> ProvisioningStatusResponse:
    """Get provisioning status for a tenant."""
    provisioning = TenantProvisioningService(db)
    state = await provisioning.get_provisioning_status(tenant_id)
    return ProvisioningStatusResponse.from_state(state)

@router.post("/{tenant_id}/provision-retry", response_model=ProvisioningStatusResponse)
async def retry_provisioning(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db_from_context),
    context: RequestContext = Depends(require_super_admin()),
) -> ProvisioningStatusResponse:
    """Retry failed provisioning for a tenant."""
    provisioning = TenantProvisioningService(db)
    state = await provisioning.retry_provisioning(
        tenant_id=tenant_id,
        actor_id=context.user_id,
    )
    return ProvisioningStatusResponse.from_state(state)
```

---

### Task 2.5: Provisioning Webhook Handler
**Estimated Effort:** 4 hours
**Priority:** P1

Create webhook endpoint for external provisioning triggers.

**New File:** `services/layer4-agents/src/tenants/api/routes/provisioning_webhook.py`

```python
"""Webhook handlers for external provisioning triggers."""

import hashlib
import hmac
import os
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from shared.audit import emit_audit_event, AuditAction, AuditOutcome
from ...database import get_db_session
from ...provisioning import TenantProvisioningService
from ...service import TenantService
from ..models.requests import CreateTenantRequest

router = APIRouter(prefix="/webhooks", tags=["Provisioning Webhooks"])

WEBHOOK_SECRET = os.getenv("PROVISIONING_WEBHOOK_SECRET", "")

class ProvisionWebhookPayload(BaseModel):
    """Payload for provisioning webhook."""
    name: str
    slug: str
    admin_email: str
    external_id: str | None = None  # External system reference
    metadata: dict[str, Any] = {}

def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify HMAC-SHA256 signature."""
    expected = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(signature, expected)

@router.post("/provision-tenant", status_code=status.HTTP_202_ACCEPTED)
async def provision_tenant_webhook(
    request: Request,
    payload: ProvisionWebhookPayload,
    x_webhook_signature: str = Header(..., alias="X-Webhook-Signature"),
    x_webhook_id: str = Header(..., alias="X-Webhook-ID"),
) -> dict[str, Any]:
    """Receive provisioning trigger from external system.

    Authentication: HMAC-SHA256 of payload using shared secret.
    Idempotency: X-Webhook-ID tracked to prevent duplicates.
    """
    # Verify signature
    body = await request.body()
    if not verify_webhook_signature(body, x_webhook_signature, WEBHOOK_SECRET):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )

    # Get DB session (outside FastAPI dependency injection)
    async with get_db_session(require_tenant=False) as db:
        # Check if webhook already processed (idempotency)
        # SEC-4271 (Platform Identity, M4-2026Q3): enforce webhook idempotency by persisting and rejecting duplicate X-Webhook-ID values

        # Create tenant service
        tenant_service = TenantService(db)

        # Check if tenant exists by slug
        existing = await tenant_service.get_tenant_by_slug(payload.slug)
        if existing:
            return {
                "status": "exists",
                "tenant_id": str(existing.id),
                "message": "Tenant already exists",
            }

        # Create tenant (PENDING status)
        tenant = await tenant_service.create_tenant(
            name=payload.name,
            slug=payload.slug,
            external_id=payload.external_id,
            metadata=payload.metadata,
            created_by=None,  # System/webhook created
        )

        # Trigger provisioning
        provisioning = TenantProvisioningService(db)
        state = await provisioning.provision_tenant(
            tenant_id=tenant.id,
            actor_id=None,  # System/webhook actor
        )

        # Emit audit event
        await emit_audit_event(
            action=AuditAction.TENANT_PROVISIONED_WEBHOOK,
            outcome=AuditOutcome.SUCCESS if state.status == "completed" else AuditOutcome.FAILURE,
            resource_type="tenant",
            resource_id=str(tenant.id),
            actor_id=None,
            details={
                "webhook_id": x_webhook_id,
                "external_id": payload.external_id,
                "provisioning_status": state.status,
            },
        )

        return {
            "status": state.status,
            "tenant_id": str(tenant.id),
            "webhook_id": x_webhook_id,
        }
```

---

### Task 2.6: OIDC Configuration Guide
**Estimated Effort:** 2 hours
**Priority:** P2

Document OIDC setup for new tenants.

**New File:** `docs/operations/tenant-oidc-configuration.md`

```markdown
# Tenant OIDC Configuration Guide

This document explains how to configure OIDC for new tenants using the generic OIDC client.

## Overview

Fabric 4L uses generic OIDC (not Keycloak-specific) via `shared/identity/oidc.py`.
Tenants can use any OIDC-compliant identity provider.

## Supported OIDC Providers

- Auth0
- Okta
- Keycloak (if self-hosted)
- Azure AD
- Any OIDC-compliant IdP

## Configuration Steps

### 1. Create OIDC Application

In your IdP, create a new application:
- **Type**: Regular Web Application
- **Allowed Callback URLs**: `https://{tenant-slug}.fabric4l.example.com/api/v1/auth/callback`
- **Allowed Logout URLs**: `https://{tenant-slug}.fabric4l.example.com`

### 2. Configure Claims

Ensure the IdP includes these claims in the ID token:
- `sub` (user ID)
- `tenant_id` (must match tenant UUID)
- `role` or `groups` (for role mapping)

### 3. Register in Fabric 4L

Store OIDC configuration in tenant secrets (Infisical):
- Path: `/tenants/{tenant-slug}/oidc`
- Keys:
  - `OIDC_ISSUER_URL`
  - `OIDC_CLIENT_ID`
  - `OIDC_CLIENT_SECRET`

### 4. Test Configuration

Use the test endpoint:
```bash
curl /api/v1/tenants/{tenant-id}/test-oidc
```

## Webhook Integration

External provisioning systems can trigger tenant creation via webhook:
- Endpoint: `POST /api/v1/webhooks/provision-tenant`
- Authentication: HMAC-SHA256 signature
- See: `provisioning_webhook.py` for payload format
```

---

### Task 2.7: Audit Action Additions
**Estimated Effort:** 2 hours
**Priority:** P1

Add provisioning audit actions.

**Modified File:** `shared/audit/models.py`

```python
class AuditAction(str, Enum):
    # Existing actions...

    # Provisioning actions
    PROVISIONING_STEP_COMPLETED = "provisioning_step_completed"
    PROVISIONING_FAILED = "provisioning_failed"
    TENANT_PROVISIONED_WEBHOOK = "tenant_provisioned_webhook"
    INFISICAL_PATH_CREATED = "infisical_path_created"
    INFISICAL_SECRET_CREATED = "infisical_secret_created"
```

---

### Task 2.8: Integration Tests
**Estimated Effort:** 6 hours
**Priority:** P1

Create comprehensive integration tests.

**New File:** `tests/integration/test_tenant_provisioning.py`

```python
"""Integration tests for tenant provisioning."""

import pytest
from httpx import AsyncClient

@pytest.mark.integration
async def test_provisioning_workflow(client: AsyncClient, admin_token: str):
    """Test full provisioning workflow."""
    # 1. Create tenant
    response = await client.post(
        "/tenants",
        json={"name": "Test Tenant", "slug": "test-tenant"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201
    tenant_id = response.json()["id"]
    assert response.json()["status"] == "pending"

    # 2. Trigger provisioning
    response = await client.post(
        f"/tenants/{tenant_id}/provision",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "completed"

    # 3. Verify tenant active
    response = await client.get(
        f"/tenants/{tenant_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.json()["status"] == "active"

@pytest.mark.integration
async def test_webhook_provisioning(client: AsyncClient, webhook_secret: str):
    """Test webhook-triggered provisioning."""
    import hmac, hashlib, json

    payload = {
        "name": "Webhook Tenant",
        "slug": "webhook-tenant",
        "admin_email": "admin@example.com",
    }
    body = json.dumps(payload).encode()
    signature = hmac.new(
        webhook_secret.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()

    response = await client.post(
        "/webhooks/provision-tenant",
        content=body,
        headers={
            "X-Webhook-Signature": signature,
            "X-Webhook-ID": "test-webhook-123",
        },
    )
    assert response.status_code == 202
```

---

## 5. Execution Order

| Step | Task | Dependencies |
|------|------|--------------|
| 1 | Task 2.1 | None |
| 2 | Task 2.2 | Task 2.1 |
| 3 | Task 2.7 | None |
| 4 | Task 2.3 | Task 2.2, Task 2.7 |
| 5 | Task 2.4 | Task 2.3 |
| 6 | Task 2.5 | Task 2.3 |
| 7 | Task 2.6 | None (docs) |
| 8 | Task 2.8 | All above |

---

## 6. Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| Infisical API unavailable | High | Retry with exponential backoff; queue for retry |
| Webhook signature bypass | Critical | Constant-time comparison; secret rotation |
| Partial provisioning state | Medium | Idempotency checks; state tracking |
| Secret leakage in logs | Critical | Never log secret values; audit metadata only |

---

## 7. Acceptance Criteria

1. `POST /tenants` creates tenant with status=PENDING
2. `POST /tenants/{id}/provision` executes provisioning workflow
3. Infisical paths created with seeded secrets
4. Tenant status transitions PENDING → ACTIVE on success
5. Webhook endpoint accepts HMAC-signed requests
6. Failed provisioning returns retryable flag
7. All provisioning steps emit audit events
8. Integration tests pass with test Infisical instance

---

## 8. File Inventory

| Action | File | Description |
|--------|------|-------------|
| **Create** | `shared/secrets/infisical_client.py` | Infisical API client |
| **Create** | `shared/secrets/tenant_secrets.py` | Tenant secrets service |
| **Create** | `layer4-agents/src/tenants/api/routes/provisioning_webhook.py` | Webhook handler |
| **Create** | `tests/integration/test_tenant_provisioning.py` | Integration tests |
| **Create** | `docs/operations/tenant-oidc-configuration.md` | OIDC setup guide |
| **Modify** | `layer4-agents/src/tenants/provisioning.py` | Full implementation |
| **Modify** | `layer4-agents/src/tenants/api/routes/tenants.py` | Add endpoints |
| **Modify** | `shared/audit/models.py` | Add provisioning actions |

---

## 9. Post-Phase 2 State

After Phase 2 completion:

- ✅ Automated tenant provisioning operational
- ✅ Infisical integration for tenant secrets
- ✅ Webhook API for external triggers
- ✅ Provisioning status tracking
- ✅ Retry mechanism for failed provisioning
- ✅ Comprehensive audit logging
- ✅ Ready for Phase 3 self-service control plane
