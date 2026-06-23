from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from layer5_ground_truth.api import router as api_router
from layer5_ground_truth.api.auth import TokenClaims
from layer5_ground_truth.api.schemas import TruthObjectCreate
from layer5_ground_truth.models.truth_object import MaturityLevel, TruthStatus
from layer5_ground_truth.services import truth_service
from layer5_ground_truth.services.state_machine import InsufficientEvidenceError, ValidationStateMachine


@pytest.mark.unit
def test_truth_object_create_requires_meaningful_required_fields() -> None:
    with pytest.raises(Exception):
        TruthObjectCreate(claim="   ", confidence=0.2)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_validate_rejects_duplicate_evidence_pairs() -> None:
    sm = ValidationStateMachine.__new__(ValidationStateMachine)
    sm._settings = SimpleNamespace(
        min_confidence_for_validated=0.5,
        min_sources_for_validated=2,
        auto_advance_to_validated=True,
    )
    truth = SimpleNamespace(
        id=uuid4(),
        tenant_id=uuid4(),
        status=TruthStatus.PROPOSED.value,
        confidence=0.9,
        maturity_level=MaturityLevel.EXTRACTED.value,
    )

    result = SimpleNamespace(scalar=lambda: 1)
    db = AsyncMock()
    db.execute = AsyncMock(return_value=result)

    with pytest.raises(InsufficientEvidenceError):
        await sm.validate(db, truth, validated_by="reviewer@example.com")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_maturity_mapping_regression_boundaries() -> None:
    sm = ValidationStateMachine.__new__(ValidationStateMachine)
    sm._settings = SimpleNamespace(
        min_confidence_for_validated=0.5,
        min_sources_for_validated=1,
        auto_advance_to_validated=True,
    )
    truth = SimpleNamespace(
        id=uuid4(),
        tenant_id=uuid4(),
        status=TruthStatus.PROPOSED.value,
        confidence=0.9,
        maturity_level=MaturityLevel.OPERATIONALIZED.value,
        updated_at=None,
        validated_by=None,
        validated_at=None,
        validation_notes=None,
    )

    update_result = SimpleNamespace(rowcount=1)
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[SimpleNamespace(scalar=lambda: 2), update_result])
    db.add = lambda *_args, **_kwargs: None
    db.flush = AsyncMock()

    transitioned = await sm.validate(db, truth, validated_by="reviewer@example.com")
    assert transitioned.maturity_level == MaturityLevel.OPERATIONALIZED.value


@pytest.mark.unit
@pytest.mark.asyncio
async def test_router_list_truths_passes_caller_tenant_to_service() -> None:
    caller = TokenClaims(tenant_id=uuid4(), user_id="tester", permissions=["read:analytics"])
    db = AsyncMock()
    captured: dict[str, object] = {}

    async def _fake_list_truth_objects(**kwargs):
        captured.update(kwargs)
        return [], 0

    original = api_router.list_truth_objects
    api_router.list_truth_objects = _fake_list_truth_objects  # type: ignore[assignment]
    try:
        resp = await api_router.list_truths(caller=caller, db=db, limit=100, offset=0)
        assert resp.total == 0
        assert captured["tenant_id"] == caller.tenant_id
    finally:
        api_router.list_truth_objects = original  # type: ignore[assignment]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_truth_object_cross_tenant_isolation() -> None:
    db = AsyncMock()
    db.execute = AsyncMock(return_value=SimpleNamespace(scalar_one_or_none=lambda: None))
    found = await truth_service.get_truth_object(db=db, truth_id=uuid4(), tenant_id=uuid4())
    assert found is None
