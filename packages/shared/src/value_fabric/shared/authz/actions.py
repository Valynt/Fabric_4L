"""Typed action, role, and principal catalogs for the authorization control plane.

These catalogs are the single source of truth for *what can be authorized*.
Any action, role, or principal type not present here is denied by default.

Raw string role checks scattered across the codebase are expected to migrate
onto this catalog (see ``scripts/ci/check_raw_role_guards.py`` and
``docs/authz/staged-migration.md``).
"""

from __future__ import annotations

import enum


# ---------------------------------------------------------------------------
# Workflow roles (job authority) — distinct from IdP/platform roles.
# ---------------------------------------------------------------------------
class WorkflowRole(str, enum.Enum):
    """Small, opinionated workflow-role set.

    These grant *job authority* within governed workflows. They are bound to
    tenants and must never be inferred from an IdP "admin" claim alone.
    """

    VALUE_ENGINEER = "value_engineer"
    VALUE_MANAGER = "value_manager"
    FINANCE_APPROVER = "finance_approver"
    TECHNICAL_REVIEWER = "technical_reviewer"
    DEAL_DESK = "deal_desk"
    SECURITY_REVIEWER = "security_reviewer"
    REALIZATION_OWNER = "realization_owner"
    TENANT_ADMIN = "tenant_admin"


# Alias for convenience/back-compat with naming in policy bundles.
WORKFLOW_ROLES = {r.value for r in WorkflowRole}


# ---------------------------------------------------------------------------
# Principal types
# ---------------------------------------------------------------------------
class PrincipalType(str, enum.Enum):
    """Modeled principals for the control plane."""

    HUMAN = "human"
    AGENT = "agent"
    SERVICE = "service"
    SYSTEM = "system"
    EXTERNAL_VIEWER = "external_viewer"


PRINCIPAL_TYPES = {p.value for p in PrincipalType}


# ---------------------------------------------------------------------------
# Action catalog (must match policies/authorization/bundle/data/action_catalog.json)
# ---------------------------------------------------------------------------
class Action(str, enum.Enum):
    """Authorization actions.

    Every action used in ``authorize()`` MUST be catalogued here and in the
    policy bundle's ``action_catalog.json``. CI gate
    ``check_authorization_catalog.py`` enforces the two stay in sync.
    """

    # ------------------------------------------------------- claims
    CLAIM_VIEW = "claim.view"
    CLAIM_EDIT_WORKING = "claim.edit_working"
    CLAIM_VALIDATE = "claim.validate"
    CLAIM_APPROVE = "claim.approve"
    CLAIM_INCLUDE_IN_CASE = "claim.include_in_case"
    CLAIM_OPEN_DISPUTE = "claim.open_dispute"
    CLAIM_RESOLVE_DISPUTE = "claim.resolve_dispute"
    # ------------------------------------------------------- models
    MODEL_MARK_CANONICAL = "model.mark_canonical"
    # ------------------------------------------------------- deliverables
    DELIVERABLE_PUBLISH_EXTERNAL = "deliverable.publish_external"
    DELIVERABLE_REVOKE_LINK = "deliverable.revoke_link"
    # ------------------------------------------------------- exceptions
    EXCEPTION_SUBMIT = "exception.submit"
    EXCEPTION_APPROVE = "exception.approve"
    EXCEPTION_ACTIVATE = "exception.activate"
    EXCEPTION_REVOKE = "exception.revoke"
    # ------------------------------------------------------- opportunities
    OPPORTUNITY_LOCK_REALIZATION = "opportunity.lock_realization"
    # ------------------------------------------------------- administration
    MEMBERSHIP_ASSIGN_ROLE = "membership.assign_role"
    BREAK_GLASS_APPROVE = "break_glass.approve"


# Canonical set of catalogued actions.
ACTION_CATALOG: frozenset[str] = frozenset(a.value for a in Action)


# ---------------------------------------------------------------------------
# Protected domain commands
# ---------------------------------------------------------------------------
# Principle 7: approval, validation, publication, exception activation,
# canonicalization, and realization locking are protected domain commands,
# not generic CRUD updates. Treating them as CRUD enables unauthorized direct
# state mutation. CI gate ``check_protected_transition_guards.py`` enforces
# each of these has an enforcement point.
PROTECTED_DOMAIN_COMMANDS: frozenset[str] = frozenset({
    Action.CLAIM_APPROVE.value,
    Action.CLAIM_VALIDATE.value,
    Action.CLAIM_INCLUDE_IN_CASE.value,
    Action.CLAIM_RESOLVE_DISPUTE.value,
    Action.MODEL_MARK_CANONICAL.value,
    Action.DELIVERABLE_PUBLISH_EXTERNAL.value,
    Action.EXCEPTION_SUBMIT.value,
    Action.EXCEPTION_APPROVE.value,
    Action.EXCEPTION_ACTIVATE.value,
    Action.EXCEPTION_REVOKE.value,
    Action.OPPORTUNITY_LOCK_REALIZATION.value,
})


# ---------------------------------------------------------------------------
# Agent capability ceiling
# ---------------------------------------------------------------------------
# Principle 8: agents may propose and analyze but may never approve, validate,
# publish, activate exceptions, resolve disputes, mark models canonical, or
# lock realization. CI gate ``check_agent_tool_metadata.py`` enforces agent
# tools declare authorization metadata and never wrap these actions.
AGENT_FORBIDDEN_ACTIONS: frozenset[str] = frozenset({
    Action.CLAIM_VALIDATE.value,
    Action.CLAIM_APPROVE.value,
    Action.CLAIM_INCLUDE_IN_CASE.value,
    Action.CLAIM_RESOLVE_DISPUTE.value,
    Action.MODEL_MARK_CANONICAL.value,
    Action.DELIVERABLE_PUBLISH_EXTERNAL.value,
    Action.EXCEPTION_SUBMIT.value,
    Action.EXCEPTION_APPROVE.value,
    Action.EXCEPTION_ACTIVATE.value,
    Action.OPPORTUNITY_LOCK_REALIZATION.value,
})


# Actions that never return a cached decision; the PDP must be consulted and
# the decision recorded each time (revision/state sensitive, audit-critical).
UNCACHEABLE_ACTIONS: frozenset[str] = frozenset(
    PROTECTED_DOMAIN_COMMANDS | {Action.BREAK_GLASS_APPROVE.value}
)