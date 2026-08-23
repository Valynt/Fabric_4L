from __future__ import annotations

import asyncio

from value_fabric.shared.error_handling.exceptions import (
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    ValidationError,
)

"""
CRM Webhook handlers for real-time updates from Salesforce and HubSpot.

Handles push notifications when accounts are created/updated in CRM,
triggering immediate sync to keep Account records fresh.
"""


import hashlib
import hmac
import json
import logging
import os
from typing import Any

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    Header,
    Query,
    Request,
    status,
)
from pydantic import BaseModel, Field, TypeAdapter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from value_fabric.shared.audit import AuditAction, AuditOutcome, emit_audit_event
from value_fabric.shared.error_handling import sanitize_log_error
from value_fabric.shared.models.typed_dict import TypedDictModel
from value_fabric.shared.probes import normalize_probe_payload

# SECURITY: CRM webhook endpoints are server-to-server calls from
# Salesforce/HubSpot. Authentication is via HMAC signature verification,
# not JWT. get_db (no tenant context) is intentional here.
from ...database import get_db_from_context
from ...models.account import CRMProvider
from ...models.integration import Integration
from ...services.crm_sync_service import CRMSyncService
from ...services.integration_service import IntegrationService


class _handle_webhook_errorResult(TypedDictModel):
    audit_event_id: Any
    error_type: Any
    provider: Any
    status: str


class webhook_healthResult(TypedDictModel):
    status: str
    webhooks: list[Any]


class salesforce_webhookResult(TypedDictModel):
    event_type: Any
    provider: str
    record_id: Any
    status: str


class hubspot_webhookResult(TypedDictModel):
    companies_to_sync: Any
    events_processed: Any
    provider: str
    status: str


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks/crm", tags=["CRM Webhooks"])

# Header constants for webhook signature verification
SALESFORCE_SIGNATURE_HEADER = "X-Salesforce-Signature"
HUBSPOT_SIGNATURE_HEADER = "X-HubSpot-Signature"
HUBSPOT_SIGNATURE_V3_HEADER = "X-HubSpot-Signature-v3"

# App state attribute names for webhook secrets
SALESFORCE_WEBHOOK_SECRET_ATTR = "salesforce_webhook_secret"
HUBSPOT_WEBHOOK_SECRET_ATTR = "hubspot_webhook_secret"

_TRUE_VALUES = ("true", "1", "yes", "on")
_DEV_RELAXED_TENANT_FLAG = "CRM_WEBHOOKS_ALLOW_DEV_RELAXED_TENANT_RESOLUTION"


# CONTRACT §2.5: Pydantic schemas for webhook payload validation
class SalesforceSObject(BaseModel):
    """Salesforce sObject in outbound message."""

    Id: str | None = None
    Name: str | None = None


class SalesforceNotification(BaseModel):
    """Salesforce outbound message notification wrapper."""

    sObject: SalesforceSObject = Field(default_factory=SalesforceSObject)  # noqa: N815


class SalesforcePayloadData(BaseModel):
    """Salesforce platform event data wrapper."""

    payload: dict[str, Any] = Field(default_factory=dict)


class SalesforceWebhookPayload(BaseModel):
    """Unified schema for Salesforce webhook payloads.

    Supports both:
    - Platform events: {"data": {"payload": {"ChangeEventHeader": {...}}}}
    - Outbound messages: {"Notification": {"sObject": {"Id": "..."}}}
    """

    Notification: SalesforceNotification | None = None
    data: SalesforcePayloadData | None = None
    # Allow extra fields for flexibility
    model_config = {"extra": "allow"}


class HubSpotWebhookEvent(BaseModel):
    """Single HubSpot webhook subscription event.

    HubSpot sends arrays of these events for object changes.
    """

    eventId: int | None = None  # noqa: N815
    subscriptionId: int | None = None  # noqa: N815
    portalId: int | None = None  # noqa: N815
    occurredAt: int | None = None  # noqa: N815
    subscriptionType: str = ""  # noqa: N815
    objectId: int | None = None  # noqa: N815
    propertyName: str | None = None  # noqa: N815
    propertyValue: str | None = None  # noqa: N815
    # Allow extra fields for future compatibility
    model_config = {"extra": "allow"}


# ============================================================================
# Webhook Authentication Helpers
# ============================================================================


def _flag_enabled(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in _TRUE_VALUES


def _is_production_env() -> bool:
    return os.getenv("ENVIRONMENT", os.getenv("APP_ENV", "development")).lower() in {
        "production",
        "prod",
    }


def _allow_dev_relaxed_tenant_resolution() -> bool:
    return not _is_production_env() and _flag_enabled(_DEV_RELAXED_TENANT_FLAG, False)


def _build_signature(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


async def _decrypt_integration_credentials(integration: Integration) -> dict[str, Any]:
    from ...services.encryption_service import EncryptionService

    try:
        decrypted = await EncryptionService.decrypt(
            integration.credentials_encrypted,
            integration.encryption_key_id,
        )
        credentials = json.loads(decrypted)
        return credentials if isinstance(credentials, dict) else {}
    except asyncio.CancelledError:
        raise
    except Exception:
        return {}


async def _emit_dev_relaxed_mode_audit(
    *,
    request: Request,
    provider: CRMProvider,
    tenant_id: str,
    resolution_mode: str,
) -> None:
    try:
        await emit_audit_event(
            action="crm_webhook_dev_relaxed_tenant_resolution",
            outcome=AuditOutcome.SUCCESS,
            tenant_id=tenant_id,
            resource=f"crm_webhook:{provider.value}",
            details={
                "provider": provider.value,
                "resolution_mode": resolution_mode,
                "warning": (
                    "Development-only CRM webhook tenant fallback was used. "
                    "Disable it outside local development."
                ),
                "request_id": getattr(request.state, "request_id", None),
            },
        )
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.warning(
            "Failed to emit audit event for relaxed CRM webhook tenant resolution",
            exc_info=True,
            extra={"tenant_id": tenant_id, "provider": provider.value},
        )


async def _resolve_integration_from_token(
    *,
    db: AsyncSession,
    provider: CRMProvider,
    provided_token: str | None,
) -> Integration | None:
    if not provided_token:
        return None

    result = await db.execute(
        select(Integration).where(
            Integration.provider == provider,
            Integration.enabled.is_(True),
        )
    )

    matched_integration: Integration | None = None
    for integration in result.scalars().all():
        credentials = await _decrypt_integration_credentials(integration)
        stored_token = credentials.get("webhook_token")
        if isinstance(stored_token, str) and hmac.compare_digest(
            stored_token, provided_token
        ):
            if matched_integration is not None:
                logger.warning(
                    "CRM webhook token matched multiple integrations; refusing relaxed dev resolution",
                    extra={"provider": provider.value},
                )
                raise AuthenticationError(message="Invalid webhook credentials")
            matched_integration = integration

    return matched_integration


async def _resolve_webhook_integration(
    *,
    request: Request,
    db: AsyncSession,
    provider: CRMProvider,
    tenant_id: str | None,
    provided_token: str | None,
) -> tuple[Integration, bool]:
    integration_service = IntegrationService(db)

    if tenant_id:
        integration = await integration_service.get_integration(tenant_id, provider)
        if not integration:
            logger.warning(
                "%s webhook rejected: no %s integration for tenant=%s",
                provider.value.capitalize(),
                provider.value.capitalize(),
                tenant_id,
            )
            raise NotFoundError(
                message=str(
                    f"No {provider.value.capitalize()} integration configured for tenant {tenant_id}"
                )
            )
        if not integration.enabled:
            logger.warning(
                "%s webhook rejected: %s integration disabled for tenant=%s",
                provider.value.capitalize(),
                provider.value.capitalize(),
                tenant_id,
            )
            raise AuthorizationError(
                message=str(
                    f"{provider.value.capitalize()} integration is disabled for this tenant"
                )
            )
        return integration, False

    if not _allow_dev_relaxed_tenant_resolution():
        logger.warning(
            "%s webhook rejected: tenant_id query parameter is required",
            provider.value.capitalize(),
        )
        raise ValidationError(message="tenant_id query parameter is required")

    integration = await _resolve_integration_from_token(
        db=db,
        provider=provider,
        provided_token=provided_token,
    )
    if not integration:
        logger.warning(
            "%s webhook rejected: dev relaxed mode could not resolve tenant from authenticated token",
            provider.value.capitalize(),
        )
        raise AuthenticationError(message="Invalid webhook credentials")

    logger.warning(
        "%s webhook resolved tenant=%s via development-only relaxed token binding. "
        "Set %s=false outside local development.",
        provider.value.capitalize(),
        integration.tenant_id,
        _DEV_RELAXED_TENANT_FLAG,
    )
    await _emit_dev_relaxed_mode_audit(
        request=request,
        provider=provider,
        tenant_id=integration.tenant_id,
        resolution_mode="token_without_tenant_id",
    )
    return integration, True


def _verify_webhook_token(integration: Integration, provided_token: str | None) -> bool:
    """Verify webhook token using constant-time comparison.

    SECURITY:
        - Uses hmac.compare_digest to prevent timing attacks.
        - Never logs the provided or stored token.
        - Returns False if no token is configured (fail-closed).
    """
    if not provided_token:
        return False

    # Extract webhook_token from decrypted credentials
    # Note: this is called after integration lookup but before sync.
    # The caller is responsible for having the integration object ready.
    _stored_token = None
    if integration and integration.credentials_encrypted:
        # We can't decrypt here (async context needed), so the caller
        # must pass the decrypted token. This signature is kept for
        # interface compatibility; the actual check is in _authenticate_webhook.
        pass
    return False


async def _authenticate_webhook(
    integration: Integration,
    provided_token: str | None,
    provided_signature: str | None,
    body: bytes,
    app_state_webhook_secret: str | None,
) -> tuple[dict[str, Any], str]:
    """Authenticate a CRM webhook using token + optional HMAC signature.

    Raises:
       : 401 if authentication fails.
    """
    creds = await _decrypt_integration_credentials(integration)
    stored_webhook_token = creds.get("webhook_token")

    # Primary auth: per-tenant webhook token (constant-time comparison)
    token_valid = False
    if isinstance(stored_webhook_token, str) and provided_token:
        token_valid = hmac.compare_digest(stored_webhook_token, provided_token)

    if not token_valid:
        if (
            _allow_dev_relaxed_tenant_resolution()
            and app_state_webhook_secret
            and provided_signature
        ):
            expected = _build_signature(app_state_webhook_secret, body)
            if hmac.compare_digest(expected, provided_signature):
                logger.warning(
                    "Webhook authenticated via development-only signature fallback for tenant=%s provider=%s. "
                    "Configure per-tenant webhook_token and tenant_id binding outside local development.",
                    integration.tenant_id,
                    integration.provider,
                )
                return creds, "dev_signature_fallback"
        logger.warning(
            "Webhook authentication failed for tenant=%s provider=%s",
            integration.tenant_id,
            integration.provider,
        )
        raise AuthenticationError(message="Invalid webhook credentials")

    # Secondary auth: HMAC signature verification (defense-in-depth)
    if app_state_webhook_secret and provided_signature:
        expected = _build_signature(app_state_webhook_secret, body)
        if not hmac.compare_digest(expected, provided_signature):
            logger.warning(
                "Webhook HMAC signature mismatch for tenant=%s provider=%s",
                integration.tenant_id,
                integration.provider,
            )
            raise AuthenticationError(message="Invalid webhook signature")
    return creds, "token"


def _collect_nested_values(node: Any, keys: set[str]) -> set[str]:
    values: set[str] = set()
    if isinstance(node, dict):
        for key, value in node.items():
            if key in keys and value is not None:
                values.add(str(value))
            values.update(_collect_nested_values(value, keys))
    elif isinstance(node, list):
        for item in node:
            values.update(_collect_nested_values(item, keys))
    return values


def _validate_webhook_metadata(
    *,
    provider: CRMProvider,
    integration: Integration,
    credentials: dict[str, Any],
    payload: Any,
) -> None:
    if provider == CRMProvider.SALESFORCE and integration.salesforce_org_id:
        payload_org_ids = _collect_nested_values(
            payload,
            {"organizationId", "OrganizationId", "orgId", "OrgId"},
        )
        if payload_org_ids and integration.salesforce_org_id not in payload_org_ids:
            logger.warning(
                "Salesforce webhook org mismatch for tenant=%s expected_org=%s actual_orgs=%s",
                integration.tenant_id,
                integration.salesforce_org_id,
                sorted(payload_org_ids),
            )
            raise AuthenticationError(message="Invalid webhook tenant binding")

    if provider == CRMProvider.HUBSPOT:
        configured_portal_id = (
            credentials.get("portal_id")
            or credentials.get("portalId")
            or credentials.get("hub_id")
            or credentials.get("hubId")
        )
        payload_portal_ids = _collect_nested_values(payload, {"portalId", "portal_id"})
        if configured_portal_id is not None and payload_portal_ids:
            if str(configured_portal_id) not in payload_portal_ids:
                logger.warning(
                    "HubSpot webhook portal mismatch for tenant=%s expected_portal=%s actual_portals=%s",
                    integration.tenant_id,
                    configured_portal_id,
                    sorted(payload_portal_ids),
                )
                raise AuthenticationError(message="Invalid webhook tenant binding")


# ============================================================================
# Salesforce Webhooks
# ============================================================================


@router.post(
    "/salesforce",
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        401: {"description": "Invalid webhook credentials or signature"},
    },
)
async def salesforce_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    tenant_id: str | None = Query(
        None, description="Tenant identifier for multi-tenant webhook routing"
    ),
    webhook_token: str | None = Query(
        None, description="Per-tenant webhook token for authentication"
    ),
    x_webhook_token: str | None = Header(None, alias="X-Webhook-Token"),
    x_salesforce_signature: str | None = Header(
        None, alias=SALESFORCE_SIGNATURE_HEADER
    ),
    db: AsyncSession = Depends(get_db_from_context),
) -> dict[str, Any]:
    """Handle Salesforce outbound message or platform event webhook.

    Salesforce sends notifications when Accounts, Opportunities, or Contacts
    are created/updated. We trigger incremental sync for affected records.

    **Tenant Binding:**
    Configure the Salesforce outbound message URL with
    `?tenant_id=<your-tenant-id>&webhook_token=<token>`.
    The handler requires an authenticated tenant-bound integration for normal
    operation and only allows tenant-free local development flows behind an
    explicit development-only flag.

    Headers:
        X-Webhook-Token: Per-tenant opaque token (preferred)
        X-Salesforce-Signature: HMAC signature (defense-in-depth)

    Request Body:
        Salesforce platform event or outbound message payload
    """
    provided_token = x_webhook_token or webhook_token
    integration, tenant_resolved_without_query = await _resolve_webhook_integration(
        request=request,
        db=db,
        provider=CRMProvider.SALESFORCE,
        tenant_id=tenant_id,
        provided_token=provided_token,
    )
    effective_tenant_id = integration.tenant_id

    # Read body once and cache for both signature verification and JSON parsing
    body = await request.body()

    # Authenticate webhook using the resolved tenant integration
    app_state_secret = getattr(request.app.state, SALESFORCE_WEBHOOK_SECRET_ATTR, None)
    credentials, auth_mode = await _authenticate_webhook(
        integration,
        provided_token=provided_token,
        provided_signature=x_salesforce_signature,
        body=body,
        app_state_webhook_secret=app_state_secret,
    )
    if auth_mode != "token":
        await _emit_dev_relaxed_mode_audit(
            request=request,
            provider=CRMProvider.SALESFORCE,
            tenant_id=effective_tenant_id,
            resolution_mode=auth_mode,
        )

    # CONTRACT §2.5: Parse and validate webhook payload with Pydantic schema
    try:
        payload_str = body.decode()
        data = SalesforceWebhookPayload.model_validate_json(payload_str).model_dump()
    except asyncio.CancelledError:
        raise
    except Exception as e:
        logger.warning(
            "Salesforce webhook received invalid payload",
            extra={
                "error_code": "WEBHOOK_PARSE_ERROR",
                "error": sanitize_log_error(e),
                "body_preview": body[:200].decode(errors="replace"),
            },
        )
        data = {
            "raw_body": body.decode(errors="replace"),
            "parse_error": "Webhook payload parse failed",
        }

    # Extract record info from Salesforce payload
    # Platform events: {"data": {"payload": {"RecordId": "...", "ChangeEventHeader": {...}}}}
    # Outbound messages: {"Notification": {"sObject": {"Id": "...", ...}}}

    record_id = _extract_salesforce_record_id(data)
    event_type = _extract_salesforce_event_type(data)
    _validate_webhook_metadata(
        provider=CRMProvider.SALESFORCE,
        integration=integration,
        credentials=credentials,
        payload=data,
    )

    logger.info(
        "Salesforce webhook: %s for record %s tenant=%s",
        event_type,
        record_id,
        effective_tenant_id,
        extra={
            "tenant_resolution_mode": (
                "query_tenant_id"
                if not tenant_resolved_without_query
                else "dev_relaxed_token"
            ),
            "auth_mode": auth_mode,
        },
    )

    # Trigger sync for the affected record
    sync_service = CRMSyncService(db)

    try:
        if record_id:
            # Sync specific account
            await sync_service.sync_provider(
                CRMProvider.SALESFORCE,
                tenant_id=effective_tenant_id,
                incremental=True,
                account_ids=[record_id],
            )
            logger.info(
                "Triggered sync for Salesforce account %s tenant=%s",
                record_id,
                effective_tenant_id,
            )
        else:
            # No specific record - trigger general incremental sync
            await sync_service.sync_provider(
                CRMProvider.SALESFORCE,
                tenant_id=effective_tenant_id,
                incremental=True,
            )
            logger.info(
                "Triggered general Salesforce incremental sync tenant=%s",
                effective_tenant_id,
            )

        return salesforce_webhookResult.model_validate(
            {
                "status": "accepted",
                "provider": "salesforce",
                "event_type": event_type,
                "record_id": record_id,
                "tenant_id": effective_tenant_id,
            }
        ).model_dump()

    except asyncio.CancelledError:
        raise
    except Exception as e:
        return _handle_webhook_error(
            logger,
            e,
            "salesforce",
            record_id=record_id,
            event_type=event_type,
            request_id=getattr(request.state, "request_id", None),
        )


def _extract_salesforce_record_id(data: dict) -> str | None:
    """Extract record ID from Salesforce webhook payload."""
    # Platform Event format
    if "data" in data and "payload" in data["data"]:
        payload = data["data"]["payload"]
        # Change Data Capture format
        if "ChangeEventHeader" in payload:
            record_ids = payload["ChangeEventHeader"].get("recordIds", [])
            return record_ids[0] if record_ids else None
        # Custom platform event with RecordId
        return payload.get("RecordId") or payload.get("recordId")

    # Outbound Message format
    if "Notification" in data:
        notification = data["Notification"]
        if "sObject" in notification:
            return notification["sObject"].get("Id")

    # Generic sObject format
    return data.get("Id") or data.get("recordId") or data.get("RecordId")


def _extract_salesforce_event_type(data: dict) -> str:
    """Extract event type from Salesforce webhook payload."""
    if "data" in data and "payload" in data["data"]:
        payload = data["data"]["payload"]
        if "ChangeEventHeader" in payload:
            return payload["ChangeEventHeader"].get("entityName", "unknown")

    if "Notification" in data:
        notification = data["Notification"]
        if "sObject" in notification:
            obj_type = notification["sObject"].get("type", "unknown")
            return f"{obj_type}_update"

    return "unknown"


def _handle_webhook_error(
    logger: logging.Logger,
    error: Exception,
    provider: str,
    *,
    record_id: str | None = None,
    event_type: str = "unknown",
    event_count: int = 0,
    companies_to_sync: int = 0,
    request_id: str | None = None,
) -> dict[str, Any]:
    """Handle webhook processing error with audit logging.

    Returns a 202 Accepted response to prevent CRM retry storms,
    while emitting an audit event for observability.
    """
    extra = {"provider": provider, "error_type": type(error).__name__}
    if request_id:
        extra["request_id"] = request_id
    if record_id:
        extra["record_id"] = record_id
    if event_count:
        extra["event_count"] = event_count

    logger.error(
        f"Failed to process {provider} webhook: {type(error).__name__}",
        extra={**extra, "error_type": type(error).__name__},
    )

    # Build resource_id based on provider and available context
    resource_id = record_id or f"{provider}_{event_count}_events"

    # Build details dict with only relevant fields
    # Note: error_type only (not str(error)) to prevent leaking sensitive data
    details: dict[str, Any] = {
        "provider": provider,
        "error_type": type(error).__name__,
    }
    if event_type != "unknown":
        details["event_type"] = event_type
    if record_id:
        details["record_id"] = record_id
    if event_count:
        details["event_count"] = event_count
    if companies_to_sync:
        details["companies_to_sync"] = companies_to_sync

    event = emit_audit_event(
        AuditAction.WEBHOOK_PROCESSING_FAILED,
        resource_type="CRM_Webhook",
        resource_id=resource_id,
        outcome=AuditOutcome.FAILURE,
        details=details,
    )

    return _handle_webhook_errorResult.model_validate(
        {
            "status": "error",
            "provider": provider,
            "error_type": type(error).__name__,
            "audit_event_id": str(event.id),
        }
    ).model_dump()


# ============================================================================
# HubSpot Webhooks
# ============================================================================


@router.post(
    "/hubspot",
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        401: {"description": "Invalid webhook credentials or signature"},
    },
)
async def hubspot_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    tenant_id: str | None = Query(
        None, description="Tenant identifier for multi-tenant webhook routing"
    ),
    webhook_token: str | None = Query(
        None, description="Per-tenant webhook token for authentication"
    ),
    x_webhook_token: str | None = Header(None, alias="X-Webhook-Token"),
    x_hubspot_signature: str | None = Header(None, alias=HUBSPOT_SIGNATURE_HEADER),
    x_hubspot_signature_v3: str | None = Header(
        None, alias=HUBSPOT_SIGNATURE_V3_HEADER
    ),
    db: AsyncSession = Depends(get_db_from_context),
) -> dict[str, Any]:
    """Handle HubSpot webhook for contact/company/deal changes.

    HubSpot sends notifications when objects are created, updated, or deleted.
    We trigger incremental sync for affected company (account) records.

    **Tenant Binding:**
    Configure the HubSpot webhook URL with
    `?tenant_id=<your-tenant-id>&webhook_token=<token>`.
    The handler requires an authenticated tenant-bound integration for normal
    operation and only allows tenant-free local development flows behind an
    explicit development-only flag.

    Headers:
        X-Webhook-Token: Per-tenant opaque token (preferred)
        X-HubSpot-Signature: Legacy signature (optional)
        X-HubSpot-Signature-v3: v3 signature for verification (optional)

    Request Body:
        Array of subscription notification events:
        [
            {
                "eventId": 123,
                "subscriptionId": 456,
                "portalId": 789,
                "occurredAt": 1234567890,
                "subscriptionType": "company.propertyChange",
                "objectId": 987654321,
                "propertyName": "name",
                "propertyValue": "New Company Name"
            }
        ]
    """
    provided_token = x_webhook_token or webhook_token
    integration, tenant_resolved_without_query = await _resolve_webhook_integration(
        request=request,
        db=db,
        provider=CRMProvider.HUBSPOT,
        tenant_id=tenant_id,
        provided_token=provided_token,
    )
    effective_tenant_id = integration.tenant_id

    # Read body once and cache for both signature verification and JSON parsing
    body = await request.body()

    # Authenticate webhook using the resolved tenant integration
    app_state_secret = getattr(request.app.state, HUBSPOT_WEBHOOK_SECRET_ATTR, None)
    provided_signature = x_hubspot_signature_v3 or x_hubspot_signature
    credentials, auth_mode = await _authenticate_webhook(
        integration,
        provided_token=provided_token,
        provided_signature=provided_signature,
        body=body,
        app_state_webhook_secret=app_state_secret,
    )
    if auth_mode != "token":
        await _emit_dev_relaxed_mode_audit(
            request=request,
            provider=CRMProvider.HUBSPOT,
            tenant_id=effective_tenant_id,
            resolution_mode=auth_mode,
        )

    # CONTRACT §2.5: Parse and validate HubSpot events with Pydantic schema
    try:
        payload_str = body.decode()
        # HubSpot sends arrays of events
        events_adapter = TypeAdapter(list[HubSpotWebhookEvent])
        events_data = events_adapter.validate_json(payload_str)
        events = [e.model_dump() for e in events_data]
    except asyncio.CancelledError:
        raise
    except Exception as e:
        logger.warning(f"HubSpot webhook received invalid payload: {e}")
        raise ValidationError(message="Invalid JSON payload") from e
    _validate_webhook_metadata(
        provider=CRMProvider.HUBSPOT,
        integration=integration,
        credentials=credentials,
        payload=events,
    )

    # Collect unique company IDs to sync
    company_ids = set()
    event_count = 0

    for event in events:
        # Skip non-dict events (malformed payload protection)
        if not isinstance(event, dict):
            logger.warning(f"Skipping non-dict event in HubSpot webhook: {type(event)}")
            continue

        event_count += 1
        subscription_type = event.get("subscriptionType", "")
        object_id = event.get("objectId")

        # Validate subscription_type is string before .lower()
        if not isinstance(subscription_type, str):
            logger.warning(
                f"Skipping event with non-string subscriptionType: {type(subscription_type)}"
            )
            continue

        # Handle company events directly
        if "company" in subscription_type.lower() and object_id:
            company_ids.add(str(object_id))

        # Handle deal events - we need to find associated company
        elif "deal" in subscription_type.lower() and object_id:
            # Deal events require looking up the associated company
            # We'll trigger a general sync to pick up deal changes
            pass

    logger.info(
        "HubSpot webhook: %s events, %s unique companies tenant=%s",
        event_count,
        len(company_ids),
        effective_tenant_id,
        extra={
            "tenant_resolution_mode": (
                "query_tenant_id"
                if not tenant_resolved_without_query
                else "dev_relaxed_token"
            ),
            "auth_mode": auth_mode,
        },
    )

    # Trigger sync
    sync_service = CRMSyncService(db)

    try:
        if company_ids:
            # Sync specific companies
            await sync_service.sync_provider(
                CRMProvider.HUBSPOT,
                tenant_id=effective_tenant_id,
                incremental=True,
                account_ids=list(company_ids),
            )
            logger.info(
                "Triggered sync for %s HubSpot companies tenant=%s",
                len(company_ids),
                effective_tenant_id,
            )
        else:
            # No specific companies - trigger general incremental sync
            await sync_service.sync_provider(
                CRMProvider.HUBSPOT,
                tenant_id=effective_tenant_id,
                incremental=True,
            )
            logger.info(
                "Triggered general HubSpot incremental sync tenant=%s",
                effective_tenant_id,
            )

        return hubspot_webhookResult.model_validate(
            {
                "status": "accepted",
                "provider": "hubspot",
                "events_processed": event_count,
                "companies_to_sync": len(company_ids),
                "tenant_id": effective_tenant_id,
            }
        ).model_dump()

    except asyncio.CancelledError:
        raise
    except Exception as e:
        return _handle_webhook_error(
            logger,
            e,
            "hubspot",
            event_count=event_count,
            companies_to_sync=len(company_ids),
            request_id=getattr(request.state, "request_id", None),
        )


# ============================================================================
# Health Check
# ============================================================================


@router.get("/health")
async def webhook_health() -> dict[str, Any]:
    """Health check endpoint for webhook monitoring."""
    payload = normalize_probe_payload(
        status="healthy",
        service="layer4-agents",
        extra={"webhooks": ["salesforce", "hubspot"]},
    )
    return webhook_healthResult.model_validate(payload).model_dump()
