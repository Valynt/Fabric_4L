from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from pydantic import ValidationError

from layer5_ground_truth.api.schemas import (
    AddSourceRequest,
    TruthObjectCreate,
    ValidateRequest,
)
from layer5_ground_truth.models.truth_object import MaturityLevel, TruthStatus
from layer5_ground_truth.services import truth_service
from layer5_ground_truth.services.state_machine import ValidationStateMachine


@pytest.mark.unit
def test_truth_object_create_requires_non_blank_claim_and_confidence_bounds() -> None:
    with pytest.raises(ValidationError):
        TruthObjectCreate(claim="   ", confidence=0.4)

    with pytest.raises(ValidationError):
        TruthObjectCreate(claim="valid claim", confidence=1.2)


@pytest.mark.unit
def test_validate_request_enforces_reason_fields() -> None:
    with pytest.raises(ValidationError, match="dispute_reason"):
        ValidateRequest(action="dispute", actor="reviewer")

    with pytest.raises(ValidationError, match="rejection_reason"):
        ValidateRequest(action="reject", actor="reviewer")


@pytest.mark.unit
def test_add_source_requires_provenance_reference() -> None:
    with pytest.raises(ValidationError, match="Value error"):
        AddSourceRequest(source_type="other")


@pytest.mark.unit
async def test_service_add_source_propagates_tenant_to_repository_boundary() -> None:
    tenant_id = uuid4()
    truth_object = SimpleNamespace(id=uuid4(), tenant_id=tenant_id)
    captured: list[object] = []

    def _capture(obj: object) -> None:
        captured.append(obj)

    db = SimpleNamespace(add=_capture, flush=AsyncMock(), refresh=AsyncMock())

    await truth_service.add_source(
        db=db,
        truth_object=truth_object,
        tenant_id=tenant_id,
        source_data={"source_type": "other", "source_id": "doc-123"},
        auto_advance=False,
    )

    assert captured, "expected TruthSource insertion"
    assert getattr(captured[0], "tenant_id") == tenant_id


@pytest.mark.unit
async def test_maturity_operationalize_boundary_idempotent() -> None:
    sm = ValidationStateMachine()
    truth = SimpleNamespace(
        id=uuid4(),
        tenant_id=uuid4(),
        status=TruthStatus.VALIDATED.value,
        maturity_level=MaturityLevel.OPERATIONALIZED.value,
    )
    db = AsyncMock()

    result = await sm.mark_operationalized(
        db,
        truth,
        trigger="regression_fixture",
        triggered_by="tester",
        context={"case": "already-op"},
    )

    assert result.maturity_level == MaturityLevel.OPERATIONALIZED.value
    db.add.assert_not_called()
