from __future__ import annotations

from value_fabric.shared.error_handling.exceptions import AuthenticationError
"""Tenant-scoped collaboration comment routes."""


from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_authenticated

from .notifications import create_notification_record

router = APIRouter(prefix="/comments", tags=["comments"])


class CommentRecord(BaseModel):
    id: str
    account_id: str | None = None
    subject_type: str
    subject_id: str
    body: str
    author: str
    created_at: str
    updated_at: str


class CommentListResponse(BaseModel):
    items: list[CommentRecord]
    total: int


class CreateCommentRequest(BaseModel):
    account_id: str | None = None
    subject_type: str = Field(min_length=1, max_length=80)
    subject_id: str = Field(min_length=1, max_length=160)
    body: str = Field(min_length=1, max_length=4000)


_COMMENTS_BY_TENANT: dict[str, dict[str, CommentRecord]] = {}


def _tenant_key(ctx: RequestContext) -> str:
    if ctx.tenant_id is None:
        raise AuthenticationError(message = "Validated tenant context required")
    return str(ctx.tenant_id)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


@router.get("", response_model=CommentListResponse)
async def list_comments(
    subject_type: str | None = Query(default=None),
    subject_id: str | None = Query(default=None),
    account_id: str | None = Query(default=None),
    ctx: RequestContext = Depends(require_authenticated),
) -> CommentListResponse:
    """List tenant-scoped comments with optional subject/account filters."""
    comments = list(_COMMENTS_BY_TENANT.get(_tenant_key(ctx), {}).values())
    if subject_type:
        comments = [comment for comment in comments if comment.subject_type == subject_type]
    if subject_id:
        comments = [comment for comment in comments if comment.subject_id == subject_id]
    if account_id:
        comments = [comment for comment in comments if comment.account_id == account_id]
    comments.sort(key=lambda comment: comment.created_at, reverse=True)
    return CommentListResponse(items=comments, total=len(comments))


@router.post("", response_model=CommentRecord, status_code=status.HTTP_201_CREATED)
async def create_comment(
    request: CreateCommentRequest,
    ctx: RequestContext = Depends(require_authenticated),
) -> CommentRecord:
    """Create a tenant-scoped comment that remains available after page reload."""
    tenant_id = _tenant_key(ctx)
    now = _now_iso()
    comment = CommentRecord(
        id=f"comment-{uuid4()}",
        account_id=request.account_id,
        subject_type=request.subject_type.strip(),
        subject_id=request.subject_id.strip(),
        body=request.body.strip(),
        author=str(ctx.user_id or "current-user"),
        created_at=now,
        updated_at=now,
    )
    _COMMENTS_BY_TENANT.setdefault(tenant_id, {})[comment.id] = comment
    create_notification_record(
        tenant_id=tenant_id,
        notification_type="comment_created",
        title="Comment posted",
        message=f"Comment posted on {comment.subject_type}:{comment.subject_id}",
        account_id=comment.account_id,
        subject_id=comment.id,
        subject_type="comment",
    )
    return comment
