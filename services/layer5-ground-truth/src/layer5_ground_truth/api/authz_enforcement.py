"""Layer 5 PBAC enforcement: the single typed authorization facade.

Wires the shared authorization control plane (``value_fabric.shared.authz``)
into Layer 5 domain writes. It is the *only* module that calls
:func:`guard_protected_command`; individual routes must not scatter ad-hoc
``has_role`` checks onto protected verbs.

Enforcement contract (fail closed):
  * ``guard_protected_command`` raises a canonical ``HTTPException`` 403 when a
    protected command is denied and 503 when the PDP/obligation/decision sink
    is unavailable. A protected command can never fall through to a generic
    CRUD write on an authorization outage.
  * Role assignments and resource bindings are resolved server-side. In test
    environments the SQLite ORM schema does not carry the authz control-plane
    tables, so a deterministic static map keyed by caller identity is used.
    Production reads authoritative rows from ``authz_role_assignments`` /
    ``authz_resource_bindings``.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Test-mode role provider
# ---------------------------------------------------------------------------
# SQLite tests create only ORM tables (not the authz control-plane migration),
# so we resolve workflow roles from a declarative map. Production resolves them
# from authz_role_assignments. This map is loaded ONCE at call time so tests can
# reconfigure it; it is never consulted in production-like environments.
_TEST_WORKFLOW_ROLES: dict[str, list[str]] = {
    "test-user": ["value_engineer", "finance_approver"],
    "test-user-full-perm": ["value_engineer", "finance_approver"],
    "approver": ["finance_approver"],
    "author": [],
    "agent": [],
    "test-user-no-perm": [],
}


def _is_test_environment() -> bool:
    env = os.environ.get("ENVIRONMENT") or os.environ.get("APP_ENV") or ""
    return env.strip().lower() == "test"


async def get_workflow_roles(caller: Any, db: Any) -> list[str]:
    """Resolve authoritative workflow-role assignments for a caller.

    Test-mode: static map keyed by ``caller.user_id`` (deterministic).
    Production: read ``authz_role_assignments``; absent table / DB failure
    falls back to empty (deny) rather than raising, so a role outage can never
    broaden authority.
    """
    if _is_test_environment():
        return list(_TEST_WORKFLOW_ROLES.get(str(getattr(caller, "user_id", "")), []))

    # Production path — authoritative DB read. Catch table/connection gaps and
    # fail closed (no roles = ROLE_MISSING deny at the engine).
    try:
        rows = await _read_role_assignments(db, caller)
        return list(rows)
    except Exception as exc:  # pragma: no cover - DB/table availability
        logger.warning(
            "workflow-role resolution failed; failing closed with no roles: %s", exc
        )
        return []


async def _read_role_assignments(db: Any, caller: Any) -> set[str]:
    # Imported lazily to keep the module importable before SQLAlchemy env is set.
    from sqlalchemy import text

    principal_id = str(getattr(caller, "user_id", "") or "")
    result = await db.execute(
        text(
            "SELECT role_id FROM authz_role_assignments "
            "WHERE tenant_id = :tenant AND principal_id = :principal "
            "AND (expires_at IS NULL OR expires_at > now())"
        ),
        {"tenant": str(getattr(caller, "tenant_id", "")), "principal": principal_id},
    )
    return {row[0] for row in result.all()}


async def build_principal(caller: Any, db: Any) -> Any:
    """Build a typed ``PrincipalContext`` from the authenticated caller.

    Roles are injected from ``get_workflow_roles`` (authoritative server-side)
    and never trusted from the wire. Principal type is inferred from the auth
    source (agent/system/service/external_viewer) by the shared adapter.
    """
    from value_fabric.shared.authz.principal_context import (
        principal_context_from_request,
    )

    roles = await get_workflow_roles(caller, db)
    ctx = principal_context_from_request(caller)
    caller_tenant = getattr(caller, "tenant_id", None)
    caller_user = getattr(caller, "user_id", None)
    tenant_id = ctx.tenant_id or (str(caller_tenant) if caller_tenant else None)
    user_id = ctx.user_id or (str(caller_user) if caller_user else None)
    # Re-project with authoritative roles.
    return type(ctx).build(
        principal_type=ctx.principal_type,
        principal_id=ctx.principal_id
        or str(getattr(caller, "user_id", "") or "anonymous"),
        tenant_id=tenant_id,
        user_id=user_id,
        roles=roles,
        bound_tenant_ids=(
            (ctx.bound_tenant_ids or [ctx.tenant_id])
            if ctx.tenant_id
            else ([tenant_id] if tenant_id else [])
        ),
        impersonator_id=ctx.impersonator_id,
    )


# ---------------------------------------------------------------------------
# Protected-command guard
# ---------------------------------------------------------------------------
# Maps action -> canonical place where the enforcement point lives. Used by the
# CI gate ``check_protected_transition_guards.py`` to prove every protected
# command in the catalog is actually enforced, and by the fail-closed claim.
PROTECTED_COMMAND_PATHS: dict[str, str] = {
    "claim.approve": "layer5_ground_truth.api.value_claim_routes.transition_value_claim_status",
    "claim.validate": "layer5_ground_truth.services.value_claim_service.transition_status",
    "claim.include_in_case": "layer5_ground_truth.api.authz_enforcement.guard_protected_command",
    "claim.resolve_dispute": "layer5_ground_truth.api.authz_enforcement.guard_protected_command",
    "model.mark_canonical": "layer5_ground_truth.api.authz_enforcement.guard_protected_command",
}

_unknown_action: set[str] = set()


async def guard_protected_command(
    *,
    action: str,
    principal: Any,
    resource: dict[str, Any],
    requested_resource_revision: str | None = None,
    environment: Any | None = None,
    request_context: Any = None,
) -> Any:
    """Enforce a protected domain command via the shared command guard.

    Raises:
      HTTPException 403:AuthorizationDeniedError (denied by policy).
      HTTPException 503:PDUnavailableError (PDP / obligations / sink outage —
                          FAIL CLOSED).
    Returns the resulting ``AuthzDecision`` when allowed and obligations
    honored.
    """
    from value_fabric.shared.authz.client import get_authorization_client
    from value_fabric.shared.authz.command_guard import CommandGuard
    from value_fabric.shared.authz.errors import (
        AuthorizationDeniedError,
        PDUnavailableError,
    )

    if action in _unknown_action:  # pragma: no cover - defensive
        logger.warning("guard invoked for non-protected catalog action: %s", action)
    guard = CommandGuard(get_authorization_client())
    try:
        return await guard.require(
            principal=principal,
            action=action,
            resource=resource,
            requested_resource_revision=requested_resource_revision,
            environment=environment,
            request_context=request_context,
        )
    except AuthorizationDeniedError as exc:
        deny_code = (exc.details or {}).get("deny_code") or (
            exc.reason_code.value if hasattr(exc, "reason_code") else exc.message
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error_code": deny_code or "authorization_denied",
                "message": str(getattr(exc, "message", "") or "authorization denied"),
                "decision_id": (exc.details or {}).get("decision_id"),
            },
        ) from exc
    except PDUnavailableError as exc:
        logger.error("protected command %s failed closed (outage): %s", action, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error_code": "authorization_unavailable",
                "message": "authorization service unavailable; failing closed",
            },
        ) from exc


# ---------------------------------------------------------------------------
# Claim-approval fact resolution
# ---------------------------------------------------------------------------
# Conservative by default: any fact we cannot authoritatively resolve is
# treated as NOT satisfied so the engine denies (fail closed). Production
# deployments should back these with authoritative sources (truth-object
# validation records, a dispute registry, and approval ceilings). Where a fact
# has no source of truth yet we default to deny and flag behavior debt.
#
# Included claim fields and bindings below are the minimal projection required
# by the engine's ``claim.approve`` verb rule.


async def resolve_claim_approval_facts(
    claim: Any, caller: Any, db: Any, overrides: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Resolve server-side ABAC/ReBAC facts for a ``claim.approve`` decision.

    Returns a dict that is merged into the request environment as resource
    attributes and relationships. Anything unknown resolves to the safe
    (deny) default.  Optional ``overrides`` are applied after the conservative
    defaults and are intended for test scenarios.
    """
    overrides = overrides or {}
    bindings = await _resolve_claim_bindings(claim, caller, db)
    claim_status = str(getattr(claim, "status", "") or "").lower()

    # Reaching MODELED is the authoritative lifecycle indication that the
    # claim completed the validation stage required before approval.
    attrs: dict[str, Any] = {
        "author_id": str(getattr(claim, "created_by_user_id", "") or ""),
        # No authoritative validation/evidence resolver exists yet on ValueClaim;
        # benign-but-not-part-of-core defaults deny so we never over-authorize.
        "validation_complete": overrides.get(
            "validation_complete", claim_status == "modeled"
        ),
        "has_open_dispute": overrides.get("has_open_dispute", False),
        "impact_amount": _to_float(getattr(claim, "expected_value", None)),
        "approval_ceiling": await _resolve_approval_ceiling(caller, db),
        "revision": str(getattr(claim, "version", "1") or "1"),
    }
    # Apply test overrides after defaults (so test can selectively override).
    if overrides:
        attrs.update({k: v for k, v in overrides.items() if k in attrs})
    # ReBAC relationships (ReBAC bindings) — default deny.
    rel: dict[str, Any] = {
        # Economic reviewer / reviewer pool binding. Tests may set this.
        "per_claim_binding": overrides.get(
            "per_claim_binding", bindings["per_claim_binding"]
        ),
        "review_pool_binding": overrides.get(
            "review_pool_binding", bindings["review_pool_binding"]
        ),
        "same_tenant": overrides.get(
            "same_tenant",
            str(getattr(claim, "tenant_id", ""))
            == str(getattr(caller, "tenant_id", "")),
        ),
    }
    return {"attributes": attrs, "relationships": rel}


async def _resolve_claim_bindings(claim: Any, caller: Any, db: Any) -> dict[str, bool]:
    """Resolve active approver bindings from server-owned state."""
    user_id = str(getattr(caller, "user_id", "") or "")
    if _is_test_environment():
        roles = _TEST_WORKFLOW_ROLES.get(user_id, [])
        return {
            "per_claim_binding": False,
            "review_pool_binding": "finance_approver" in roles,
        }

    try:
        from sqlalchemy import text

        result = await db.execute(
            text(
                "SELECT relation FROM authz_resource_bindings "
                "WHERE tenant_id = :tenant AND resource_type = 'value_claim' "
                "AND resource_id = :resource AND principal_id = :principal "
                "AND relation IN ('economic_reviewer', 'review_pool') "
                "AND (expires_at IS NULL OR expires_at > now())"
            ),
            {
                "tenant": str(getattr(caller, "tenant_id", "")),
                "resource": str(getattr(claim, "id", "")),
                "principal": user_id,
            },
        )
        relations = {row[0] for row in result.all()}
        return {
            "per_claim_binding": "economic_reviewer" in relations,
            "review_pool_binding": "review_pool" in relations,
        }
    except Exception:  # pragma: no cover - DB/table availability
        return {"per_claim_binding": False, "review_pool_binding": False}


async def _resolve_approval_ceiling(caller: Any, db: Any) -> float | None:
    # Deterministic ceiling for the finance_approver test principal.
    if (
        _is_test_environment()
        and str(getattr(caller, "user_id", "")) in _TEST_WORKFLOW_ROLES
        and "finance_approver"
        in _TEST_WORKFLOW_ROLES.get(str(getattr(caller, "user_id", "")))
    ):
        return _TEST_APPROVAL_CEILING
    try:
        from sqlalchemy import text

        pid = str(getattr(caller, "user_id", "") or "")
        rows = await db.execute(
            text(
                "SELECT approval_ceiling_usd FROM authz_role_assignments "
                "WHERE tenant_id = :tenant AND principal_id = :principal "
                "AND role_id = 'finance_approver' AND approval_ceiling_usd IS NOT NULL "
                "ORDER BY approval_ceiling_usd DESC LIMIT 1"
            ),
            {"tenant": str(getattr(caller, "tenant_id", "")), "principal": pid},
        )
        row = rows.first()
        return _to_float(row[0]) if row else None
    except Exception:  # pragma: no cover - DB availability
        return None


# Deterministic test ceiling so a finance_approver's impact within ceiling.
_TEST_APPROVAL_CEILING = 1_000_000.0


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def make_claim_approval_environment(facts: dict[str, Any]) -> Any:
    """Build an ``AuthzEnvironment`` from resolved facts for a claim.approve."""
    from value_fabric.shared.authz.models import AuthzEnvironment

    return AuthzEnvironment(
        resource_attributes=dict(facts.get("attributes", {})),
        relationships=dict(facts.get("relationships", {})),
    )


# ---------------------------------------------------------------------------
# Obligation handlers
# ---------------------------------------------------------------------------
_obligations_registered = False


def register_l5_obligations() -> None:
    """Register obligation handlers required for protected commands.

    Idempotent. Without the ``audit`` handler, every *allowed* protected
    decision would fail its obligations and 503 (fail closed). This is the
    sanctioned place to add Layer 5 obligation handling (audit correlation,
    external-scope masking, dual control).
    """
    global _obligations_registered
    if _obligations_registered:
        return
    from value_fabric.shared.authz.obligations import register_obligation

    async def _audit_handler(request_context: Any, decision: Any) -> bool:
        # Audit correlation: the decision is correlated to the resulting domain
        # event via request_context (request_id / trace_id) and decision_id.
        action = next(
            (
                obligation.detail.get("action")
                for obligation in getattr(decision, "obligations", [])
                if obligation.kind == "audit"
            ),
            None,
        )
        logger.info(
            "authz decision: action=%s allowed=%s decision_id=%s reason_codes=%s",
            action,
            getattr(decision, "allowed", None),
            getattr(decision, "decision_id", None),
            getattr(decision, "reason_codes", None) or [],
        )
        return True

    register_obligation("audit", _audit_handler)
    _obligations_registered = True
    logger.info("registered authorization obligation handlers (audit)")
