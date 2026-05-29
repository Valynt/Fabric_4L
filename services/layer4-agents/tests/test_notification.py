from __future__ import annotations

"""Unit tests for NotificationService.

Tests quiet hours enforcement, event generation, and channel selection.
"""


import asyncio
from unittest.mock import MagicMock, patch

import pytest

from layer4_agents.models.pause_point import PauseSeverity
from layer4_agents.services.notification import (
    NotificationChannel,
    NotificationEvent,
    NotificationPreference,
    NotificationPriority,
    NotificationService,
)


class TestQuietHoursEnforcement:
    """Test suite for quiet hours channel suppression."""

    @pytest.fixture
    def service(self):
        """Create a fresh notification service."""
        return NotificationService()

    @pytest.fixture
    def user_with_quiet_hours(self, service):
        """Create a user with quiet hours configured (09:00-17:00)."""
        prefs = NotificationPreference(
            user_id="user-001",
            channels=[NotificationChannel.EMAIL, NotificationChannel.WEBHOOK, NotificationChannel.IN_APP],
            quiet_hours_start=9,
            quiet_hours_end=17,
        )
        service.set_user_preferences(prefs)
        return "user-001"

    def test_quiet_hours_suppresses_email_and_webhook(self, service, user_with_quiet_hours):
        """Test that quiet hours suppress email/webhook but allow in-app."""
        # Mock current time to be within quiet hours (10:00)
        mock_now = MagicMock()
        mock_now.hour = 10
        with patch('src.services.notification.datetime') as mock_datetime:
            mock_datetime.now.return_value = mock_now
            channels = service._get_channels_for_user(user_with_quiet_hours, PauseSeverity.WARNING)

        # Should only return IN_APP during quiet hours
        assert channels == [NotificationChannel.IN_APP]
        assert NotificationChannel.EMAIL not in channels
        assert NotificationChannel.WEBHOOK not in channels

    def test_quiet_hours_allow_in_app_only(self, service, user_with_quiet_hours):
        """Test that in-app notifications are allowed during quiet hours."""
        mock_now = MagicMock()
        mock_now.hour = 10
        with patch('src.services.notification.datetime') as mock_datetime:
            mock_datetime.now.return_value = mock_now
            channels = service._get_channels_for_user(user_with_quiet_hours, PauseSeverity.CRITICAL)

        # Even for CRITICAL severity, quiet hours should restrict to IN_APP
        assert channels == [NotificationChannel.IN_APP]

    def test_outside_quiet_hours_allows_all_channels(self, service, user_with_quiet_hours):
        """Test that outside quiet hours all configured channels are allowed."""
        # Mock current time to be outside quiet hours (20:00)
        mock_now = MagicMock()
        mock_now.hour = 20
        with patch('src.services.notification.datetime') as mock_datetime:
            mock_datetime.now.return_value = mock_now
            channels = service._get_channels_for_user(user_with_quiet_hours, PauseSeverity.WARNING)

        # Should return all configured channels when not in quiet hours
        assert NotificationChannel.IN_APP in channels
        assert NotificationChannel.EMAIL in channels
        assert NotificationChannel.WEBHOOK in channels

    def test_wrapped_quiet_hours_range(self, service):
        """Test quiet hours that wrap around midnight (22:00-08:00)."""
        prefs = NotificationPreference(
            user_id="user-002",
            channels=[NotificationChannel.EMAIL, NotificationChannel.IN_APP],
            quiet_hours_start=22,
            quiet_hours_end=8,
        )
        service.set_user_preferences(prefs)

        # Test at midnight (within quiet hours)
        mock_midnight = MagicMock()
        mock_midnight.hour = 0
        with patch('src.services.notification.datetime') as mock_datetime:
            mock_datetime.now.return_value = mock_midnight
            channels = service._get_channels_for_user("user-002", PauseSeverity.WARNING)
            assert channels == [NotificationChannel.IN_APP]

        # Test at noon (outside quiet hours)
        mock_noon = MagicMock()
        mock_noon.hour = 12
        with patch('src.services.notification.datetime') as mock_datetime:
            mock_datetime.now.return_value = mock_noon
            channels = service._get_channels_for_user("user-002", PauseSeverity.WARNING)
            assert NotificationChannel.EMAIL in channels

    def test_no_quiet_hours_allows_all_channels(self, service):
        """Test that users without quiet hours get all channels."""
        prefs = NotificationPreference(
            user_id="user-003",
            channels=[NotificationChannel.EMAIL, NotificationChannel.WEBHOOK, NotificationChannel.IN_APP],
            quiet_hours_start=None,
            quiet_hours_end=None,
        )
        service.set_user_preferences(prefs)

        channels = service._get_channels_for_user("user-003", PauseSeverity.WARNING)

        assert NotificationChannel.EMAIL in channels
        assert NotificationChannel.WEBHOOK in channels
        assert NotificationChannel.IN_APP in channels

    def test_null_user_returns_default_channels(self, service):
        """Test that null user returns default channels."""
        channels = service._get_channels_for_user(None, PauseSeverity.WARNING)
        # Should return default channels (IN_APP only by default)
        assert channels == [NotificationChannel.IN_APP]


class TestQuietHoursValidation:
    """Test suite for quiet hours preference validation."""

    @pytest.fixture
    def service(self):
        """Create a fresh notification service."""
        return NotificationService()

    def test_quiet_hours_start_out_of_range_raises_error(self, service):
        """Test that quiet_hours_start > 23 raises ValueError."""
        prefs = NotificationPreference(
            user_id="user-001",
            channels=[NotificationChannel.IN_APP],
            quiet_hours_start=25,  # Invalid
            quiet_hours_end=8,
        )

        with pytest.raises(ValueError, match="Quiet hours must be between 0-23"):
            service.set_user_preferences(prefs)

    def test_quiet_hours_end_out_of_range_raises_error(self, service):
        """Test that quiet_hours_end > 23 raises ValueError."""
        prefs = NotificationPreference(
            user_id="user-001",
            channels=[NotificationChannel.IN_APP],
            quiet_hours_start=22,
            quiet_hours_end=24,  # Invalid
        )

        with pytest.raises(ValueError, match="Quiet hours must be between 0-23"):
            service.set_user_preferences(prefs)

    def test_quiet_hours_negative_start_raises_error(self, service):
        """Test that negative quiet_hours_start raises ValueError."""
        prefs = NotificationPreference(
            user_id="user-001",
            channels=[NotificationChannel.IN_APP],
            quiet_hours_start=-1,
            quiet_hours_end=8,
        )

        with pytest.raises(ValueError, match="Quiet hours must be between 0-23"):
            service.set_user_preferences(prefs)

    def test_valid_quiet_hours_accepted(self, service):
        """Test that valid quiet hours are accepted."""
        prefs = NotificationPreference(
            user_id="user-001",
            channels=[NotificationChannel.IN_APP],
            quiet_hours_start=9,
            quiet_hours_end=17,
        )

        # Should not raise
        service.set_user_preferences(prefs)

        # Verify stored correctly
        stored = service.get_user_preferences("user-001")
        assert stored.quiet_hours_start == 9
        assert stored.quiet_hours_end == 17


class TestEventIdGeneration:
    """Test suite for event ID uniqueness and security."""

    @pytest.fixture
    def service(self):
        """Create a notification service."""
        return NotificationService()

    @pytest.mark.asyncio
    async def test_event_ids_are_unique_under_concurrent_load(self, service):
        """Test that concurrent event generation produces unique IDs."""
        event_ids = []
        workflow_id = "wf-concurrent-test"
        user_id = "user-concurrent"

        async def generate_event():
            event = await service.notify_workflow_paused(
                workflow_id=workflow_id,
                pause_point={"severity": "warning", "node": "test"},
                user_id=user_id,
            )
            return event.event_id

        # Generate 100 events concurrently
        tasks = [generate_event() for _ in range(100)]
        event_ids = await asyncio.gather(*tasks)

        # All IDs should be unique
        assert len(event_ids) == len(set(event_ids)), f"Found {len(event_ids) - len(set(event_ids))} duplicate IDs"

    @pytest.mark.asyncio
    async def test_event_id_format_is_secure(self, service):
        """Test that event IDs use secure random component."""
        event = await service.notify_workflow_paused(
            workflow_id="wf-123",
            pause_point={"severity": "warning", "node": "test"},
        )

        # Format: notif-{timestamp:.6f}-{workflow_id}-{secrets.token_hex(4)}
        parts = event.event_id.split("-")
        assert len(parts) >= 4, f"Unexpected event ID format: {event.event_id}"

        # The random component should be 8 hex characters (4 bytes)
        random_component = parts[-1]
        assert len(random_component) == 8, f"Random component should be 8 hex chars, got: {len(random_component)}"
        assert all(c in '0123456789abcdef' for c in random_component.lower()), "Random component should be hex"

    @pytest.mark.asyncio
    async def test_workflow_completed_event_ids_unique(self, service):
        """Test that workflow completed events also have unique IDs."""
        event_ids = []

        for i in range(50):
            event = await service.notify_workflow_completed(
                workflow_id=f"wf-{i}",
                status="completed",
            )
            event_ids.append(event.event_id)

        # All should be unique
        assert len(event_ids) == len(set(event_ids))

    @pytest.mark.asyncio
    async def test_checkpoint_event_ids_unique(self, service):
        """Test that checkpoint events have unique IDs."""
        event_ids = []

        for i in range(50):
            event = await service.notify_checkpoint_reached(
                workflow_id=f"wf-{i}",
                checkpoint_id=f"chk-{i}",
                node_name=f"node-{i}",
            )
            event_ids.append(event.event_id)

        assert len(event_ids) == len(set(event_ids))


class TestNotificationEventProperties:
    """Test suite for NotificationEvent dataclass."""

    def test_event_delivery_tracking_initialized(self):
        """Test that delivery tracking is initialized for all channels."""
        event = NotificationEvent(
            event_id="test-001",
            workflow_id="wf-001",
            tenant_id="tenant-001",
            user_id="user-001",
            event_type="test",
            title="Test",
            message="Test message",
            priority=NotificationPriority.NORMAL,
            channels=[NotificationChannel.IN_APP, NotificationChannel.EMAIL],
        )

        assert event.delivered[NotificationChannel.IN_APP] is False
        assert event.delivered[NotificationChannel.EMAIL] is False

    def test_event_delivery_tracking_single_channel(self):
        """Test delivery tracking with single channel."""
        event = NotificationEvent(
            event_id="test-002",
            workflow_id="wf-001",
            tenant_id=None,
            user_id=None,
            event_type="test",
            title="Test",
            message="Test message",
            priority=NotificationPriority.LOW,
            channels=[NotificationChannel.IN_APP],
        )

        assert len(event.delivered) == 1
        assert NotificationChannel.IN_APP in event.delivered
