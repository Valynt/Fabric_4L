"""
Tests for the Freshness Monitoring service.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID
from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from layer5_ground_truth.models.truth_object import (
    ClaimType,
    TruthObject,
    TruthStatus,
    ValidationEvent,
)
from layer5_ground_truth.database import _mark_session_tenant_bypass
from layer5_ground_truth.services.freshness_monitor import (
    FreshnessMonitor,
    check_freshness,
    get_stale_truths,
)


@pytest.fixture
def monitor():
    return FreshnessMonitor()


@pytest.fixture(autouse=True)
async def clean_truth_objects(db: AsyncSession):
    """Clean up TruthObjects before each test to ensure isolation."""
    from sqlalchemy import text
    _mark_session_tenant_bypass(db, reason="test_fixture")
    await db.execute(text("DELETE FROM truth_objects"))
    await db.flush()
    yield


class TestFreshnessMonitor:
    async def test_get_ttl_for_claim_type(self, monitor: FreshnessMonitor) -> None:
        """Test TTL lookup for different claim types."""
        assert monitor.get_ttl_for_claim_type(ClaimType.COST_SAVINGS_BASELINE.value) == 90
        assert monitor.get_ttl_for_claim_type(ClaimType.REVENUE_IMPACT.value) == 60
        assert monitor.get_ttl_for_claim_type(ClaimType.COMPLIANCE_REQUIREMENT.value) == 365
        # Unknown claim type should return default
        assert monitor.get_ttl_for_claim_type("unknown_type") == 90  # default_freshness_days

    async def test_calculate_expires_at(self, monitor: FreshnessMonitor) -> None:
        """Test expires_at calculation."""
        freshness = datetime(2024, 1, 1, tzinfo=UTC)
        
        # COST_SAVINGS_BASELINE has 90 day TTL
        expires = monitor.calculate_expires_at(
            freshness, ClaimType.COST_SAVINGS_BASELINE.value
        )
        expected = freshness + timedelta(days=90)  # Use dynamic calculation
        assert expires == expected

        # REVENUE_IMPACT has 60 day TTL
        expires = monitor.calculate_expires_at(
            freshness, ClaimType.REVENUE_IMPACT.value
        )
        expected = freshness + timedelta(days=60)
        assert expires == expected

    async def test_check_and_mark_stale_finds_expired(
        self,
        db: AsyncSession,
        monitor: FreshnessMonitor,
    ) -> None:
        """Test that expired truths are marked stale."""
        org_id = UUID("00000000-0000-0000-0000-000000000001")

        # Create a truth that expired yesterday
        expired_truth = TruthObject(
            id=UUID("11111111-1111-1111-1111-111111111111"),
            tenant_id=org_id,
            claim="Expired claim",
            claim_type=ClaimType.OTHER.value,
            confidence=0.8,
            status=TruthStatus.VALIDATED.value,
            maturity_level=2,
            freshness=datetime.now(UTC) - timedelta(days=100),
            expires_at=datetime.now(UTC) - timedelta(days=1),  # Expired!
            is_stale=False,
        )
        db.add(expired_truth)
        await db.flush()

        # Run the freshness check
        result = await monitor.check_and_mark_stale(db, org_id)

        assert result["checked"] == 1
        assert result["marked_stale"] == 1
        assert result["dry_run"] is False

        # Flush changes made by freshness check so refresh works
        await db.flush()

        # Verify the truth was marked stale
        await db.refresh(expired_truth)
        assert expired_truth.is_stale is True

        # Verify a ValidationEvent was created
        from sqlalchemy import select as sa_select
        events_result = await db.execute(
            sa_select(ValidationEvent)
            .where(ValidationEvent.truth_object_id == expired_truth.id)
        )
        events = events_result.scalars().all()
        assert len(events) == 1
        assert events[0].actor == "system:freshness_monitor"
        assert "expired" in events[0].notes.lower()

    async def test_check_and_mark_stale_respects_dry_run(
        self,
        db: AsyncSession,
        monitor: FreshnessMonitor,
    ) -> None:
        """Test that dry_run mode doesn't actually mark stale."""
        org_id = UUID("00000000-0000-0000-0000-000000000001")

        # Create an expired truth
        expired_truth = TruthObject(
            id=UUID("22222222-2222-2222-2222-222222222222"),
            tenant_id=org_id,
            claim="Expired claim dry run",
            claim_type=ClaimType.OTHER.value,
            confidence=0.8,
            status=TruthStatus.VALIDATED.value,
            maturity_level=2,
            freshness=datetime.now(UTC) - timedelta(days=100),
            expires_at=datetime.now(UTC) - timedelta(days=1),
            is_stale=False,
        )
        db.add(expired_truth)
        await db.flush()

        # Run in dry-run mode
        result = await monitor.check_and_mark_stale(db, org_id, dry_run=True)

        assert result["checked"] == 1
        assert result["marked_stale"] == 0  # Not actually marked
        assert result["dry_run"] is True

        # Verify the truth was NOT marked stale
        await db.refresh(expired_truth)
        assert expired_truth.is_stale is False

    async def test_check_and_mark_stale_ignores_already_expired(
        self,
        db: AsyncSession,
        monitor: FreshnessMonitor,
    ) -> None:
        """Test that already expired truths are ignored."""
        org_id = UUID("00000000-0000-0000-0000-000000000001")

        # Create a truth that's already expired
        already_expired = TruthObject(
            id=UUID("33333333-3333-3333-3333-333333333333"),
            tenant_id=org_id,
            claim="Already expired",
            claim_type=ClaimType.OTHER.value,
            confidence=0.8,
            status=TruthStatus.EXPIRED.value,
            maturity_level=2,
            freshness=datetime.now(UTC) - timedelta(days=100),
            expires_at=datetime.now(UTC) - timedelta(days=30),
            is_stale=True,
        )
        db.add(already_expired)
        await db.flush()

        # Run the check
        result = await monitor.check_and_mark_stale(db, org_id)

        # Should not check already expired truths
        assert result["checked"] == 0
        assert result["marked_stale"] == 0

    async def test_check_and_mark_stale_ignores_null_expires_at(
        self,
        db: AsyncSession,
        monitor: FreshnessMonitor,
    ) -> None:
        """Test that truths without expires_at are ignored."""
        org_id = UUID("00000000-0000-0000-0000-000000000001")

        # Create a truth with no expiry
        no_expiry = TruthObject(
            id=UUID("44444444-4444-4444-4444-444444444444"),
            tenant_id=org_id,
            claim="No expiry set",
            claim_type=ClaimType.OTHER.value,
            confidence=0.8,
            status=TruthStatus.VALIDATED.value,
            maturity_level=2,
            freshness=datetime.now(UTC),
            expires_at=None,  # No expiry
            is_stale=False,
        )
        db.add(no_expiry)
        await db.flush()

        # Run the check
        result = await monitor.check_and_mark_stale(db, org_id)

        assert result["checked"] == 0
        assert result["marked_stale"] == 0


    async def test_check_and_mark_stale_is_idempotent_back_to_back(
        self,
        db: AsyncSession,
        monitor: FreshnessMonitor,
    ) -> None:
        """Running reconciliation twice must not duplicate stale transition events."""
        org_id = UUID("00000000-0000-0000-0000-000000000001")

        expired_truth = TruthObject(
            id=UUID("77777777-7777-7777-7777-777777777777"),
            tenant_id=org_id,
            claim="Idempotent stale transition",
            claim_type=ClaimType.OTHER.value,
            confidence=0.7,
            status=TruthStatus.VALIDATED.value,
            maturity_level=2,
            freshness=datetime.now(UTC) - timedelta(days=100),
            expires_at=datetime.now(UTC) - timedelta(days=2),
            is_stale=False,
        )
        db.add(expired_truth)
        await db.flush()

        first = await monitor.check_and_mark_stale(db, org_id)
        second = await monitor.check_and_mark_stale(db, org_id)

        assert first["marked_stale"] == 1
        assert second["marked_stale"] == 0

        await db.refresh(expired_truth)
        assert expired_truth.is_stale is True

        from sqlalchemy import select as sa_select

        events_result = await db.execute(
            sa_select(ValidationEvent).where(ValidationEvent.truth_object_id == expired_truth.id)
        )
        events = events_result.scalars().all()
        assert len(events) == 1

    async def test_check_and_mark_stale_is_idempotent_in_back_to_back_unit_flow(
        self,
        monitor: FreshnessMonitor,
    ) -> None:
        """Two immediate passes should emit a stale transition event only once."""
        truth = TruthObject(
            claim="Unit idempotency",
            claim_type=ClaimType.OTHER.value,
            confidence=0.7,
            status=TruthStatus.VALIDATED.value,
            maturity_level=2,
            is_stale=False,
        )
        truth.id = UUID("12121212-1212-1212-1212-121212121212")
        truth.tenant_id = UUID("00000000-0000-0000-0000-000000000001")
        truth.sources = []
        truth.expires_at = datetime.now(UTC) - timedelta(days=2)

        first_select = Mock()
        first_select.scalars.return_value.all.return_value = [truth]
        count_result = Mock()
        count_result.scalar.return_value = 0
        first_update = Mock(rowcount=1)
        second_select = Mock()
        second_select.scalars.return_value.all.return_value = []

        db = Mock(spec=AsyncSession)
        db.execute = AsyncMock(
            side_effect=[first_select, count_result, first_update, second_select]
        )
        db.add = Mock()

        first = await monitor.check_and_mark_stale(db)
        second = await monitor.check_and_mark_stale(db)

        assert first["marked_stale"] == 1
        assert second["marked_stale"] == 0
        # expire() adds a ValidationEvent (via _apply_transition)
        assert db.add.call_count >= 1

    async def test_list_stale_truths(
        self,
        db: AsyncSession,
        monitor: FreshnessMonitor,
    ) -> None:
        """Test listing stale truths."""
        org_id = UUID("00000000-0000-0000-0000-000000000001")

        # Create some stale truths
        for i in range(3):
            truth = TruthObject(
                id=UUID(f"55555555-5555-5555-5555-a{i:011d}"),
                tenant_id=org_id,
                claim=f"Stale truth {i}",
                claim_type=ClaimType.OTHER.value,
                confidence=0.8,
                status=TruthStatus.VALIDATED.value,
                maturity_level=2,
                freshness=datetime.now(UTC),
                expires_at=datetime.now(UTC) - timedelta(days=1),
                is_stale=True,
            )
            db.add(truth)

        # Create a non-stale truth
        fresh_truth = TruthObject(
            id=UUID("66666666-6666-6666-6666-666666666666"),
            tenant_id=org_id,
            claim="Fresh truth",
            claim_type=ClaimType.OTHER.value,
            confidence=0.8,
            status=TruthStatus.VALIDATED.value,
            maturity_level=2,
            freshness=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(days=30),
            is_stale=False,
        )
        db.add(fresh_truth)
        await db.flush()

        # List stale truths
        items, total = await monitor.list_stale_truths(db, org_id)

        assert total == 3
        assert len(items) == 3
        assert all(t.is_stale for t in items)

    async def test_get_freshness_summary(
        self,
        db: AsyncSession,
        monitor: FreshnessMonitor,
    ) -> None:
        """Test freshness summary report."""
        org_id = UUID("00000000-0000-0000-0000-000000000001")

        # Create 2 stale truths
        for i in range(2):
            truth = TruthObject(
                id=UUID(f"77777777-7777-7777-7777-a{i:011d}"),
                tenant_id=org_id,
                claim=f"Stale truth {i}",
                claim_type=ClaimType.OTHER.value,
                confidence=0.8,
                status=TruthStatus.VALIDATED.value,
                maturity_level=2,
                freshness=datetime.now(UTC),
                expires_at=datetime.now(UTC) - timedelta(days=1),
                is_stale=True,
            )
            db.add(truth)

        # Create 3 fresh truths (not expiring soon)
        for i in range(3):
            truth = TruthObject(
                id=UUID(f"88888888-8888-8888-8888-a{i:011d}"),
                tenant_id=org_id,
                claim=f"Fresh truth {i}",
                claim_type=ClaimType.OTHER.value,
                confidence=0.8,
                status=TruthStatus.VALIDATED.value,
                maturity_level=2,
                freshness=datetime.now(UTC),
                expires_at=datetime.now(UTC) + timedelta(days=100),
                is_stale=False,
            )
            db.add(truth)

        # Create 1 truth expiring soon
        expiring_soon = TruthObject(
            id=UUID("99999999-9999-9999-9999-999999999999"),
            tenant_id=org_id,
            claim="Expiring soon",
            claim_type=ClaimType.OTHER.value,
            confidence=0.8,
            status=TruthStatus.VALIDATED.value,
            maturity_level=2,
            freshness=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(days=5),  # Within warning period
            is_stale=False,
        )
        db.add(expiring_soon)
        await db.flush()

        # Get summary
        summary = await monitor.get_freshness_summary(db, org_id)

        assert summary.summary.stale == 2
        assert summary.summary.fresh == 4  # 3 fresh + 1 expiring soon
        assert summary.summary.expiring_soon == 1
        assert summary.summary.total == 6
        assert summary.tenant_id == str(org_id)

    async def test_convenience_functions(
        self,
        db: AsyncSession,
    ) -> None:
        """Test the module-level convenience functions."""
        org_id = UUID("00000000-0000-0000-0000-000000000001")

        # Create an expired truth
        expired = TruthObject(
            id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
            tenant_id=org_id,
            claim="Expired",
            claim_type=ClaimType.OTHER.value,
            confidence=0.8,
            status=TruthStatus.VALIDATED.value,
            maturity_level=2,
            freshness=datetime.now(UTC) - timedelta(days=100),
            expires_at=datetime.now(UTC) - timedelta(days=1),
            is_stale=False,
        )
        db.add(expired)
        await db.flush()

        # Test check_freshness
        result = await check_freshness(db, org_id, dry_run=False)
        assert result["checked"] == 1
        assert result["marked_stale"] == 1

        # Flush changes made by check_freshness
        await db.flush()

        # Test get_stale_truths
        items, total = await get_stale_truths(db, org_id)
        assert total == 1
        assert len(items) == 1
        assert items[0].id == expired.id
