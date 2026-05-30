# Runbook Title

## Purpose

Describe the system, customer journey, control, or operational risk this runbook protects.

## Trigger

List the alerts, CI/readiness gate failures, operator observations, support escalations, or scheduled events that start this runbook.

## Severity

Define severity mapping for the runbook. Include customer impact, tenant-isolation/security impact, data-loss risk, and production-readiness impact.

## Preconditions

List required access, owners, dashboards, secrets-management paths, backup artifacts, tenant-scope data, and approval requirements before operators act.

## Immediate Actions

1. Declare or confirm the incident owner and severity.
2. Freeze risky automated changes affecting the impacted service or control.
3. Capture timestamps, affected tenants/customers, deployment version, and active alerts.
4. Preserve evidence before restarts, restores, rotations, or routing changes.

## Diagnosis Steps

1. Confirm the trigger and affected environment.
2. Check dashboards, logs, audit records, dependency status, and gate output.
3. Determine whether the issue is tenant-specific, dependency-specific, deployment-specific, or global.
4. Identify the safest reversible mitigation.

## Resolution Steps

1. Apply the least-risk corrective action for the confirmed failure mode.
2. Preserve tenant isolation, contract compatibility, and fail-closed security behavior.
3. Escalate before destructive operations such as data restore, credential revocation, or broad traffic cutover.
4. Record all commands, approvals, configuration changes, and timestamps.

## Validation

- Re-run the readiness, smoke, contract, tenant-isolation, backup/restore, eval, or observability gates relevant to the incident.
- Confirm customer-critical paths recover.
- Confirm logs, metrics, and audit records show no new regressions.

## Rollback / Fallback

Document the last known-good deployment, configuration, registry record, credentials, backup artifact, or manual fallback. State when rollback is preferred over forward-fix.

## Customer / Stakeholder Communication

Specify who must be notified, what information can be shared, update cadence, and any security/privacy restrictions.

## Evidence to Preserve

List alert names, timestamps, dashboard links, deployment SHAs, migration IDs, sanitized logs, audit events, backup IDs, eval outputs, and operator actions to attach to the incident record.

## Related Gates

Name the relevant readiness or CI gates, such as deployment gates, migration readiness gates, tenant-isolation gates, backup/restore readiness gates, agent evaluation gates, and observability alert gates.

## Related Runbooks

Link to adjacent runbooks and escalation paths.

## Post-Incident Follow-Up

List expected corrective actions, runbook updates, alert/test/gate improvements, owner assignments, and due dates.
