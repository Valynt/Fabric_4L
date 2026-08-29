"""Policy decision engine implementations behind the authorization facade.

The facade must not depend on raw Rego/OPA response shapes. This module defines
the ``PolicyEngine`` protocol and two implementations:

* :class:`InProcessPolicyEngine` — a deterministic Python evaluation of the
  policy rules. It mirrors the Rego bundle under ``policies/authorization/``
  so the same decision tables are tested in Python and in Rego.
* :class:`FailClosedPolicyEngine` — a wrapper that returns a deny decision
  (``PDP_UNAVAILABLE``) whenever the wrapped engine is unavailable, raises, or
  is not configured. This is the default until a real OPA client is wired in.
"""
from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime
from typing import Protocol

from app.authz.constants import ReasonCode
from app.authz.schemas import AuthzRequest, Obligation

POLICY_VERSION = "authz-1.0.0"

# Workflow roles recognized by the policy plane.
_WORKFLOW_ROLES = frozenset(
    {
        "workflow.finance_approver",
        "workflow.economic_reviewer",
        "workflow.deal_desk",
        "workflow.value_manager",
        "workflow.realization_owner",
        "workflow.security_reviewer",
        "workflow.exception_approver",
    }
)

_LOGICAL_REALIZATION_ROLES = frozenset(
    {"workflow.finance_approver", "workflow.deal_desk", "workflow.value_manager"}
)


class PolicyEngine(Protocol):
    """Protocol for a policy decision engine."""

    def evaluate(self, request: AuthzRequest) -> tuple[bool, frozenset[ReasonCode], frozenset[Obligation]]:
        """Return ``(allow, reason_codes, obligations)``."""
        ...


def fingerprint_input(request: AuthzRequest) -> str:
    """Deterministic input fingerprint (SHA-256 hex) for the decision record."""
    payload = request.model_dump_json()
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class _Claims:
    """Intermediate facts about claim attributes."""

    __slots__ = (
        "author_id",
        "validation_state",
        "approval_state",
        "model_version",
        "impact_usd",
        "open_dispute_count",
        "publication_state",
    )

    def __init__(self, attributes: dict) -> None:
        self.author_id = attributes.get("author_id")
        self.validation_state = attributes.get("validation_state")
        self.approval_state = attributes.get("approval_state")
        self.model_version = attributes.get("model_version")
        self.impact_usd = attributes.get("impact_usd")
        self.open_dispute_count = attributes.get("open_dispute_count")
        self.publication_state = attributes.get("publication_state")


class InProcessPolicyEngine:
    """Deterministic Python mirror of the Rego policy bundle.

    The evaluation matches the Rego rules one-for-one so divergence between the
    Python test oracle and the opa bundle is detectable in CI even before OPA
    is deployed as a service.
    """

    version = POLICY_VERSION

    def evaluate(self, request: AuthzRequest) -> tuple[bool, frozenset[ReasonCode], frozenset[Obligation]]:
        reasons: list[ReasonCode] = []
        obligations: list[Obligation] = []

        # Global deny rules (design Section 11.1).
        if request.principal.type == "agent" or request.principal.is_agent:
            if request.action in {
                "claim.validate",
                "claim.approve",
                "claim.include_in_case",
                "claim.resolve_dispute",
                "model.mark_canonical",
                "deliverable.publish_external",
                "exception.submit",
                "exception.approve",
                "exception.activate",
                "opportunity.lock_realization",
            }:
                reasons.append(ReasonCode.AGENT_ACTION_FORBIDDEN)
                return False, frozenset(reasons), frozenset(obligations)

        if request.action == "claim.approve":
            return self._evaluate_claim_approve(request, reasons, obligations)
        if request.action == "deliverable.publish_external":
            return self._evaluate_deliverable_publish(request, reasons, obligations)
        if request.action == "exception.activate":
            return self._evaluate_exception_activate(request, reasons, obligations)
        if request.action == "opportunity.lock_realization":
            return self._evaluate_opportunity_lock(request, reasons, obligations)

        # Non-critical known actions: allow only for active, same-tenant humans
        # with any recognized workflow role or platform role (attribute checks
        # are attached in later milestones). Fail closed otherwise.
        if request.principal.status != "active":
            reasons.append(ReasonCode.PRINCIPAL_INACTIVE)
            return False, frozenset(reasons), frozenset(obligations)
        has_role = bool(set(request.principal.workflow_roles) & _WORKFLOW_ROLES) or bool(
            request.principal.platform_roles
        )
        if not has_role:
            reasons.append(ReasonCode.ROLE_MISSING)
            return False, frozenset(reasons), frozenset(obligations)
        reasons.append(ReasonCode.ROLE_ELIGIBLE)
        return True, frozenset(reasons), frozenset(obligations)

    # ── claim.approve (design Section 11.2) ───────────────────────────────
    def _evaluate_claim_approve(
        self,
        request: AuthzRequest,
        reasons: list[ReasonCode],
        obligations: list[Obligation],
    ) -> tuple[bool, frozenset[ReasonCode], frozenset[Obligation]]:
        claims = _Claims(request.resource.attributes)

        if "workflow.finance_approver" not in request.principal.workflow_roles:
            reasons.append(ReasonCode.ROLE_MISSING)
            return False, frozenset(reasons), frozenset(obligations)
        if "economic_reviewer" not in request.resource.relationships:
            reasons.append(ReasonCode.RELATIONSHIP_MISSING)
            return False, frozenset(reasons), frozenset(obligations)
        if request.principal.id == claims.author_id:
            reasons.append(ReasonCode.SELF_APPROVAL_FORBIDDEN)
            return False, frozenset(reasons), frozenset(obligations)
        if claims.validation_state not in {"REVIEWED", "DISPUTED_RESOLVED"}:
            reasons.append(ReasonCode.POLICY_INPUT_INVALID)
            return False, frozenset(reasons), frozenset(obligations)
        if (
            request.context.requested_model_version is not None
            and claims.model_version != request.context.requested_model_version
        ):
            reasons.append(ReasonCode.MODEL_VERSION_STALE)
            return False, frozenset(reasons), frozenset(obligations)
        if request.principal.approval_ceiling_usd is not None:
            if abs(claims.impact_usd or 0) > request.principal.approval_ceiling_usd:
                reasons.append(ReasonCode.APPROVAL_CEILING_EXCEEDED)
                return False, frozenset(reasons), frozenset(obligations)
        if (claims.open_dispute_count or 0) != 0:
            reasons.append(ReasonCode.DISPUTE_OPEN)
            return False, frozenset(reasons), frozenset(obligations)
        # Realization constraint.
        if claims.publication_state == "LOCKED_REALIZATION":
            if "workflow.realization_owner" not in request.principal.workflow_roles:
                reasons.append(ReasonCode.REALIZATION_CONSTRAINT_FAILED)
                return False, frozenset(reasons), frozenset(obligations)
        reasons.extend([ReasonCode.ROLE_ELIGIBLE, ReasonCode.BOUND_REVIEWER])
        if request.principal.id != claims.author_id:
            reasons.append(ReasonCode.SOD_PASS)
        if request.principal.approval_ceiling_usd is not None:
            reasons.append(ReasonCode.CEILING_PASS)
        obligations.append(Obligation(type="record_approval_reason"))
        return True, frozenset(reasons), frozenset(obligations)

    # ── deliverable.publish_external (design Section 11.3) ────────────────
    def _evaluate_deliverable_publish(
        self,
        request: AuthzRequest,
        reasons: list[ReasonCode],
        obligations: list[Obligation],
    ) -> tuple[bool, frozenset[ReasonCode], frozenset[Obligation]]:
        attrs = request.resource.attributes
        roles = set(request.principal.workflow_roles)
        if not (roles & {"workflow.deal_desk", "workflow.value_manager"}):
            reasons.append(ReasonCode.ROLE_MISSING)
            return False, frozenset(reasons), frozenset(obligations)
        if attrs.get("all_included_claims_approved") is not True:
            reasons.append(ReasonCode.PUBLICATION_BLOCKED)
            return False, frozenset(reasons), frozenset(obligations)
        if (attrs.get("open_included_dispute_count") or 0) != 0:
            reasons.append(ReasonCode.DISPUTE_OPEN)
            return False, frozenset(reasons), frozenset(obligations)
        if attrs.get("quote_matches_model") is not True:
            reasons.append(ReasonCode.PUBLICATION_BLOCKED)
            return False, frozenset(reasons), frozenset(obligations)
        if attrs.get("exception_required") is True:
            if attrs.get("exception_state") != "ACTIVATED":
                reasons.append(ReasonCode.EXCEPTION_NOT_ACTIVATED)
                return False, frozenset(reasons), frozenset(obligations)
            if attrs.get("exception_covers_deliverable") is not True:
                reasons.append(ReasonCode.EXCEPTION_SCOPE_MISMATCH)
                return False, frozenset(reasons), frozenset(obligations)
            if attrs.get("exception_expires_at"):
                try:
                    expires = datetime.fromisoformat(str(attrs["exception_expires_at"]))
                    if expires.replace(tzinfo=UTC) <= request.context.now.replace(tzinfo=UTC):
                        reasons.append(ReasonCode.EXCEPTION_EXPIRED)
                        return False, frozenset(reasons), frozenset(obligations)
                except ValueError:
                    reasons.append(ReasonCode.POLICY_INPUT_INVALID)
                    return False, frozenset(reasons), frozenset(obligations)
        reasons.append(ReasonCode.ROLE_ELIGIBLE)
        obligations.extend(
            [
                Obligation(type="watermark_provisional"),
                Obligation(type="write_audit_event"),
            ]
        )
        return True, frozenset(reasons), frozenset(obligations)

    # ── exception.activate (design Section 11.4) ──────────────────────────
    def _evaluate_exception_activate(
        self,
        request: AuthzRequest,
        reasons: list[ReasonCode],
        obligations: list[Obligation],
    ) -> tuple[bool, frozenset[ReasonCode], frozenset[Obligation]]:
        attrs = request.resource.attributes
        if request.principal.id != attrs.get("approver_id"):
            reasons.append(ReasonCode.RELATIONSHIP_MISSING)
            return False, frozenset(reasons), frozenset(obligations)
        if request.principal.id == attrs.get("requester_id"):
            reasons.append(ReasonCode.SELF_APPROVAL_FORBIDDEN)
            return False, frozenset(reasons), frozenset(obligations)
        if attrs.get("state") != "APPROVED":
            reasons.append(ReasonCode.EXCEPTION_NOT_ACTIVATED)
            return False, frozenset(reasons), frozenset(obligations)
        if attrs.get("policy_eligibility") != "PASS":
            reasons.append(ReasonCode.EXCEPTION_NOT_ACTIVATED)
            return False, frozenset(reasons), frozenset(obligations)
        if attrs.get("scope_non_empty") is not True:
            reasons.append(ReasonCode.EXCEPTION_SCOPE_MISMATCH)
            return False, frozenset(reasons), frozenset(obligations)
        approval_expires = attrs.get("approval_expires_at")
        if approval_expires:
            try:
                expires = datetime.fromisoformat(str(approval_expires))
                if expires.replace(tzinfo=UTC) <= request.context.now.replace(tzinfo=UTC):
                    reasons.append(ReasonCode.EXCEPTION_EXPIRED)
                    return False, frozenset(reasons), frozenset(obligations)
            except ValueError:
                reasons.append(ReasonCode.POLICY_INPUT_INVALID)
                return False, frozenset(reasons), frozenset(obligations)
        reasons.append(ReasonCode.ROLE_ELIGIBLE)
        obligations.append(Obligation(type="write_audit_event"))
        return True, frozenset(reasons), frozenset(obligations)

    # ── opportunity.lock_realization (design Section 12.3) ────────────────
    def _evaluate_opportunity_lock(
        self,
        request: AuthzRequest,
        reasons: list[ReasonCode],
        obligations: list[Obligation],
    ) -> tuple[bool, frozenset[ReasonCode], frozenset[Obligation]]:
        attrs = request.resource.attributes
        if "workflow.realization_owner" not in request.principal.workflow_roles:
            reasons.append(ReasonCode.ROLE_MISSING)
            return False, frozenset(reasons), frozenset(obligations)
        if attrs.get("lifecycle_state") not in {"QUALIFIED", "COMMITTED", "WON"}:
            reasons.append(ReasonCode.POLICY_INPUT_INVALID)
            return False, frozenset(reasons), frozenset(obligations)
        if attrs.get("required_approvals_complete") is not True:
            reasons.append(ReasonCode.ROLE_MISSING)
            return False, frozenset(reasons), frozenset(obligations)
        if (attrs.get("blocking_dispute_count") or 0) != 0:
            reasons.append(ReasonCode.DISPUTE_OPEN)
            return False, frozenset(reasons), frozenset(obligations)
        exp = set(request.principal.workflow_roles) & _LOGICAL_REALIZATION_ROLES
        if request.principal.approval_ceiling_usd is None and not exp:
            reasons.append(ReasonCode.ROLE_MISSING)
            return False, frozenset(reasons), frozenset(obligations)
        reasons.append(ReasonCode.ROLE_ELIGIBLE)
        obligations.extend(
            [
                Obligation(type="write_audit_event"),
                Obligation(type="require_idempotency_key"),
            ]
        )
        return True, frozenset(reasons), frozenset(obligations)


class FailClosedPolicyEngine:
    """Wraps an engine and returns deny when the engine is unavailable.

    Used as the default facade engine until OPA is deployed; also exercises the
    ``PDP_UNAVAILABLE`` failure path deterministically.
    """

    def __init__(self, inner: PolicyEngine | None = None) -> None:
        self._inner = inner

    def evaluate(self, request: AuthzRequest) -> tuple[bool, frozenset[ReasonCode], frozenset[Obligation]]:
        if self._inner is None:
            return False, frozenset({ReasonCode.PDP_UNAVAILABLE}), frozenset()
        try:
            return self._inner.evaluate(request)
        except Exception:
            return False, frozenset({ReasonCode.PDP_UNAVAILABLE}), frozenset()


def new_decision_id() -> str:
    return f"azd_{uuid.uuid4().hex[:16]}"


def utcnow() -> datetime:
    return datetime.now(UTC)
