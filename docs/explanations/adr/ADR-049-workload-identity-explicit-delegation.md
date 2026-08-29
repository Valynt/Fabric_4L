# ADR-049: Workload identity and explicit delegation for AI and services

**Status:** Accepted
**Date:** 2026-08-28
**Deciders:** Platform Architecture Committee, Security & Identity Engineering
**Reviewers:** Authorization Control Plane Working Group, Layer 4 Agents
---

## Context

AI agents and backend services execute on behalf of humans. Without a workload identity model, an agent could inherit the full authority of the human principal it operates for, including approval and publication power, which the platform must never grant.

## Decision

Preserve actor and subject identity for workload principals. Effective authority is the intersection of the workload's own capabilities and the explicit delegation granted by the actor, never a superset of either. Agents carry `principal.type == "agent"` and are subject to a categorical agent-forbidden action set (claim approval, validation, publication, exception activation, realization lock, canonicalization, and similar protected verbs) regardless of tenant equality or the requested resource. The control-plane module expresses this as `AGENT_FORBIDDEN_ACTIONS` and the `AGENT_ACTION_FORBIDDEN` deny reason, mirrored in the Rego `agent_forbidden_actions` set.

## Consequences

- Agents can read and analyze but can never approve, publish, or activate.
- Delegation is explicit, bounded, and auditable.
- Service-to-service calls preserve the originating actor for decision recording.

## Related

Design Section 23 ADR-Authz-49
