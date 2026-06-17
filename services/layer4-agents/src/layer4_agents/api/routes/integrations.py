from __future__ import annotations

import asyncio

from value_fabric.shared.error_handling.exceptions import (
    NotFoundError,
    ServiceUnavailableError,
    ValidationError,
)

"""
Integrations Management API Routes.

Provides CRUD operations for CRM provider configurations (Salesforce, HubSpot).
All credentials are encrypted at rest and never returned in API responses.
"""


import base64
import hashlib
import hmac
import json
import logging
import os
import time
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from uuid import UUID

from fastapi import APIRouter, Depends, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from value_fabric.shared.audit import AuditAction, AuditOutcome, emit_audit_event
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_authenticated

from ...database import get_db_from_context
from ...models.account import CRMProvider
from ...services.integration_service import (
    IntegrationNotFoundError,
    IntegrationService,
    IntegrationValidationError,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/integrations", tags=["Integrations"])

# -----------------------------------------------------------------------------
# Request / Response Schemas
# -----------------------------------------------------------------------------


class IntegrationConfig(BaseModel):
    """Integration configuration (no credentials - for responses)."""

    provider: str = Field(..., description="CRM provider: salesforce or hubspot")
    enabled: bool = Field(False, description="Whether integration is active")
    instance_url: str | None = Field(None, description="CRM instance URL")
    sync_interval_minutes: int = Field(60, ge=5, le=1440)
    sync_batch_size: int = Field(100, ge=10, le=500)


class IntegrationStatusResponse(IntegrationConfig):
    """Integration with sync status (response only)."""

    id: str = Field(..., description="Integration UUID")
    tenant_id: str = Field(..., description="Tenant identifier")
    last_sync_at: str | None = None
    last_successful_sync_at: str | None = None
    records_synced: int = 0
    records_updated: int = 0
    records_failed: int = 0
    status: str = "idle"
    last_error_message: str | None = None
    has_refresh_token: bool = False
    webhook_url: str | None = Field(None, description="Webhook URL with token (shown once on create/update)")
    created_at: str
    updated_at: str


class IntegrationCreateRequest(BaseModel):
    """Request to create/update an integration.

    SECURITY: Never accept access_token, refresh_token, or auth_code
    from frontend requests. Tokens are obtained via OAuth callback
    or internal service mechanisms only.
    """

    enabled: bool = Field(False, description="Whether to enable the integration")
    api_key: str | None = Field(None, description="API key/token for the CRM")
    api_secret: str | None = Field(None, description="API secret (if required)")
    instance_url: str | None = Field(None, description="CRM instance URL")
    sync_interval_minutes: int = Field(60)
    sync_batch_size: int = Field(100)
    salesforce_org_id: str | None = Field(None, description="Salesforce organization ID")

    @field_validator("sync_interval_minutes")
    @classmethod
    def validate_interval(cls, v: int) -> int:
        if not 5 <= v <= 1440:
            raise ValueError("sync_interval_minutes must be between 5 and 1440")
        return v

    @field_validator("sync_batch_size")
    @classmethod
    def validate_batch_size(cls, v: int) -> int:
        if not 10 <= v <= 500:
            raise ValueError("sync_batch_size must be between 10 and 500")
        return v


class IntegrationListResponse(BaseModel):
    """List of integrations response."""

    integrations: list[IntegrationStatusResponse]


class ConnectionTestResponse(BaseModel):
    """Connection test result."""

    success: bool
    message: str
    details: dict[str, Any] | None = None
    error_code: str | None = None


class SyncTriggerResponse(BaseModel):
    """Manual sync trigger response."""

    sync_id: str
    job_id: str
    status: str
    provider: str
    queued_at: str | None = None


class SalesforceOAuthAuthorizeRequest(BaseModel):
    """Request to start Salesforce OAuth."""

    return_to: str = Field(
        "/context/integrations?provider=salesforce",
        description="Relative frontend path to return to after OAuth completes",
    )

    @field_validator("return_to")
    @classmethod
    def validate_return_to(cls, value: str) -> str:
        if not value.startswith("/"):
            raise ValueError("return_to must be an application-relative path")
        return value


class SalesforceOAuthAuthorizeResponse(BaseModel):
    authorization_url: str
    authorize_url: str | None = Field(default=None, description="Deprecated compatibility alias")
    state_expires_at: str


class CRMSyncJobResponse(BaseModel):
    id: str
    tenant_id: str
    provider: str
    status: str
    requested_by: str | None = None
    queued_at: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    records_synced: int = 0
    records_updated: int = 0
    records_failed: int = 0
    error_summary: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class CRMSyncJobListResponse(BaseModel):
    jobs: list[CRMSyncJobResponse]


# -----------------------------------------------------------------------------
# Dependencies
# -----------------------------------------------------------------------------


def get_integration_service(
    db: AsyncSession = Depends(get_db_from_context),
) -> IntegrationService:
    """Dependency for integration service."""
    return IntegrationService(db)


_OAUTH_STATE_TTL_SECONDS = 600


def _state_secret() -> str:
    secret = os.getenv("SALESFORCE_OAUTH_STATE_SECRET") or os.getenv("JWT_SECRET")
    if not secret:
        raise IntegrationValidationError(
            "SALESFORCE_OAUTH_STATE_SECRET or JWT_SECRET must be configured for OAuth state signing"
        )
    return secret


def _api_base_url() -> str:
    return (os.getenv("PUBLIC_API_URL") or "http://localhost:8000").rstrip("/")


def _salesforce_redirect_uri() -> str:
    explicit = os.getenv("SALESFORCE_OAUTH_REDIRECT_URI")
    if explicit:
        return explicit
    return f"{_api_base_url()}/v1/integrations/salesforce/oauth/callback"


def _build_signed_state(*, tenant_id: str, user_id: str | None, return_to: str, oauth_base_url: str) -> str:
    payload = {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "return_to": return_to,
        "oauth_base_url": oauth_base_url,
        "iat": int(time.time()),
    }
    payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    encoded_payload = base64.urlsafe_b64encode(payload_json).decode("utf-8").rstrip("=")
    signature = hmac.new(
        _state_secret().encode("utf-8"),
        encoded_payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{encoded_payload}.{signature}"


def _decode_signed_state(state: str) -> dict[str, Any]:
    try:
        encoded_payload, provided_signature = state.split(".", 1)
    except ValueError as exc:
        raise IntegrationValidationError("Invalid OAuth state format") from exc

    expected_signature = hmac.new(
        _state_secret().encode("utf-8"),
        encoded_payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected_signature, provided_signature):
        raise IntegrationValidationError("Invalid OAuth state signature")

    padding = "=" * (-len(encoded_payload) % 4)
    payload_bytes = base64.urlsafe_b64decode((encoded_payload + padding).encode("utf-8"))
    payload = json.loads(payload_bytes.decode("utf-8"))
    tenant_id = payload.get("tenant_id", None)
    return_to = payload.get("return_to")
    oauth_base_url = payload.get("oauth_base_url")
    if not tenant_id or not isinstance(tenant_id, str):
        raise IntegrationValidationError("OAuth state is missing tenant mapping")
    try:
        UUID(tenant_id)
    except (TypeError, ValueError) as exc:
        raise IntegrationValidationError("OAuth state tenant mapping is invalid") from exc
    if not isinstance(return_to, str) or not return_to.startswith("/"):
        raise IntegrationValidationError("OAuth state return_to must be an application-relative path")
    if not isinstance(oauth_base_url, str) or not oauth_base_url.startswith("https://"):
        if not (isinstance(oauth_base_url, str) and oauth_base_url.startswith("http://localhost")):
            raise IntegrationValidationError("OAuth state provider base URL is invalid")
    issued_at = int(payload.get("iat", 0))
    if issued_at <= 0 or time.time() - issued_at > _OAUTH_STATE_TTL_SECONDS:
        raise IntegrationValidationError("OAuth state has expired")
    return payload


def _append_query_params(url: str, **params: str) -> str:
    parsed = urlparse(url)
    existing = dict(parse_qsl(parsed.query, keep_blank_values=True))
    existing.update(params)
    return urlunparse(parsed._replace(query=urlencode(existing)))


# -----------------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------------


@router.get("", response_model=IntegrationListResponse)
async def list_integrations(
    context: RequestContext = Depends(require_authenticated),
    service: IntegrationService = Depends(get_integration_service),
) -> IntegrationListResponse:
    """List all configured integrations for the tenant.

    Returns integrations without credentials (encrypted at rest).
    """
    tenant_id = str(context.tenant_id)
    integrations = await service.list_integrations(tenant_id)

    return IntegrationListResponse(
        integrations=[
            IntegrationStatusResponse(**integration.to_dict())
            for integration in integrations
        ]
    )


@router.get("/{provider}", response_model=IntegrationStatusResponse)
async def get_integration(
    provider: CRMProvider,
    context: RequestContext = Depends(require_authenticated),
    service: IntegrationService = Depends(get_integration_service),
) -> IntegrationStatusResponse:
    """Get a specific integration configuration.

    Args:
        provider: CRM provider (salesforce or hubspot)
    """
    tenant_id = str(context.tenant_id)
    integration = await service.get_integration(tenant_id, provider)

    if not integration:
        raise NotFoundError(message = str(f"No {provider.value} integration configured"))

    return IntegrationStatusResponse(**integration.to_dict())


@router.post("/{provider}", response_model=IntegrationStatusResponse)
async def create_or_update_integration(
    provider: CRMProvider,
    request: IntegrationCreateRequest,
    context: RequestContext = Depends(require_authenticated),
    service: IntegrationService = Depends(get_integration_service),
) -> IntegrationStatusResponse:
    """Create or update an integration configuration.

    Args:
        provider: CRM provider (salesforce or hubspot)
        request: Integration configuration with credentials

    Notes:
        - Credentials are encrypted at rest using AES-256
        - Credentials are never returned in API responses
        - Audit logged for all changes
    """
    tenant_id = str(context.tenant_id)
    x_user_id = context.user_id

    # Build credentials dict
    credentials: dict[str, str] = {}
    if request.api_key:
        credentials["api_key"] = request.api_key
    if request.api_secret:
        credentials["api_secret"] = request.api_secret
    if request.instance_url:
        credentials["instance_url"] = request.instance_url

    try:
        integration, is_created = await service.create_or_update_integration(
            tenant_id=tenant_id,
            provider=provider,
            enabled=request.enabled,
            credentials=credentials,
            instance_url=request.instance_url,
            sync_interval_minutes=request.sync_interval_minutes,
            sync_batch_size=request.sync_batch_size,
            user_id=x_user_id,
            salesforce_org_id=request.salesforce_org_id,
        )

        # Emit audit event (best-effort, log failure but don't fail request)
        try:
            await emit_audit_event(
                action=AuditAction.CREATE if is_created else AuditAction.UPDATE,
                resource_type="integration",
                resource_id=str(integration.id),
                tenant_id=tenant_id,
                user_id=x_user_id,
                outcome=AuditOutcome.SUCCESS,
                details={"provider": provider.value, "enabled": request.enabled, "is_created": is_created},
            )
        except asyncio.CancelledError:
            raise
        except Exception as audit_error:
            logger.error(
                "Audit event failed for integration %s: %s",
                integration.id,
                audit_error,
                exc_info=True,
            )

        # Build webhook URL with token for one-time display
        response_data = integration.to_dict()
        try:
            decrypted = await service.decrypt_credentials(integration, tenant_id=tenant_id)
            webhook_token = decrypted.get("webhook_token")
            if webhook_token:
                # SECURITY: Only include token in create/update response, never in list/get
                base_url = os.getenv("PUBLIC_API_URL", "https://localhost:3000")
                response_data["webhook_url"] = (
                    f"{base_url}/v1/webhooks/crm/{provider.value}"
                    f"?tenant_id={tenant_id}&webhook_token={webhook_token}"
                )
        except asyncio.CancelledError:
            raise
        except Exception:
            # Don't fail the request if webhook URL generation fails
            pass

        return IntegrationStatusResponse(**response_data)

    except IntegrationValidationError as e:
        logger.warning("integration_validation_error", extra={"error": repr(e)})
        raise ValidationError(message = "Invalid integration request")


@router.delete("/{provider}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_integration(
    provider: CRMProvider,
    context: RequestContext = Depends(require_authenticated),
    service: IntegrationService = Depends(get_integration_service),
) -> None:
    """Delete an integration configuration.

    Args:
        provider: CRM provider (salesforce or hubspot)
    """
    tenant_id = str(context.tenant_id)
    x_user_id = context.user_id
    deleted = await service.delete_integration(tenant_id, provider, user_id=x_user_id)

    if not deleted:
        raise NotFoundError(message = str(f"No {provider.value} integration found"))

    # Emit audit event (best-effort, log failure but don't fail request)
    try:
        await emit_audit_event(
            action=AuditAction.DELETE,
            resource_type="integration",
            resource_id=f"{tenant_id}:{provider.value}",
            tenant_id=tenant_id,
            user_id=x_user_id,
            outcome=AuditOutcome.SUCCESS,
            details={"provider": provider.value},
        )
    except asyncio.CancelledError:
        raise
    except Exception as audit_error:
        logger.error(
            "Audit event failed for deleted integration %s:%s: %s",
            tenant_id,
            provider.value,
            audit_error,
            exc_info=True,
        )


@router.post("/{provider}/test", response_model=ConnectionTestResponse)
async def test_integration_connection(
    provider: CRMProvider,
    context: RequestContext = Depends(require_authenticated),
    service: IntegrationService = Depends(get_integration_service),
) -> ConnectionTestResponse:
    """Test the connection to a CRM provider.

    Uses stored credentials to verify connectivity.
    """
    tenant_id = str(context.tenant_id)
    result = await service.test_connection(tenant_id, provider)
    return ConnectionTestResponse(**result)


@router.post("/{provider}/sync", response_model=SyncTriggerResponse)
async def trigger_sync(
    provider: CRMProvider,
    context: RequestContext = Depends(require_authenticated),
    service: IntegrationService = Depends(get_integration_service),
) -> SyncTriggerResponse:
    """Trigger a manual sync for an integration.

    Args:
        provider: CRM provider (salesforce or hubspot)
    """
    tenant_id = str(context.tenant_id)
    x_user_id = context.user_id
    try:
        result = await service.trigger_sync(tenant_id, provider, user_id=x_user_id)

        # Emit audit event (best-effort, log failure but don't fail request)
        try:
            await emit_audit_event(
                action=AuditAction.CREATE,
                resource_type="sync_job",
                resource_id=result["sync_id"],
                tenant_id=tenant_id,
                user_id=x_user_id,
                outcome=AuditOutcome.SUCCESS,
                details={"provider": provider.value, "sync_id": result["sync_id"]},
            )
        except asyncio.CancelledError:
            raise
        except Exception as audit_error:
            logger.error(
                "Audit event failed for sync job %s: %s",
                result["sync_id"],
                audit_error,
                exc_info=True,
            )

        return SyncTriggerResponse(**result)

    except IntegrationNotFoundError as e:
        logger.warning("integration_not_found", extra={"error": repr(e)})
        raise NotFoundError(message = "Integration not found")
    except IntegrationValidationError as e:
        logger.warning("integration_validation_error", extra={"error": repr(e)})
        raise ValidationError(message = "Invalid integration request")


@router.get("/{provider}/sync-jobs", response_model=CRMSyncJobListResponse)
async def list_sync_jobs(
    provider: CRMProvider,
    limit: int = 20,
    context: RequestContext = Depends(require_authenticated),
    service: IntegrationService = Depends(get_integration_service),
) -> CRMSyncJobListResponse:
    tenant_id = str(context.tenant_id)
    jobs = await service.list_sync_jobs(tenant_id, provider, limit=limit)
    return CRMSyncJobListResponse(jobs=[CRMSyncJobResponse(**job.to_dict()) for job in jobs])


@router.get("/{provider}/sync-jobs/{job_id}", response_model=CRMSyncJobResponse)
async def get_sync_job(
    provider: CRMProvider,
    job_id: str,
    context: RequestContext = Depends(require_authenticated),
    service: IntegrationService = Depends(get_integration_service),
) -> CRMSyncJobResponse:
    tenant_id = str(context.tenant_id)
    job = await service.get_sync_job(tenant_id, provider, job_id)
    if not job:
        raise NotFoundError(message = str(f"No sync job {job_id} found for {provider.value}"))
    return CRMSyncJobResponse(**job.to_dict())


async def _build_salesforce_oauth_response(
    request: SalesforceOAuthAuthorizeRequest,
    context: RequestContext,
) -> SalesforceOAuthAuthorizeResponse:
    """Generate the Salesforce OAuth authorize URL for the current tenant."""
    tenant_id = str(context.tenant_id)
    client_id = os.getenv("SALESFORCE_CLIENT_ID")
    if not client_id:
        raise ServiceUnavailableError(message = "Salesforce OAuth is not configured")
    oauth_base_url = (os.getenv("SALESFORCE_OAUTH_BASE_URL") or "https://login.salesforce.com").rstrip("/")
    state = _build_signed_state(
        tenant_id=tenant_id,
        user_id=str(context.user_id) if context.user_id is not None else None,
        return_to=request.return_to,
        oauth_base_url=oauth_base_url,
    )

    authorize_url = (
        f"{oauth_base_url}/services/oauth2/authorize?"
        + urlencode(
            {
                "response_type": "code",
                "client_id": client_id,
                "redirect_uri": _salesforce_redirect_uri(),
                "state": state,
            }
        )
    )
    expires_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() + _OAUTH_STATE_TTL_SECONDS))
    return SalesforceOAuthAuthorizeResponse(
        authorization_url=authorize_url,
        authorize_url=authorize_url,
        state_expires_at=expires_at,
    )


@router.post("/salesforce/oauth/start", response_model=SalesforceOAuthAuthorizeResponse)
async def start_salesforce_oauth(
    request: SalesforceOAuthAuthorizeRequest,
    context: RequestContext = Depends(require_authenticated),
) -> SalesforceOAuthAuthorizeResponse:
    """Canonical Salesforce OAuth start route."""
    return await _build_salesforce_oauth_response(request, context)


@router.post(
    "/salesforce/oauth/authorize",
    response_model=SalesforceOAuthAuthorizeResponse,
    deprecated=True,
)
async def start_salesforce_oauth_compat(
    request: SalesforceOAuthAuthorizeRequest,
    context: RequestContext = Depends(require_authenticated),
) -> SalesforceOAuthAuthorizeResponse:
    """Deprecated compatibility alias for the old OAuth start route."""
    return await _build_salesforce_oauth_response(request, context)


@router.get("/salesforce/oauth/callback", include_in_schema=False)
async def complete_salesforce_oauth(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
    service: IntegrationService = Depends(get_integration_service),
) -> RedirectResponse:
    """Complete the Salesforce OAuth exchange and redirect back to the frontend."""
    if error:
        destination = _append_query_params(
            "/context/integrations?provider=salesforce",
            oauth_status="error",
            error=error,
        )
        if error_description:
            destination = _append_query_params(destination, error_description=error_description)
        return RedirectResponse(destination, status_code=status.HTTP_303_SEE_OTHER)

    if not code or not state:
        raise ValidationError(message = "code and state are required")

    try:
        decoded_state = _decode_signed_state(state)
        tenant_id = decoded_state["tenant_id"]
        token_data = await service.exchange_salesforce_oauth_code(
            code=code,
            redirect_uri=_salesforce_redirect_uri(),
            oauth_base_url=decoded_state["oauth_base_url"],
            tenant_id=tenant_id,
        )
        await service.upsert_salesforce_oauth_integration(
            tenant_id=tenant_id,
            user_id=decoded_state.get("user_id"),
            token_data=token_data,
        )
    except IntegrationValidationError as exc:
        destination = _append_query_params(
            decoded_state.get("return_to", "/context/integrations?provider=salesforce") if "decoded_state" in locals() else "/context/integrations?provider=salesforce",
            oauth_status="error",
            error_type=type(exc).__name__,
        )
        return RedirectResponse(destination, status_code=status.HTTP_303_SEE_OTHER)

    destination = _append_query_params(
        decoded_state["return_to"],
        oauth_status="connected",
        provider="salesforce",
    )
    return RedirectResponse(destination, status_code=status.HTTP_303_SEE_OTHER)
