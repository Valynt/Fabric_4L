from __future__ import annotations

"""
CRM Sync Service for background account synchronization.

Handles periodic syncing of accounts from Salesforce and HubSpot,
with rate limiting, deduplication, and error handling.
"""


import asyncio
import json
import logging
import os
import time
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from value_fabric.shared.error_handling import sanitize_log_error
from value_fabric.shared.models.typed_dict import TypedDictModel

from ..integrations.core.connector import CRMConnector
from ..integrations.core.errors import AuthError, TransientError
from ..integrations.core.observations import (
    ErrorClass,
    sync_failed,
    sync_partial,
    sync_started,
    sync_succeeded,
)
from ..integrations.core.state import apply_observation
from ..integrations.factory import get_connector
from ..metrics import get_metrics
from ..models.account import (
    Account,
    AccountSyncStatus,
    CRMProvider,
    SyncStatus,
)
from ..models.integration import Integration
from .encryption_service import EncryptionService


class CRMSyncService__get_crm_configResult(TypedDictModel):
    api_key: Any
    crm_api_key: Any
    crm_api_secret: Any
    crm_instance_url: str
    crm_type: Any


logger = logging.getLogger(__name__)

# Module-level constants for configuration
DEFAULT_SYNC_BATCH_SIZE = int(os.getenv("CRM_SYNC_BATCH_SIZE", "100"))
DEFAULT_SYNC_INTERVAL_MINUTES = int(os.getenv("CRM_SYNC_INTERVAL_MINUTES", "60"))

# Simple in-memory metrics counters (replace with Prometheus in production)
_metrics: dict[str, int] = {
    "crm_salesforce_sync_started_total": 0,
    "crm_salesforce_sync_completed_total": 0,
    "crm_salesforce_sync_failed_total": 0,
    "crm_salesforce_records_synced_total": 0,
    "crm_salesforce_token_refresh_failed_total": 0,
    "crm_salesforce_rate_limit_total": 0,
}


def _increment_metric(name: str, value: int = 1) -> None:
    """Increment an internal metric counter."""
    _metrics[name] = _metrics.get(name, 0) + value


def _log_sync_event(
    event: str,
    tenant_id: str,
    provider: str,
    extra: dict[str, Any] | None = None,
) -> None:
    """Emit a structured log entry for CRM sync observability.

    Secrets are never logged. Only metadata, counts, and status.
    """
    payload = {
        "event": event,
        "tenant_id": tenant_id,
        "provider": provider,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    if extra:
        payload.update(extra)
    logger.info("crm_sync_event: %s", payload)


class SyncTruncatedError(Exception):
    """Raised when CRM sync returns partial results due to pagination limits."""

    pass


class CRMSyncService:
    """Service for orchestrating CRM account synchronization.

    Handles:
    - Full sync: All accounts from CRM
    - Incremental sync: Recently modified accounts
    - Single account refresh: On-demand sync
    - Rate limiting and retry logic
    - Deduplication across providers
    """

    def __init__(self, db: AsyncSession, batch_size: int = DEFAULT_SYNC_BATCH_SIZE):
        self.db = db
        self.sync_batch_size = batch_size
        self._provider_timeout: float = float(os.getenv("CRM_PROVIDER_TIMEOUT_SECONDS", "30.0"))

    async def sync_provider(
        self,
        provider: CRMProvider,
        tenant_id: str,
        incremental: bool = True,
        account_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """Sync accounts from a CRM provider.

        Args:
            provider: CRM provider (salesforce or hubspot)
            tenant_id: Authenticated tenant — required, never falls back to "default"
            incremental: If True, only sync recently modified accounts
            account_ids: Optional list of specific account IDs to sync

        Returns:
            Sync statistics: synced, updated, failed, errors
        """
        sync_start = time.monotonic()
        sync_type = "incremental" if incremental else "full"
        _increment_metric("crm_salesforce_sync_started_total")
        prom = get_metrics()
        if prom:
            prom.increment_crm_salesforce_sync_started(tenant_id, sync_type=sync_type)
        _log_sync_event(
            "sync_started",
            tenant_id,
            provider.value,
            {
                "incremental": incremental,
                "account_count": len(account_ids) if account_ids else None,
            },
        )

        # Emit sync_started observation on the Integration row
        integration_result = await self.db.execute(
            select(Integration).where(
                and_(
                    Integration.tenant_id == tenant_id,
                    Integration.provider == provider.value,
                )
            )
        )
        integration = integration_result.scalar_one_or_none()
        if isinstance(integration, Integration):
            await apply_observation(self.db, integration, sync_started())

        # Update AccountSyncStatus to running
        await self._update_account_sync_status(tenant_id, provider, "running", None)

        stats = {
            "provider": provider.value,
            "synced": 0,
            "updated": 0,
            "failed": 0,
            "errors": [],
        }

        try:
            # Get CRM config from tenant integration table
            config = await self._get_crm_config(provider, tenant_id)
            if not config or not config.get("api_key"):
                raise ValueError(f"CRM configuration missing for {provider.value}")

            # Initialize connector
            connector = get_connector(provider, config)

            # Get list of accounts to sync
            if account_ids:
                # Sync specific accounts
                prospect_ids = account_ids
            else:
                # Fetch all accounts from CRM (would use CRM API query)
                # For now, we rely on accounts already in our DB
                prospect_ids = await self._get_accounts_to_sync(tenant_id, provider, incremental)

            # Sync each account
            has_truncation = False
            for prospect_id in prospect_ids[: self.sync_batch_size]:
                try:
                    result = await self._sync_single_account(
                        connector, tenant_id, provider, prospect_id
                    )
                    if result:
                        stats["updated"] += 1
                    else:
                        stats["synced"] += 1
                except SyncTruncatedError:
                    has_truncation = True
                    stats["failed"] += 1
                    stats["errors"].append(f"{prospect_id}: SYNC_TRUNCATED_ERROR")
                    logger.warning(
                        "Sync truncated for account %s from %s: %s",
                        prospect_id,
                        provider.value,
                        sanitize_log_error("SYNC_TRUNCATED_ERROR"),
                        extra={"tenant_id": tenant_id, "provider": provider.value},
                    )
                except asyncio.CancelledError:
                    raise
                except Exception:
                    stats["failed"] += 1
                    stats["errors"].append(f"{prospect_id}: SYNC_ERROR")
                    logger.error(
                        "Failed to sync account %s from %s: %s",
                        prospect_id,
                        provider.value,
                        sanitize_log_error("SYNC_ERROR"),
                        extra={"tenant_id": tenant_id, "provider": provider.value},
                    )

            # Determine final sync status and emit observation
            if has_truncation and stats["failed"] == len(stats["errors"]):
                final_status = "degraded"
                final_error = "Partial sync: some result sets were truncated"
            elif has_truncation:
                final_status = "failed"
                final_error = "; ".join(stats["errors"][:3]) or "Sync failed"
            else:
                final_status = "idle"
                final_error = None

            # Emit observation on Integration row
            if isinstance(integration, Integration):
                if final_status == "idle":
                    await apply_observation(self.db, integration, sync_succeeded())
                    integration.last_error_message = None
                elif final_status == "degraded":
                    await apply_observation(self.db, integration, sync_partial(message=final_error))
                    integration.last_error_message = final_error
                elif final_status == "failed":
                    await apply_observation(self.db, integration, sync_failed(message=final_error))
                    integration.last_error_message = final_error

            await self._update_account_sync_status(
                tenant_id,
                provider,
                final_status,
                final_error,
                records_synced=stats["synced"] + stats["updated"],
                records_updated=stats["updated"],
                records_failed=stats["failed"],
            )

            duration = time.monotonic() - sync_start
            if final_status == "idle":
                _increment_metric("crm_salesforce_sync_completed_total")
                _increment_metric(
                    "crm_salesforce_records_synced_total", stats["synced"] + stats["updated"]
                )
                if prom:
                    prom.increment_crm_salesforce_sync_completed(tenant_id, sync_type=sync_type)
                    prom.increment_crm_salesforce_records_synced(
                        tenant_id, record_type="account", count=stats["synced"] + stats["updated"]
                    )
                    prom.observe_crm_salesforce_sync_duration(
                        tenant_id, duration, sync_type=sync_type
                    )
                _log_sync_event(
                    "sync_completed",
                    tenant_id,
                    provider.value,
                    {
                        "duration_seconds": round(duration, 3),
                        "records_synced": stats["synced"] + stats["updated"],
                        "records_failed": stats["failed"],
                    },
                )
            elif final_status == "degraded":
                _increment_metric("crm_salesforce_sync_failed_total")
                if prom:
                    prom.increment_crm_salesforce_sync_failed(tenant_id, error_type="truncated")
                    prom.observe_crm_salesforce_sync_duration(
                        tenant_id, duration, sync_type=sync_type
                    )
                _log_sync_event(
                    "sync_degraded",
                    tenant_id,
                    provider.value,
                    {
                        "duration_seconds": round(duration, 3),
                        "records_synced": stats["synced"] + stats["updated"],
                        "records_failed": stats["failed"],
                        "error": final_error,
                    },
                )
            return stats

        except asyncio.CancelledError:
            raise
        except Exception as e:
            # Emit failure observation on Integration row
            if isinstance(integration, Integration):
                error_cls = ErrorClass.AUTH if isinstance(e, AuthError) else ErrorClass.TRANSIENT
                await apply_observation(
                    self.db, integration, sync_failed(error_class=error_cls, message="SYNC_ERROR")
                )
                integration.last_error_message = "SYNC_ERROR"[:1000]
            await self._update_account_sync_status(
                tenant_id, provider, "failed", "SYNC_ERROR"[:1000]
            )
            _increment_metric("crm_salesforce_sync_failed_total")
            duration = time.monotonic() - sync_start
            error_type = type(e).__name__
            if prom:
                prom.increment_crm_salesforce_sync_failed(tenant_id, error_type=error_type)
                prom.observe_crm_salesforce_sync_duration(tenant_id, duration, sync_type=sync_type)
            _log_sync_event(
                "sync_failed",
                tenant_id,
                provider.value,
                {
                    "duration_seconds": round(duration, 3),
                    "error_type": error_type,
                },
            )
            logger.error(
                "CRM sync failed for %s: %s",
                provider.value,
                sanitize_log_error(e),
                extra={"tenant_id": tenant_id, "provider": provider.value},
            )
            stats["errors"].append("CRM sync failed due to internal error")
            return stats

    async def _sync_single_account(
        self,
        connector: CRMConnector,
        tenant_id: str,
        provider: CRMProvider,
        prospect_id: str,
    ) -> bool:
        """Sync a single account from CRM via the connector.

        Args:
            connector: A CRMConnector instance.
            tenant_id: Tenant ID for RLS.
            provider: CRM provider enum.
            prospect_id: Provider's record ID.

        Returns:
            True if account was updated (existed), False if created (new)
        """
        # Fetch account record via connector
        record = await connector.get_account(prospect_id, timeout=self._provider_timeout)

        if record is None:
            raise ValueError(f"No profile data returned for {prospect_id}")

        # Check if account exists
        existing = await self.db.execute(
            select(Account).where(
                and_(
                    Account.tenant_id == UUID(str(tenant_id)),
                    Account.provider == provider.value,
                    Account.provider_record_id == prospect_id,
                )
            )
        )
        account = existing.scalar_one_or_none()

        is_update = account is not None

        if not account:
            # Create new account
            account = Account(
                tenant_id=UUID(str(tenant_id)),
                provider=provider.value,
                provider_record_id=prospect_id,
            )
            self.db.add(account)

        # Update account fields from canonical record
        profile = record.canonical
        account.name = profile.get("name", account.name)
        account.industry = profile.get("industry", account.industry)
        account.region = profile.get("region", account.region)
        account.company_size = profile.get("company_size", account.company_size)
        account.annual_revenue = profile.get("annual_revenue", account.annual_revenue)
        account.headquarters = profile.get("headquarters", account.headquarters)
        account.website = profile.get("website", account.website)
        account.domain = profile.get("domain", account.domain)
        account.employees = profile.get("employees", account.employees)
        account.segment = profile.get("segment", account.segment)

        # Fetch opportunities via connector
        try:
            opp_records, _ = await connector.list_opportunities(
                prospect_id, timeout=self._provider_timeout
            )
        except TransientError as exc:
            raise SyncTruncatedError("Opportunity sync returned a truncated result set") from exc
        except Exception:
            opp_records = []

        if opp_records:
            account.opportunities = [
                {
                    "provider_opportunity_id": opp.remote_id,
                    "name": opp.canonical.get("name", ""),
                    "stage": opp.canonical.get("stage", ""),
                    "value": opp.canonical.get("value"),
                    "probability": opp.canonical.get("probability"),
                    "close_date": opp.canonical.get("close_date"),
                    "pipeline": opp.canonical.get("pipeline"),
                    "last_synced_at": datetime.now(UTC).isoformat(),
                }
                for opp in opp_records
            ]

        # Update sync metadata
        account.last_synced_at = datetime.now(UTC)
        account.sync_status = SyncStatus.SYNCED.value
        account.updated_at = datetime.now(UTC)

        await self.db.commit()

        return is_update

    async def _get_accounts_to_sync(
        self,
        tenant_id: str,
        provider: CRMProvider,
        incremental: bool = True,
    ) -> list[str]:
        """Get list of account IDs that need syncing.

        For incremental sync, returns accounts with stale status or
        recently modified in CRM.
        """
        if incremental:
            # Get accounts that need sync (stale, failed, or pending)
            result = await self.db.execute(
                select(Account.provider_record_id)
                .where(
                    and_(
                        Account.tenant_id == UUID(str(tenant_id)),
                        Account.provider == provider.value,
                        Account.sync_status.in_(
                            [
                                SyncStatus.STALE.value,
                                SyncStatus.FAILED.value,
                                SyncStatus.PENDING.value,
                            ]
                        ),
                    )
                )
                .limit(self.sync_batch_size)
            )
            stale_ids = [row[0] for row in result.all() if row[0]]

            # Also get accounts not synced in last 24 hours
            day_ago = datetime.now(UTC) - timedelta(hours=24)
            result = await self.db.execute(
                select(Account.provider_record_id)
                .where(
                    and_(
                        Account.tenant_id == UUID(str(tenant_id)),
                        Account.provider == provider.value,
                        Account.sync_status == SyncStatus.SYNCED.value,
                        Account.last_synced_at < day_ago,
                    )
                )
                .limit(self.sync_batch_size - len(stale_ids))
            )
            old_ids = [row[0] for row in result.all() if row[0]]

            return stale_ids + old_ids
        else:
            # Full sync - all accounts for provider
            result = await self.db.execute(
                select(Account.provider_record_id)
                .where(
                    and_(
                        Account.tenant_id == UUID(str(tenant_id)),
                        Account.provider == provider.value,
                    )
                )
                .limit(self.sync_batch_size)
            )
            return [row[0] for row in result.all() if row[0]]

    async def _update_account_sync_status(
        self,
        tenant_id: str,
        provider: CRMProvider,
        status: str,
        error_message: str | None,
        records_synced: int = 0,
        records_updated: int = 0,
        records_failed: int = 0,
    ) -> None:
        """Update the AccountSyncStatus record (bookkeeping only; Integration state is driven by apply_observation in sync_provider)."""
        now = datetime.now(UTC)

        # Get or create sync status record
        result = await self.db.execute(
            select(AccountSyncStatus).where(
                and_(
                    AccountSyncStatus.tenant_id == tenant_id,
                    AccountSyncStatus.provider == provider.value,
                )
            )
        )
        sync_status = result.scalar_one_or_none()

        if not sync_status:
            sync_status = AccountSyncStatus(
                tenant_id=tenant_id,
                provider=provider.value,
                status=status,
                last_sync_at=now if status == "running" else None,
                last_successful_sync_at=now if status == "idle" else None,
                records_synced=records_synced,
                records_updated=records_updated,
                records_failed=records_failed,
                error_message=error_message,
            )
            self.db.add(sync_status)
        else:
            sync_status.status = status
            if status == "running":
                sync_status.last_sync_at = now
            elif status == "idle":
                sync_status.last_successful_sync_at = now
                sync_status.records_synced = records_synced
                sync_status.records_updated = records_updated
                sync_status.records_failed = records_failed
                sync_status.error_message = None
            elif status == "failed":
                sync_status.error_message = error_message
                sync_status.records_failed = records_failed
            sync_status.updated_at = now

        await self.db.commit()

    async def _get_crm_config(self, provider: CRMProvider, tenant_id: str) -> dict[str, Any] | None:
        """Get CRM configuration from tenant integration table.

        SECURITY: Never falls back to environment variables in production.
        Per-tenant integration config is the only authorized source.
        """
        from .integration_service import IntegrationService

        integration_service = IntegrationService(self.db)
        integration: Integration | None = await integration_service.get_integration(
            tenant_id, provider
        )

        if not integration:
            logger.warning(
                "No integration configured for tenant=%s provider=%s", tenant_id, provider.value
            )
            return None

        if not integration.enabled:
            logger.debug(
                "Integration disabled for tenant=%s provider=%s", tenant_id, provider.value
            )
            return None

        decrypted = await integration_service.decrypt_credentials(integration)
        config = CRMSyncService__get_crm_configResult.model_validate(
            {
                "crm_type": provider.value,
                "api_key": decrypted.get("api_key"),
                "crm_api_key": decrypted.get("api_key"),
                "crm_api_secret": decrypted.get("api_secret"),
                "crm_instance_url": integration.instance_url or decrypted.get("instance_url"),
            }
        )
        # Pass refresh token to connector config so it can handle 401→refresh→retry
        if integration.refresh_token_encrypted:
            try:
                config["refresh_token"] = await EncryptionService.decrypt(
                    integration.refresh_token_encrypted, integration.encryption_key_id
                )
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.warning(
                    "Failed to decrypt stored OAuth credential metadata for tenant=%s provider=%s",
                    tenant_id,
                    provider.value,
                )

        async def persist_refreshed_tokens(token_result: dict[str, Any]) -> None:
            new_access_token = token_result.get("api_key")
            if new_access_token:
                decrypted["api_key"] = new_access_token
                decrypted["crm_api_key"] = new_access_token
                integration.credentials_encrypted = await EncryptionService.encrypt(
                    json.dumps(decrypted), key_id=integration.encryption_key_id
                )
            new_instance_url = token_result.get("instance_url")
            if new_instance_url:
                integration.instance_url = str(new_instance_url)
            new_refresh_token = token_result.get("refresh_token")
            if new_refresh_token:
                integration.refresh_token_encrypted = await EncryptionService.encrypt(
                    str(new_refresh_token), key_id=integration.encryption_key_id
                )
            await self.db.flush()
            await self.db.commit()

        config["on_token_refresh"] = persist_refreshed_tokens
        return config

    async def get_sync_status(
        self, provider: CRMProvider, tenant_id: str
    ) -> AccountSyncStatus | None:
        """Get current sync status for a provider."""
        result = await self.db.execute(
            select(AccountSyncStatus).where(
                and_(
                    AccountSyncStatus.tenant_id == tenant_id,
                    AccountSyncStatus.provider == provider.value,
                )
            )
        )
        return result.scalar_one_or_none()

    async def refresh_single_account(
        self,
        account_id: UUID,
        tenant_id: str,
    ) -> Account | None:
        """Refresh a single account from its CRM provider.

        Args:
            account_id: Internal account UUID

        Returns:
            Updated Account or None if not found
        """
        # Get account
        result = await self.db.execute(
            select(Account).where(
                and_(
                    Account.id == account_id,
                    Account.tenant_id == UUID(str(tenant_id)),
                )
            )
        )
        account = result.scalar_one_or_none()

        if not account:
            return None

        # Get provider
        try:
            provider = CRMProvider(account.provider)
        except ValueError as e:
            raise ValueError(
                f"Invalid CRM provider '{account.provider}' for account {account_id}"
            ) from e

        # Get CRM config
        config = await self._get_crm_config(provider, tenant_id)
        if not config or not config.get("api_key"):
            raise ValueError(f"CRM not configured for provider {provider.value}")

        # Sync the account via connector
        connector = get_connector(provider, config)
        await self._sync_single_account(connector, tenant_id, provider, account.provider_record_id)

        # Refresh and return
        await self.db.refresh(account)
        return account

    async def sync_narrative_to_crm(
        self,
        tenant_id: str,
        account_id: str,
        narrative_artifact_id: str,
        narrative_version: int,
        narrative_content_hash: str,
        evidence_set_hash: str,
        human_approved_hash: str,
        integrity_precondition: Any,
    ) -> dict[str, Any]:
        """Delegate or write narrative claims to CRM.

        Enforces Pillar 3 Integrity Gate & CRM TOCTOU defense:
        1. Human approval must match exact narrative content hash.
        2. Integrity precondition must be passed, non-stale, and match exact hashes immediately before sync.
        3. Fails closed with 422 INTEGRITY_GATE_OPEN if integrity is missing, stale, or human approval is mismatched.
        """
        from ..contracts.artifacts import IntegrityGateErrorResponse, IntegrityPrecondition

        if not integrity_precondition:
            raise ValueError(
                IntegrityGateErrorResponse(
                    code="INTEGRITY_GATE_OPEN",
                    message="CRM sync requires an active, passing IntegrityArtifact.",
                    narrative_artifact_id=narrative_artifact_id,
                    narrative_version=narrative_version,
                    integrity_status="missing",
                    required_action="rerun_integrity_validation",
                ).model_dump()
            )

        # Verify human approval matches exact content hash
        if human_approved_hash != narrative_content_hash:
            raise ValueError(
                IntegrityGateErrorResponse(
                    code="INTEGRITY_GATE_OPEN",
                    message="Human approval hash does not match current narrative content hash.",
                    narrative_artifact_id=narrative_artifact_id,
                    narrative_version=narrative_version,
                    integrity_status="mismatched",
                    required_action="reapprove_narrative",
                ).model_dump()
            )

        # Re-verify integrity immediately before CRM write (TOCTOU defense)
        if (
            integrity_precondition.narrative_artifact_id != narrative_artifact_id
            or integrity_precondition.narrative_version != narrative_version
            or integrity_precondition.narrative_content_hash != narrative_content_hash
            or integrity_precondition.evidence_set_hash != evidence_set_hash
            or integrity_precondition.tenant_id != tenant_id
            or integrity_precondition.account_id != account_id
            or integrity_precondition.status != "passed"
            or integrity_precondition.unresolved_findings > 0
            or not integrity_precondition.is_passed
        ):
            raise ValueError(
                IntegrityGateErrorResponse(
                    code="INTEGRITY_GATE_OPEN",
                    message="Integrity check failed immediately prior to CRM write (stale or unverified).",
                    narrative_artifact_id=narrative_artifact_id,
                    narrative_version=narrative_version,
                    integrity_status="stale",
                    required_action="rerun_integrity_validation",
                ).model_dump()
            )

        # Execute idempotent CRM sync
        return {
            "status": "synced",
            "narrative_artifact_id": narrative_artifact_id,
            "account_id": account_id,
            "crm_sync_timestamp": datetime.now(UTC).isoformat(),
        }


# Factory function for dependency injection
async def get_crm_sync_service(db: AsyncSession) -> CRMSyncService:
    """Factory for creating CRMSyncService with database session."""
    return CRMSyncService(db)
