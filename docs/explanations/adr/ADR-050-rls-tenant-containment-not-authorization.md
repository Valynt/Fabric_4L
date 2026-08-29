# ADR-050: RLS is tenant containment, not complete authorization

**Status:** Accepted
**Date:** 2026-08-28
**Deciders:** Platform Architecture Committee, Security & Identity Engineering
**Reviewers:** Authorization Control Plane Working Group, Layer 4 Agents
---

## Context

PostgreSQL row-level security (RLS) filters at the row level by `tenant_id` and is a hard requirement for multi-tenant containment. But RLS cannot express object-, relationship-, workflow-, or state-level decisions: an active same-tenant role-holder is still not entitled to approve a claim they authored, or to publish a deliverable with an unapproved included claim. Treating RLS as complete authorization would leak decision logic into the storage layer and make those semantics un-expressible and un-auditable.

## Decision

Force RLS at the storage layer as tenant containment, and keep object-, relationship-, workflow-, and state-level decisions in the policy plane and domain commands. Every repository method scopes queries by authenticated `tenant_id`; the policy plane additionally verifies tenant equality on every decision (`input.principal.tenant_id == input.resource.tenant_id` is necessary but never sufficient). The two layers are complementary and neither can be skipped.

## Consequences

- RLS continues to enforce physical tenant isolation.
- Authorization semantics live in one auditable policy plane.
- Tenant-equality failure is a distinct, stable deny reason (`TENANT_MISMATCH`).

## Related

Design Section 23 ADR-Authz-50
