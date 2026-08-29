"""Namespace action catalog for the Fabric authorization control plane.

Permission identifiers are stable, namespaced contracts (design �9). The
catalog is the single source of truth for which actions are known to the
policy plane. Any action not present in ``KNOWN_ACTIONS`` is denied by the
fail-closed facade as ``POLICY_INPUT_INVALID``.
"""
from __future__ import annotations

# Agent categorical-forbidden actions (design �11.1). These are the protected
# transitions that agents may never perform; only a human principal may even be
# *considered* for them, and the per-domain policy gates the human additionally.
AGENT_FORBIDDEN_ACTIONS: frozenset[str] = frozenset(
    {
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
    }
)

# The four critical protected-transition verbs (design �21 Phase 2). These are
# the first enforcement milestone and must deny by default.
CRITICAL_FOUR_ACTIONS: frozenset[str] = frozenset(
    {
        "claim.approve",
        "deliverable.publish_external",
        "exception.activate",
        "opportunity.lock_realization",
    }
)

# Known resource types. Resource types are also narrowly enumerated so that an
# unknown resource type is denied rather than silently skipped.
KNOWN_RESOURCE_TYPES: frozenset[str] = frozenset(
    {
        "claim",
        "opportunity",
        "model",
        "deliverable",
        "exception",
        "evidence",
        "membership",
        "relationship",
        "policy",
        "audit",
    }
)

# Full known-action catalog from design �9. Mapping action -> canonical
# resource type the action governs.
_ACTIONS_BY_RESOURCE: dict[str, tuple[str, ...]] = {
    "opportunity": (
        "opportunity.view",
        "opportunity.assign",
        "opportunity.edit_working",
        "opportunity.change_stage",
        "opportunity.lock_realization",
        "opportunity.archive",
    ),
    "claim": (
        "claim.view",
        "claim.edit_working",
        "claim.propose_edit",
        "claim.set_derivation",
        "claim.link_evidence",
        "claim.validate",
        "claim.approve",
        "claim.include_in_case",
        "claim.exclude_from_case",
        "claim.open_dispute",
        "claim.resolve_dispute",
    ),
    "model": (
        "model.create_version",
        "model.compare_versions",
        "model.mark_canonical",
        "model.tag_scenario",
        "model.accept_candidate",
    ),
    "deliverable": (
        "deliverable.render_lens",
        "deliverable.share_internal",
        "deliverable.publish_external",
        "deliverable.view_external",
        "deliverable.revoke_link",
    ),
    "exception": (
        "exception.draft",
        "exception.submit",
        "exception.review",
        "exception.approve",
        "exception.reject",
        "exception.activate",
        "exception.revoke",
        "exception.extend",
    ),
    "evidence": (
        "evidence.ingest",
        "evidence.search",
        "evidence.accept",
        "evidence.reject",
        "evidence.reclassify",
        "evidence.link",
    ),
    "membership": (
        "membership.assign_role",
        "membership.revoke_role",
    ),
    "relationship": (
        "relationship.assign",
        "relationship.revoke",
    ),
    "policy": (
        "policy.view_effective",
        "policy.simulate",
    ),
    "audit": (
        "audit.read_business",
        "audit.read_security",
        "verification.read",
        "verification.append",
        "break_glass.request",
        "break_glass.approve",
        "break_glass.revoke",
    ),
}

KNOWN_ACTIONS: frozenset[str] = frozenset(
    action
    for actions in _ACTIONS_BY_RESOURCE.values()
    for action in actions
)

# Reverse map for resource-type lookup / validation.
_ACTION_TO_RESOURCE: dict[str, str] = {
    action: resource
    for resource, actions in _ACTIONS_BY_RESOURCE.items()
    for action in actions
}


def resource_type_for_action(action: str) -> str | None:
    """Return the canonical resource type governing ``action`` (or None)."""
    return _ACTION_TO_RESOURCE.get(action)


def is_known_action(action: str) -> bool:
    """True if ``action`` is a known namespaced permission identifier."""
    return action in KNOWN_ACTIONS
