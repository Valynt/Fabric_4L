---
owner: docs-team
status: draft
last_reviewed: 2026-06-06
---

# Security Readiness Gates

This page tracks the security gates required before Fabric4L can be considered production-safe.

## Gate format

Each gate should define:

- Requirement
- Why it matters
- Validation command
- Expected pass condition
- Owner
- Status
- Evidence link

## Gates

| Gate | Requirement | Validation | Status |
| --- | --- | --- | --- |
| Auth boundary | Protected endpoints reject unauthenticated access | Add command | Pending |
| Tenant isolation | Cross-tenant access is denied by default | Add command | Pending |
| Secret handling | No production secrets committed or logged | Add command | Pending |
| Metrics access | Metrics endpoint is protected | Add command | Pending |
| SSRF protection | Metadata and private network targets are blocked | Add command | Pending |
