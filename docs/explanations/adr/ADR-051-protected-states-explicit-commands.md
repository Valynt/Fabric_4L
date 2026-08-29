# ADR-051: Protected states are reachable only through explicit commands

**Status:** Accepted
**Date:** 2026-08-28
**Deciders:** Platform Architecture Committee, Security & Identity Engineering
**Reviewers:** Authorization Control Plane Working Group, Layer 4 Agents
---

## Context

Approval, publication, activation, canonicalization, and realization lock are protected state transitions. If these states could be set through generic update APIs or normal direct database writes, authorization policy on those transitions would be meaningless and bypassable.

## Decision

Protected states are reachable only through explicit, authorized commands. Each protected transition is a dedicated action (`claim.approve`, `deliverable.publish_external`, `exception.activate`, `opportunity.lock_realization`, `model.mark_canonical`) that the policy plane evaluates against `input.action`. A generic update cannot set these states because the protected-transition rules key on the dedicated action name, and the command layer that owns the transition performs the state change only after an allow decision. The control-plane module ships a catalog of these actions plus security tests asserting that direct generic-update bypass attempts are denied.

## Consequences

- No generic write path can fabricate a protected state.
- Each protected transition is a first-class, versioned, auditable action.
- Bypass attempts fail closed and are recorded.

## Related

Design Section 23 ADR-Authz-51
