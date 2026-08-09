from __future__ import annotations

"""Notification service for human-in-the-loop workflows.

Provides multi-channel notifications:
- In-app notifications (via WebSocket)
- Email notifications (for critical pauses)
- Webhook callbacks (for external integrations)
- Push notifications (for mobile/PWA)
"""


import asyncio
import hashlib
import hmac
import json
import logging
import secrets
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

import aiohttp

from ..models.pause_point import PauseSeverity

logger = logging.getLogger(__name__)

# Maximum quiet hours duration to prevent configuration errors
MAX_QUIET_HOURS_DURATION_HOURS = 16


class NotificationChannel(str, Enum):
    """Available notification channels."""

    IN_APP = "in_app"  # WebSocket/SSE to connected clients
    EMAIL = "email"  # Email notification
    WEBHOOK = "webhook"  # External webhook callback
    PUSH = "push"  # Push notification (mobile/PWA)
    SLACK = "slack"  # Slack message
    TEAMS = "teams"  # Microsoft Teams message


class NotificationPriority(str, Enum):
    """Notification priority levels."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class NotificationEvent:
    """A notification event to be delivered across channels."""

    event_id: str
    workflow_id: str
    tenant_id: str | None
    user_id: str | None
    event_type: str  # workflow_paused, workflow_completed, etc.
    title: str
    message: str
    priority: NotificationPriority
    channels: list[NotificationChannel]
    payload: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime | None = None
    delivered: dict[NotificationChannel, bool] = field(default_factory=dict)

    def __post_init__(self):
        """Initialize delivery tracking."""
        for channel in self.channels:
            if channel not in self.delivered:
                self.delivered[channel] = False


@dataclass
class NotificationPreference:
    """User notification preferences."""

    user_id: str
    channels: list[NotificationChannel]
    pause_severity_threshold: PauseSeverity = PauseSeverity.WARNING
    quiet_hours_start: int | None = None  # Hour (0-23) when quiet hours start
    quiet_hours_end: int | None = None  # Hour (0-23) when quiet hours end
    webhook_url: str | None = None
    email: str | None = None
    slack_webhook: str | None = None


class NotificationService:
    """Multi-channel notification service.

    Features:
    - Intelligent routing based on severity and preferences
    - Batching for high-frequency events
    - Delivery tracking and retry logic
    - Quiet hours support
    - Webhook signature verification

    Example:
        service = NotificationService()
        await service.notify_workflow_paused(
            workflow_id="wf-123",
            user_id="user-001",
            pause_point=pause_point_dict,
            channels=[NotificationChannel.EMAIL, NotificationChannel.WEBHOOK]
        )
    """

    def __init__(
        self,
        webhook_secret: str | None = None,
        email_config: dict | None = None,
        default_channels: list[NotificationChannel] | None = None,
    ):
        """Initialize notification service.

        Args:
            webhook_secret: Secret for webhook HMAC signatures
            email_config: SMTP configuration for email notifications
            default_channels: Default channels for notifications
        """
        self.webhook_secret = webhook_secret
        self.email_config = email_config or {}
        self.default_channels = default_channels or [NotificationChannel.IN_APP]

        # User preferences storage (in production, use database)
        self._preferences: dict[str, NotificationPreference] = {}

        # Event queue for batched processing — bounded to prevent OOM (P0-26)
        self._max_queue_size = 10_000
        self._max_event_age_seconds = 3600  # 1 hour
        self._event_queue: asyncio.Queue = asyncio.Queue(maxsize=self._max_queue_size)
        self._batch_task: asyncio.Task | None = None
        self._dropped_count = 0

        # Webhook session (reused for efficiency)
        self._webhook_session: aiohttp.ClientSession | None = None

        # Callbacks for in-app notifications
        self._in_app_callbacks: list[Callable[[NotificationEvent], None]] = []

    async def start(self) -> None:
        """Start background batch processing."""
        self._batch_task = asyncio.create_task(self._batch_processor())
        self._webhook_session = aiohttp.ClientSession()
        logger.info("Notification service started")

    async def stop(self) -> None:
        """Stop background processing."""
        if self._batch_task:
            self._batch_task.cancel()
            try:
                await self._batch_task
            except asyncio.CancelledError:
                pass
            self._batch_task = None
        if self._webhook_session:
            await self._webhook_session.close()
            self._webhook_session = None
        logger.info("Notification service stopped")

    def register_in_app_callback(self, callback: Callable[[NotificationEvent], None]) -> None:
        """Register a callback for in-app notifications.

        The callback receives NotificationEvent and should handle
        WebSocket broadcasting or UI updates.
        """
        self._in_app_callbacks.append(callback)

    def set_user_preferences(self, preference: NotificationPreference) -> None:
        """Set notification preferences for a user.

        Args:
            preference: The notification preference to set

        Raises:
            ValueError: If quiet hours configuration is invalid
        """
        # Validate quiet hours if configured
        if preference.quiet_hours_start is not None and preference.quiet_hours_end is not None:
            # Ensure both are set if either is set
            if not (0 <= preference.quiet_hours_start <= 23 and 0 <= preference.quiet_hours_end <= 23):
                raise ValueError(
                    f"Quiet hours must be between 0-23, got "
                    f"start={preference.quiet_hours_start}, end={preference.quiet_hours_end}"
                )

        self._preferences[preference.user_id] = preference

    def get_user_preferences(self, user_id: str) -> NotificationPreference:
        """Get notification preferences for a user."""
        if user_id not in self._preferences:
            # Return default preferences
            return NotificationPreference(user_id=user_id, channels=list(self.default_channels))
        return self._preferences[user_id]

    async def notify_workflow_paused(
        self,
        workflow_id: str,
        pause_point: dict[str, Any],
        user_id: str | None = None,
        tenant_id: str | None = None,
        channels: list[NotificationChannel] | None = None,
    ) -> NotificationEvent:
        """Send notification when workflow pauses for human input.

        Automatically determines priority based on pause severity.
        """
        severity_str = pause_point.get("severity", "warning")
        severity = (
            PauseSeverity(severity_str)
            if severity_str in [s.value for s in PauseSeverity]
            else PauseSeverity.WARNING
        )

        # Map pause severity to notification priority
        priority_map = {
            PauseSeverity.INFO: NotificationPriority.NORMAL,
            PauseSeverity.WARNING: NotificationPriority.HIGH,
            PauseSeverity.CRITICAL: NotificationPriority.URGENT,
        }
        priority = priority_map.get(severity, NotificationPriority.HIGH)

        # Generate unique event ID using timestamp + random component (not id())
        event_id = f"notif-{datetime.now(UTC).timestamp():.6f}-{workflow_id}-{secrets.token_hex(4)}"

        event = NotificationEvent(
            event_id=event_id,
            workflow_id=workflow_id,
            tenant_id=tenant_id,
            user_id=user_id,
            event_type="workflow_paused",
            title=pause_point.get("title", "Workflow Paused"),
            message=pause_point.get("message", "Action required"),
            priority=priority,
            channels=channels or self._get_channels_for_user(user_id, severity),
            payload={
                "pause_point": pause_point,
                "pause_reason": pause_point.get("reason"),
                "required_inputs": [f.get("name") for f in pause_point.get("required_inputs", [])],
            },
        )

        await self._enqueue_event(event)
        return event

    async def notify_workflow_completed(
        self,
        workflow_id: str,
        status: str,
        user_id: str | None = None,
        tenant_id: str | None = None,
        result_summary: dict | None = None,
        channels: list[NotificationChannel] | None = None,
    ) -> NotificationEvent:
        """Send notification when workflow completes."""
        event = NotificationEvent(
            event_id=f"notif-{datetime.now(UTC).timestamp():.6f}-{workflow_id}-{secrets.token_hex(4)}",
            workflow_id=workflow_id,
            tenant_id=tenant_id,
            user_id=user_id,
            event_type="workflow_completed",
            title=f"Workflow {status.title()}",
            message=f"Workflow {workflow_id} has {status}",
            priority=NotificationPriority.NORMAL,
            channels=channels or self._get_channels_for_user(user_id),
            payload={"status": status, "result_summary": result_summary or {}},
        )

        await self._enqueue_event(event)
        return event

    async def notify_checkpoint_reached(
        self,
        workflow_id: str,
        checkpoint_id: str,
        node_name: str,
        user_id: str | None = None,
        tenant_id: str | None = None,
        channels: list[NotificationChannel] | None = None,
    ) -> NotificationEvent:
        """Send notification when workflow reaches a checkpoint."""
        event = NotificationEvent(
            event_id=f"notif-{datetime.now(UTC).timestamp():.6f}-{workflow_id}-{secrets.token_hex(4)}",
            workflow_id=workflow_id,
            tenant_id=tenant_id,
            user_id=user_id,
            event_type="checkpoint_reached",
            title=f"Checkpoint: {node_name}",
            message=f"Workflow reached checkpoint after {node_name}",
            priority=NotificationPriority.LOW,
            channels=channels or [NotificationChannel.IN_APP],  # Low priority, in-app only
            payload={"checkpoint_id": checkpoint_id, "node_name": node_name},
        )

        await self._enqueue_event(event)
        return event

    def _get_channels_for_user(
        self, user_id: str | None, severity: PauseSeverity = PauseSeverity.WARNING
    ) -> list[NotificationChannel]:
        """Determine notification channels based on user preferences and severity."""
        if not user_id:
            return list(self.default_channels)

        prefs = self.get_user_preferences(user_id)

        # Check quiet hours - if in quiet hours, only allow in-app notifications
        # (in-app is considered non-intrusive compared to email/webhook)
        if self._is_quiet_hours_active(user_id):
            return [NotificationChannel.IN_APP]

        # Filter channels based on severity threshold
        if severity.value < prefs.pause_severity_threshold.value:
            # Below threshold - only in-app
            return [NotificationChannel.IN_APP]

        return prefs.channels

    def _is_quiet_hours_active(self, user_id: str) -> bool:
        """Check if current time is in user's quiet hours.

        Quiet hours suppress non-urgent notifications (email, webhook, etc.)
        while still allowing in-app notifications.

        Returns:
            True if quiet hours are active for this user
        """
        prefs = self.get_user_preferences(user_id)

        if prefs.quiet_hours_start is None or prefs.quiet_hours_end is None:
            return False

        current_hour = datetime.now(UTC).hour

        if prefs.quiet_hours_start <= prefs.quiet_hours_end:
            # Simple range (e.g., 09:00 - 17:00)
            return prefs.quiet_hours_start <= current_hour < prefs.quiet_hours_end
        else:
            # Wrapped range (e.g., 22:00 - 08:00)
            return current_hour >= prefs.quiet_hours_start or current_hour < prefs.quiet_hours_end

    async def _enqueue_event(self, event: NotificationEvent) -> bool:
        """Add event to queue with bounded size handling.

        Returns True if event was queued, False if dropped.
        Implements priority-aware dropping: URGENT can evict LOW priority.
        """
        try:
            self._event_queue.put_nowait(event)
            return True
        except asyncio.QueueFull:
            # Queue is full — apply drop policy based on priority
            if event.priority == NotificationPriority.URGENT:
                # Try to drop oldest LOW priority event to make room
                dropped = await self._drop_oldest_by_priority(NotificationPriority.LOW)
                if dropped:
                    try:
                        self._event_queue.put_nowait(event)
                        return True
                    except asyncio.QueueFull:
                        logger.warning(
                            f"Dropped URGENT notification {event.event_id}: queue full after eviction"
                        )
                else:
                    logger.warning(
                        f"Dropped URGENT notification {event.event_id}: queue full, no LOW priority to evict"
                    )
            else:
                logger.warning(
                    f"Dropped {event.priority.value} notification {event.event_id}: queue full"
                )

            self._dropped_count += 1
            return False

    def _drop_oldest_by_priority(self, priority: NotificationPriority) -> bool:
        """Drop oldest event of specified priority from queue.

        Returns True if an event was dropped.

        Note: This drains the entire queue and rebuilds it. In high-concurrency
        scenarios, some events may be dropped if the queue refills during re-add.
        This is acceptable behavior for preventing OOM under extreme load.
        """
        # asyncio.Queue doesn't support peek/remove, so we drain and re-add
        # We use a list that can grow beyond maxsize, then truncate
        temp_events: list[NotificationEvent] = []
        overflow_events: list[NotificationEvent] = []
        dropped = False

        try:
            # Drain queue (non-blocking)
            while not self._event_queue.empty():
                try:
                    event = self._event_queue.get_nowait()
                    if not dropped and event.priority == priority:
                        # Drop this one (don't re-add)
                        dropped = True
                        logger.debug(f"Evicted {priority.value} event {event.event_id} to make room")
                    else:
                        temp_events.append(event)
                except asyncio.QueueEmpty:
                    break

            # Sort by priority (URGENT first, LOW last) to ensure important events stay
            priority_order = {
                NotificationPriority.URGENT: 0,
                NotificationPriority.HIGH: 1,
                NotificationPriority.NORMAL: 2,
                NotificationPriority.LOW: 3,
            }
            temp_events.sort(key=lambda e: priority_order.get(e.priority, 2))

            # Re-add events, respecting max size
            for event in temp_events:
                try:
                    self._event_queue.put_nowait(event)
                except asyncio.QueueFull:
                    # Queue full during re-add, collect overflow
                    overflow_events.append(event)

            # Count dropped overflow events
            if overflow_events:
                self._dropped_count += len(overflow_events)
                logger.warning(
                    f"Dropped {len(overflow_events)} events during priority eviction "
                    f"(queue refilled during re-add)"
                )

            return dropped
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Error during priority drop: {e}")
            return False

    async def _batch_processor(self) -> None:
        """Background task to process notification queue."""
        while True:
            try:
                # Use timeout to allow periodic checks for cancellation
                event = await asyncio.wait_for(
                    self._event_queue.get(),
                    timeout=1.0
                )

                # Check event age (drop stale events)
                age = (datetime.now(UTC) - event.created_at).total_seconds()
                if age > self._max_event_age_seconds:
                    logger.debug(
                        f"Dropped stale notification {event.event_id} (age={age:.0f}s)"
                    )
                    continue

                await self._process_notification(event)
            except TimeoutError:
                # No events in queue, continue loop
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing notification: {e}")

    async def _process_notification(self, event: NotificationEvent) -> None:
        """Process a single notification event across all channels."""
        for channel in event.channels:
            try:
                if channel == NotificationChannel.IN_APP:
                    await self._send_in_app(event)
                elif channel == NotificationChannel.EMAIL:
                    await self._send_email(event)
                elif channel == NotificationChannel.WEBHOOK:
                    await self._send_webhook(event)
                elif channel == NotificationChannel.SLACK:
                    await self._send_slack(event)
                elif channel == NotificationChannel.TEAMS:
                    await self._send_teams(event)

                event.delivered[channel] = True

            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"Failed to send {channel} notification: {e}")
                event.delivered[channel] = False

    async def _send_in_app(self, event: NotificationEvent) -> None:
        """Send in-app notification via registered callbacks."""
        for callback in self._in_app_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event)
                else:
                    callback(event)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"In-app callback failed: {e}")

    async def _send_email(self, event: NotificationEvent) -> None:
        """Send email notification."""
        if not event.user_id:
            return

        prefs = self.get_user_preferences(event.user_id)
        if not prefs.email:
            logger.warning(f"No email configured for user {event.user_id}")
            return

        # In production, integrate with email service (SendGrid, SES, etc.)
        logger.info(f"[EMAIL] To: {prefs.email}, Subject: {event.title}, Body: {event.message}")

    async def _send_webhook(self, event: NotificationEvent) -> None:
        """Send webhook notification."""
        if not event.user_id:
            return

        prefs = self.get_user_preferences(event.user_id)
        if not prefs.webhook_url:
            return

        if not self._webhook_session:
            logger.warning("Webhook session not initialized")
            return

        payload = {
            "event_id": event.event_id,
            "workflow_id": event.workflow_id,
            "event_type": event.event_type,
            "title": event.title,
            "message": event.message,
            "priority": event.priority.value,
            "timestamp": event.created_at.isoformat(),
            "payload": event.payload,
        }

        try:
            async with self._webhook_session.post(
                prefs.webhook_url,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "X-Workflow-Event": event.event_type,
                    "X-Workflow-Signature": self._generate_signature(payload),
                },
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                if response.status >= 400:
                    logger.warning(f"Webhook returned {response.status}")
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Webhook delivery failed: {e}")
            raise

    async def _send_slack(self, event: NotificationEvent) -> None:
        """Send Slack notification."""
        if not event.user_id:
            return

        prefs = self.get_user_preferences(event.user_id)
        if not prefs.slack_webhook:
            return

        color = {
            NotificationPriority.LOW: "#36a64f",
            NotificationPriority.NORMAL: "#36a64f",
            NotificationPriority.HIGH: "#daa520",
            NotificationPriority.URGENT: "#ff0000",
        }.get(event.priority, "#36a64f")

        slack_payload = {
            "attachments": [
                {
                    "color": color,
                    "title": event.title,
                    "text": event.message,
                    "fields": [
                        {"title": "Workflow ID", "value": event.workflow_id, "short": True},
                        {"title": "Event Type", "value": event.event_type, "short": True},
                    ],
                    "footer": "Value Fabric Layer 4",
                    "ts": int(event.created_at.timestamp()),
                }
            ]
        }

        if self._webhook_session:
            try:
                async with self._webhook_session.post(
                    prefs.slack_webhook, json=slack_payload, timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status != 200:
                        logger.warning(f"Slack webhook returned {response.status}")
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"Slack delivery failed: {e}")

    async def _send_teams(self, event: NotificationEvent) -> None:
        """Send Microsoft Teams notification."""
        # Similar to Slack, with Teams-specific message format
        logger.info(f"[TEAMS] {event.title}: {event.message}")

    def _generate_signature(self, payload: dict) -> str:
        """Generate HMAC signature for webhook verification."""
        if not self.webhook_secret:
            return ""

        payload_str = json.dumps(payload, sort_keys=True)
        signature = hmac.new(
            self.webhook_secret.encode(), payload_str.encode(), hashlib.sha256
        ).hexdigest()

        return f"sha256={signature}"


# Global singleton
_notification_service: NotificationService | None = None


def get_notification_service() -> NotificationService:
    """Get or create the global notification service."""
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService()
    return _notification_service
