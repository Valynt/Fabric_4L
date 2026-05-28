# Formula Approval Chain Runbook

## Purpose

Define and audit multi-level approval chains for governance artifacts (formula, benchmark, policy, assumption) with tenant-scoped isolation.

## Workflow Configuration

Approval chains are configured in `approval_workflows` using:

- `required_approval_levels`: number of ordered levels required before terminal approval.
- `level_definitions`: ordered level quorum rules (example: `[{"level":1,"quorum":1},{"level":2,"quorum":2}]`).
- `default_level_quorum`: fallback quorum for levels not explicitly defined.
- `escalation_mode`: `manual` or `automatic` escalation semantics.

## Guard Semantics

- A request **must remain `pending`** until all required level quorums are satisfied.
- Transition to `approved` is blocked when any required quorum is unmet.
- Approval workflows and decisions are tenant-scoped; cross-tenant workflow/decision mixing is rejected.

## Audit Procedure

1. Confirm request tenant and workflow tenant are identical.
2. Query decisions by request and verify all rows share same tenant.
3. Group decisions by `approval_level` and count `approve` actions.
4. Compare counts to configured per-level quorum.
5. Validate escalation path aligns with `escalation_mode` and decision history.

## Incident Response

If approval bypass is suspected:

1. Freeze new approval transitions for affected tenant/entity type.
2. Export decision history and workflow definition.
3. Identify drift between configured level/quorum and persisted decisions.
4. Re-run tenant isolation checks and hostile cross-tenant regression suite.
5. File governance incident with corrective migration or workflow fix.
