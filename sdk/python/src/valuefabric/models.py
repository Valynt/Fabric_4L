"""Lightweight Pydantic models for the Value Fabric SDK."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class Tenant(BaseModel):
    id: UUID
    name: str
    slug: str
    status: str
    settings: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class User(BaseModel):
    id: UUID
    tenant_id: UUID
    email: str
    display_name: str | None = None
    role: str
    status: str
    last_login_at: datetime | None = None
    invited_by: UUID | None = None
    created_at: datetime
    updated_at: datetime


class APIKey(BaseModel):
    key_id: str
    tenant_id: UUID
    user_id: UUID | None = None
    name: str
    prefix: str
    role: str
    permissions: frozenset[str] = Field(default_factory=frozenset)
    enabled: bool = True
    created_at: datetime
    expires_at: datetime | None = None
    last_used_at: datetime | None = None
    rate_limit_per_minute: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class APIKeyCreateResult(BaseModel):
    key_id: str
    tenant_id: UUID
    name: str
    api_key: str
    prefix: str
    role: str
    permissions: frozenset[str] = Field(default_factory=frozenset)
    expires_at: datetime | None = None
    rate_limit_per_minute: int | None = None
    created_at: datetime


class Workflow(BaseModel):
    workflow_instance_id: str
    workflow_type: str
    status: str
    current_state: str | None = None
    current_node: str | None = None
    progress_percentage: float = 0.0
    started_at: str | None = None
    completed_at: str | None = None
    error_count: int = 0
    has_output: bool = False
    results: dict[str, Any] | None = None
    tenant_id: str | None = None
    user_id: str | None = None
    priority: int | None = None
    scheduler_status: str | None = None


class WorkflowTypeInfo(BaseModel):
    type: str
    name: str
    description: str


class ModelVersion(BaseModel):
    id: UUID
    tenant_id: UUID
    provider: str
    model_name: str
    model_version: str
    stage: str
    promoted_by: UUID | None = None
    eval_score: float | None = None
    eval_run_id: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)
    created_at: str


class FeatureFlag(BaseModel):
    id: UUID
    tenant_id: UUID | None = None
    flag_key: str
    enabled: bool
    rollout_percentage: int = 0
    description: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str
    updated_at: str
    updated_by: UUID | None = None


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    timestamp: str
    executor_ready: bool
    uptime_seconds: float
    dependencies: list[dict[str, Any]] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
