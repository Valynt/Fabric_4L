"""The Fabric authorization facade.

Application code calls :meth:`AuthorizationService.authorize` with an
:class:`AuthzRequest` (or a built request from an :class:`AuthContext`) and
receives a typed :class:`AuthzDecision`. The facade is the only stable
interface; application code must not depend on raw Rego/OPA response shapes.

Fail-closed guarantees:
  * unknown action / resource type                 → deny (POLICY_INPUT_INVALID)
  * tenant mismatch between principal & resource   → deny (TENANT_MISMATCH)
  * unrecognized constraint for a protected write  → deny
  * decision engine unavailable or raising         → deny (PDP_UNAVAILABLE)
"""
from __future__ import annotations

from typing import Any

from value_fabric.shared.identity.fabric_auth import AuthContext

from app.authz.actions import (
    AGENT_FORBIDDEN_ACTIONS as _AGENT_FORBIDDEN,
)
from app.authz.actions import (
    is_known_action,
    resource_type_for_action,
)
from app.authz.constants import DenyCode, ReasonCode
from app.authz.engine import (
    POLICY_VERSION,
    FailClosedPolicyEngine,
    InProcessPolicyEngine,
    PolicyEngine,
    fingerprint_input,
    new_decision_id,
    utcnow,
)
from app.authz.records import DecisionOutbox, DecisionRecordStore
from app.authz.schemas import (
    AuthzDecision,
    AuthzRequest,
    Principal,
)

# Obligation types the enforcement point understands. An unrecognized
# mandatory obligation must fail closed.
KNOWN_OBLIGATIONS = frozenset(
    {
        "record_approval_reason",
        "append_domain_audit",
        "write_audit_event",
        "watermark_provisional",
        "require_idempotency_key",
        "require_reason_code",
        "require_mfa_step_up",
        "require_second_approver",
        "redact_fields",
        "limit_export_columns",
        "notify_security_reviewer",
    }
)

_DENY_CODE_BY_REASON: dict[ReasonCode, DenyCode] = {
    ReasonCode.TENANT_MISMATCH: DenyCode.DENIED,
    ReasonCode.PRINCIPAL_INACTIVE: DenyCode.DENIED,
    ReasonCode.ROLE_MISSING: DenyCode.DENIED,
    ReasonCode.RELATIONSHIP_MISSING: DenyCode.DENIED,
    ReasonCode.SELF_APPROVAL_FORBIDDEN: DenyCode.SELF_APPROVAL_FORBIDDEN,
    ReasonCode.APPROVAL_CEILING_EXCEEDED: DenyCode.APPROVAL_CEILING_EXCEEDED,
    ReasonCode.MODEL_VERSION_STALE: DenyCode.MODEL_VERSION_STALE,
    ReasonCode.DISPUTE_OPEN: DenyCode.DISPUTE_OPEN,
    ReasonCode.EXCEPTION_NOT_ACTIVATED: DenyCode.EXCEPTION_NOT_ACTIVATED,
    ReasonCode.EXCEPTION_EXPIRED: DenyCode.EXCEPTION_EXPIRED,
    ReasonCode.AGENT_ACTION_FORBIDDEN: DenyCode.AGENT_FORBIDDEN,
    ReasonCode.POLICY_INPUT_INVALID: DenyCode.POLICY_INPUT_INVALID,
    ReasonCode.PDP_UNAVAILABLE: DenyCode.PDP_UNAVAILABLE,
    ReasonCode.RESOURCE_REVISION_CHANGED: DenyCode.RESOURCE_REVISION_CHANGED,
    ReasonCode.UNKNOWN_ACTION: DenyCode.UNKNOWN_ACTION,
    ReasonCode.UNKNOWN_RESOURCE_TYPE: DenyCode.POLICY_INPUT_INVALID,
    ReasonCode.UNKNOWN_OBLIGATION: DenyCode.UNKNOWN_OBLIGATION,
    ReasonCode.REALIZATION_CONSTRAINT_FAILED: DenyCode.DENIED,
    ReasonCode.PUBLICATION_BLOCKED: DenyCode.DENIED,
    ReasonCode.EXCEPTION_REQUIRED: DenyCode.EXCEPTION_NOT_ACTIVATED,
    ReasonCode.EXCEPTION_SCOPE_MISMATCH: DenyCode.EXCEPTION_NOT_ACTIVATED,
}


class AuthorizationError(RuntimeError):
    """Raised by the facade when a request cannot be evaluated safely."""


class AuthorizationService:
    """Fail-closed facade over a policy engine with decision persistence."""

    def __init__(
        self,
        *,
        engine: PolicyEngine | None = None,
        store: DecisionRecordStore | None = None,
        outbox: DecisionOutbox | None = None,
    ) -> None:
        self._engine: PolicyEngine
        if engine is None:
            self._engine = FailClosedPolicyEngine(InProcessPolicyEngine())
        else:
            self._engine = engine
        self._store = store if store is not None else DecisionRecordStore()
        self._outbox = outbox if outbox is not None else DecisionOutbox(self._store)

    @staticmethod
    def principal_from_auth_context(auth: AuthContext) -> Principal:
        """Adapt an existing :class:`AuthContext` into a policy principal.

        Platform roles are carried as-is; workflow roles are derived in later
        milestones from governed membership. Critically, tenant identity and
        role strings alone never grant authority — the policy plane re-evaluates.
        """
        return Principal(
            id=auth.user_id,
            type="human",
            tenant_id=auth.tenant_id,
            status="active",
            platform_roles=frozenset(auth.roles or ()),
            workflow_roles=frozenset(),
            is_agent=False,
        )

    def authorize(
        self,
        request: AuthzRequest,
        *,
        protected: bool = True,
        revisions: tuple[dict[str, Any], ...] = (),
    ) -> AuthzDecision:
        """Evaluate ``request`` and return a typed decision.

        Always returns a decision (never raises for policy denials). Raises
        :class:`AuthorizationError` only for programmer misuse (invalid request
        construction), which itself encodes a fail-closed deny.
        """
        denied: AuthzDecision | None = self._validate(request)
        if denied is not None:
            self._record(request, denied, revisions=revisions)
            return denied

        allow, reason_codes, obligations = self._engine.evaluate(request)
        deny_code = None
        if not allow:
            deny_code = _first_deny_code(reason_codes)

        unknown_obligation = next(
            (ob for ob in obligations if ob.type not in KNOWN_OBLIGATIONS),
            None,
        )
        if unknown_obligation is not None:
            allow = False
            reason_codes = frozenset({ReasonCode.UNKNOWN_OBLIGATION})
            deny_code = DenyCode.UNKNOWN_OBLIGATION
            obligations = frozenset()

        decision = AuthzDecision(
            decision_id=new_decision_id(),
            allow=allow,
            reason_codes=reason_codes,
            deny_code=deny_code,
            policy_version=getattr(self._engine, "version", POLICY_VERSION),
            input_fingerprint=fingerprint_input(request),
            obligations=obligations,
            evaluated_at=utcnow(),
        )
        self._record(request, decision, revisions=revisions)
        return decision

    # ── validation (fail-closed, evaluated before any engine call) ────────
    def _validate(self, request: AuthzRequest) -> AuthzDecision | None:
        if request.schema_version != "fabric.authz.request.v1":
            return self._deny(ReasonCode.POLICY_INPUT_INVALID, request)
        if not is_known_action(request.action):
            return self._deny(ReasonCode.UNKNOWN_ACTION, request)
        resource = resource_type_for_action(request.action)
        if resource is None or resource != request.resource.type:
            return self._deny(ReasonCode.UNKNOWN_RESOURCE_TYPE, request)
        if request.principal.tenant_id != request.resource.tenant_id:
            return self._deny(ReasonCode.TENANT_MISMATCH, request)
        if request.principal.status != "active":
            return self._deny(ReasonCode.PRINCIPAL_INACTIVE, request)
        if request.principal.type == "agent" or request.principal.is_agent:
            if request.action in _AGENT_FORBIDDEN:
                return self._deny(ReasonCode.AGENT_ACTION_FORBIDDEN, request)
        return None

    def _deny(self, reason: ReasonCode, request: AuthzRequest) -> AuthzDecision:
        return AuthzDecision(
            decision_id=new_decision_id(),
            allow=False,
            reason_codes=frozenset({reason}),
            deny_code=_DENY_CODE_BY_REASON.get(reason, DenyCode.DENIED),
            policy_version=getattr(self._engine, "version", POLICY_VERSION),
            input_fingerprint=fingerprint_input(request),
            evaluated_at=utcnow(),
        )

    def _record(
        self,
        request: AuthzRequest,
        decision: AuthzDecision,
        *,
        revisions: tuple[dict[str, Any], ...] = (),
    ) -> None:
        self._outbox.enqueue(
            decision,
            tenant_id=request.principal.tenant_id,
            principal_id=request.principal.id,
            principal_type=request.principal.type,
            resource_type=request.resource.type,
            resource_id=request.resource.id,
            action=request.action,
            revisions=revisions,
        )

    # ── persistence accessors for control-plane surfaces ─────────────────
    def recent_decisions(self, tenant_id: str, *, limit: int = 500) -> list[Any]:
        return self._store.list_by_tenant(tenant_id, limit=limit)

    @property
    def store(self) -> DecisionRecordStore:
        return self._store
    @property
    def outbox(self) -> DecisionOutbox:
        return self._outbox


def _first_deny_code(reason_codes: frozenset[ReasonCode]) -> DenyCode:
    for reason in reason_codes:
        if reason in _DENY_CODE_BY_REASON:
            return _DENY_CODE_BY_REASON[reason]
    return DenyCode.DENIED
