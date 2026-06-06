---
owner: docs-team
status: draft
last_reviewed: 2026-06-06
---

# Critical Behaviors

Critical behaviors are the intended behaviors that must not regress.

A behavior is critical when a failure would affect:

- Tenant isolation
- Authentication or authorization
- Data privacy
- Billing or financial correctness
- Production availability
- Security posture
- Compliance evidence

## Behavior contract format

Each behavior contract should include:

- Behavior name
- Allowed behavior
- Denied behavior
- Test file
- Validation command
- Failure meaning
- Owner

## Example

| Behavior | Allowed | Denied | Test |
| --- | --- | --- | --- |
| Tenant-scoped access | User accesses own tenant data | User accesses another tenant's data | Add test path |
