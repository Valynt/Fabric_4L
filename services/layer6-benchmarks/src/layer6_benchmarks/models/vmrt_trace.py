"""Persistent VMRT trace record model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

VMRTTraceStatus = Literal["draft", "validated", "production_ready", "rejected"]


@dataclass
class VMRTTraceRecord:
    """Tenant-scoped Value Modeling Reasoning Trace persistence record."""

    trace_id: str
    tenant_id: str
    schema_version: str
    status: VMRTTraceStatus
    trace: dict[str, Any]
    quality_score_overall: str | None = None
    production_ready: bool = False
    errors: list[str] = field(default_factory=list)
    reviewer: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    promoted_at: datetime | None = None
