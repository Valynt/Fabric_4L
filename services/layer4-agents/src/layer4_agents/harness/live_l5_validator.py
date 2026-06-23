from __future__ import annotations

"""LiveL5Validator — ClaimValidator backed by the Layer 5 Ground Truth service.

Implements the idempotent query-first / submit-if-missing flow described in
ADR-001:

  1. Query L5 list_truths filtered by tenant + claim_type + account_id.
  2. Match an existing TruthObject by normalized claim text.
  3. If found: map TruthStatus → ValidationState and return.
  4. If not found: submit a new TruthObject and return NEEDS_REVIEW.
  5. On any exception: return INSUFFICIENT_EVIDENCE (never raise, never approve).

Tenant isolation invariant: list_truths is always called with
organization_id=request.tenant_id. Cross-tenant TruthObjects are never reused.
"""
import asyncio
import logging
from datetime import UTC, datetime, timedelta

from .models import ClaimValidationResult, ValidationState
from .validation_hooks import ClaimValidationRequest, ClaimValidator

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# TruthStatus → ValidationState mapping
# ---------------------------------------------------------------------------

_STATUS_MAP: dict[str, ValidationState] = {
    "proposed": ValidationState.NEEDS_REVIEW,
    "validated": ValidationState.PASSED,
    "disputed": ValidationState.FAILED,
    "rejected": ValidationState.FAILED,
    "superseded": ValidationState.INSUFFICIENT_EVIDENCE,
    "expired": ValidationState.INSUFFICIENT_EVIDENCE,
    # Backward-compat aliases
    "extracted": ValidationState.NEEDS_REVIEW,
    "supported": ValidationState.NEEDS_REVIEW,
    "corroborated": ValidationState.NEEDS_REVIEW,
    "approved": ValidationState.PASSED,
}


def _map_status(l5_status: str) -> ValidationState:
    """Map L5 TruthStatus string to harness ValidationState."""
    return _STATUS_MAP.get(l5_status.lower(), ValidationState.INSUFFICIENT_EVIDENCE)


# ---------------------------------------------------------------------------
# Claim type inference
# ---------------------------------------------------------------------------

def _infer_claim_type(request: ClaimValidationRequest) -> str:
    """Infer L5 claim_type from harness ClaimValidationRequest.

    Defaults to Layer 5's customer_outcome enum value. Refined by value_pack_id hints.
    """
    vp = (request.value_pack_id or "").lower()
    if "roi" in vp:
        return "cost_savings_baseline"
    if "benchmark" in vp:
        return "market_benchmark"
    return "customer_outcome"


# ---------------------------------------------------------------------------
# Text normalization for matching
# ---------------------------------------------------------------------------

def _normalize(text: str) -> str:
    return text.strip().lower()


# ---------------------------------------------------------------------------
# LiveL5Validator
# ---------------------------------------------------------------------------


class LiveL5Validator(ClaimValidator):
    """ClaimValidator that calls the Layer 5 Ground Truth service.

    Uses the existing Layer5GroundTruthClient (src/integration/layer5_client.py).
    Never raises — all exceptions produce INSUFFICIENT_EVIDENCE.
    """

    def __init__(
        self,
        client,  # Layer5GroundTruthClient — typed loosely to avoid hard import
        stale_threshold_hours: int = 24,
    ) -> None:
        self._client = client
        self._stale_threshold = timedelta(hours=stale_threshold_hours)

    async def health(self) -> bool:
        """Return True if L5 is reachable."""
        try:
            await self._client.get_freshness_summary(organization_id=None)
            return True
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("LiveL5Validator.health() failed: %s", exc)
            return False

    async def validate(
        self,
        request: ClaimValidationRequest,
    ) -> ClaimValidationResult:
        """Idempotent claim validation via L5 Ground Truth.

        Flow:
          1. Query existing TruthObjects for this tenant + claim_type + account.
          2. Match by normalized claim text.
          3. If found: return mapped status (revalidate if stale).
          4. If not found: submit new TruthObject, return NEEDS_REVIEW.
          5. On any error: return INSUFFICIENT_EVIDENCE.
        """
        try:
            return await self._validate_inner(request)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning(
                "LiveL5Validator.validate() unhandled error for claim '%s': %s",
                request.claim_id,
                exc,
            )
            return self._insufficient(request, reason=f"Unexpected error: {exc}")

    async def _validate_inner(
        self,
        request: ClaimValidationRequest,
    ) -> ClaimValidationResult:
        claim_type = _infer_claim_type(request)
        normalized_text = _normalize(request.claim_text)

        # --- Step 1: Query L5 for existing TruthObjects (paginated) ---
        _page_size = 100
        truths: list = []
        offset = 0
        try:
            while True:
                list_result = await self._client.list_truths(
                    organization_id=request.tenant_id,
                    claim_type=claim_type,
                    applies_to_opportunity=request.account_id,
                    limit=_page_size,
                    offset=offset,
                )
                # list_truths returns {"items": [...], "total": ..., "has_more": ...}
                page = list_result if isinstance(list_result, list) else (
                    list_result.get("items", []) if isinstance(list_result, dict) else []
                )
                truths.extend(page)
                has_more = (
                    isinstance(list_result, dict) and list_result.get("has_more", False)
                )
                if not has_more or not page:
                    break
                offset += _page_size
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning(
                "LiveL5Validator: list_truths failed for tenant '%s': %s",
                request.tenant_id,
                exc,
            )
            return self._insufficient(request, reason=f"L5 list_truths unavailable: {exc}")

        # --- Step 2: Match by normalized claim text ---
        matched = None
        for truth in truths:
            truth_text = _normalize(str(truth.get("claim", "")))
            if truth_text == normalized_text:
                matched = truth
                break

        # --- Step 3: Found — map status ---
        if matched is not None:
            l5_status = str(matched.get("status", "extracted")).lower()
            validation_state = _map_status(l5_status)

            # Check staleness for approved truths
            if l5_status == "approved" and self._is_stale(matched):
                logger.info(
                    "LiveL5Validator: approved TruthObject is stale for claim '%s' — "
                    "returning needs_review",
                    request.claim_id,
                )
                validation_state = ValidationState.NEEDS_REVIEW

            confidence = float(matched.get("confidence", 0.5))
            return ClaimValidationResult(
                tenant_id=request.tenant_id,
                claim_id=request.claim_id,
                validation_state=validation_state,
                evidence_refs=list(request.evidence_refs),
                confidence=confidence,
                trust_score=confidence,
                validator="agent",
                reason=f"Existing TruthObject status: {l5_status}",
            )

        # --- Step 4: Not found — submit new TruthObject ---
        sources = [
            {"url": ref, "source_type": "internal"}
            for ref in (request.evidence_refs or [])
        ]
        applies_to: dict = {}
        if request.account_id:
            applies_to["account_id"] = request.account_id

        try:
            await self._client.submit_truth(
                claim=request.claim_text,
                claim_type=claim_type,
                confidence=0.5,
                organization_id=request.tenant_id,
                applies_to=applies_to or None,
                sources=sources or None,
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning(
                "LiveL5Validator: submit_truth failed for claim '%s': %s",
                request.claim_id,
                exc,
            )
            return self._insufficient(request, reason=f"L5 submit_truth failed: {exc}")

        return ClaimValidationResult(
            tenant_id=request.tenant_id,
            claim_id=request.claim_id,
            validation_state=ValidationState.NEEDS_REVIEW,
            evidence_refs=list(request.evidence_refs),
            confidence=0.5,
            trust_score=0.0,
            validator="agent",
            reason="New TruthObject submitted — awaiting L5 validation",
        )

    def _is_stale(self, truth: dict) -> bool:
        """Return True if the TruthObject's updated_at is older than stale_threshold."""
        updated_at_str = truth.get("updated_at") or truth.get("created_at")
        if not updated_at_str:
            return False
        try:
            updated_at = datetime.fromisoformat(str(updated_at_str).replace("Z", "+00:00"))
            return datetime.now(UTC) - updated_at > self._stale_threshold
        except (ValueError, TypeError):
            return False

    def _insufficient(
        self,
        request: ClaimValidationRequest,
        reason: str = "L5 validation unavailable",
    ) -> ClaimValidationResult:
        return ClaimValidationResult(
            tenant_id=request.tenant_id,
            claim_id=request.claim_id,
            validation_state=ValidationState.INSUFFICIENT_EVIDENCE,
            evidence_refs=list(request.evidence_refs),
            confidence=0.0,
            trust_score=0.0,
            validator="unavailable",
            reason=reason,
        )
