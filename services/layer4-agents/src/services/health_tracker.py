from __future__ import annotations

"""Health tracking service for graceful degradation and status badges.

Provides real-time health status for:
- WebSocket connections
- Database connectivity
- Checkpoint storage
- External service dependencies
- Rate limiting status

Emits events when health status changes for UI badge updates.
"""


import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

from value_fabric.shared.models.typed_dict import TypedDictModel


class HealthTracker_to_dictResult(TypedDictModel):
    active_badges: Any
    checked_at: Any
    components: Any
    overall_status: Any

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    """Health status levels."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ComponentHealth:
    """Health status of a single component."""

    name: str
    status: HealthStatus
    last_checked: datetime
    response_time_ms: float | None = None
    error_message: str | None = None
    failure_count: int = 0
    recovery_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class HealthBadge:
    """Health badge for UI display."""

    badge_id: str
    title: str
    message: str
    status: HealthStatus
    icon: str  # Icon identifier for UI
    priority: int  # Display priority (lower = more important)
    dismissible: bool
    auto_hide_after_seconds: int | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    action_required: str | None = None  # Action user can take


# Default configuration constants
DEFAULT_CHECK_INTERVAL_SECONDS = 30
DEFAULT_STALE_THRESHOLD_MINUTES = 5

# Badge auto-hide timeouts (seconds)
AUTO_HIDE_AFTER_SECONDS = {
    "database_degraded": 300,
    "rate_limit_approaching": 60,
    "rate_limit_exceeded": 60,
    "high_load": 120,
}


class HealthTracker:
    """Tracks health status of all system components.

    Features:
    - Real-time component health monitoring
    - Automatic badge generation for degradations
    - Health status event callbacks
    - Connection resilience tracking
    - History of health transitions

    Example:
        tracker = HealthTracker()
        tracker.register_callback(lambda badge: print(f"Badge: {badge}"))

        # Update component status
        await tracker.update_component(
            "websocket",
            HealthStatus.DEGRADED,
            error_message="Reconnecting..."
        )
    """

    def __init__(self, check_interval_seconds: int = DEFAULT_CHECK_INTERVAL_SECONDS):
        """Initialize health tracker.

        Args:
            check_interval_seconds: How often to run health checks (must be >= 1)

        Raises:
            ValueError: If check_interval_seconds is less than 1
        """
        if check_interval_seconds < 1:
            raise ValueError(f"check_interval_seconds must be >= 1, got {check_interval_seconds}")
        self.check_interval = check_interval_seconds
        self._components: dict[str, ComponentHealth] = {}
        self._badges: dict[str, HealthBadge] = {}
        self._callbacks: list[Callable[[HealthBadge], None]] = []
        self._status_callbacks: list[Callable[[str, HealthStatus, HealthStatus], None]] = []
        self._check_task: asyncio.Task | None = None
        self._auto_hide_tasks: set[asyncio.Task] = set()
        self._lock = asyncio.Lock()

        # Badge priority mapping
        self._badge_configs = {
            "websocket_disconnected": {
                "title": "Live Updates Paused",
                "message": "Reconnecting to server...",
                "icon": "wifi-off",
                "priority": 1,
                "dismissible": False,
                "auto_hide_after_seconds": None,
            },
            "database_degraded": {
                "title": "Database Connection Slow",
                "message": "Some operations may take longer than usual.",
                "icon": "database-warning",
                "priority": 3,
                "dismissible": True,
                "auto_hide_after_seconds": AUTO_HIDE_AFTER_SECONDS["database_degraded"],
            },
            "database_unhealthy": {
                "title": "Database Unavailable",
                "message": "Data persistence temporarily unavailable.",
                "icon": "database-error",
                "priority": 1,
                "dismissible": False,
                "auto_hide_after_seconds": None,
            },
            "checkpoint_unavailable": {
                "title": "Workflow Resume Unavailable",
                "message": "Checkpointing is disabled. Workflows cannot be resumed.",
                "icon": "checkpoint-off",
                "priority": 5,
                "dismissible": True,
                "auto_hide_after_seconds": None,
            },
            "rate_limit_approaching": {
                "title": "Rate Limit Warning",
                "message": "You're approaching the API rate limit. Slow down to avoid throttling.",
                "icon": "speed-slow",
                "priority": 4,
                "dismissible": True,
                "auto_hide_after_seconds": AUTO_HIDE_AFTER_SECONDS["rate_limit_approaching"],
            },
            "rate_limit_exceeded": {
                "title": "Rate Limit Exceeded",
                "message": "API requests are being throttled. Please wait before making more requests.",
                "icon": "blocked",
                "priority": 2,
                "dismissible": False,
                "auto_hide_after_seconds": AUTO_HIDE_AFTER_SECONDS["rate_limit_exceeded"],
            },
            "high_load": {
                "title": "High System Load",
                "message": "The system is experiencing high load. Some operations may be delayed.",
                "icon": "load-high",
                "priority": 6,
                "dismissible": True,
                "auto_hide_after_seconds": AUTO_HIDE_AFTER_SECONDS["high_load"],
            },
        }

    async def start(self) -> None:
        """Start background health monitoring."""
        self._check_task = asyncio.create_task(self._health_check_loop())
        logger.info("Health tracker started")

    async def stop(self) -> None:
        """Stop health monitoring."""
        if self._check_task:
            self._check_task.cancel()
            try:
                await self._check_task
            except asyncio.CancelledError:
                pass

        # Cancel any pending auto-hide tasks
        for task in list(self._auto_hide_tasks):
            task.cancel()

        logger.info("Health tracker stopped")

    def register_badge_callback(self, callback: Callable[[HealthBadge], None]) -> None:
        """Register callback for badge events."""
        self._callbacks.append(callback)

    def register_status_callback(
        self, callback: Callable[[str, HealthStatus, HealthStatus], None]
    ) -> None:
        """Register callback for status changes.

        Callback receives (component_name, old_status, new_status).
        """
        self._status_callbacks.append(callback)

    async def update_component(
        self,
        name: str,
        status: HealthStatus,
        response_time_ms: float | None = None,
        error_message: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Update health status of a component.

        Automatically generates/deletes badges based on status changes.
        """
        async with self._lock:
            await self._do_component_update(name, status, response_time_ms, error_message, metadata)

    async def _update_badges_for_component(
        self, component: str, status: HealthStatus, error_message: str | None
    ) -> None:
        """Update badges based on component status change."""
        badge_id = f"{component}_{status.value}"

        if status == HealthStatus.HEALTHY:
            # Remove any degraded/unhealthy badges for this component
            for badge_id_to_remove in list(self._badges.keys()):
                if badge_id_to_remove.startswith(f"{component}_"):
                    removed_badge = self._badges.pop(badge_id_to_remove)
                    # Emit removal event (empty message signals removal)
                    removal_badge = HealthBadge(
                        badge_id=removed_badge.badge_id,
                        title="",
                        message="",
                        status=HealthStatus.HEALTHY,
                        icon="",
                        priority=0,
                        dismissible=True,
                    )
                    await self._emit_badge(removal_badge)
            return

        # Create or update badge for degraded/unhealthy status
        config = self._badge_configs.get(
            f"{component}_{status.value}",
            {
                "title": f"{component.title()} {status.value.title()}",
                "message": error_message or f"{component} is experiencing issues.",
                "icon": "warning",
                "priority": 5,
                "dismissible": status == HealthStatus.DEGRADED,
                "auto_hide_after_seconds": None,
            },
        )

        badge = HealthBadge(
            badge_id=badge_id,
            title=config["title"],
            message=config["message"],
            status=status,
            icon=config["icon"],
            priority=config["priority"],
            dismissible=config["dismissible"],
            auto_hide_after_seconds=config.get("auto_hide_after_seconds"),
            action_required=self._get_action_for_badge(badge_id),
        )

        self._badges[badge_id] = badge
        await self._emit_badge(badge)

        # Auto-hide if configured
        if badge.auto_hide_after_seconds:
            task = asyncio.create_task(
                self._auto_hide_badge(badge_id, badge.auto_hide_after_seconds)
            )
            self._auto_hide_tasks.add(task)
            task.add_done_callback(self._auto_hide_tasks.discard)

    async def _auto_hide_badge(self, badge_id: str, delay_seconds: int) -> None:
        """Automatically hide a badge after a delay."""
        await asyncio.sleep(delay_seconds)

        async with self._lock:
            if badge_id in self._badges:
                removed_badge = self._badges.pop(badge_id)
                # Emit removal
                removal_badge = HealthBadge(
                    badge_id=removed_badge.badge_id,
                    title="",
                    message="",
                    status=HealthStatus.HEALTHY,
                    icon="",
                    priority=0,
                    dismissible=True,
                )
                await self._emit_badge(removal_badge)

    def _get_action_for_badge(self, badge_id: str) -> str | None:
        """Get recommended action for a badge."""
        actions = {
            "websocket_disconnected": "Check network connection and wait for automatic reconnection",
            "database_unhealthy": "Contact support - data persistence unavailable",
            "rate_limit_exceeded": "Wait 60 seconds before making more requests",
        }
        return actions.get(badge_id)

    async def _emit_badge(self, badge: HealthBadge) -> None:
        """Emit badge to all registered callbacks."""
        for callback in self._callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(badge)
                else:
                    callback(badge)
            except Exception as e:
                logger.error(f"Badge callback error: {e}")

    def get_component_health(self, name: str) -> ComponentHealth | None:
        """Get health status of a specific component."""
        return self._components.get(name)

    def get_all_health(self) -> dict[str, ComponentHealth]:
        """Get health status of all components."""
        return dict(self._components)

    def get_active_badges(self) -> list[HealthBadge]:
        """Get all currently active health badges."""
        return sorted(
            list(self._badges.values()),
            key=lambda b: (b.status != HealthStatus.UNHEALTHY, b.priority),
        )

    def get_overall_status(self) -> HealthStatus:
        """Get overall system health status."""
        if not self._components:
            return HealthStatus.UNKNOWN

        statuses = [h.status for h in self._components.values()]

        if HealthStatus.UNHEALTHY in statuses:
            return HealthStatus.UNHEALTHY
        if HealthStatus.DEGRADED in statuses:
            return HealthStatus.DEGRADED
        if all(s == HealthStatus.HEALTHY for s in statuses):
            return HealthStatus.HEALTHY

        return HealthStatus.UNKNOWN

    def dismiss_badge(self, badge_id: str) -> bool:
        """Dismiss a badge by ID.

        Args:
            badge_id: The unique identifier of the badge to dismiss

        Returns:
            True if the badge was dismissed, False if not found or not dismissible
        """
        if badge_id in self._badges and self._badges[badge_id].dismissible:
            del self._badges[badge_id]
            return True
        return False

    async def _health_check_loop(self) -> None:
        """Background loop for periodic health checks."""
        while True:
            try:
                await asyncio.sleep(self.check_interval)
                await self._run_health_checks()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check loop error: {e}")

    async def _run_health_checks(self) -> None:
        """Run health checks on all components."""
        # Check for stale health data
        now = datetime.now(UTC)
        stale_threshold = timedelta(minutes=DEFAULT_STALE_THRESHOLD_MINUTES)

        # Collect stale components first (under lock)
        stale_components: list[str] = []
        async with self._lock:
            for name, health in self._components.items():
                if now - health.last_checked > stale_threshold:
                    if health.status == HealthStatus.HEALTHY:
                        stale_components.append(name)

        # Update stale components - use internal method that doesn't re-acquire lock
        # to avoid deadlock (update_component also acquires the lock)
        for name in stale_components:
            await self._update_component_internal(
                name, HealthStatus.UNKNOWN, error_message="Health check stale - no recent updates"
            )

    async def _update_component_internal(
        self,
        name: str,
        status: HealthStatus,
        response_time_ms: float | None = None,
        error_message: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Internal version of update_component that assumes lock is NOT held.

        Used by health check loop to avoid deadlock when called from _run_health_checks.
        """
        async with self._lock:
            await self._do_component_update(name, status, response_time_ms, error_message, metadata)

    async def _do_component_update(
        self,
        name: str,
        status: HealthStatus,
        response_time_ms: float | None = None,
        error_message: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Actual update logic - assumes caller holds the lock."""
        old_health = self._components.get(name)

        # Calculate counters: increment only on status transitions, preserve otherwise
        old_status = old_health.status if old_health else HealthStatus.UNKNOWN
        failure_count = old_health.failure_count if old_health else 0
        recovery_count = old_health.recovery_count if old_health else 0

        if old_status != status:
            # Status changed - update transition counters
            if status == HealthStatus.UNHEALTHY:
                failure_count += 1
            elif status == HealthStatus.HEALTHY and old_status in (
                HealthStatus.UNHEALTHY,
                HealthStatus.DEGRADED,
            ):
                recovery_count += 1

        health = ComponentHealth(
            name=name,
            status=status,
            last_checked=datetime.now(UTC),
            response_time_ms=response_time_ms,
            error_message=error_message,
            failure_count=failure_count,
            recovery_count=recovery_count,
            metadata=metadata or {},
        )

        self._components[name] = health

        # Notify on status change
        if old_status != status:
            # Notify status callbacks
            for callback in self._status_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(name, old_status, status)
                    else:
                        callback(name, old_status, status)
                except Exception as e:
                    logger.error(f"Status callback error: {e}")

            # Update badges
            await self._update_badges_for_component(name, status, error_message)

    def to_dict(self) -> dict[str, Any]:
        """Convert health status to dictionary for API response."""
        return HealthTracker_to_dictResult.model_validate({
            "overall_status": self.get_overall_status().value,
            "checked_at": datetime.now(UTC).isoformat(),
            "components": {
                name: {
                    "status": health.status.value,
                    "last_checked": health.last_checked.isoformat(),
                    "response_time_ms": health.response_time_ms,
                    "error_message": health.error_message,
                    "failure_count": health.failure_count,
                    "recovery_count": health.recovery_count,
                    "metadata": health.metadata,
                }
                for name, health in self._components.items()
            },
            "active_badges": [
                {
                    "badge_id": b.badge_id,
                    "title": b.title,
                    "message": b.message,
                    "status": b.status.value,
                    "icon": b.icon,
                    "priority": b.priority,
                    "dismissible": b.dismissible,
                    "action_required": b.action_required,
                    "created_at": b.created_at.isoformat(),
                }
                for b in self.get_active_badges()
            ],
        })


# Global singleton
_health_tracker: HealthTracker | None = None


def get_health_tracker() -> HealthTracker:
    """Get or create the global health tracker."""
    global _health_tracker
    if _health_tracker is None:
        _health_tracker = HealthTracker()
    return _health_tracker
