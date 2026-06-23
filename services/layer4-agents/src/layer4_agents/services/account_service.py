from __future__ import annotations

"""
Account service layer for CRM account operations.

Business logic and data access for the accounts surface.
"""
import asyncio
import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from value_fabric.shared.models.typed_dict import TypedDictModel

from ..models.account import (
    Account,
    AccountSyncStatus,
    CRMProvider,
    SyncStatus,
)
from ..models.tool_schemas import (
    FetchInteractionHistoryInput,
)
from ..tools.crm_tools import (
    FetchInteractionHistoryTool,
)
from .crm_sync_service import CRMSyncService


class AccountService_get_filter_optionsResult(TypedDictModel):
    industries: Any
    owners: Any
    providers: Any
    regions: Any
    segments: Any
    stages: Any

class AccountService_get_account_activityResult(TypedDictModel):
    account_id: Any
    interactions: list[Any]
    summary: str
    total_count: int

class AccountService_trigger_syncResult(TypedDictModel):
    message: str
    provider: Any
    stats: Any
    status: str
    sync_id: Any

logger = logging.getLogger(__name__)


class AccountService:
    """Service for account operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ========================================================================
    # List & Search
    # ========================================================================

    async def create_account(
        self,
        *,
        provider: CRMProvider,
        provider_record_id: str | None,
        name: str,
        tenant_id: str,
        domain: str | None = None,
        industry: str | None = None,
        region: str | None = None,
        company_size: int | None = None,
        annual_revenue: float | None = None,
        headquarters: str | None = None,
        website: str | None = None,
        owner_id: str | None = None,
        owner_name: str | None = None,
        owner_email: str | None = None,
        stage: str | None = None,
        segment: str | None = None,
        account_id: UUID | None = None,
    ) -> Account:
        """Create a new account record scoped to the authenticated tenant."""
        # Auto-generate provider_record_id for manual accounts
        if provider == CRMProvider.MANUAL and not provider_record_id:
            provider_record_id = f"manual-{uuid.uuid4()}"

        if not provider_record_id:
            raise ValueError("provider_record_id is required for non-manual providers")

        existing = await self.get_account_by_provider_id(provider, provider_record_id, tenant_id=tenant_id)
        if existing:
            raise ValueError(
                f"Account already exists for provider={provider.value} provider_record_id={provider_record_id}"
            )

        account = Account(
            id=account_id,
            provider=provider.value,
            provider_record_id=provider_record_id,
            name=name,
            normalized_name=name.strip().lower(),
            domain=domain,
            industry=industry,
            region=region,
            company_size=company_size,
            annual_revenue=annual_revenue,
            headquarters=headquarters,
            website=website,
            owner_id=owner_id,
            owner_name=owner_name,
            owner_email=owner_email,
            stage=stage,
            segment=segment,
            tenant_id=tenant_id,
            sync_status=SyncStatus.PENDING.value,
            opportunities=[],
            contacts=[],
        )

        self.db.add(account)
        await self.db.commit()
        await self.db.refresh(account)
        return account

    async def list_accounts(
        self,
        provider: CRMProvider | None = None,
        stage: str | None = None,
        industry: str | None = None,
        region: str | None = None,
        segment: str | None = None,
        owner_id: str | None = None,
        sync_status: SyncStatus | None = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "updated_at",
        sort_order: str = "desc",
        tenant_id: str | None = None,
    ) -> tuple[list[Account], int]:
        """List accounts with filtering and pagination.

        Returns:
            Tuple of (accounts list, total count)
        """
        # Build base query
        query = select(Account)
        count_query = select(func.count(Account.id))

        # Apply filters
        filters = []
        if tenant_id:
            filters.append(Account.tenant_id == tenant_id)
        if provider:
            filters.append(Account.provider == provider.value)
        if stage:
            filters.append(Account.stage == stage)
        if industry:
            filters.append(Account.industry == industry)
        if region:
            filters.append(Account.region == region)
        if segment:
            filters.append(Account.segment == segment)
        if owner_id:
            filters.append(Account.owner_id == owner_id)
        if sync_status:
            filters.append(Account.sync_status == sync_status.value)

        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))

        # Apply sorting
        sort_column = getattr(Account, sort_by, Account.updated_at)
        if sort_order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        # Execute queries
        result = await self.db.execute(query)
        accounts = result.scalars().all()

        total_result = await self.db.execute(count_query)
        total = total_result.scalar()

        return list(accounts), total

    async def search_accounts(
        self,
        query_str: str | None = None,
        provider: CRMProvider | None = None,
        stage: str | None = None,
        industry: str | None = None,
        region: str | None = None,
        segment: str | None = None,
        owner_id: str | None = None,
        sync_status: SyncStatus | None = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "updated_at",
        sort_order: str = "desc",
        tenant_id: str | None = None,
    ) -> tuple[list[Account], int]:
        """Search accounts across name, domain, and owner."""
        # Build base query
        query = select(Account)
        count_query = select(func.count(Account.id))

        filters = []
        if tenant_id:
            filters.append(Account.tenant_id == tenant_id)

        # Text search across name, domain, owner_name
        if query_str:
            search_filter = or_(
                Account.name.ilike(f"%{query_str}%"),
                Account.domain.ilike(f"%{query_str}%"),
                Account.owner_name.ilike(f"%{query_str}%"),
                Account.normalized_name.ilike(f"%{query_str.lower()}%"),
            )
            filters.append(search_filter)

        # Additional filters
        if provider:
            filters.append(Account.provider == provider.value)
        if stage:
            filters.append(Account.stage == stage)
        if industry:
            filters.append(Account.industry == industry)
        if region:
            filters.append(Account.region == region)
        if segment:
            filters.append(Account.segment == segment)
        if owner_id:
            filters.append(Account.owner_id == owner_id)
        if sync_status:
            filters.append(Account.sync_status == sync_status.value)

        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))

        # Sorting
        sort_column = getattr(Account, sort_by, Account.updated_at)
        if sort_order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

        # Pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        # Execute
        result = await self.db.execute(query)
        accounts = result.scalars().all()

        total_result = await self.db.execute(count_query)
        total = total_result.scalar()

        return list(accounts), total

    # ========================================================================
    # Detail & Activity
    # ========================================================================

    async def get_account(self, account_id: UUID, *, tenant_id: str | None = None) -> Account | None:
        """Get a single account by ID, optionally scoped to a tenant."""
        filters = [Account.id == account_id]
        if tenant_id:
            filters.append(Account.tenant_id == tenant_id)
        result = await self.db.execute(select(Account).where(and_(*filters)))
        return result.scalar_one_or_none()

    async def get_account_by_provider_id(
        self,
        provider: CRMProvider,
        provider_record_id: str,
        *,
        tenant_id: str | None = None,
    ) -> Account | None:
        """Get account by provider-specific ID, optionally scoped to a tenant."""
        filters = [
            Account.provider == provider.value,
            Account.provider_record_id == provider_record_id,
        ]
        if tenant_id:
            filters.append(Account.tenant_id == tenant_id)
        result = await self.db.execute(select(Account).where(and_(*filters)))
        return result.scalar_one_or_none()

    async def get_account_activity(
        self,
        account_id: UUID,
        limit: int = 50,
        since_days: int = 90,
        tenant_id: str | None = None,
    ) -> dict:
        """Fetch account activity via CRM tools.

        Uses fetch_interaction_history tool to get recent activity.
        """
        account = await self.get_account(account_id, tenant_id=tenant_id)
        if not account:
            raise ValueError(f"Account not found: {account_id}")

        # Calculate since date
        since_date = (datetime.now(UTC) - timedelta(days=since_days)).strftime("%Y-%m-%d")

        try:
            # Use the fetch_interaction_history tool
            tool = FetchInteractionHistoryTool()
            result = await tool.execute(
                FetchInteractionHistoryInput(
                    prospect_id=account.provider_record_id,
                    limit=limit,
                    since_date=since_date,
                )
            )

            return AccountService_get_account_activityResult.model_validate({
                "account_id": account_id,
                "interactions": [
                    {
                        "id": i.get("id", ""),
                        "type": i.get("type", "unknown"),
                        "date": i.get("date", ""),
                        "subject": i.get("subject", ""),
                        "duration_minutes": i.get("duration_minutes"),
                        "notes": i.get("notes", ""),
                        "outcome": i.get("outcome", ""),
                    }
                    for i in result.interactions
                ],
                "total_count": result.total_count,
                "summary": result.summary,
            })


        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Failed to fetch activity for account {account_id}: {e}")
            return AccountService_get_account_activityResult.model_validate({
                "account_id": account_id,
                "interactions": [],
                "total_count": 0,
                "summary": "Activity data unavailable",
            })


    # ========================================================================
    # Sync Operations
    # ========================================================================

    async def get_sync_status(
        self, provider: CRMProvider, tenant_id: str
    ) -> AccountSyncStatus | None:
        """Get sync status for a provider."""
        result = await self.db.execute(
            select(AccountSyncStatus).where(
                AccountSyncStatus.tenant_id == tenant_id,
                AccountSyncStatus.provider == provider.value,
            )
        )
        return result.scalar_one_or_none()

    async def get_all_sync_status(self, tenant_id: str) -> list[AccountSyncStatus]:
        """Get sync status for all providers."""
        result = await self.db.execute(
            select(AccountSyncStatus).where(AccountSyncStatus.tenant_id == tenant_id)
        )
        return list(result.scalars().all())

    async def trigger_sync(
        self,
        tenant_id: str,
        provider: CRMProvider | None = None,
        account_ids: list[str] | None = None,
        force_refresh: bool = False,
    ) -> dict:
        """Trigger manual sync for accounts.

        ``tenant_id`` is required — callers must pass the authenticated tenant.
        Uses CRMSyncService to execute the actual synchronization.
        """
        if not tenant_id:
            raise ValueError("tenant_id is required for CRM sync")
        sync_id = f"sync-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"

        # Initialize sync service
        sync_service = CRMSyncService(self.db)

        if provider:
            # Sync specific provider
            stats = await sync_service.sync_provider(
                provider,
                tenant_id=tenant_id,
                incremental=not force_refresh,
                account_ids=account_ids,
            )
            return AccountService_trigger_syncResult.model_validate({
                "sync_id": sync_id,
                "status": "completed" if not stats["errors"] else "partial",
                "provider": provider.value,
                "message": f"Synced {stats['updated']} accounts, {stats['failed']} failed",
                "stats": stats,
            })


        elif account_ids:
            # Sync specific accounts (try both providers)
            all_stats = []
            for prov in [CRMProvider.SALESFORCE, CRMProvider.HUBSPOT]:
                stats = await sync_service.sync_provider(
                    prov,
                    tenant_id=tenant_id,
                    incremental=not force_refresh,
                    account_ids=account_ids,
                )
                all_stats.append(stats)

            total_updated = sum(s["updated"] for s in all_stats)
            total_failed = sum(s["failed"] for s in all_stats)

            return AccountService_trigger_syncResult.model_validate({
                "sync_id": sync_id,
                "status": "completed" if total_failed == 0 else "partial",
                "provider": None,
                "message": f"Synced {total_updated} accounts, {total_failed} failed",
                "stats": all_stats,
            })


        else:
            # Sync all providers
            all_stats = []
            for prov in [CRMProvider.SALESFORCE, CRMProvider.HUBSPOT]:
                stats = await sync_service.sync_provider(
                    prov,
                    tenant_id=tenant_id,
                    incremental=not force_refresh,
                )
                all_stats.append(stats)

            total_updated = sum(s["updated"] for s in all_stats)
            total_failed = sum(s["failed"] for s in all_stats)

            return AccountService_trigger_syncResult.model_validate({
                "sync_id": sync_id,
                "status": "completed" if total_failed == 0 else "partial",
                "provider": None,
                "message": f"Synced {total_updated} accounts across all providers, {total_failed} failed",
                "stats": all_stats,
            })


    async def refresh_account(self, account_id: UUID, tenant_id: str) -> Account | None:
        """Refresh single account from CRM provider.

        Uses CRMSyncService for consistent sync behavior.
        """
        sync_service = CRMSyncService(self.db)
        return await sync_service.refresh_single_account(account_id, tenant_id)

    # ========================================================================
    # Filter Options
    # ========================================================================

    async def get_filter_options(self, *, tenant_id: str) -> dict:
        """Get available filter options for account list scoped to a tenant."""
        if not tenant_id:
            raise ValueError("tenant_id is required for account filter options")

        # Get distinct industries
        industry_result = await self.db.execute(
            select(Account.industry)
            .where(Account.tenant_id == tenant_id, Account.industry.isnot(None))
            .distinct()
        )
        industries = [row[0] for row in industry_result.all() if row[0]]

        # Get distinct stages
        stage_result = await self.db.execute(
            select(Account.stage)
            .where(Account.tenant_id == tenant_id, Account.stage.isnot(None))
            .distinct()
        )
        stages = [row[0] for row in stage_result.all() if row[0]]

        # Get distinct regions
        region_result = await self.db.execute(
            select(Account.region)
            .where(Account.tenant_id == tenant_id, Account.region.isnot(None))
            .distinct()
        )
        regions = [row[0] for row in region_result.all() if row[0]]

        # Get distinct segments
        segment_result = await self.db.execute(
            select(Account.segment)
            .where(Account.tenant_id == tenant_id, Account.segment.isnot(None))
            .distinct()
        )
        segments = [row[0] for row in segment_result.all() if row[0]]

        # Get owners
        owner_result = await self.db.execute(
            select(Account.owner_id, Account.owner_name)
            .where(Account.tenant_id == tenant_id, Account.owner_id.isnot(None))
            .distinct()
        )
        owners = [
            {"id": row[0], "name": row[1] or "Unknown"} for row in owner_result.all() if row[0]
        ]

        return AccountService_get_filter_optionsResult.model_validate({
            "industries": industries,
            "stages": stages,
            "regions": regions,
            "segments": segments,
            "providers": [p.value for p in CRMProvider],
            "owners": owners,
        })


# Factory function for dependency injection
async def get_account_service(db: AsyncSession) -> AccountService:
    """Factory for creating AccountService with database session."""
    return AccountService(db)
