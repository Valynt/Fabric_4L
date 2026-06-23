from __future__ import annotations

from value_fabric.shared.error_handling.exceptions import AuthenticationError, NotFoundError

"""Tenant-scoped task workflow routes for collaboration validation."""


from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_authenticated

from .notifications import create_notification_record

router = APIRouter(prefix="/tasks", tags=["tasks"])


class TaskStatus(StrEnum):
    open = "open"
    in_progress = "in_progress"
    completed = "completed"


class TaskRecord(BaseModel):
    id: str
    title: str
    account_id: str | None = None
    assignee: str | None = None
    due_date: str | None = None
    stage: str | None = None
    status: TaskStatus = TaskStatus.open
    created_at: str
    updated_at: str


class TaskListResponse(BaseModel):
    items: list[TaskRecord]
    total: int


class CreateTaskRequest(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    account_id: str | None = None
    assignee: str | None = Field(default=None, max_length=160)
    due_date: str | None = None
    stage: str | None = Field(default=None, max_length=80)


class UpdateTaskRequest(BaseModel):
    status: TaskStatus | None = None
    assignee: str | None = Field(default=None, max_length=160)
    due_date: str | None = None
    stage: str | None = Field(default=None, max_length=80)


_TASKS_BY_TENANT: dict[str, dict[str, TaskRecord]] = {}


def _tenant_key(ctx: RequestContext) -> str:
    if ctx.tenant_id is None:
        raise AuthenticationError(message = "Validated tenant context required")
    return str(ctx.tenant_id)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    account_id: str | None = Query(default=None),
    status_filter: TaskStatus | None = Query(default=None, alias="status"),
    ctx: RequestContext = Depends(require_authenticated),
) -> TaskListResponse:
    """List tenant-scoped tasks with optional account and status filters."""
    tasks = list(_TASKS_BY_TENANT.get(_tenant_key(ctx), {}).values())
    if account_id:
        tasks = [task for task in tasks if task.account_id == account_id]
    if status_filter:
        tasks = [task for task in tasks if task.status == status_filter]
    tasks.sort(key=lambda task: task.updated_at, reverse=True)
    return TaskListResponse(items=tasks, total=len(tasks))


@router.post("", response_model=TaskRecord, status_code=status.HTTP_201_CREATED)
async def create_task(
    request: CreateTaskRequest,
    ctx: RequestContext = Depends(require_authenticated),
) -> TaskRecord:
    """Create a tenant-scoped task that remains available after page reload."""
    tenant_id = _tenant_key(ctx)
    now = _now_iso()
    task = TaskRecord(
        id=f"task-{uuid4()}",
        title=request.title.strip(),
        account_id=request.account_id,
        assignee=request.assignee,
        due_date=request.due_date,
        stage=request.stage,
        status=TaskStatus.open,
        created_at=now,
        updated_at=now,
    )
    _TASKS_BY_TENANT.setdefault(tenant_id, {})[task.id] = task
    create_notification_record(
        tenant_id=tenant_id,
        notification_type="task_created",
        title="Task created",
        message=f"Task created: {task.title}",
        account_id=task.account_id,
        subject_id=task.id,
        subject_type="task",
    )
    return task


@router.patch("/{task_id}", response_model=TaskRecord)
async def update_task(
    task_id: str,
    request: UpdateTaskRequest,
    ctx: RequestContext = Depends(require_authenticated),
) -> TaskRecord:
    """Update mutable task fields for the authenticated tenant only."""
    tenant_tasks = _TASKS_BY_TENANT.get(_tenant_key(ctx), {})
    task = tenant_tasks.get(task_id)
    if task is None:
        raise NotFoundError(message = "Task not found")

    update = request.model_dump(exclude_unset=True)
    task = task.model_copy(update={**update, "updated_at": _now_iso()})
    tenant_tasks[task_id] = task
    if request.status == TaskStatus.completed:
        create_notification_record(
            tenant_id=_tenant_key(ctx),
            notification_type="task_completed",
            title="Task completed",
            message=f"Task completed: {task.title}",
            account_id=task.account_id,
            subject_id=task.id,
            subject_type="task",
        )
    return task
