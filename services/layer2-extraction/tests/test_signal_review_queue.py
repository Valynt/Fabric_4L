from __future__ import annotations

import pytest
from fastapi import HTTPException

from layer2_extraction.api.routes.extraction import (
    approve_reviewed_signal,
    reject_reviewed_signal,
    route_signals_for_review,
)
from layer2_extraction.integration.signal_review_store import (
    ReviewedSignalRecord,
    SignalReviewStatus,
    build_signal_review_store,
)
from layer2_extraction.models import SignalReviewDecisionRequest


class _Ctx:
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id


class _State:
    def __init__(self, tenant_id: str):
        self.governance_context = _Ctx(tenant_id)


class _Req:
    def __init__(self, tenant_id: str):
        self.state = _State(tenant_id)


@pytest.mark.asyncio
async def test_threshold_routing_enqueues_low_confidence_signals() -> None:
    approved, queued = route_signals_for_review(
        signals=[
            {"signal_type": "buying_intent", "confidence": 0.9, "evidence_links": ["http://a"]},
            {"signal_type": "org_change", "confidence": 0.4, "evidence_links": ["http://b"]},
        ],
        confidence_threshold=0.75,
        tenant_id="tenant-a",
        account_id="acct-1",
        value_pack_id="pack-1",
        extraction_job_id="job-1",
    )

    assert len(approved) == 1
    assert len(queued) == 1
    assert queued[0].review_status == SignalReviewStatus.PENDING_REVIEW
    assert queued[0].tenant_id == "tenant-a"
    assert queued[0].value_pack_id == "pack-1"


@pytest.mark.asyncio
async def test_review_actions_enforce_tenant_isolation() -> None:
    store = build_signal_review_store()
    record = await store.enqueue(
        ReviewedSignalRecord(
            tenant_id="tenant-owner",
            account_id="acct-1",
            value_pack_id="pack-1",
            extraction_job_id="job-2",
            signal_type="org_change",
            confidence=0.2,
            evidence_links=["http://evidence"],
        )
    )

    with pytest.raises(HTTPException) as exc:
        await approve_reviewed_signal(
            record.review_id,
            _Req("tenant-attacker"),
            SignalReviewDecisionRequest(reviewed_by="analyst"),
        )
    assert exc.value.status_code == 404

    rejected = await reject_reviewed_signal(
        record.review_id,
        _Req("tenant-owner"),
        SignalReviewDecisionRequest(reviewed_by="analyst-owner"),
    )
    assert rejected.review_status == SignalReviewStatus.REJECTED

    with pytest.raises(HTTPException) as conflict:
        await approve_reviewed_signal(
            record.review_id,
            _Req("tenant-owner"),
            SignalReviewDecisionRequest(reviewed_by="analyst-owner"),
        )
    assert conflict.value.status_code == 409
