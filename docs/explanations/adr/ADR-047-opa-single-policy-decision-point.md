# ADR-047: OPA as the single general-purpose policy decision point

**Status:** Accepted
**Date:** 2026-08-28
**Deciders:** Platform Architecture Committee, Security & Identity Engineering
**Reviewers:** Authorization Control Plane Working Group, Layer 4 Agents
---

## Context

Fabric spans six layers and a shared gateway; each service could easily embed its own authorization policy, reproducing checks inconsistently and drifting from the intended contract. Two equal policy engines would make the platform's behavior depend on which engine happened to evaluate a request.

## Decision

Use OPA/Rego behind the Fabric `AuthorizationService` facade as the single general-purpose policy decision point (PDP). No service embeds independent authorization policy, and no second equal policy engine is introduced. Before OPA runs as a service, the facade executes the in-process engine (`InProcessPolicyEngine`), which mirrors the Rego exactly and fails closed (`PDP_UNAVAILABLE` -> deny) when the engine is unavailable. The Rego bundle defines `package fabric.authz.*` with default-deny semantics and the exact decision tables mirrored in Python, so the in-process oracle and the future OPA PDP produce identical verdicts.

## Consequences

- Authorization policy lives in one place and is versioned (`authz-1.0.0`).
- Every service and the gateway share one decision contract and one reason-code vocabulary.
- PDP failure is always deny, never allow.

## Related

Design Section 23 ADR-Authz-47
