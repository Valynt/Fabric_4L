from __future__ import annotations

"""
Integration Service for managing CRM provider configurations.

Handles CRUD operations for integrations with credential encryption,
validation, and audit logging. Supports Salesforce and HubSpot.
"""
import asyncio
import json
import logging
import os
import re
import secrets
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from value_fabric.shared.models.typed_dict import TypedDictModel

from layer4_agents.integration.connectors.core.errors import (
    AuthError,
    CRMError,
    classify_http_status,
)
from layer4_agents.integration.connectors.core.state import (
    ErrorClass,
    ObservedStatus,
    apply_observation,
)
from layer4_agents.integration.connectors.factory import get_connector

from ..metrics import get_metrics
from ..models.account import CRMProvider
from ..models.crm_sync_job import CRMSyncJob, CRMSyncJobStatus
from ..models.integration import Integration
from .crm_sync_queue import enqueue_crm_sync_job
from .encryption_service import DEFAULT_KEY_ID, EncryptionService


class IntegrationService_trigger_syncResult(TypedDictModel):
    job_id: Any
    provider: Any
    queued_at: Any
    status: str
    sync_id: Any


class IntegrationService_test_connectionResult(TypedDictModel):
    error_code: str | None = None
    message: str
    success: bool


class IntegrationService__test_salesforce_connectionResult(TypedDictModel):
    details: dict[str, Any] | None = None
    error_code: str | None = None
    message: str
    success: bool


class IntegrationService__test_hubspot_connectionResult(TypedDictModel):
    details: dict[str, Any] | None = None
    error_code: str | None = None
    message: str
    success: bool


class IntegrationService__test_crm_connectionResult(TypedDictModel):
    error_code: str
    message: str
    success: bool


# CRM API endpoint constants
SALESFORCE_API_VERSION = "v58.0"
HUBSPOT_API_VERSION = "v3"

logger = logging.getLogger(__name__)

# URL validation pattern for instance URLs
_INSTANCE_URL_PATTERN = re.compile(
    r"^https?://"  # http:// or https://
    r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"  # domain
    r"localhost|"  # localhost
    r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # or ip
    r"(?::\d+)?"  # optional port
    r"(?:/?|[/?]\S+)$",
    re.IGNORECASE,
)


class IntegrationValidationError(ValueError):
    """Raised when integration configuration is invalid."""

    pass


class IntegrationNotFoundError(ValueError):
    """Raised when requested integration does not exist."""

    pass


class IntegrationService:
    """Service for managing CRM integration configurations.

    Handles:
    - CRUD operations with encrypted credential storage
    - Configuration validation
    - Connection testing
    - Audit logging
    """

    # Validation constants
    MIN_SYNC_INTERVAL = 5  # minutes
    MAX_SYNC_INTERVAL = 1440  # minutes (24 hours)
    MIN_BATCH_SIZE = 10
    MAX_BATCH_SIZE = 500

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _manual_salesforce_config_allowed() -> bool:
        env = (os.getenv("ENVIRONMENT") or os.getenv("APP_ENV") or "development").strip().lower()
        if env in {"", "local", "dev", "development", "test", "testing", "ci"}:
            return True
        flag = (os.getenv("ALLOW_SALESFORCE_MANUAL_CONFIG") or "").strip().lower()
        return flag in {"1", "true", "yes"}

    async def list_integrations(
        self, tenant_id: str, provider: CRMProvider | None = None
    ) -> list[Integration]:
        """List all integrations for a tenant.

        Args:
            tenant_id: Tenant identifier
            provider: Optional filter by provider type

        Returns:
            List of integration configurations (credentials excluded)
        """
        query = select(Integration).where(Integration.tenant_id == tenant_id)

        if provider:
            query = query.where(Integration.provider == provider)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_integration(self, tenant_id: str, provider: CRMProvider) -> Integration | None:
        """Get integration by tenant and provider.

        Args:
            tenant_id: Tenant identifier
            provider: CRM provider type

        Returns:
            Integration or None if not found
        """
        result = await self.db.execute(
            select(Integration).where(
                Integration.tenant_id == tenant_id,
                Integration.provider == provider,
            )
        )
        return result.scalar_one_or_none()

    async def create_or_update_integration(
        self,
        tenant_id: str,
        provider: CRMProvider,
        enabled: bool,
        credentials: dict[str, str],
        instance_url: str | None = None,
        sync_interval_minutes: int = 60,
        sync_batch_size: int = 100,
        user_id: str | None = None,
        salesforce_org_id: str | None = None,
    ) -> tuple[Integration, bool]:
        """Create or update an integration configuration.

        SECURITY: refresh_token is NOT accepted here. It is obtained
        exclusively via the OAuth callback flow and stored separately.

        Args:
            tenant_id: Tenant identifier
            provider: CRM provider (salesforce/hubspot)
            enabled: Whether integration is active
            credentials: Dict with api_key, api_secret, etc.
            instance_url: Optional CRM instance URL
            sync_interval_minutes: Sync frequency (5-1440)
            sync_batch_size: Records per batch (10-500)
            user_id: User making the change (for audit)
            salesforce_org_id: Salesforce organization ID

        Returns:
            Tuple of (Integration, is_created) where is_created is True for new integrations

        Raises:
            IntegrationValidationError: If configuration is invalid
        """
        # Check if integration exists
        existing = await self.get_integration(tenant_id, provider)
        is_update = existing is not None

        if provider == CRMProvider.SALESFORCE and not self._manual_salesforce_config_allowed():
            if not is_update:
                raise IntegrationValidationError(
                    "Salesforce manual credential entry is disabled. Use the OAuth connect flow."
                )
            if credentials.get("api_key") or credentials.get("api_secret"):
                raise IntegrationValidationError(
                    "Salesforce manual credential updates are disabled. Use the OAuth reconnect flow."
                )

        merged_credentials = dict(credentials)
        if (
            provider == CRMProvider.SALESFORCE
            and is_update
            and not merged_credentials.get("api_key")
        ):
            try:
                existing_credentials = await self.decrypt_credentials(existing)
            except asyncio.CancelledError:
                raise
            except Exception:
                existing_credentials = {}
            if existing_credentials.get("api_key"):
                merged_credentials["api_key"] = existing_credentials["api_key"]
            if not instance_url:
                instance_url = existing_credentials.get("instance_url") or existing.instance_url

        if is_update and not instance_url:
            instance_url = existing.instance_url

        # Validate configuration
        self._validate_config(
            enabled, merged_credentials, sync_interval_minutes, sync_batch_size, instance_url
        )

        # Preserve or generate webhook token
        if is_update:
            try:
                old_creds = await self.decrypt_credentials(existing)
                existing_webhook_token = old_creds.get("webhook_token")
            except asyncio.CancelledError:
                raise
            except Exception:
                existing_webhook_token = None
            if existing_webhook_token:
                merged_credentials["webhook_token"] = existing_webhook_token
            else:
                merged_credentials["webhook_token"] = secrets.token_hex(32)
        else:
            merged_credentials["webhook_token"] = secrets.token_hex(32)

        # Encrypt credentials
        credentials_json = json.dumps(merged_credentials)
        encrypted_creds = await EncryptionService.encrypt(credentials_json, key_id=DEFAULT_KEY_ID)

        if is_update:
            # Update existing
            existing.enabled = enabled
            existing.credentials_encrypted = encrypted_creds
            existing.encryption_key_id = DEFAULT_KEY_ID
            existing.instance_url = instance_url
            existing.sync_interval_minutes = sync_interval_minutes
            existing.sync_batch_size = sync_batch_size
            existing.updated_by = user_id
            if salesforce_org_id:
                existing.salesforce_org_id = salesforce_org_id
            # Reset status on config change via the reducer.
            await apply_observation(
                self.db,
                existing,
                ObservedStatus.IDLE,
            )
        else:
            # Create new
            existing = Integration(
                tenant_id=tenant_id,
                provider=provider,
                enabled=enabled,
                credentials_encrypted=encrypted_creds,
                encryption_key_id=DEFAULT_KEY_ID,
                instance_url=instance_url,
                salesforce_org_id=salesforce_org_id,
                sync_interval_minutes=sync_interval_minutes,
                sync_batch_size=sync_batch_size,
                created_by=user_id,
                updated_by=user_id,
            )
            self.db.add(existing)
            await apply_observation(self.db, existing, ObservedStatus.IDLE)

        await self.db.commit()
        await self.db.refresh(existing)

        logger.info(
            "Integration %s for tenant=%s provider=%s by user=%s",
            "updated" if is_update else "created",
            tenant_id,
            provider,
            user_id,
        )

        return existing, not is_update

    async def delete_integration(
        self, tenant_id: str, provider: CRMProvider, user_id: str | None = None
    ) -> bool:
        """Delete an integration configuration.

        Args:
            tenant_id: Tenant identifier
            provider: CRM provider type
            user_id: User making the deletion (for audit)

        Returns:
            True if deleted, False if not found
        """
        integration = await self.get_integration(tenant_id, provider)
        if not integration:
            return False

        await self.db.delete(integration)
        await self.db.commit()

        logger.info(
            "Integration deleted for tenant=%s provider=%s by user=%s",
            tenant_id,
            provider,
            user_id,
        )

        return True

    async def test_connection(self, tenant_id: str, provider: CRMProvider) -> dict[str, Any]:
        """Test the CRM connection using stored credentials.

        Args:
            tenant_id: Tenant identifier
            provider: CRM provider type

        Returns:
            Test result dict with success, message, and details
        """
        integration = await self.get_integration(tenant_id, provider)
        if not integration:
            return IntegrationService_test_connectionResult.model_validate(
                {
                    "success": False,
                    "message": f"No {provider.value} integration configured",
                    "error_code": "NOT_CONFIGURED",
                }
            )

        if not integration.enabled:
            return IntegrationService_test_connectionResult.model_validate(
                {
                    "success": False,
                    "message": "Integration is disabled",
                    "error_code": "DISABLED",
                }
            )

        try:
            creds_json = await EncryptionService.decrypt(
                integration.credentials_encrypted, integration.encryption_key_id
            )
            credentials = json.loads(creds_json)

            # Perform actual HTTP connection test through the provider connector.
            connector = get_connector(provider, credentials)
            test_result = await connector.test_connection()
            return IntegrationService_test_connectionResult.model_validate(test_result)

        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error("Connection test failed for %s: %s", provider, e)
            return IntegrationService_test_connectionResult.model_validate(
                {
                    "success": False,
                    "message": "CONNECTION_FAILED_ERROR",
                    "error_code": "CONNECTION_FAILED",
                }
            )

    async def _test_crm_connection(
        self,
        provider: CRMProvider,
        credentials: dict[str, str],
        instance_url: str | None,
    ) -> dict[str, Any]:
        """Test connection to CRM provider.

        Args:
            provider: CRM provider type
            credentials: Decrypted credentials dict
            instance_url: Optional CRM instance URL

        Returns:
            Test result dict with success, message, and details
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            if provider == CRMProvider.SALESFORCE:
                return await self._test_salesforce_connection(client, credentials, instance_url)
            elif provider == CRMProvider.HUBSPOT:
                return await self._test_hubspot_connection(client, credentials)
            else:
                return IntegrationService__test_crm_connectionResult.model_validate(
                    {
                        "success": False,
                        "message": f"Unsupported provider: {provider.value}",
                        "error_code": "UNSUPPORTED_PROVIDER",
                    }
                )

    async def _test_salesforce_connection(
        self,
        client: httpx.AsyncClient,
        credentials: dict[str, str],
        instance_url: str | None,
    ) -> dict[str, Any]:
        """Test Salesforce API connection using OAuth token.

        Args:
            client: HTTP client
            credentials: Must contain 'api_key' (OAuth access token)
            instance_url: Salesforce instance URL

        Returns:
            Connection test result
        """
        access_token = credentials.get("api_key")
        if not access_token:
            return IntegrationService__test_salesforce_connectionResult.model_validate(
                {
                    "success": False,
                    "message": "Missing OAuth access token in credentials",
                    "error_code": "MISSING_CREDENTIALS",
                }
            )

        # Use provided instance_url or construct from credentials
        base_url = instance_url or credentials.get("instance_url", "")
        if not base_url:
            return IntegrationService__test_salesforce_connectionResult.model_validate(
                {
                    "success": False,
                    "message": "Salesforce instance URL is required",
                    "error_code": "MISSING_INSTANCE_URL",
                }
            )

        try:
            # Test API access by querying Organization info (lightweight call)
            response = await client.get(
                f"{base_url}/services/data/{SALESFORCE_API_VERSION}/query/",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"q": "SELECT Name FROM Organization LIMIT 1"},
            )

            if response.status_code == 200:
                data = response.json()
                org_name = data.get("records", [{}])[0].get("Name", "Unknown")

                return IntegrationService__test_salesforce_connectionResult.model_validate(
                    {
                        "success": True,
                        "message": f"Connected to Salesforce: {org_name}",
                        "details": {
                            "accounts_accessible": True,
                            "opportunities_accessible": True,
                            "organization": org_name,
                            "api_version": SALESFORCE_API_VERSION,
                        },
                    }
                )

            elif response.status_code == 401:
                return IntegrationService__test_salesforce_connectionResult.model_validate(
                    {
                        "success": False,
                        "message": "Authentication failed - token may be expired",
                        "error_code": "AUTH_FAILED",
                    }
                )

            else:
                return IntegrationService__test_salesforce_connectionResult.model_validate(
                    {
                        "success": False,
                        "message": f"Salesforce API error: {response.status_code}",
                        "error_code": f"API_ERROR_{response.status_code}",
                    }
                )

        except httpx.TimeoutException:
            return IntegrationService__test_salesforce_connectionResult.model_validate(
                {
                    "success": False,
                    "message": "Connection timed out after 30 seconds",
                    "error_code": "TIMEOUT",
                }
            )

        except httpx.NetworkError:
            return IntegrationService__test_salesforce_connectionResult.model_validate(
                {
                    "success": False,
                    "message": "NETWORK_ERROR",
                    "error_code": "NETWORK_ERROR",
                }
            )

    async def _test_hubspot_connection(
        self,
        client: httpx.AsyncClient,
        credentials: dict[str, str],
    ) -> dict[str, Any]:
        """Test HubSpot API connection using API key.

        Args:
            client: HTTP client
            credentials: Must contain 'api_key' (HubSpot API key)

        Returns:
            Connection test result
        """
        api_key = credentials.get("api_key")
        if not api_key:
            return IntegrationService__test_hubspot_connectionResult.model_validate(
                {
                    "success": False,
                    "message": "Missing API key in credentials",
                    "error_code": "MISSING_CREDENTIALS",
                }
            )

        try:
            # Test API access by querying account info
            response = await client.get(
                f"https://api.hubapi.com/account-info/{HUBSPOT_API_VERSION}/details",
                headers={"Authorization": f"Bearer {api_key}"},
            )

            if response.status_code == 200:
                data = response.json()
                portal_name = data.get("portalName", "Unknown")

                return IntegrationService__test_hubspot_connectionResult.model_validate(
                    {
                        "success": True,
                        "message": f"Connected to HubSpot: {portal_name}",
                        "details": {
                            "accounts_accessible": True,
                            "opportunities_accessible": True,
                            "portal_name": portal_name,
                            "api_version": HUBSPOT_API_VERSION,
                        },
                    }
                )

            elif response.status_code == 401:
                return IntegrationService__test_hubspot_connectionResult.model_validate(
                    {
                        "success": False,
                        "message": "Authentication failed - API key may be invalid",
                        "error_code": "AUTH_FAILED",
                    }
                )

            else:
                return IntegrationService__test_hubspot_connectionResult.model_validate(
                    {
                        "success": False,
                        "message": f"HubSpot API error: {response.status_code}",
                        "error_code": f"API_ERROR_{response.status_code}",
                    }
                )

        except httpx.TimeoutException:
            return IntegrationService__test_hubspot_connectionResult.model_validate(
                {
                    "success": False,
                    "message": "Connection timed out after 30 seconds",
                    "error_code": "TIMEOUT",
                }
            )

        except httpx.NetworkError:
            return IntegrationService__test_hubspot_connectionResult.model_validate(
                {
                    "success": False,
                    "message": "NETWORK_ERROR",
                    "error_code": "NETWORK_ERROR",
                }
            )

    async def trigger_sync(
        self, tenant_id: str, provider: CRMProvider, user_id: str | None = None
    ) -> dict[str, Any]:
        """Trigger a manual sync for an integration.

        Args:
            tenant_id: Tenant identifier
            provider: CRM provider type
            user_id: User triggering sync (for audit)

        Returns:
            Sync job information
        """
        integration = await self.get_integration(tenant_id, provider)
        if not integration:
            raise IntegrationNotFoundError(f"No {provider.value} integration found")

        if not integration.enabled:
            raise IntegrationValidationError("Integration is disabled")

        queued_at_dt = datetime.now(UTC)
        queued_at = queued_at_dt.isoformat()

        # Mark as running/pending until the worker starts
        await apply_observation(self.db, integration, ObservedStatus.RUNNING)
        job = CRMSyncJob(
            tenant_id=tenant_id,
            provider=provider,
            status=CRMSyncJobStatus.QUEUED,
            requested_by=user_id,
            queued_at=queued_at_dt,
        )
        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)

        try:
            await enqueue_crm_sync_job(
                redis_client=None,
                job_id=str(job.id),
                tenant_id=tenant_id,
                provider=provider.value,
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            job.status = CRMSyncJobStatus.FAILED
            job.finished_at = datetime.now(UTC)
            job.error_summary = f"Failed to enqueue sync: {exc}"
            await apply_observation(
                self.db,
                integration,
                ObservedStatus.FAILURE,
                error_class=ErrorClass.TRANSIENT,
            )
            integration.last_error_message = f"Failed to enqueue sync: {exc}"
            await self.db.commit()
            raise IntegrationValidationError(f"Unable to queue sync: {exc}") from exc

        logger.info(
            "Sync queued for tenant=%s provider=%s sync_id=%s by user=%s",
            tenant_id,
            provider.value,
            str(job.id),
            user_id,
        )

        return IntegrationService_trigger_syncResult.model_validate(
            {
                "sync_id": str(job.id),
                "job_id": str(job.id),
                "status": "queued",
                "provider": provider.value,
                "queued_at": queued_at,
            }
        )

    async def list_sync_jobs(
        self,
        tenant_id: str,
        provider: CRMProvider,
        *,
        limit: int = 20,
    ) -> list[CRMSyncJob]:
        result = await self.db.execute(
            select(CRMSyncJob)
            .where(
                CRMSyncJob.tenant_id == tenant_id,
                CRMSyncJob.provider == provider,
            )
            .order_by(CRMSyncJob.queued_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_sync_job(
        self,
        tenant_id: str,
        provider: CRMProvider,
        job_id: str,
    ) -> CRMSyncJob | None:
        result = await self.db.execute(
            select(CRMSyncJob).where(
                CRMSyncJob.id == job_id,
                CRMSyncJob.tenant_id == tenant_id,
                CRMSyncJob.provider == provider,
            )
        )
        return result.scalar_one_or_none()

    def _validate_config(
        self,
        enabled: bool,
        credentials: dict[str, str],
        sync_interval: int,
        batch_size: int,
        instance_url: str | None = None,
    ) -> None:
        """Validate integration configuration.

        Raises:
            IntegrationValidationError: If any validation fails
        """
        if enabled:
            if not credentials.get("api_key"):
                raise IntegrationValidationError("api_key is required when enabled=True")

        if not (self.MIN_SYNC_INTERVAL <= sync_interval <= self.MAX_SYNC_INTERVAL):
            raise IntegrationValidationError(
                f"sync_interval_minutes must be between {self.MIN_SYNC_INTERVAL} and {self.MAX_SYNC_INTERVAL}"
            )

        if not (self.MIN_BATCH_SIZE <= batch_size <= self.MAX_BATCH_SIZE):
            raise IntegrationValidationError(
                f"sync_batch_size must be between {self.MIN_BATCH_SIZE} and {self.MAX_BATCH_SIZE}"
            )

        if instance_url:
            if not _INSTANCE_URL_PATTERN.match(instance_url):
                raise IntegrationValidationError(
                    f"instance_url must be a valid HTTP/HTTPS URL: {instance_url}"
                )
            # Require HTTPS for production URLs (allow HTTP only for localhost)
            # Match exact localhost or localhost with port (not localhost.something.com)
            localhost_prefix = "http://localhost"
            is_localhost_http = instance_url.startswith(localhost_prefix) and (
                len(instance_url) == len(localhost_prefix)
                or instance_url[len(localhost_prefix)] in (":", "/")
            )  # port, path, or exact match
            if instance_url.startswith("http://") and not is_localhost_http:
                raise IntegrationValidationError(
                    f"HTTPS is required for production URLs: {instance_url}"
                )

    async def decrypt_credentials(
        self, integration: Integration, *, tenant_id: str | None = None
    ) -> dict[str, str]:
        """Decrypt credentials for internal service use.

        Args:
            integration: Integration with encrypted credentials
            tenant_id: Optional authenticated tenant for ownership verification

        Returns:
            Decrypted credentials dict
        """
        if tenant_id is not None and str(integration.tenant_id) != str(tenant_id):
            raise IntegrationValidationError(
                "Integration tenant does not match authenticated tenant"
            )

        creds_json = await EncryptionService.decrypt(
            integration.credentials_encrypted, integration.encryption_key_id
        )
        return json.loads(creds_json)

    async def refresh_salesforce_token(self, integration: Integration) -> dict[str, str]:
        """Refresh Salesforce OAuth access token using refresh token.

        Args:
            integration: Integration with refresh_token_encrypted

        Returns:
            Updated credentials dict with new access token

        Raises:
            IntegrationValidationError: If refresh fails
        """
        if not integration.refresh_token_encrypted:
            raise IntegrationValidationError("No refresh token available for Salesforce")

        try:
            refresh_token = await EncryptionService.decrypt(
                integration.refresh_token_encrypted, integration.encryption_key_id
            )
        except asyncio.CancelledError:
            raise
        except Exception as e:
            raise IntegrationValidationError(f"Failed to decrypt refresh token: {e}") from e

        # Salesforce OAuth token endpoint
        instance_url = integration.instance_url or "https://login.salesforce.com"

        client_id = os.getenv("SALESFORCE_CLIENT_ID")
        client_secret = os.getenv("SALESFORCE_CLIENT_SECRET")

        from layer4_agents.integration.connectors.providers.salesforce.connector import (
            SalesforceConnector,
        )

        try:
            token_result = await SalesforceConnector.refresh_token(
                refresh_token=refresh_token,
                instance_url=instance_url,
                client_id=client_id,
                client_secret=client_secret,
            )
        except CRMError as e:
            classified = classify_http_status(getattr(e, "status_code", 0), str(e))
            logger.warning(
                "Salesforce OAuth credential renewal failed for tenant=%s error_class=%s",
                integration.tenant_id,
                type(classified).__name__,
            )
            error_cls = (
                ErrorClass.AUTH if isinstance(classified, AuthError) else ErrorClass.TRANSIENT
            )
            await apply_observation(
                self.db, integration, ObservedStatus.FAILURE, error_class=error_cls
            )
            integration.last_error_message = "Token refresh failed"
            await self.db.commit()
            prom = get_metrics()
            if prom:
                prom.increment_crm_salesforce_token_refresh_failed(integration.tenant_id)
            raise IntegrationValidationError("Token refresh failed") from e

        new_access_token = token_result["api_key"]
        new_instance_url = token_result.get("instance_url")

        # Update credentials with new access token
        credentials = await self.decrypt_credentials(integration)
        credentials["api_key"] = new_access_token
        if new_instance_url:
            credentials["instance_url"] = new_instance_url
            integration.instance_url = new_instance_url

        credentials_json = json.dumps(credentials)
        integration.credentials_encrypted = await EncryptionService.encrypt(
            credentials_json, key_id=integration.encryption_key_id
        )

        # Update refresh token if rotated
        new_refresh_token = token_result.get("refresh_token")
        if new_refresh_token:
            integration.refresh_token_encrypted = await EncryptionService.encrypt(
                new_refresh_token, key_id=integration.encryption_key_id
            )

        await apply_observation(self.db, integration, ObservedStatus.SUCCESS)
        integration.last_error_message = None
        await self.db.commit()

        logger.info(
            "Salesforce token refreshed for tenant=%s org=%s",
            integration.tenant_id,
            integration.salesforce_org_id or "unknown",
        )

        return credentials

    async def exchange_salesforce_oauth_code(
        self,
        *,
        code: str,
        redirect_uri: str,
        tenant_id: str,
        oauth_base_url: str | None = None,
    ) -> dict[str, Any]:
        """Exchange a Salesforce authorization code for OAuth tokens."""
        if not tenant_id:
            raise IntegrationValidationError("tenant_id is required for Salesforce OAuth exchange")

        client_id = os.getenv("SALESFORCE_CLIENT_ID")
        client_secret = os.getenv("SALESFORCE_CLIENT_SECRET")
        if not client_id or not client_secret:
            raise IntegrationValidationError(
                "SALESFORCE_CLIENT_ID and SALESFORCE_CLIENT_SECRET must be configured"
            )

        base_url = (
            oauth_base_url
            or os.getenv("SALESFORCE_OAUTH_BASE_URL")
            or "https://login.salesforce.com"
        ).rstrip("/")
        self._validate_config(
            enabled=False,
            credentials={},
            sync_interval=self.MIN_SYNC_INTERVAL,
            batch_size=self.MIN_BATCH_SIZE,
            instance_url=base_url,
        )
        token_url = f"{base_url}/services/oauth2/token"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                token_url,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri,
                },
            )

        if response.status_code != 200:
            raise IntegrationValidationError(
                f"Salesforce OAuth exchange failed: HTTP {response.status_code} - {response.text}"
            )

        token_data = response.json()
        if not token_data.get("access_token"):
            raise IntegrationValidationError("Salesforce OAuth response missing access_token")
        if not token_data.get("refresh_token"):
            raise IntegrationValidationError("Salesforce OAuth response missing refresh_token")
        if not token_data.get("instance_url"):
            raise IntegrationValidationError("Salesforce OAuth response missing instance_url")
        return token_data

    async def upsert_salesforce_oauth_integration(
        self,
        *,
        tenant_id: str,
        user_id: str | None,
        token_data: dict[str, Any],
    ) -> Integration:
        """Create or update a Salesforce integration from an OAuth token response."""
        access_token = str(token_data.get("access_token", "")).strip()
        refresh_token = str(token_data.get("refresh_token", "")).strip()
        instance_url = str(token_data.get("instance_url", "")).strip()
        salesforce_org_id = token_data.get("organization_id") or token_data.get("org_id")

        if not access_token or not refresh_token or not instance_url:
            raise IntegrationValidationError(
                "OAuth token response is missing required Salesforce values"
            )

        self._validate_config(
            enabled=True,
            credentials={"api_key": access_token},
            sync_interval=60,
            batch_size=100,
            instance_url=instance_url,
        )

        existing = await self.get_integration(tenant_id, CRMProvider.SALESFORCE)
        credentials = {
            "api_key": access_token,
            "instance_url": instance_url,
        }

        if existing:
            try:
                old_credentials = await self.decrypt_credentials(existing)
            except asyncio.CancelledError:
                raise
            except Exception:
                old_credentials = {}
            webhook_token = old_credentials.get("webhook_token")
            if webhook_token:
                credentials["webhook_token"] = webhook_token

        if "webhook_token" not in credentials:
            credentials["webhook_token"] = secrets.token_hex(32)

        encrypted_credentials = await EncryptionService.encrypt(
            json.dumps(credentials),
            key_id=DEFAULT_KEY_ID,
        )
        encrypted_refresh_token = await EncryptionService.encrypt(
            refresh_token,
            key_id=DEFAULT_KEY_ID,
        )

        if existing:
            existing.enabled = True
            existing.credentials_encrypted = encrypted_credentials
            existing.refresh_token_encrypted = encrypted_refresh_token
            existing.encryption_key_id = DEFAULT_KEY_ID
            existing.instance_url = instance_url
            existing.last_error_message = None
            await apply_observation(self.db, existing, ObservedStatus.SUCCESS)
            existing.updated_by = user_id
            if salesforce_org_id:
                existing.salesforce_org_id = str(salesforce_org_id)
            integration = existing
        else:
            integration = Integration(
                tenant_id=tenant_id,
                provider=CRMProvider.SALESFORCE,
                enabled=True,
                credentials_encrypted=encrypted_credentials,
                refresh_token_encrypted=encrypted_refresh_token,
                encryption_key_id=DEFAULT_KEY_ID,
                instance_url=instance_url,
                salesforce_org_id=str(salesforce_org_id) if salesforce_org_id else None,
                sync_interval_minutes=60,
                sync_batch_size=100,
                created_by=user_id,
                updated_by=user_id,
            )
            self.db.add(integration)
            await apply_observation(self.db, integration, ObservedStatus.SUCCESS)

        await self.db.commit()
        await self.db.refresh(integration)
        return integration
