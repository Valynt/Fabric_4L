"""Pure-Python policy decision engine (PBAC).

Evaluates an ``AuthzRequest`` against the policy bundle (RBAC role-action
matrix, ReBAC relationships, ABAC request-time facts, SoD, and protected
state-machine rules) and yields an allow/deny interim result plus reason
codes.

This engine is the *enforcement-side mirror* of the declarative Rego bundle
under ``policies/authorization/bundle``. The Rego bundle is the human-auditable
source of truth; parity tests assert the Python engine and the bundle agree on
a shared corpus of decisions, and CI gate ``check_policy_bundle.py`` keeps the
two in sync (bundle data JSON is loaded by this engine directly so they cannot
drift).

The engine never makes network I/O and never mutates state. It is a pure
function of (bundle, request) and is safe to use in tests, workers, and the
LSP without a live PDP.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from .errors import ReasonCode


# ---------------------------------------------------------------------------
# Bundle in-memory model
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class PolicyBundle:
    """Parsed policy bundle used by the engine."""

    policy_version: str
    bundle_digest: str
    role_actions: dict[str, frozenset[str]]
    static_sod_pairs: frozenset[tuple[str, str]]
    action_catalog: frozenset[str]
    agent_forbidden_actions: frozenset[str]
    protected_commands: frozenset[str]
    reason_codes: frozenset[str]
    exception_transitions: dict[str, frozenset[str]] = field(default_factory=dict)


def load_bundle(data_dir: str, *, policy_version: str) -> PolicyBundle:
    """Load policy bundle data JSON files from a directory.

    ``data_dir`` should point at ``policies/authorization/bundle/data``.
    """
    import os

    def _read(name: str) -> dict:
        path = os.path.join(data_dir, name)
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)

    roles = _read("baseline_roles.json")
    role_actions = {
        role: frozenset(defn.get("actions", []))
        for role, defn in roles.get("roles", {}).items()
    }
    catalog = _read("action_catalog.json")
    sod = _read("static_sod.json")
    trans = _read("exception_transitions.json")
    reasons = _read("reason_codes.json")

    digest_material = json.dumps(
        {
            "roles": roles,
            "catalog": catalog,
            "sod": sod,
            "transitions": trans,
            "reasons": reasons,
        },
        sort_keys=True,
    )
    bundle_digest = hashlib.sha256(digest_material.encode("utf-8")).hexdigest()[:16]

    return PolicyBundle(
        policy_version=policy_version,
        bundle_digest=bundle_digest,
        role_actions=role_actions,
        static_sod_pairs=frozenset((a, b) for a, b in sod.get("pairs", [])),
        action_catalog=frozenset(catalog.get("actions", [])),
        agent_forbidden_actions=frozenset(catalog.get("agent_forbidden", [])),
        protected_commands=frozenset(catalog.get("protected_commands", [])),
        reason_codes=frozenset(reasons.get("reason_codes", [])),
        exception_transitions={
            state: frozenset(next_states)
            for state, next_states in trans.get("transitions", {}).items()
        },
    )


@dataclass
class InterimResult:
    """Non-persisted evaluation result from the engine."""

    allowed: bool
    deny_code: str | None = None
    reason_codes: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Dispatcher helper
# ---------------------------------------------------------------------------
class _Deny(Exception):
    def __init__(self, code: ReasonCode, *extra: ReasonCode) -> None:
        self.codes = [code, *extra]
        super().__init__(code.value)


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------
class DecisionEngine:
    """Evaluates an AuthzRequest. Fail closed on any anomaly."""

    def __init__(
        self,
        bundle: PolicyBundle,
        *,
        resolver=None,
        now: datetime | None = None,
    ) -> None:
        # ``resolver`` is an optional callable: resolver(request) -> enriched
        # resource_attributes/relationships dict used to resolve server-side
        # facts (see attribute_resolver). Unused by the pure engine when None.
        self._bundle = bundle
        self._resolver = resolver
        self._now = now or datetime.now(UTC)

    # -- public -------------------------------------------------------------
    def evaluate(self, request: Any) -> InterimResult:
        """Evaluate an AuthzRequest-like object. Returns InterimResult.

        Never raises for a *denied* decision (returns allowed=False). Raises
        only for malformed input (fail closed -> converts to a deny).
        """
        try:
            return self._evaluate(request)
        except _Deny as exc:
            return InterimResult(
                allowed=False,
                deny_code=exc.codes[0].value,
                reason_codes=[c.value for c in exc.codes],
            )
        except Exception:
            # Fail closed on any internal anomaly.
            return InterimResult(
                allowed=False,
                deny_code=ReasonCode.POLICY_INPUT_INVALID.value,
                reason_codes=[ReasonCode.POLICY_INPUT_INVALID.value],
            )

    # -- internals ----------------------------------------------------------
    def _evaluate(self, request: Any) -> InterimResult:
        action = str(request.action)
        principal = (
            request.principal.to_dict()
            if hasattr(request.principal, "to_dict")
            else dict(request.principal)
        )
        resource = dict(request.resource or {})
        env = request.environment

        # 1. action must be catalogued (default deny).
        if action not in self._bundle.action_catalog:
            raise _Deny(ReasonCode.UNCATALOGUED_ACTION)

        # 2. principal must be active.
        if not principal.get("is_active", True):
            raise _Deny(ReasonCode.PRINCIPAL_INACTIVE)

        # 3. agent capability ceiling.
        ptype = principal.get("principal_type")
        if ptype == "agent" and action in self._bundle.agent_forbidden_actions:
            raise _Deny(ReasonCode.AGENT_ACTION_FORBIDDEN)

        ptype = ptype or "human"

        # 4. tenant containment.
        principal_tenant = principal.get("tenant_id")
        resource_tenant = resource.get("tenant_id") or env.relationships.get(
            "tenant_id"
        )
        if resource_tenant and principal_tenant:
            if str(resource_tenant) != str(principal_tenant):
                raise _Deny(ReasonCode.TENANT_MISMATCH)
        elif resource_tenant and not principal_tenant:
            raise _Deny(ReasonCode.TENANT_MISMATCH)

        # 5. RBAC job authority: does any held role permit the action?
        held_roles = principal.get("roles") or []
        permitted = False
        for role in held_roles:
            if action in self._bundle.role_actions.get(str(role), frozenset()):
                permitted = True
                break
        if not permitted:
            raise _Deny(ReasonCode.ROLE_MISSING)

        # 6. Static separation of duties: no principal may hold both roles in
        # any configured conflicting pair.
        normalized_roles = {str(role) for role in held_roles}
        if any(
            first in normalized_roles and second in normalized_roles
            for first, second in self._bundle.static_sod_pairs
        ):
            raise _Deny(ReasonCode.STATIC_SOD_VIOLATION)

        # 7. verb-specific domain rules.
        self._apply_verb_rules(action, principal, resource, env)

        return InterimResult(allowed=True)

    def _apply_verb_rules(
        self, action: str, principal: dict, resource: dict, env: Any
    ) -> None:
        attrs = (
            env.resource_attributes
            if hasattr(env, "resource_attributes")
            else (env or {})
        )
        rel = env.relationships if hasattr(env, "relationships") else {}
        principal_id = str(
            principal.get("principal_id") or principal.get("user_id") or ""
        )

        # -------- claim.approve --------
        if action == "claim.approve":
            author_id = str(attrs.get("author_id") or "")
            if author_id and principal_id and author_id == principal_id:
                raise _Deny(ReasonCode.SELF_APPROVAL_FORBIDDEN)
            if not attrs.get("validation_complete"):
                raise _Deny(ReasonCode.VALIDATION_INCOMPLETE)
            if attrs.get("has_open_dispute"):
                raise _Deny(ReasonCode.DISPUTE_OPEN)
            ceiling = attrs.get("approval_ceiling")
            impact = attrs.get("impact_amount")
            if (
                ceiling is not None
                and impact is not None
                and float(impact) > float(ceiling)
            ):
                raise _Deny(ReasonCode.APPROVAL_CEILING_EXCEEDED)
            # ReBAC: approver must be bound economic reviewer or approved pool.
            if (
                rel.get("per_claim_binding") is False
                and rel.get("review_pool_binding") is False
            ):
                raise _Deny(ReasonCode.RELATIONSHIP_MISSING)
            if not rel.get("same_tenant", True):
                raise _Deny(ReasonCode.TENANT_MISMATCH)

        # -------- deliverable.publish_external --------
        if action == "deliverable.publish_external":
            if not attrs.get("all_included_claims_approved"):
                raise _Deny(ReasonCode.REQUIREMENT_NOT_MET)
            if attrs.get("any_open_dispute"):
                raise _Deny(ReasonCode.DISPUTE_OPEN)
            if rel.get("quote_matches_model") is False:
                raise _Deny(ReasonCode.REQUIREMENT_NOT_MET)
            if not rel.get("publisher_sod_ok", True):
                raise _Deny(ReasonCode.PUBLISHER_SOD_VIOLATION)
            # Required activated in-scope unexpired exception.
            if rel.get("requires_exception") and not rel.get("exception_active"):
                raise _Deny(ReasonCode.EXCEPTION_NOT_ACTIVATED)

        # -------- exception transitions (state machine) --------
        if action == "exception.activate":
            current = attrs.get("current_state")
            target = attrs.get("target_state")
            allowed_next = self._bundle.exception_transitions.get(current, frozenset())
            if target not in allowed_next:
                raise _Deny(ReasonCode.EXCEPTION_INVALID_TRANSITION)
            if attrs.get("is_expired"):
                raise _Deny(ReasonCode.EXCEPTION_EXPIRED)
            requester_id = str(attrs.get("requester_id") or "")
            if requester_id and principal_id and requester_id == principal_id:
                raise _Deny(ReasonCode.SELF_APPROVAL_FORBIDDEN)
            # Only eligible approver or controlled system transition may activate.
            if not rel.get("eligible_activator", False):
                raise _Deny(ReasonCode.ROLE_MISSING)

        # -------- opportunity.lock_realization --------
        if action == "opportunity.lock_realization":
            if attrs.get("is_locked"):
                raise _Deny(ReasonCode.DEPLOYMENT_LOCK_VIOLATION)
            # ReBAC: realization lock requires opportunity binding.
            if not rel.get("opportunity_bound", False):
                raise _Deny(ReasonCode.RELATIONSHIP_MISSING)
            if principal.get("principal_type") == "agent":
                raise _Deny(ReasonCode.AGENT_ACTION_FORBIDDEN)

        # -------- membership/administration --------
        if action == "break_glass.approve":
            if not rel.get("dual_control_ok", False):
                raise _Deny(ReasonCode.DUAL_CONTROL_REQUIRED)

        # -------- generic protected-command guard --------
        # If a protected command reaches the engine without a domain rule, the
        # role matrix already gated it; anything uncatalogued was filtered.
        return


# ---------------------------------------------------------------------------
# Convenience singleton-less factory for parity tests
# ---------------------------------------------------------------------------
def default_engine(data_dir: str, *, policy_version: str) -> DecisionEngine:
    return DecisionEngine(load_bundle(data_dir, policy_version=policy_version))
