from __future__ import annotations

from value_fabric.shared.error_handling.exceptions import NotFoundError, ValidationError
"""Health Badges API for graceful degradation visibility.

Provides endpoints for:
- Current health status of all components
- Active health badges for UI display
- WebSocket connection status
- Component health history
"""


import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from value_fabric.shared.models.typed_dict import TypedDictModel

from ...api.websocket import get_ws_manager
from ...services.health_tracker import HealthStatus, HealthTracker, get_health_tracker


class report_connection_qualityResult(TypedDictModel):
    assessed_quality: Any
    received: bool
    timestamp: Any

from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_authenticated

logger = logging.getLogger(__name__)
health_badges_router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================


class ComponentHealthInfo(BaseModel):
    """Health information for a single component."""

    name: str
    status: str
    last_checked: str
    response_time_ms: float | None
    error_message: str | None
    failure_count: int
    recovery_count: int
    metadata: dict[str, Any]


class HealthBadgeInfo(BaseModel):
    """Health badge for UI display."""

    badge_id: str
    title: str
    message: str
    status: str
    icon: str
    priority: int
    dismissible: bool
    action_required: str | None
    created_at: str


class HealthStatusResponse(BaseModel):
    """Complete health status response."""

    overall_status: str
    checked_at: str
    components: dict[str, ComponentHealthInfo]
    active_badges: list[HealthBadgeInfo]
    degraded_components: list[str]
    healthy_components: list[str]


class WebSocketStatusResponse(BaseModel):
    """WebSocket connection status."""

    status: str = Field(..., description="connected, disconnected, or connecting")
    active_workflows: int = Field(..., description="Number of workflows with active connections")
    total_connections: int
    reconnect_attempts: int
    last_event_id: str | None
    connection_quality: str = Field(..., description="excellent, good, fair, or poor")


class DismissBadgeRequest(BaseModel):
    """Request to dismiss a health badge."""

    badge_id: str


class DismissBadgeResponse(BaseModel):
    """Response from dismissing a badge."""

    success: bool
    message: str
    dismissed_badge_id: str


class ConnectionQualityRequest(BaseModel):
    """Request to report connection quality from client."""

    latency_ms: int
    packet_loss_percent: float = Field(default=0.0, ge=0.0, le=100.0)
    connection_type: str = Field(default="unknown", description="wifi, ethernet, cellular, unknown")


# ============================================================================
# API Routes
# ============================================================================


@health_badges_router.get("/health/detailed", response_model=HealthStatusResponse, tags=["health"])
async def get_detailed_health(
    tracker: HealthTracker = Depends(get_health_tracker),
    context: RequestContext = Depends(require_authenticated),
) -> HealthStatusResponse:
    """Get detailed health status of all system components.

    Returns comprehensive health information including:
    - Individual component status
    - Active health badges for UI display
    - Categorized component lists

    Example:
        GET /v1/health/detailed

        Returns:
        {
            "overall_status": "degraded",
            "checked_at": "2024-01-15T10:30:00Z",
            "components": {
                "postgres": {
                    "name": "postgres",
                    "status": "healthy",
                    "last_checked": "2024-01-15T10:30:00Z",
                    "response_time_ms": 15.5,
                    "error_message": null,
                    "failure_count": 0,
                    "recovery_count": 1,
                    "metadata": {}
                },
                "websocket": {
                    "name": "websocket",
                    "status": "degraded",
                    "last_checked": "2024-01-15T10:29:00Z",
                    "response_time_ms": null,
                    "error_message": "Reconnecting...",
                    "failure_count": 2,
                    "recovery_count": 0,
                    "metadata": {"reconnect_attempt": 2}
                }
            },
            "active_badges": [
                {
                    "badge_id": "websocket_degraded",
                    "title": "Live Updates Paused",
                    "message": "Reconnecting to server...",
                    "status": "degraded",
                    "icon": "wifi-off",
                    "priority": 1,
                    "dismissible": false,
                    "action_required": "Check network connection",
                    "created_at": "2024-01-15T10:29:00Z"
                }
            ],
            "degraded_components": ["websocket"],
            "healthy_components": ["postgres", "redis", "checkpoint"]
        }
    """
    data = tracker.to_dict()

    # Categorize components
    degraded = []
    healthy = []

    for name, component in data["components"].items():
        if component["status"] in ["degraded", "unhealthy"]:
            degraded.append(name)
        elif component["status"] == "healthy":
            healthy.append(name)

    return HealthStatusResponse(
        overall_status=data["overall_status"],
        checked_at=data["checked_at"],
        components={name: ComponentHealthInfo(**info) for name, info in data["components"].items()},
        active_badges=[HealthBadgeInfo(**badge) for badge in data["active_badges"]],
        degraded_components=degraded,
        healthy_components=healthy,
    )


@health_badges_router.get("/health/badges", response_model=list[HealthBadgeInfo], tags=["health"])
async def get_active_badges(
    priority_filter: int | None = Query(None, description="Filter by max priority"),
    tracker: HealthTracker = Depends(get_health_tracker),
    context: RequestContext = Depends(require_authenticated),
) -> list[HealthBadgeInfo]:
    """Get active health badges for UI display.

    Returns health badges sorted by priority (most important first).
    Use priority_filter to only show critical badges.

    Example:
        GET /v1/health/badges
        GET /v1/health/badges?priority_filter=3
    """
    badges = tracker.get_active_badges()

    if priority_filter is not None:
        badges = [b for b in badges if b.priority <= priority_filter]

    return [
        HealthBadgeInfo(
            badge_id=b.badge_id,
            title=b.title,
            message=b.message,
            status=b.status.value,
            icon=b.icon,
            priority=b.priority,
            dismissible=b.dismissible,
            action_required=b.action_required,
            created_at=b.created_at.isoformat(),
        )
        for b in badges
    ]


@health_badges_router.get(
    "/health/websocket", response_model=WebSocketStatusResponse, tags=["health"]
)
async def get_websocket_status(
    context: RequestContext = Depends(require_authenticated),
) -> WebSocketStatusResponse:
    """Get WebSocket connection status.

    Returns real-time information about WebSocket infrastructure:
    - Connection status
    - Active workflow streams
    - Connection quality metrics

    Example:
        GET /v1/health/websocket
    """
    ws_manager = get_ws_manager()

    # Count active connections
    active_workflows = len(ws_manager._workflow_connections)
    total_connections = sum(len(conns) for conns in ws_manager._workflow_connections.values())

    # Determine status
    tracker = get_health_tracker()
    ws_health = tracker.get_component_health("websocket") if tracker else None

    if ws_health and ws_health.status == HealthStatus.HEALTHY:
        status = "connected"
        quality = "excellent"
    elif ws_health and ws_health.status == HealthStatus.DEGRADED:
        status = "connecting"
        quality = "fair"
    else:
        status = "disconnected"
        quality = "poor"

    return WebSocketStatusResponse(
        status=status,
        active_workflows=active_workflows,
        total_connections=total_connections,
        reconnect_attempts=ws_health.metadata.get("reconnect_attempts", 0) if ws_health else 0,
        last_event_id=None,  # Would track per-connection
        connection_quality=quality,
    )


@health_badges_router.post(
    "/health/badges/dismiss", response_model=DismissBadgeResponse, tags=["health"]
)
async def dismiss_badge(
    request: DismissBadgeRequest,
    tracker: HealthTracker = Depends(get_health_tracker),
    context: RequestContext = Depends(require_authenticated),
) -> DismissBadgeResponse:
    """Dismiss a health badge.

    Some badges are dismissible (marked with dismissible=true).
    Critical badges cannot be dismissed.

    Example:
        POST /v1/health/badges/dismiss
        {"badge_id": "rate_limit_approaching"}
    """
    success = tracker.dismiss_badge(request.badge_id)

    if success:
        return DismissBadgeResponse(
            success=True,
            message=f"Badge {request.badge_id} dismissed",
            dismissed_badge_id=request.badge_id,
        )
    else:
        raise ValidationError(message = str(f"Badge {request.badge_id} not found or cannot be dismissed"))


@health_badges_router.post("/health/report-connection-quality", tags=["health"])
async def report_connection_quality(
    request: ConnectionQualityRequest,
    tracker: HealthTracker = Depends(get_health_tracker),
    context: RequestContext = Depends(require_authenticated),
) -> dict[str, Any]:
    """Report connection quality metrics from client.

    Clients should report latency and packet loss periodically
    to help assess connection quality. This informs health badges.

    Example:
        POST /v1/health/report-connection-quality
        {
            "latency_ms": 150,
            "packet_loss_percent": 0.5,
            "connection_type": "wifi"
        }
    """
    # Determine connection quality
    quality = "excellent"
    if request.latency_ms > 500 or request.packet_loss_percent > 5:
        quality = "poor"
        await tracker.update_component(
            "websocket",
            HealthStatus.DEGRADED,
            error_message=f"High latency ({request.latency_ms}ms) or packet loss ({request.packet_loss_percent}%)",
            metadata={
                "latency_ms": request.latency_ms,
                "packet_loss": request.packet_loss_percent,
                "connection_type": request.connection_type,
            },
        )
    elif request.latency_ms > 200 or request.packet_loss_percent > 1:
        quality = "fair"
    elif request.latency_ms > 100:
        quality = "good"

    # Update component health if not already degraded
    current = tracker.get_component_health("websocket")
    if current and current.status != HealthStatus.DEGRADED:
        await tracker.update_component(
            "websocket",
            HealthStatus.HEALTHY,
            response_time_ms=request.latency_ms,
            metadata={
                "latency_ms": request.latency_ms,
                "packet_loss": request.packet_loss_percent,
                "connection_type": request.connection_type,
                "quality": quality,
            },
        )

    return report_connection_qualityResult.model_validate({
        "received": True,
        "assessed_quality": quality,
        "timestamp": datetime.now(UTC).isoformat(),
    })


@health_badges_router.get(
    "/health/components/{component_name}", response_model=ComponentHealthInfo, tags=["health"]
)
async def get_component_health(
    component_name: str,
    tracker: HealthTracker = Depends(get_health_tracker),
    context: RequestContext = Depends(require_authenticated),
) -> ComponentHealthInfo:
    """Get detailed health status of a specific component.

    Example:
        GET /v1/health/components/postgres
    """
    health = tracker.get_component_health(component_name)

    if not health:
        raise NotFoundError(message = str(f"Component {component_name} not found or has no health data"))

    return ComponentHealthInfo(
        name=health.name,
        status=health.status.value,
        last_checked=health.last_checked.isoformat(),
        response_time_ms=health.response_time_ms,
        error_message=health.error_message,
        failure_count=health.failure_count,
        recovery_count=health.recovery_count,
        metadata=health.metadata,
    )
