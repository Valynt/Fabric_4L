from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from value_fabric.shared.error_handling.exceptions import NotFoundError

from app.core.database import db
from app.core.tenant_context import tenant_required
from app.models.schemas import PaginatedResponse, ReviewComment, ReviewRequest

router = APIRouter(prefix="/accounts/{account_id}", tags=["Reviews"])


@router.post("/reviews", response_model=ReviewRequest, status_code=201)
async def create_review_request(
    account_id: str,
    review: ReviewRequest,
    tenant_id: str = Depends(tenant_required),
):
    review.account_id = account_id
    review.tenant_id = tenant_id
    db.review_requests.insert(review.id, review)
    return review


@router.get("/reviews", response_model=PaginatedResponse[ReviewRequest])
async def list_review_requests(
    account_id: str,
    tenant_id: str = Depends(tenant_required),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    items = db.review_requests.list(
        tenant_id=tenant_id,
        filter_fn=lambda r: r.account_id == account_id,
        limit=limit,
        offset=offset,
    )
    total = db.review_requests.count(tenant_id=tenant_id, filter_fn=lambda r: r.account_id == account_id)
    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/reviews/{review_id}", response_model=ReviewRequest)
async def get_review_request(
    account_id: str,
    review_id: str,
    tenant_id: str = Depends(tenant_required),
):
    review = db.review_requests.get(review_id, tenant_id=tenant_id)
    if not review or review.account_id != account_id:
        raise NotFoundError(message="Review request not found")
    return review


@router.patch("/reviews/{review_id}", response_model=ReviewRequest)
async def update_review_request(
    account_id: str,
    review_id: str,
    fields: dict[str, Any],
    tenant_id: str = Depends(tenant_required),
):
    review = db.review_requests.get(review_id, tenant_id=tenant_id)
    if not review or review.account_id != account_id:
        raise NotFoundError(message="Review request not found")
    updated = db.review_requests.update(review_id, tenant_id=tenant_id, **fields)
    return updated


@router.post("/reviews/{review_id}/comments", response_model=ReviewComment, status_code=201)
async def create_review_comment(
    account_id: str,
    review_id: str,
    comment: ReviewComment,
    tenant_id: str = Depends(tenant_required),
):
    review = db.review_requests.get(review_id, tenant_id=tenant_id)
    if not review or review.account_id != account_id:
        raise NotFoundError(message="Review request not found")
    comment.review_id = review_id
    comment.tenant_id = tenant_id
    db.review_comments.insert(comment.id, comment)
    # Append comment to review
    comments = review.comments + [comment]
    db.review_requests.update(review_id, tenant_id=tenant_id, comments=comments)
    return comment


@router.get("/reviews/{review_id}/comments", response_model=PaginatedResponse[ReviewComment])
async def list_review_comments(
    account_id: str,
    review_id: str,
    tenant_id: str = Depends(tenant_required),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    review = db.review_requests.get(review_id, tenant_id=tenant_id)
    if not review or review.account_id != account_id:
        raise NotFoundError(message="Review request not found")
    items = db.review_comments.list(
        tenant_id=tenant_id,
        filter_fn=lambda c: c.review_id == review_id,
        limit=limit,
        offset=offset,
    )
    total = db.review_comments.count(tenant_id=tenant_id, filter_fn=lambda c: c.review_id == review_id)
    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)
