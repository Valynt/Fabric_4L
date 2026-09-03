from __future__ import annotations

"""Unit tests for HealthTracker service.

Tests health status tracking, badge generation, and callback mechanisms.
"""


import asyncio

import pytest

from _wait_utils import wait_until

from layer4_agents.services.health_tracker import (
    HealthBadge,
    HealthStatus,
    HealthTracker,
    get_health_tracker,
)


class TestHealthTrackerValidation:
    """Test suite for HealthTracker input validation."""

    def test_check_interval_seconds_zero_raises_value_error(self):
        """Test that check_interval_seconds=0 raises ValueError."""
        with pytest.raises(ValueError, match="check_interval_seconds must be >= 1"):
            HealthTracker(check_interval_seconds=0)

    def test_check_interval_seconds_negative_raises_value_error(self):
        """Test that negative check_interval_seconds raises ValueError."""
        with pytest.raises(ValueError, match="check_interval_seconds must be >= 1"):
            HealthTracker(check_interval_seconds=-1)

    def test_check_interval_seconds_one_is_valid(self):
        """Test that check_interval_seconds=1 is accepted."""
        tracker = HealthTracker(check_interval_seconds=1)
        assert tracker.check_interval == 1

    def test_check_interval_seconds_default_is_valid(self):
        """Test that default check_interval_seconds is valid."""
        tracker = HealthTracker()  # Uses default
        assert tracker.check_interval >= 1


class TestHealthTracker:
    """Test suite for HealthTracker."""

    @pytest.fixture
    async def tracker(self):
        """Create a fresh health tracker for each test."""
        tracker = HealthTracker(check_interval_seconds=1)
        yield tracker
        await tracker.stop()

    @pytest.fixture
    def badge_collector(self):
        """Create a badge collector callback fixture."""
        badges: list[HealthBadge] = []

        def collect(badge: HealthBadge):
            badges.append(badge)

        return badges, collect

    @pytest.fixture
    def status_collector(self):
        """Create a status change collector callback fixture."""
        changes: list[tuple[str, HealthStatus, HealthStatus]] = []

        def collect(component: str, old: HealthStatus, new: HealthStatus):
            changes.append((component, old, new))

        return changes, collect

    async def test_update_component_creates_health(self, tracker):
        """Test that updating a component creates health record."""
        await tracker.update_component("test_db", HealthStatus.HEALTHY)

        health = tracker.get_component_health("test_db")
        assert health is not None
        assert health.name == "test_db"
        assert health.status == HealthStatus.HEALTHY

    async def test_status_change_triggers_callback(
        self, tracker, status_collector
    ):
        """Test that status changes trigger registered callbacks."""
        changes, collect = status_collector
        tracker.register_status_callback(collect)

        await tracker.update_component("websocket", HealthStatus.HEALTHY)
        await tracker.update_component("websocket", HealthStatus.DEGRADED)

        # Callbacks triggered for: UNKNOWN->HEALTHY and HEALTHY->DEGRADED
        assert len(changes) == 2
        assert changes[0] == ("websocket", HealthStatus.UNKNOWN, HealthStatus.HEALTHY)
        assert changes[1] == ("websocket", HealthStatus.HEALTHY, HealthStatus.DEGRADED)

    async def test_degraded_status_creates_badge(self, tracker, badge_collector):
        """Test that degraded status creates a health badge."""
        badges, collect = badge_collector
        tracker.register_badge_callback(collect)

        await tracker.update_component(
            "database",
            HealthStatus.DEGRADED,
            error_message="Connection slow",
        )

        # Should have created a badge
        badge_badges = [b for b in badges if b.badge_id == "database_degraded"]
        assert len(badge_badges) == 1
        assert badge_badges[0].status == HealthStatus.DEGRADED

    async def test_healthy_status_removes_degraded_badge(
        self, tracker, badge_collector
    ):
        """Test that returning to healthy status removes the degraded badge."""
        badges, collect = badge_collector
        tracker.register_badge_callback(collect)

        # First degrade, then recover
        await tracker.update_component("websocket", HealthStatus.DEGRADED)
        await tracker.update_component("websocket", HealthStatus.HEALTHY)

        # Find the removal badge (empty title signals removal)
        removal_badges = [b for b in badges if b.badge_id.startswith("websocket_") and b.title == ""]
        assert len(removal_badges) >= 1

    async def test_overall_status_aggregation(self, tracker):
        """Test that overall status is correctly aggregated."""
        # Start with unknown
        assert tracker.get_overall_status() == HealthStatus.UNKNOWN

        # Add healthy component
        await tracker.update_component("db1", HealthStatus.HEALTHY)
        assert tracker.get_overall_status() == HealthStatus.HEALTHY

        # Add degraded component
        await tracker.update_component("db2", HealthStatus.DEGRADED)
        assert tracker.get_overall_status() == HealthStatus.DEGRADED

        # Add unhealthy component
        await tracker.update_component("db3", HealthStatus.UNHEALTHY)
        assert tracker.get_overall_status() == HealthStatus.UNHEALTHY

    async def test_dismiss_badge(self, tracker, badge_collector):
        """Test that badges can be dismissed."""
        badges, collect = badge_collector
        tracker.register_badge_callback(collect)

        await tracker.update_component("rate_limit", HealthStatus.DEGRADED)

        # Dismiss the badge
        result = tracker.dismiss_badge("rate_limit_degraded")
        assert result is True

        # Should no longer be in active badges
        active = tracker.get_active_badges()
        assert all(b.badge_id != "rate_limit_degraded" for b in active)

    async def test_cannot_dismiss_non_dismissible_badge(
        self, tracker, badge_collector
    ):
        """Test that non-dismissible badges cannot be dismissed."""
        badges, collect = badge_collector
        tracker.register_badge_callback(collect)

        # websocket_disconnected is configured as non-dismissible
        await tracker.update_component("websocket", HealthStatus.UNHEALTHY)

        result = tracker.dismiss_badge("websocket_unhealthy")
        assert result is False

    async def test_dismiss_nonexistent_badge(self, tracker):
        """Test that dismissing a non-existent badge returns False."""
        result = tracker.dismiss_badge("nonexistent_degraded")
        assert result is False

    async def test_get_all_health(self, tracker):
        """Test retrieving all component health records."""
        await tracker.update_component("comp1", HealthStatus.HEALTHY)
        await tracker.update_component("comp2", HealthStatus.DEGRADED)

        all_health = tracker.get_all_health()
        assert len(all_health) == 2
        assert all_health["comp1"].status == HealthStatus.HEALTHY
        assert all_health["comp2"].status == HealthStatus.DEGRADED

    async def test_to_dict_serialization(self, tracker):
        """Test that to_dict produces serializable output."""
        await tracker.update_component(
            "test_db",
            HealthStatus.DEGRADED,
            response_time_ms=150.5,
            error_message="Slow response",
            metadata={"query_count": 42},
        )

        data = tracker.to_dict()
        assert "overall_status" in data
        assert "checked_at" in data
        assert "components" in data
        assert "active_badges" in data

        # Check component data
        comp = data["components"]["test_db"]
        assert comp["status"] == "degraded"
        assert comp["response_time_ms"] == 150.5
        assert comp["error_message"] == "Slow response"
        assert comp["metadata"]["query_count"] == 42

    async def test_failure_and_recovery_counts(self, tracker):
        """Test that failure and recovery counts track transitions."""
        # First transition to UNHEALTHY (from UNKNOWN) - counts as failure
        await tracker.update_component("service", HealthStatus.UNHEALTHY)

        # Second transition to UNHEALTHY (must go through DEGRADED or HEALTHY)
        await tracker.update_component("service", HealthStatus.HEALTHY)
        await tracker.update_component("service", HealthStatus.UNHEALTHY)

        health = tracker.get_component_health("service")
        assert health.failure_count == 2  # Two transitions to UNHEALTHY
        assert health.recovery_count == 1  # One recovery

        # Another recovery
        await tracker.update_component("service", HealthStatus.DEGRADED)
        await tracker.update_component("service", HealthStatus.HEALTHY)
        health = tracker.get_component_health("service")
        assert health.recovery_count == 2

    async def test_auto_hide_badge(self, tracker, badge_collector):
        """Test that badges auto-hide after configured delay."""
        badges, collect = badge_collector
        tracker.register_badge_callback(collect)

        # Use 'rate_limit_approaching' which has auto_hide_after_seconds=60 in config
        # We'll manually test the auto-hide mechanism
        badge_id = "rate_limit_degraded"

        # Create badge manually with auto-hide
        from layer4_agents.services.health_tracker import HealthBadge
        badge = HealthBadge(
            badge_id=badge_id,
            title="Test",
            message="Test message",
            status=HealthStatus.DEGRADED,
            icon="test",
            priority=5,
            dismissible=True,
            auto_hide_after_seconds=0,  # Very short for testing
        )
        # Documented private-member handshake (intentional test seam):
        # the health tracker exposes no public API to create a badge that
        # auto-hides on a short delay — AUTO_HIDE_AFTER_SECONDS only ships
        # 60s configurations, which is too long for a unit test. The badge
        # must therefore be injected directly into the private registry and
        # the auto-hide coroutine driven manually. The assertions below stay
        # on the public get_active_badges() surface so real behavior, not
        # internals, is verified; if the internals change, this seam (and
        # this comment) must be revisited.
        tracker._badges[badge_id] = badge

        # Start auto-hide task
        task = asyncio.create_task(tracker._auto_hide_badge(badge_id, 0))
        tracker._auto_hide_tasks.add(task)
        task.add_done_callback(tracker._auto_hide_tasks.discard)

        # Deterministic wait until the auto-hide task removes the badge.
        await wait_until(
            lambda: all(b.badge_id != badge_id for b in tracker.get_active_badges()),
            description="badge auto-hidden",
        )

    async def test_callback_exception_handling(self, tracker):
        """Test that exceptions in callbacks are handled gracefully."""
        def failing_callback(badge):
            raise ValueError("Callback failure")

        tracker.register_badge_callback(failing_callback)

        # Should not raise despite callback failure
        await tracker.update_component("test", HealthStatus.DEGRADED)

        # Component should still be updated
        health = tracker.get_component_health("test")
        assert health is not None


class TestGetHealthTracker:
    """Test suite for get_health_tracker singleton."""

    def test_singleton_returns_same_instance(self):
        """Test that get_health_tracker returns the same instance."""
        tracker1 = get_health_tracker()
        tracker2 = get_health_tracker()
        assert tracker1 is tracker2

    def test_singleton_is_global(self):
        """Test that singleton is truly global."""
        # Reset by accessing private global
        import layer4_agents.services.health_tracker as ht_module

        original = ht_module._health_tracker
        try:
            ht_module._health_tracker = None
            new_tracker = get_health_tracker()
            assert new_tracker is not None
            assert get_health_tracker() is new_tracker
        finally:
            # Restore original
            ht_module._health_tracker = original


class TestHealthStatusEnum:
    """Test suite for HealthStatus enum."""

    def test_enum_values(self):
        """Test that enum has expected values."""
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.DEGRADED.value == "degraded"
        assert HealthStatus.UNHEALTHY.value == "unhealthy"
        assert HealthStatus.UNKNOWN.value == "unknown"

    def test_enum_is_string(self):
        """Test that HealthStatus is a string enum."""
        assert isinstance(HealthStatus.HEALTHY, str)
        assert HealthStatus.HEALTHY == "healthy"
