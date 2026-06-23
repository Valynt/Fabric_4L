from __future__ import annotations

from value_fabric.shared.error_handling.exceptions import AuthenticationError, NotFoundError

"""Tenant-scoped notification feed routes."""


from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_authenticated

router = APIRouter(prefix="/notifications", tags=["notifications"])


class NotificationRecord(BaseModel):
    id: str
    account_id: str | None = None
    subject_id: str | None = None
    subject_type: str | None = None
    type: str
    title: str
    message: str
    read: bool = False
    created_at: str
    updated_at: str


class NotificationListResponse(BaseModel):
    items: list[NotificationRecord]
    total: int
    unread_count: int


class CreateNotificationRequest(BaseModel):
    account_id: str | None = None
    subject_id: str | None = None
    subject_type: str | None = None
    type: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=240)
    message: str = Field(min_length=1, max_length=1000)


_NOTIFICATIONS_BY_TENANT: dict[str, dict[str, NotificationRecord]] = {}


def _tenant_key(ctx: RequestContext) -> str:
    if ctx.tenant_id is None:
        raise AuthenticationError(message = "Validated tenant context required")
    return str(ctx.tenant_id)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def create_notification_record(
    *,
    tenant_id: str,
    notification_type: str,
    title: str,
    message: str,
    account_id: str | None = None,
    subject_id: str | None = None,
    subject_type: str | None = None,
) -> NotificationRecord:
    """Persist an unread in-app notification for the tenant."""
    now = _now_iso()
    notification = NotificationRecord(
        id=f"notif-{uuid4()}",
        account_id=account_id,
        subject_id=subject_id,
        subject_type=subject_type,
        type=notification_type,
        title=title,
        message=message,
        read=False,
        created_at=now,
        updated_at=now,
    )
    _NOTIFICATIONS_BY_TENANT.setdefault(tenant_id, {})[notification.id] = notification
    return notification


@router.get("", response_model=NotificationListResponse)
async def list_notifications(
    read: bool | None = Query(default=None),
    account_id: str | None = Query(default=None),
    ctx: RequestContext = Depends(require_authenticated),
) -> NotificationListResponse:
    """List tenant-scoped in-app notifications."""
    notifications = list(_NOTIFICATIONS_BY_TENANT.get(_tenant_key(ctx), {}).values())
    if read is not None:
        notifications = [notification for notification in notifications if notification.read is read]
    if account_id:
        notifications = [notification for notification in notifications if notification.account_id == account_id]
    notifications.sort(key=lambda notification: notification.created_at, reverse=True)
    return NotificationListResponse(
        items=notifications,
        total=len(notifications),
        unread_count=sum(1 for notification in notifications if not notification.read),
    )


@router.post("", response_model=NotificationRecord, status_code=status.HTTP_201_CREATED)
async def create_notification(
    request: CreateNotificationRequest,
    ctx: RequestContext = Depends(require_authenticated),
) -> NotificationRecord:
    """Create a tenant-scoped notification for validation and explicit workflow events."""
    return create_notification_record(
        tenant_id=_tenant_key(ctx),
        notification_type=request.type.strip(),
        title=request.title.strip(),
        message=request.message.strip(),
        account_id=request.account_id,
        subject_id=request.subject_id,
        subject_type=request.subject_type,
    )


@router.patch("/{notification_id}/read", response_model=NotificationRecord)
async def mark_notification_read(
    notification_id: str,
    ctx: RequestContext = Depends(require_authenticated),
) -> NotificationRecord:
    """Mark a tenant-scoped notification as read."""
    tenant_notifications = _NOTIFICATIONS_BY_TENANT.get(_tenant_key(ctx), {})
    notification = tenant_notifications.get(notification_id)
    if notification is None:
        raise NotFoundError(message = "Notification not found")

    notification = notification.model_copy(update={"read": True, "updated_at": _now_iso()})
    tenant_notifications[notification_id] = notification
    return notification
