"""Contract checks for the shared Layer-5 response/request DTOs.

The canonical Layer-5 payload DTOs now live in
``value_fabric.shared.contracts.layer5_payloads`` (consumed by the Layer-4
``integration.layer5_client``). These tests assert, deterministically without
live services, that each DTO validates a canonical well-formed payload and
rejects a structurally-wrong one (absent required field).
"""

from __future__ import annotations

import pytest
from value_fabric.shared.contracts.layer5_payloads import (
    L5GetFreshnessSummaryResult,
    L5GetMaturityLadderResult,
    L5GetStaleTruthsResult,
    L5GetTruthAuditResult,
    L5GetTruthResult,
    L5ListTruthsResult,
    L5SubmitTruthResult,
    L5SyncValidatedTruthsResult,
    L5ValidateTruthResult,
)

pytestmark = pytest.mark.contract_static_no_service

# DTOs with at least one required (no-default) field: missing it must fail
# closed with a ValidationError, never silently pass.
# name -> (DTO, canonical payload, payload missing a required field)
_REJECT_CASES: list[tuple[str, type, dict, dict]] = [
    (
        "sync_validated_truths",
        L5SyncValidatedTruthsResult,
        {"synced": 3, "failed": 1, "error": ""},
        {"synced": 3, "failed": 1},
    ),
    (
        "submit_truth",
        L5SubmitTruthResult,
        {"error": ""},
        {},
    ),
    (
        "list_truths",
        L5ListTruthsResult,
        {"items": [], "total": 0, "error": None},
        {"items": [], "error": None},
    ),
    (
        "validate_truth",
        L5ValidateTruthResult,
        {"error": None, "truth_object_id": "abc-123"},
        {"truth_object_id": "abc-123"},
    ),
]

# DTOs whose every field is optional (all defaults) — assert they validate a
# canonical payload and reject a type-incoherent one where a typed field is
# malformed.
# name -> (DTO, canonical payload, type-broken payload)
_TYPE_BROKEN_CASES: list[tuple[str, type, dict, dict]] = [
    (
        "get_truth_audit",
        L5GetTruthAuditResult,
        {"error": None, "events": []},
        # events is typed list[Any]; a non-list must fail closed.
        {"events": "not-a-list"},
    ),
    (
        "get_freshness_summary",
        L5GetFreshnessSummaryResult,
        {"error": None, "total_count": 0},
        {"total_count": "not-an-int"},
    ),
    (
        "get_stale_truths",
        L5GetStaleTruthsResult,
        {"error": None, "items": [], "total": 0},
        {"total": "not-an-int"},
    ),
]

# DTOs that carry only a loose ``error`` field (accept any payload by design).
# Assert they accept a canonical payload so the contract stays stable.
_ERROR_ONLY_CASES: list[tuple[str, type]] = [
    ("get_truth", L5GetTruthResult),
    ("get_maturity_ladder", L5GetMaturityLadderResult),
]


@pytest.mark.parametrize(
    "name,klass,ok,broken",
    _REJECT_CASES,
    ids=[c[0] for c in _REJECT_CASES],
)
def test_l5_dto_validates_canonical_and_rejects_missing_required(name, klass, ok, broken) -> None:
    """Each required-field L5 DTO accepts canonical payload, rejects missing field."""
    parsed = klass.model_validate(ok)
    assert parsed is not None
    with pytest.raises(Exception):
        klass.model_validate(broken)


@pytest.mark.parametrize(
    "name,klass,ok,broken",
    _TYPE_BROKEN_CASES,
    ids=[c[0] for c in _TYPE_BROKEN_CASES],
)
def test_l5_dto_validates_canonical_and_rejects_type_broken(name, klass, ok, broken) -> None:
    """All-optional L5 DTOs accept canonical, reject a malformed typed field."""
    parsed = klass.model_validate(ok)
    assert parsed is not None
    with pytest.raises(Exception):
        klass.model_validate(broken)


@pytest.mark.parametrize("name,klass", _ERROR_ONLY_CASES, ids=[c[0] for c in _ERROR_ONLY_CASES])
def test_l5_error_only_dto_accepts_canonical_payload(name, klass) -> None:
    """error-only L5 DTOs remain stable: canonical payload validates."""
    parsed = klass.model_validate({"error": None})
    assert parsed is not None
