# ADR-048: Platform roles and workflow roles are separate namespaces

**Status:** Accepted
**Date:** 2026-08-28
**Deciders:** Platform Architecture Committee, Security & Identity Engineering
**Reviewers:** Authorization Control Plane Working Group, Layer 4 Agents
---

## Context

Clerk/bootstrap organization roles authorize platform access such as tenant administration, membership, billing, and read-only access. These roles must not implicitly grant value-governance authority such as claim approval or deliverable publication, otherwise a membership grant could silently become a business-approval grant.

## Decision

Keep platform roles (`platform.tenant_admin`, `platform.member`, `platform.billing_admin`, `platform.read_only`) and workflow roles (`workflow.*`) in separate namespaces. Identity-provider organization roles never confer approval, publication, exception, or realization-lock authority. Protected transitions require a recognized `workflow.*` role validated against `baseline_roles.json`, and tenant administration alone is never sufficient. `any_recognized_role` in the global policy accepts either namespace for non-critical known actions, but the protected verbs are decided only by their own domain packages.

## Consequences

- Tenant administration cannot silently become business approval.
- Role administration is auditable and namespace-scoped.
- New approval authorities are explicit workflow roles, not incidental platform grants.

## Related

Design Section 23 ADR-Authz-48
