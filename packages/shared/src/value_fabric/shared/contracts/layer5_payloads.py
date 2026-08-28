"""Canonical Layer 5 request/response payloads for the Layer 4 edge client.

These DTOs are the single source of truth for the shapes the
``Layer5GroundTruthClient`` accepts and returns. They live in the shared
``contracts`` package so a Layer 5 response-shape change fails the contract
test suite here instead of surfacing as a silent ``.get()`` misread in Layer 4.

Alignment target: ``contracts/openapi/layer5-ground-truth.json``.
"""

from __future__ import annotations

from typing import Any

from value_fabric.shared.models.typed_dict import TypedDictModel


class L5SyncValidatedTruthsRequest(TypedDictModel):
    """Body for POST /api/v1/truths/sync-kg."""

    organization_id: str


class L5SyncValidatedTruthsResult(TypedDictModel):
    detail: Any | None = None
    error: str
    failed: int
    synced: int


class L5SubmitTruthRequest(TypedDictModel):
    """Body for submitting a new TruthObject."""

    claim: str
    claim_type: str
    confidence: float
    organization_id: str
    applies_to: dict[str, object] | None = None
    sources: list[dict[str, object]] | None = None
    raw_extraction_data: dict[str, object] | None = None


class L5SubmitTruthResult(TypedDictModel):
    detail: Any | None = None
    error: str


class L5ListTruthsResult(TypedDictModel):
    error: Any
    items: list[Any]
    total: int


class L5ValidateTruthResult(TypedDictModel):
    error: Any
    truth_object_id: Any


class L5GetTruthResult(TypedDictModel):
    error: Any | None = None


class L5GetTruthAuditResult(TypedDictModel):
    error: Any | None = None
    events: list[Any] = []


class L5GetFreshnessSummaryResult(TypedDictModel):
    error: Any | None = None
    stale_count: int = 0
    fresh_count: int = 0
    expiring_soon_count: int = 0
    total_count: int = 0


class L5GetStaleTruthsResult(TypedDictModel):
    error: Any | None = None
    items: list[Any] = []
    total: int = 0
    limit: int = 0
    offset: int = 0
    has_more: bool = False


class L5GetMaturityLadderResult(TypedDictModel):
    error: Any | None = None


__all__ = [
    "L5GetFreshnessSummaryResult",
    "L5GetMaturityLadderResult",
    "L5GetStaleTruthsResult",
    "L5GetTruthAuditResult",
    "L5GetTruthResult",
    "L5ListTruthsResult",
    "L5SubmitTruthRequest",
    "L5SubmitTruthResult",
    "L5SyncValidatedTruthsRequest",
    "L5SyncValidatedTruthsResult",
    "L5ValidateTruthResult",
]