"""
Freshness Monitoring Service for Layer 5 Ground Truth.

Checks for TruthObjects that have exceeded their freshness (expires_at < now())
and marks them as stale. Creates audit events for each staleness transition.

Can be run:
1. Manually via API endpoint POST /truths/check-stale
2. As a dedicated cron/job runner
"""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import and_, case, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from ..config import get_settings
from ..models.truth_object import ClaimType, TruthObject, ValidationEvent
from .freshness_contracts import FreshnessCheckResponse, FreshnessSummaryResponse


logger = logging.getLogger(__name__)


FRESHNESS_ADVISORY_LOCK_KEY = 580051


async def run_freshness_check_with_leader_lock(
    db: AsyncSession,
    monitor: "FreshnessMonitor",
    *,
    tenant_id: UUID | None = None,
    dry_run: bool = False,
) -> FreshnessCheckResponse | None:
    """Run freshness reconciliation only for the elected leader worker.

    Returns None when lock is not acquired (another worker is leader).
    Uses PostgreSQL advisory locks; non-Postgres dialects run unguarded.
    """
    dialect_name = db.bind.dialect.name if db.bind is not None else ""
    if dialect_name != "postgresql":
        return await monitor.check_and_mark_stale(db, tenant_id=tenant_id, dry_run=dry_run)

    lock_result = await db.execute(select(func.pg_try_advisory_lock(FRESHNESS_ADVISORY_LOCK_KEY)))
    has_lock = bool(lock_result.scalar())
    if not has_lock:
        return None

    try:
        return await monitor.check_and_mark_stale(db, tenant_id=tenant_id, dry_run=dry_run)
    finally:
        await db.execute(select(func.pg_advisory_unlock(FRESHNESS_ADVISORY_LOCK_KEY)))


# ---------------------------------------------------------------------------
# TTL Configuration per Claim Type (in days)
# ---------------------------------------------------------------------------

DEFAULT_TTL_BY_CLAIM_TYPE: dict[str, int] = {
    # Financial data becomes stale faster
    ClaimType.COST_SAVINGS_BASELINE.value: 90,
    ClaimType.REVENUE_IMPACT.value: 60,
    ClaimType.EFFICIENCY_GAIN.value: 90,
    ClaimType.RISK_REDUCTION.value: 120,
    ClaimType.VALUE_DRIVER_METRIC.value: 90,
    # Compliance and legal - longer TTL
    ClaimType.COMPLIANCE_REQUIREMENT.value: 365,
    ClaimType.MARKET_BENCHMARK.value: 180,
    # Customer and persona data
    ClaimType.CUSTOMER_OUTCOME.value: 90,
    ClaimType.PERSONA_PAIN_POINT.value: 90,
    # Technical capabilities change slower
    ClaimType.TECHNICAL_CAPABILITY.value: 180,
    # Catch-all
    ClaimType.OTHER.value: 90,
}


# ---------------------------------------------------------------------------
# Freshness Monitor Service
# ---------------------------------------------------------------------------


class FreshnessMonitor:
    """
    Monitors and enforces truth object freshness policies.

    Automatically marks expired truths as stale and creates audit events.
    TTL is configurable per claim_type via config.
    """

    def __init__(self, custom_ttls: dict[str, int] | None = None) -> None:
        """
        Initialize the freshness monitor.

        Args:
            custom_ttls: Optional override for TTL configuration per claim_type.
                        Maps claim_type values to days.
        """
        self._settings = get_settings()
        self._ttls = custom_ttls or DEFAULT_TTL_BY_CLAIM_TYPE

    def get_ttl_for_claim_type(self, claim_type: str) -> int:
        """Get TTL in days for a specific claim type."""
        return self._ttls.get(claim_type, self._settings.default_freshness_days)

    def calculate_expires_at(
        self,
        freshness: datetime,
        claim_type: str,
    ) -> datetime:
        """
        Calculate expires_at timestamp based on freshness date and claim type.

        Args:
            freshness: The freshness timestamp (when claim was last validated)
            claim_type: The type of claim

        Returns:
            Datetime when the truth object should expire
        """
        ttl_days = self.get_ttl_for_claim_type(claim_type)
        return freshness + timedelta(days=ttl_days)

    async def check_and_mark_stale(
        self,
        db: AsyncSession,
        tenant_id: UUID | None = None,
        dry_run: bool = False,
    ) -> FreshnessCheckResponse:
        """
        Query for expired truths and mark them as stale.

        Args:
            db: Database session
            tenant_id: Optional org filter (None = all orgs)
            dry_run: If True, only count without updating

        Returns:
            Dict with counts: {"checked": int, "marked_stale": int, "already_stale": int}
        """
        now = datetime.now(UTC)

        # Build query to find non-deleted, non-stale truths that have expired
        stmt = (
            select(TruthObject)
            .options(selectinload(TruthObject.sources))
            .where(
                and_(
                    TruthObject.deleted_at.is_(None),
                    TruthObject.is_stale.is_(False),
                    TruthObject.expires_at.isnot(None),
                    TruthObject.expires_at < now,
                )
            )
        )

        if tenant_id:
            stmt = stmt.where(TruthObject.tenant_id == tenant_id)

        result = await db.execute(stmt)
        expired_truths = result.scalars().all()

        marked_count = 0
        for truth in expired_truths:
            if dry_run:
                marked_count += 1
                continue

            update_result = await db.execute(
                update(TruthObject)
                .where(
                    and_(
                        TruthObject.id == truth.id,
                        TruthObject.deleted_at.is_(None),
                        TruthObject.is_stale.is_(False),
                    )
                )
                .values(is_stale=True, updated_at=now)
                .execution_options(synchronize_session=False)
            )
            if (update_result.rowcount or 0) == 0:
                logger.info(
                    "TruthObject %s stale transition skipped; another worker already updated it",
                    truth.id,
                )
                continue

            event = ValidationEvent(
                truth_object_id=truth.id,
                tenant_id=truth.tenant_id,
                from_status=truth.status,
                to_status=truth.status,  # Status doesn't change, just marked stale
                from_maturity=truth.maturity_level,
                to_maturity=truth.maturity_level,
                actor="system:freshness_monitor",
                actor_type="system",
                confidence_at_transition=truth.confidence,
                source_count_at_transition=len(truth.sources)
                if truth.sources
                else 0,
                notes=f"Automatically marked stale: expired at {truth.expires_at.isoformat()}",
            )
            db.add(event)

            logger.warning(
                "TruthObject %s marked stale (expired %s)",
                truth.id,
                truth.expires_at.isoformat(),
            )
            marked_count += 1

        if dry_run:
            logger.info(
                "[DRY RUN] Found %d expired TruthObjects that would be marked stale",
                marked_count,
            )
        else:
            logger.info(
                "Freshness check complete: %d TruthObjects marked stale",
                marked_count,
            )

        return FreshnessCheckResponse.model_validate({
            "checked": len(expired_truths),
            "marked_stale": marked_count if not dry_run else 0,
            "dry_run": dry_run,
            "timestamp": now.isoformat(),
        })


    async def list_stale_truths(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[TruthObject], int]:
        """
        List all stale TruthObjects for an organization.

        Args:
            db: Database session
            tenant_id: Organization to filter by
            limit: Max results to return
            offset: Pagination offset

        Returns:
            Tuple of (list of stale truths, total count)
        """
        # Get total count using func.count() for efficiency
        from sqlalchemy import func as sa_func

        count_stmt = (
            select(sa_func.count())
            .select_from(TruthObject)
            .where(
                and_(
                    TruthObject.tenant_id == tenant_id,
                    TruthObject.deleted_at.is_(None),
                    TruthObject.is_stale.is_(True),
                )
            )
        )
        count_result = await db.execute(count_stmt)
        total = count_result.scalar() or 0

        # Get paginated results with eager-loaded sources
        stmt = (
            select(TruthObject)
            .options(selectinload(TruthObject.sources))
            .where(
                and_(
                    TruthObject.tenant_id == tenant_id,
                    TruthObject.deleted_at.is_(None),
                    TruthObject.is_stale.is_(True),
                )
            )
            .order_by(TruthObject.expires_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await db.execute(stmt)
        items = result.scalars().all()

        return items, total

    async def get_freshness_summary(
        self,
        db: AsyncSession,
        tenant_id: UUID,
    ) -> FreshnessSummaryResponse:
        """
        Get a summary of freshness status for an organization.

        Returns counts by status and days until expiry breakdown.
        """
        now = datetime.now(UTC)

        # Base where clause
        base_where = and_(
            TruthObject.tenant_id == tenant_id,
            TruthObject.deleted_at.is_(None),
        )

        stale_count, fresh_count = await self._count_by_stale_status(db, base_where)

        # Count expiring soon (within warning period)
        warning_date = now + timedelta(days=self._settings.stale_warning_days)
        expiring_soon_stmt = select(func.count()).where(
            and_(
                base_where,
                TruthObject.is_stale.is_(False),
                TruthObject.expires_at.isnot(None),
                TruthObject.expires_at <= warning_date,
                TruthObject.expires_at > now,
            )
        )
        expiring_soon_result = await db.execute(expiring_soon_stmt)
        expiring_soon_count = expiring_soon_result.scalar() or 0

        return FreshnessSummaryResponse.model_validate({
            "tenant_id": str(tenant_id),
            "timestamp": now.isoformat(),
            "summary": {
                "stale": stale_count,
                "fresh": fresh_count,
                "expiring_soon": expiring_soon_count,  # Within warning period
                "total": stale_count + fresh_count,
            },
            "warning_threshold_days": self._settings.stale_warning_days,
        })


    async def _count_by_stale_status(
        self,
        db: AsyncSession,
        base_where: Any,
    ) -> tuple[int, int]:
        """Count truths by stale status in a single query for efficiency."""
        stmt = select(
            func.sum(case((TruthObject.is_stale.is_(True), 1), else_=0)).label("stale"),
            func.sum(case((TruthObject.is_stale.is_(False), 1), else_=0)).label(
                "fresh"
            ),
        ).where(base_where)
        result = await db.execute(stmt)
        row = result.one()
        return int(row.stale or 0), int(row.fresh or 0)


# ---------------------------------------------------------------------------
# Module-level convenience functions
# ---------------------------------------------------------------------------


async def check_freshness(
    db: AsyncSession,
    tenant_id: UUID | None = None,
    dry_run: bool = False,
) -> FreshnessCheckResponse:
    """
    Convenience function to run a freshness check.

    Args:
        db: Database session
        tenant_id: Optional org filter
        dry_run: If True, only count without updating

    Returns:
        Dict with check results
    """
    monitor = FreshnessMonitor()
    result = await run_freshness_check_with_leader_lock(db, monitor, tenant_id=tenant_id, dry_run=dry_run)
    return result or FreshnessCheckResponse.model_validate({"checked": 0, "marked_stale": 0, "dry_run": dry_run, "timestamp": datetime.now(UTC).isoformat()})


async def get_stale_truths(
    db: AsyncSession,
    tenant_id: UUID,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[TruthObject], int]:
    """Convenience function to list stale truths."""
    monitor = FreshnessMonitor()
    return await monitor.list_stale_truths(db, tenant_id, limit, offset)
