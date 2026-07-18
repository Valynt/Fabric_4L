from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class CRMModel(StrEnum):
    """Canonical models supported by CRM connectors."""

    ACCOUNT = "account"
    CONTACT = "contact"
    OPPORTUNITY = "opportunity"
    ENGAGEMENT = "engagement"


@dataclass(frozen=True, slots=True)
class SyncCursor:
    """Opaque pagination token; string form is JSON-serializable."""

    value: str | None = None

    def __str__(self) -> str:
        return self.value or ""


@dataclass(frozen=True, slots=True)
class CanonicalRecord:
    """Provider-neutral record emitted by a connector and consumed by the SyncEngine."""

    model: CRMModel
    remote_id: str
    remote_modified_at: datetime | None = None
    remote_deleted_at: datetime | None = None
    # Canonical scalar fields — always present names regardless of provider.
    canonical: dict[str, Any] = field(default_factory=dict)
    # Provider-specific supplemental fields preserved for round-tripping / provenance.
    supplemental: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CRMOperationResult:
    """Result of a connector write operation."""

    success: bool
    remote_id: str | None = None
    error_code: str | None = None
    error_message: str | None = None
