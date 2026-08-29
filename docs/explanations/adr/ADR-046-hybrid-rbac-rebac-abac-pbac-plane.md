# ADR-046: Hybrid constrained RBAC, ReBAC, and ABAC through a PBAC plane

**Status:** Accepted
**Date:** 2026-08-28
**Deciders:** Platform Architecture Committee, Security & Identity Engineering
**Reviewers:** Authorization Control Plane Working Group, Layer 4 Agents
---

## Context

Fabric must authorize every protected value-governance transition -- claim approval, deliverable publication, exception activation, and realization lock -- with consistent, auditable semantics. None of the three classic models alone is sufficient: plain roles cannot express resource scope, plain relationships cannot express job class, and plain attributes cannot express organizational authority. Embedding ad-hoc checks in each service would reproduce the drift problems the platform is trying to eliminate.

## Decision

Adopt a unified policy-based authorization control (PBAC) plane that composes three models under one decision surface: roles for job class (`workflow.*` and `platform.*`), relationships for resource scope (`economic_reviewer`, `realization_owner`, and similar typed bindings), and attributes for request-time constraints (approval ceiling, model version, publication state, dispute counts). One policy decision plane evaluates every request and returns a single `allow` / `deny_reason` / `obligations` contract. The Python `InProcessPolicyEngine` and the Rego bundle under `policies/authorization/` are dual mirrors of the same decision tables; the `AuthorizationService` facade is the only entry point for decisions.

## Consequences

- A single decision contract covers all protected transitions, so consumers never branch on engine internals.
- New domains add actions to the catalog instead of embedding ad-hoc logic.
- Divergence between the Python oracle and the Rego bundle is caught by dual tests before OPA is deployed.

## Related

Design Section 23 ADR-Authz-46
