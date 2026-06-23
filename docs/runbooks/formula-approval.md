# Formula Approval Chain Runbook

## Purpose

Operate and audit tenant-scoped approval chains for formulas, benchmarks, policies, assumptions, and other governance artifacts.

## Trigger

Approval queue blockage, suspected cross-tenant approval leakage, incorrect quorum outcome, governance artifact incident, or audit request.

## Severity

SEV-1 for cross-tenant approval exposure or unauthorized production formula use; SEV-2 for blocked approvals or quorum drift; SEV-3 for audit metadata gaps.

## Preconditions

Tenant context, approval workflow configuration, approver identities, audit logs, and affected artifact IDs are available.

## Immediate Actions

1. Declare or confirm the incident owner and severity.
2. Freeze risky automated changes affecting the impacted service or control.
3. Capture initial timestamps, tenant/customer scope, deployment version, and active alerts.
4. Use the diagnosis steps below before applying destructive or irreversible changes.

## Diagnosis Steps

1. Confirm the trigger condition and affected environment.
2. Review the relevant dashboards, logs, audit records, and CI/readiness gate output.
3. Identify whether the issue is isolated to one tenant, service, dependency, or deployment version.
4. Preserve evidence before restarting services, rotating credentials, restoring data, or changing routing.

## Resolution Steps

1. Apply the least-risk corrective action that addresses the confirmed failure mode.
2. Keep tenant isolation, contract compatibility, and fail-closed security behavior intact.
3. Escalate to the service owner or incident commander before any destructive operation.
4. Record each operator action, command, and configuration change in the incident record.

## Validation

- Re-run the relevant health checks, smoke tests, contract checks, or readiness gates listed below.
- Confirm impacted tenants/customers can complete the critical path that failed.
- Confirm logs, metrics, and audit records show recovery and no new cross-tenant or security errors.

## Rollback / Fallback

- Prefer rollback to the last known-good deployment, configuration, registry record, backup, or credential set.
- If rollback is unsafe, isolate the impacted component, drain traffic where supported, and use the documented fallback path in the procedure details.
- Do not delete evidence or failed artifacts until the incident commander approves cleanup.

## Customer / Stakeholder Communication

- Notify the incident channel and accountable product/support stakeholders when customer impact is confirmed or likely.
- Provide scope, severity, current mitigation, expected next update time, and known customer-facing symptoms.
- Avoid sharing secrets, raw tenant data, provider tokens, or unreviewed root-cause speculation.

## Evidence to Preserve

- Alert names, timestamps, dashboard snapshots or links, and runbook version.
- Deployment SHAs, configuration diffs, migration IDs, registry versions, or backup artifact IDs.
- Sanitized logs, audit events, gate outputs, validation commands, and operator action timeline.

## Related Gates

Tenant-isolation and governance gates: tenant boundary/security tests, contract compliance checks for approval payloads, audit evidence checks, formula/benchmark approval readiness, and deployment gates before enabling changed approval logic.

## Related Runbooks

- [Quarterly Control Attestation Runbook](compliance/quarterly-control-attestation.md)
- [Model Registry Governance Incident Runbook](operational/model-registry-governance-incident.md)

## Post-Incident Follow-Up

- Attach validation evidence and gate results to the incident record.
- File corrective actions for missing alerts, missing tests, stale documentation, or slow recovery steps.
- Update this runbook and related gates if the incident exposed drift or an undocumented dependency.

---

## Procedure Details

### Purpose

Define and audit multi-level approval chains for governance artifacts (formula, benchmark, policy, assumption) with tenant-scoped isolation.

### Workflow Configuration

Approval chains are configured in `approval_workflows` using:

- `required_approval_levels`: number of ordered levels required before terminal approval.
- `level_definitions`: ordered level quorum rules (example: `[{"level":1,"quorum":1},{"level":2,"quorum":2}]`).
- `default_level_quorum`: fallback quorum for levels not explicitly defined.
- `escalation_mode`: `manual` or `automatic` escalation semantics.

### Guard Semantics

- A request **must remain `pending`** until all required level quorums are satisfied.
- Transition to `approved` is blocked when any required quorum is unmet.
- Approval workflows and decisions are tenant-scoped; cross-tenant workflow/decision mixing is rejected.

### Audit Procedure

1. Confirm request tenant and workflow tenant are identical.
2. Query decisions by request and verify all rows share same tenant.
3. Group decisions by `approval_level` and count `approve` actions.
4. Compare counts to configured per-level quorum.
5. Validate escalation path aligns with `escalation_mode` and decision history.

### Incident Response

If approval bypass is suspected:

1. Freeze new approval transitions for affected tenant/entity type.
2. Export decision history and workflow definition.
3. Identify drift between configured level/quorum and persisted decisions.
4. Re-run tenant isolation checks and hostile cross-tenant regression suite.
5. File governance incident with corrective migration or workflow fix.
