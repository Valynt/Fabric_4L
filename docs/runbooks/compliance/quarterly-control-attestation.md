# Quarterly Control Attestation Runbook

## Purpose

Collect, review, and attest quarterly control evidence for security, compliance, governance, and operational readiness controls.

## Trigger

Quarterly compliance calendar event, auditor request, control owner rotation, failed control evidence check, or governance exception review.

## Severity

SEV-2 when a mandatory control cannot be attested by the due date; SEV-3 for evidence gaps that are contained and tracked before the deadline.

## Preconditions

Control owners are assigned, evidence repositories are accessible, prior exceptions are known, and production gate evidence is current.

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

Compliance and readiness gates: structural preflight, contract checks, tenant-isolation/security test gates, backup/restore readiness evidence, launch evidence validators, and required CI checks in `.github/workflows/pr-checks.yml`.

## Related Runbooks

- [Launch-Ops Sign-off Checklist](../operational/launch-ops-signoff-checklist.md)
- [Alerting / Alertmanager Source-of-Truth Matrix](../operational/alerting-source-of-truth.md)
- [Backup and Disaster Recovery Runbook](../backup-disaster-recovery.md)

## Post-Incident Follow-Up

- Attach validation evidence and gate results to the incident record.
- File corrective actions for missing alerts, missing tests, stale documentation, or slow recovery steps.
- Update this runbook and related gates if the incident exposed drift or an undocumented dependency.

---

## Procedure Details

### Purpose

Define the repeatable quarterly process for attesting control design and operating effectiveness with auditable sign-off checkpoints.

### Scope

- Controls listed in `docs/compliance/evidence-inventory-matrix.md`.
- Governance readiness controls from P0/P1/P2 production-readiness documents.

### Roles

- **Control Owner:** validates control operation and evidence completeness.
- **Compliance Reviewer:** verifies evidence quality, retention, and approval traceability.
- **Security Reviewer:** validates security-sensitive controls.
- **Executive Signatory:** final quarterly attestation approval.

### Inputs

1. Current quarter evidence bundle from CI/CD artifacts.
2. Access review records for in-scope systems.
3. Incident and drill outputs.
4. Any control exceptions and remediation tickets.

### Procedure

1. **Evidence collection checkpoint**
   - Pull control artifacts generated in the quarter.
   - Confirm required metadata exists (`generated_at`, `control_id`, `owner`, `sanitized`).

2. **Control-by-control validation checkpoint**
   - For each control, verify:
     - evidence exists,
     - evidence is within frequency window,
     - retention path is defined,
     - approval history is present.

3. **Exception review checkpoint**
   - Validate unresolved exceptions have owner, risk rating, due date.
   - Confirm compensating controls are documented.

4. **Sign-off checkpoint**
   - Control owner signs each control row.
   - Compliance reviewer signs overall packet.
   - Security reviewer signs security/privacy controls.
   - Executive signatory approves quarter attestation statement.

5. **Archive checkpoint**
   - Store signed attestation package in compliance archive location.
   - Record immutable reference identifier in quarterly tracker.

### Output Template

- Quarter: `YYYY-Q#`
- Overall status: `PASS | PASS WITH EXCEPTIONS | FAIL`
- Controls reviewed: `<count>`
- Exceptions open: `<count>`
- Signatures:
  - Control Owner(s): `<name/date>`
  - Compliance Reviewer: `<name/date>`
  - Security Reviewer: `<name/date>`
  - Executive Signatory: `<name/date>`

### Escalation

If any critical control lacks evidence or approval trace:
- classify as attestation blocker,
- escalate to Compliance + Security leadership within 1 business day,
- track remediation before quarter close.
