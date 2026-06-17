from __future__ import annotations

"""Tests for LiveL5Validator.

Covers:
  - TruthStatus → ValidationState mapping
  - Claim type inference from value_pack_id
  - Health check (reachable / unreachable)
  - Validate: existing truth matched → mapped status returned
  - Validate: stale approved truth → NEEDS_REVIEW
  - Validate: no match → submit + NEEDS_REVIEW
  - Validate: list_truths failure → INSUFFICIENT_EVIDENCE (never raises)
  - Validate: submit_truth failure → INSUFFICIENT_EVIDENCE (never raises)
  - Validate: unhandled exception → INSUFFICIENT_EVIDENCE (never raises)
  - Tenant isolation: list_truths always called with request.tenant_id
  - ValidationHook async integration with LiveL5Validator
"""


import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from harness.live_l5_validator import (
    LiveL5Validator,
    _infer_claim_type,
    _map_status,
)
from harness.models import ClaimValidationResult, ValidationState
from harness.validation_hooks import ClaimValidationRequest, ValidationHook

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _req(
    *,
    tenant_id: str = "tenant-abc",
    claim_id: str = "claim-1",
    claim_text: str = "Revenue will increase by 20%",
    evidence_refs: list[str] | None = None,
    value_pack_id: str | None = None,
    account_id: str | None = None,
) -> ClaimValidationRequest:
    return ClaimValidationRequest(
        tenant_id=tenant_id,
        claim_id=claim_id,
        claim_text=claim_text,
        evidence_refs=evidence_refs or ["ref-1", "ref-2"],
        value_pack_id=value_pack_id,
        account_id=account_id,
    )


def _truth(
    *,
    claim: str = "Revenue will increase by 20%",
    status: str = "approved",
    confidence: float = 0.9,
    updated_at: str | None = None,
) -> dict:
    if updated_at is None:
        updated_at = datetime.now(UTC).isoformat()
    return {
        "claim": claim,
        "status": status,
        "confidence": confidence,
        "updated_at": updated_at,
    }


def _stale_truth(**kwargs) -> dict:
    """Return a truth with updated_at 48 hours ago."""
    stale_ts = (datetime.now(UTC) - timedelta(hours=48)).isoformat()
    return _truth(updated_at=stale_ts, **kwargs)


def _mock_client(
    *,
    list_result: list | dict | None = None,
    submit_result: dict | None = None,
    freshness_result: dict | None = None,
    list_raises: Exception | None = None,
    submit_raises: Exception | None = None,
    health_raises: Exception | None = None,
) -> MagicMock:
    """Build a mock Layer5GroundTruthClient with async methods."""
    client = MagicMock()

    if list_raises is not None:
        client.list_truths = AsyncMock(side_effect=list_raises)
    else:
        client.list_truths = AsyncMock(return_value=list_result if list_result is not None else [])

    if submit_raises is not None:
        client.submit_truth = AsyncMock(side_effect=submit_raises)
    else:
        client.submit_truth = AsyncMock(return_value=submit_result or {"id": "truth-new"})

    if health_raises is not None:
        client.get_freshness_summary = AsyncMock(side_effect=health_raises)
    else:
        client.get_freshness_summary = AsyncMock(
            return_value=freshness_result or {"status": "ok"}
        )

    return client


# ---------------------------------------------------------------------------
# Status mapping
# ---------------------------------------------------------------------------


class TestStatusMapping:
    def test_proposed_maps_to_needs_review(self):
        assert _map_status("proposed") == ValidationState.NEEDS_REVIEW

    def test_validated_maps_to_passed(self):
        assert _map_status("validated") == ValidationState.PASSED

    def test_disputed_maps_to_failed(self):
        assert _map_status("disputed") == ValidationState.FAILED

    def test_rejected_maps_to_failed(self):
        assert _map_status("rejected") == ValidationState.FAILED

    def test_superseded_maps_to_insufficient_evidence(self):
        assert _map_status("superseded") == ValidationState.INSUFFICIENT_EVIDENCE

    def test_expired_maps_to_insufficient_evidence(self):
        assert _map_status("expired") == ValidationState.INSUFFICIENT_EVIDENCE

    # Backward-compat aliases
    def test_extracted_maps_to_needs_review(self):
        assert _map_status("extracted") == ValidationState.NEEDS_REVIEW

    def test_supported_maps_to_needs_review(self):
        assert _map_status("supported") == ValidationState.NEEDS_REVIEW

    def test_corroborated_maps_to_needs_review(self):
        assert _map_status("corroborated") == ValidationState.NEEDS_REVIEW

    def test_approved_maps_to_passed(self):
        assert _map_status("approved") == ValidationState.PASSED

    def test_unknown_maps_to_insufficient_evidence(self):
        assert _map_status("unknown_status") == ValidationState.INSUFFICIENT_EVIDENCE

    def test_empty_string_maps_to_insufficient_evidence(self):
        assert _map_status("") == ValidationState.INSUFFICIENT_EVIDENCE

    def test_case_insensitive(self):
        assert _map_status("APPROVED") == ValidationState.PASSED
        assert _map_status("Disputed") == ValidationState.FAILED


# ---------------------------------------------------------------------------
# Claim type inference
# ---------------------------------------------------------------------------


class TestClaimTypeInference:
    def test_roi_in_value_pack_id(self):
        req = _req(value_pack_id="saas-roi-v1")
        assert _infer_claim_type(req) == "cost_savings_baseline"

    def test_benchmark_in_value_pack_id(self):
        req = _req(value_pack_id="benchmark-2024")
        assert _infer_claim_type(req) == "market_benchmark"

    def test_no_value_pack_id_defaults_to_outcome(self):
        req = _req(value_pack_id=None)
        assert _infer_claim_type(req) == "customer_outcome"

    def test_unrecognized_value_pack_id_defaults_to_outcome(self):
        req = _req(value_pack_id="manufacturing-v2")
        assert _infer_claim_type(req) == "customer_outcome"

    def test_roi_case_insensitive(self):
        req = _req(value_pack_id="ROI-Pack")
        assert _infer_claim_type(req) == "cost_savings_baseline"


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


class TestLiveL5ValidatorHealth:
    @pytest.mark.asyncio
    async def test_health_true_when_freshness_succeeds(self):
        client = _mock_client()
        validator = LiveL5Validator(client=client)
        assert await validator.health() is True

    @pytest.mark.asyncio
    async def test_health_false_when_freshness_raises(self):
        client = _mock_client(health_raises=ConnectionError("L5 down"))
        validator = LiveL5Validator(client=client)
        assert await validator.health() is False

    @pytest.mark.asyncio
    async def test_health_calls_get_freshness_summary(self):
        client = _mock_client()
        validator = LiveL5Validator(client=client)
        await validator.health()
        client.get_freshness_summary.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_uses_valid_get_freshness_summary_signature(self):
        """Verify health() only passes kwargs accepted by the real client.

        layer5_client.py cannot be imported in isolation (it depends on
        value_fabric at module level), so we use a local stub that mirrors
        the real get_freshness_summary signature. AsyncMock(spec=stub)
        enforces the signature and raises TypeError on unexpected kwargs,
        catching regressions like passing allow_system_call=True.
        """
        from unittest.mock import create_autospec

        # Mirrors the real Layer5GroundTruthClient.get_freshness_summary signature.
        async def _freshness_stub(organization_id: str | None = None) -> dict:
            return {"status": "ok"}

        client = MagicMock()
        client.get_freshness_summary = create_autospec(
            _freshness_stub,
            return_value={"status": "ok"},
        )
        validator = LiveL5Validator(client=client)
        result = await validator.health()
        assert result is True
        client.get_freshness_summary.assert_called_once_with(organization_id=None)


# ---------------------------------------------------------------------------
# Validate: existing truth matched
# ---------------------------------------------------------------------------


class TestLiveL5ValidatorValidateExisting:
    @pytest.mark.asyncio
    async def test_approved_truth_returns_passed(self):
        req = _req()
        client = _mock_client(list_result=[_truth(claim=req.claim_text, status="approved")])
        validator = LiveL5Validator(client=client)

        result = await validator.validate(req)

        assert result.validation_state == ValidationState.PASSED
        assert result.tenant_id == req.tenant_id
        assert result.claim_id == req.claim_id
        assert result.validator == "agent"

    @pytest.mark.asyncio
    async def test_disputed_truth_returns_failed(self):
        req = _req()
        client = _mock_client(list_result=[_truth(claim=req.claim_text, status="disputed")])
        validator = LiveL5Validator(client=client)

        result = await validator.validate(req)

        assert result.validation_state == ValidationState.FAILED

    @pytest.mark.asyncio
    async def test_extracted_truth_returns_needs_review(self):
        req = _req()
        client = _mock_client(list_result=[_truth(claim=req.claim_text, status="extracted")])
        validator = LiveL5Validator(client=client)

        result = await validator.validate(req)

        assert result.validation_state == ValidationState.NEEDS_REVIEW

    @pytest.mark.asyncio
    async def test_match_is_case_insensitive(self):
        req = _req(claim_text="Revenue will increase by 20%")
        client = _mock_client(
            list_result=[_truth(claim="REVENUE WILL INCREASE BY 20%", status="approved")]
        )
        validator = LiveL5Validator(client=client)

        result = await validator.validate(req)

        assert result.validation_state == ValidationState.PASSED

    @pytest.mark.asyncio
    async def test_match_is_whitespace_insensitive(self):
        req = _req(claim_text="  Revenue will increase by 20%  ")
        client = _mock_client(
            list_result=[_truth(claim="revenue will increase by 20%", status="approved")]
        )
        validator = LiveL5Validator(client=client)

        result = await validator.validate(req)

        assert result.validation_state == ValidationState.PASSED

    @pytest.mark.asyncio
    async def test_confidence_propagated_from_truth(self):
        req = _req()
        client = _mock_client(
            list_result=[_truth(claim=req.claim_text, status="approved", confidence=0.85)]
        )
        validator = LiveL5Validator(client=client)

        result = await validator.validate(req)

        assert result.confidence == pytest.approx(0.85)
        assert result.trust_score == pytest.approx(0.85)

    @pytest.mark.asyncio
    async def test_list_truths_scoped_to_request_tenant(self):
        req = _req(tenant_id="tenant-xyz", account_id="acct-1")
        client = _mock_client(list_result=[])
        validator = LiveL5Validator(client=client)

        await validator.validate(req)

        call_kwargs = client.list_truths.call_args.kwargs
        assert call_kwargs["organization_id"] == "tenant-xyz"

    @pytest.mark.asyncio
    async def test_dict_response_with_items_key(self):
        """list_truths returns {'items': [...], 'total': ..., 'has_more': ...} dict."""
        req = _req()
        client = _mock_client(
            list_result={"items": [_truth(claim=req.claim_text, status="approved")], "total": 1, "has_more": False}
        )
        validator = LiveL5Validator(client=client)

        result = await validator.validate(req)

        assert result.validation_state == ValidationState.PASSED

    @pytest.mark.asyncio
    async def test_dict_response_with_wrong_key_falls_through_to_submit(self):
        """A dict without 'items' key produces no match and triggers submit."""
        req = _req()
        client = _mock_client(
            list_result={"truths": [_truth(claim=req.claim_text, status="approved")]}
        )
        validator = LiveL5Validator(client=client)

        result = await validator.validate(req)

        # No match found → submit → NEEDS_REVIEW, not PASSED
        assert result.validation_state == ValidationState.NEEDS_REVIEW
        client.submit_truth.assert_called_once()


# ---------------------------------------------------------------------------
# Validate: stale approved truth
# ---------------------------------------------------------------------------


class TestLiveL5ValidatorStaleness:
    @pytest.mark.asyncio
    async def test_stale_approved_truth_returns_needs_review(self):
        req = _req()
        stale = _stale_truth(claim=req.claim_text, status="approved")
        client = _mock_client(list_result=[stale])
        validator = LiveL5Validator(client=client, stale_threshold_hours=24)

        result = await validator.validate(req)

        assert result.validation_state == ValidationState.NEEDS_REVIEW

    @pytest.mark.asyncio
    async def test_fresh_approved_truth_returns_passed(self):
        req = _req()
        fresh = _truth(claim=req.claim_text, status="approved")  # updated_at = now
        client = _mock_client(list_result=[fresh])
        validator = LiveL5Validator(client=client, stale_threshold_hours=24)

        result = await validator.validate(req)

        assert result.validation_state == ValidationState.PASSED

    @pytest.mark.asyncio
    async def test_stale_disputed_truth_not_affected(self):
        """Staleness check only applies to approved truths."""
        req = _req()
        stale = _stale_truth(claim=req.claim_text, status="disputed")
        client = _mock_client(list_result=[stale])
        validator = LiveL5Validator(client=client, stale_threshold_hours=24)

        result = await validator.validate(req)

        assert result.validation_state == ValidationState.FAILED

    @pytest.mark.asyncio
    async def test_missing_updated_at_not_stale(self):
        req = _req()
        truth = _truth(claim=req.claim_text, status="approved")
        truth.pop("updated_at")
        client = _mock_client(list_result=[truth])
        validator = LiveL5Validator(client=client, stale_threshold_hours=24)

        result = await validator.validate(req)

        # No updated_at → not considered stale → PASSED
        assert result.validation_state == ValidationState.PASSED


# ---------------------------------------------------------------------------
# Validate: no match → submit
# ---------------------------------------------------------------------------


class TestLiveL5ValidatorSubmit:
    @pytest.mark.asyncio
    async def test_no_match_submits_and_returns_needs_review(self):
        req = _req()
        client = _mock_client(list_result=[])  # no existing truths
        validator = LiveL5Validator(client=client)

        result = await validator.validate(req)

        assert result.validation_state == ValidationState.NEEDS_REVIEW
        client.submit_truth.assert_called_once()

    @pytest.mark.asyncio
    async def test_submit_called_with_correct_tenant(self):
        req = _req(tenant_id="tenant-submit")
        client = _mock_client(list_result=[])
        validator = LiveL5Validator(client=client)

        await validator.validate(req)

        call_kwargs = client.submit_truth.call_args.kwargs
        assert call_kwargs["organization_id"] == "tenant-submit"

    @pytest.mark.asyncio
    async def test_submit_called_with_claim_text(self):
        req = _req(claim_text="Costs will drop by 15%")
        client = _mock_client(list_result=[])
        validator = LiveL5Validator(client=client)

        await validator.validate(req)

        call_kwargs = client.submit_truth.call_args.kwargs
        assert call_kwargs["claim"] == "Costs will drop by 15%"

    @pytest.mark.asyncio
    async def test_submit_result_has_agent_validator(self):
        req = _req()
        client = _mock_client(list_result=[])
        validator = LiveL5Validator(client=client)

        result = await validator.validate(req)

        assert result.validator == "agent"

    @pytest.mark.asyncio
    async def test_no_match_different_claim_text_does_not_match(self):
        req = _req(claim_text="Revenue up 20%")
        client = _mock_client(
            list_result=[_truth(claim="Costs down 10%", status="approved")]
        )
        validator = LiveL5Validator(client=client)

        result = await validator.validate(req)

        # No match → submit → NEEDS_REVIEW
        assert result.validation_state == ValidationState.NEEDS_REVIEW
        client.submit_truth.assert_called_once()


# ---------------------------------------------------------------------------
# Validate: error handling — never raises
# ---------------------------------------------------------------------------


class TestLiveL5ValidatorErrorHandling:
    @pytest.mark.asyncio
    async def test_list_truths_failure_returns_insufficient_evidence(self):
        req = _req()
        client = _mock_client(list_raises=ConnectionError("L5 unreachable"))
        validator = LiveL5Validator(client=client)

        result = await validator.validate(req)

        assert result.validation_state == ValidationState.INSUFFICIENT_EVIDENCE
        assert result.validator == "unavailable"

    @pytest.mark.asyncio
    async def test_submit_truth_failure_returns_insufficient_evidence(self):
        req = _req()
        client = _mock_client(list_result=[], submit_raises=RuntimeError("submit failed"))
        validator = LiveL5Validator(client=client)

        result = await validator.validate(req)

        assert result.validation_state == ValidationState.INSUFFICIENT_EVIDENCE
        assert result.validator == "unavailable"

    @pytest.mark.asyncio
    async def test_unhandled_exception_returns_insufficient_evidence(self):
        req = _req()
        client = MagicMock()
        client.list_truths = AsyncMock(side_effect=Exception("unexpected"))
        validator = LiveL5Validator(client=client)

        result = await validator.validate(req)

        assert result.validation_state == ValidationState.INSUFFICIENT_EVIDENCE

    @pytest.mark.asyncio
    async def test_validate_never_raises(self):
        """validate() must not propagate any exception."""
        req = _req()
        client = MagicMock()
        client.list_truths = AsyncMock(side_effect=SystemError("catastrophic"))
        validator = LiveL5Validator(client=client)

        # Should not raise
        result = await validator.validate(req)
        assert isinstance(result, ClaimValidationResult)

    @pytest.mark.asyncio
    async def test_insufficient_evidence_has_zero_confidence(self):
        req = _req()
        client = _mock_client(list_raises=ConnectionError("down"))
        validator = LiveL5Validator(client=client)

        result = await validator.validate(req)

        assert result.confidence == 0.0
        assert result.trust_score == 0.0

    @pytest.mark.asyncio
    async def test_insufficient_evidence_preserves_tenant_and_claim(self):
        req = _req(tenant_id="tenant-err", claim_id="claim-err")
        client = _mock_client(list_raises=ConnectionError("down"))
        validator = LiveL5Validator(client=client)

        result = await validator.validate(req)

        assert result.tenant_id == "tenant-err"
        assert result.claim_id == "claim-err"


# ---------------------------------------------------------------------------
# Tenant isolation
# ---------------------------------------------------------------------------


class TestTenantIsolation:
    @pytest.mark.asyncio
    async def test_tenant_a_truths_not_used_for_tenant_b(self):
        """Truths from tenant-a must not satisfy a request from tenant-b."""
        req_b = _req(tenant_id="tenant-b", claim_text="Revenue up 20%")

        # Client returns truths only when called with tenant-a
        async def scoped_list_truths(organization_id, **kwargs):
            if organization_id == "tenant-a":
                return [_truth(claim="Revenue up 20%", status="approved")]
            return []

        client = MagicMock()
        client.list_truths = AsyncMock(side_effect=scoped_list_truths)
        client.submit_truth = AsyncMock(return_value={"id": "new"})
        validator = LiveL5Validator(client=client)

        result = await validator.validate(req_b)

        # tenant-b gets no match → submit → NEEDS_REVIEW, not PASSED
        assert result.validation_state == ValidationState.NEEDS_REVIEW

    @pytest.mark.asyncio
    async def test_result_tenant_id_matches_request(self):
        req = _req(tenant_id="tenant-isolated")
        client = _mock_client(list_result=[])
        validator = LiveL5Validator(client=client)

        result = await validator.validate(req)

        assert result.tenant_id == "tenant-isolated"


# ---------------------------------------------------------------------------
# ValidationHook async integration
# ---------------------------------------------------------------------------


class TestValidationHookWithLiveL5:
    @pytest.mark.asyncio
    async def test_hook_uses_live_validator_when_healthy(self):
        req = _req()
        client = _mock_client(list_result=[_truth(claim=req.claim_text, status="approved")])
        validator = LiveL5Validator(client=client)
        hook = ValidationHook(primary_validator=validator)

        result = await hook.validate_single(req)

        assert result.validation_state == ValidationState.PASSED

    @pytest.mark.asyncio
    async def test_hook_falls_back_when_health_fails(self):
        req = _req()
        client = _mock_client(health_raises=ConnectionError("L5 down"))
        validator = LiveL5Validator(client=client)
        hook = ValidationHook(primary_validator=validator)

        result = await hook.validate_single(req)

        # Fallback is UnavailableValidator → INSUFFICIENT_EVIDENCE
        assert result.validation_state == ValidationState.INSUFFICIENT_EVIDENCE

    @pytest.mark.asyncio
    async def test_hook_validate_claims_batch(self):
        req1 = _req(claim_id="c1", claim_text="Claim one")
        req2 = _req(claim_id="c2", claim_text="Claim two")
        client = _mock_client(
            list_result=[
                _truth(claim="Claim one", status="approved"),
                _truth(claim="Claim two", status="disputed"),
            ]
        )
        validator = LiveL5Validator(client=client)
        hook = ValidationHook(primary_validator=validator)

        results = await hook.validate_claims([req1, req2])

        assert len(results) == 2
        states = {r.claim_id: r.validation_state for r in results}
        assert states["c1"] == ValidationState.PASSED
        assert states["c2"] == ValidationState.FAILED

    @pytest.mark.asyncio
    async def test_hook_is_available_when_l5_healthy(self):
        client = _mock_client()
        validator = LiveL5Validator(client=client)
        hook = ValidationHook(primary_validator=validator)

        assert await hook.is_available() is True

    @pytest.mark.asyncio
    async def test_hook_is_not_available_when_l5_down(self):
        client = _mock_client(health_raises=ConnectionError("down"))
        validator = LiveL5Validator(client=client)
        hook = ValidationHook(primary_validator=validator)

        assert await hook.is_available() is False


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------


class TestLiveL5ValidatorPagination:
    @pytest.mark.asyncio
    async def test_match_found_on_second_page(self):
        """A truth beyond the first page is still matched via pagination."""
        req = _req(claim_text="Revenue up 20%")

        page1 = {"items": [_truth(claim="Other claim", status="approved")], "has_more": True}
        page2 = {"items": [_truth(claim="Revenue up 20%", status="approved")], "has_more": False}

        call_count = 0

        async def paginated_list_truths(**kwargs):
            nonlocal call_count
            call_count += 1
            return page1 if call_count == 1 else page2

        client = MagicMock()
        client.list_truths = AsyncMock(side_effect=paginated_list_truths)
        validator = LiveL5Validator(client=client)

        result = await validator.validate(req)

        assert result.validation_state == ValidationState.PASSED
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_no_match_across_all_pages_triggers_submit(self):
        """When all pages are exhausted with no match, submit_truth is called."""
        req = _req(claim_text="Revenue up 20%")

        page1 = {"items": [_truth(claim="Other claim A", status="approved")], "has_more": True}
        page2 = {"items": [_truth(claim="Other claim B", status="approved")], "has_more": False}

        call_count = 0

        async def paginated_list_truths(**kwargs):
            nonlocal call_count
            call_count += 1
            return page1 if call_count == 1 else page2

        client = MagicMock()
        client.list_truths = AsyncMock(side_effect=paginated_list_truths)
        client.submit_truth = AsyncMock(return_value={"id": "new"})
        validator = LiveL5Validator(client=client)

        result = await validator.validate(req)

        assert result.validation_state == ValidationState.NEEDS_REVIEW
        client.submit_truth.assert_called_once()

    @pytest.mark.asyncio
    async def test_single_page_no_has_more_does_not_paginate(self):
        """When has_more is False on the first page, only one request is made."""
        req = _req()
        client = _mock_client(
            list_result={"items": [_truth(claim=req.claim_text, status="approved")], "has_more": False}
        )
        validator = LiveL5Validator(client=client)

        await validator.validate(req)

        client.list_truths.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_result_as_plain_list_does_not_paginate(self):
        """A plain list response (no has_more) is consumed without pagination."""
        req = _req()
        client = _mock_client(list_result=[_truth(claim=req.claim_text, status="approved")])
        validator = LiveL5Validator(client=client)

        result = await validator.validate(req)

        assert result.validation_state == ValidationState.PASSED
        client.list_truths.assert_called_once()


# ---------------------------------------------------------------------------
# validate_claims tenant_id enforcement
# ---------------------------------------------------------------------------


class TestValidateClaimsTenantEnforcement:
    @pytest.mark.asyncio
    async def test_mismatched_tenant_raises(self):
        """validate_claims raises when a request tenant_id doesn't match the caller's."""
        from harness.factory import make_in_memory_registry
        from harness.registry import HarnessRegistryError

        registry = make_in_memory_registry()
        requests = [
            ClaimValidationRequest(
                tenant_id="tenant-other",
                claim_id="c1",
                claim_text="Claim",
                evidence_refs=[],
            )
        ]
        with pytest.raises(HarnessRegistryError, match="tenant_id mismatch"):
            await registry.validate_claims("tenant-abc", requests)

    @pytest.mark.asyncio
    async def test_matching_tenant_does_not_raise(self):
        """validate_claims succeeds when all request tenant_ids match."""
        from harness.factory import make_in_memory_registry

        registry = make_in_memory_registry()
        requests = [
            ClaimValidationRequest(
                tenant_id="tenant-abc",
                claim_id="c1",
                claim_text="Claim",
                evidence_refs=[],
            )
        ]
        results = await registry.validate_claims("tenant-abc", requests)
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_mixed_tenants_raises_and_lists_mismatched_claims(self):
        """Error message includes the mismatched claim IDs."""
        from harness.factory import make_in_memory_registry
        from harness.registry import HarnessRegistryError

        registry = make_in_memory_registry()
        requests = [
            ClaimValidationRequest(tenant_id="tenant-abc", claim_id="c-ok", claim_text="OK", evidence_refs=[]),
            ClaimValidationRequest(tenant_id="tenant-evil", claim_id="c-bad", claim_text="Bad", evidence_refs=[]),
        ]
        with pytest.raises(HarnessRegistryError) as exc_info:
            await registry.validate_claims("tenant-abc", requests)
        assert "c-bad" in str(exc_info.value)
        assert "c-ok" not in str(exc_info.value)


# ---------------------------------------------------------------------------
# R1: env var standardization — missing LAYER5_GROUND_TRUTH_URL falls back
# ---------------------------------------------------------------------------


class TestEnvVarAbsentFallback:
    """make_live_l5_registry falls back to UnavailableValidator when env vars are absent."""

    @pytest.mark.asyncio
    async def test_missing_layer5_url_uses_unavailable_validator(self, monkeypatch):
        """When LAYER5_GROUND_TRUTH_URL is unset, validation returns INSUFFICIENT_EVIDENCE."""

        # Remove both env vars to simulate missing config
        monkeypatch.delenv("LAYER5_GROUND_TRUTH_URL", raising=False)
        monkeypatch.delenv("LAYER5_SERVICE_TOKEN", raising=False)

        # make_live_l5_registry still constructs a client (with default URL),
        # but the validator's health() will fail → falls back to UnavailableValidator.
        # We test the fallback path via ValidationHook directly.
        from harness.validation_hooks import ValidationHook

        hook = ValidationHook(primary_validator=None)
        req = ClaimValidationRequest(
            tenant_id="t1",
            claim_id="c1",
            claim_text="ROI claim",
            evidence_refs=[],
        )
        result = await hook.validate_single(req)
        assert result.validation_state == ValidationState.INSUFFICIENT_EVIDENCE
        assert result.validator == "unavailable"

    @pytest.mark.asyncio
    async def test_unavailable_validator_never_approves(self):
        """UnavailableValidator always returns INSUFFICIENT_EVIDENCE, never PASSED."""
        from harness.validation_hooks import UnavailableValidator

        validator = UnavailableValidator()
        req = ClaimValidationRequest(
            tenant_id="t1",
            claim_id="c1",
            claim_text="Any claim",
            evidence_refs=[],
        )
        result = await validator.validate(req)
        assert result.validation_state != ValidationState.PASSED
        assert result.validation_state == ValidationState.INSUFFICIENT_EVIDENCE
        assert await validator.health() is False
