# Model Registry Governance Incident Runbook

## Purpose

Respond when an unapproved, deprecated, blocked, or incorrectly versioned model is selected by runtime services.

## Trigger

Model registry alert, failed eval gate, unapproved production model selection, deprecated model use, model override detection, or customer-impacting model output issue.

## Severity

SEV-1 for blocked/unapproved model serving production traffic or material customer risk; SEV-2 for pre-impact version/eval drift; SEV-3 for metadata-only drift.

## Preconditions

Registry record, model card, eval evidence, runtime selection audit event, rollback model, and model steward approval are available.

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

Agent evaluation and governance gates: golden-trace evals, benchmark/safety eval gates, model registry validation, production override checks, deployment gates for runtime routing changes, and contract checks for agent output schemas.

## Related Runbooks

- [Formula Approval Chain Runbook](../formula-approval.md)
- [Launch-Ops Sign-off Checklist](launch-ops-signoff-checklist.md)

## Post-Incident Follow-Up

- Attach validation evidence and gate results to the incident record.
- File corrective actions for missing alerts, missing tests, stale documentation, or slow recovery steps.
- Update this runbook and related gates if the incident exposed drift or an undocumented dependency.

---

## Procedure Details

This runbook covers incidents where an unapproved, deprecated, blocked, or incorrectly versioned model is selected by Fabric_4L runtime services. The safe default is to stop new traffic to the affected model and roll back to the last approved production version.

### Severity Classification

| Severity | Condition | Expected response |
|---|---|---|
| SEV-1 | A blocked or unapproved model serves production traffic, or model output creates material customer risk. | Freeze model promotion, disable affected runtime selection, roll back immediately, and page model steward. |
| SEV-2 | A model version mismatch, missing model card, or failed eval gate is discovered before broad production impact. | Pause promotion and require steward approval before traffic resumes. |
| SEV-3 | Registry metadata drift or stale deprecation metadata is detected without runtime impact. | Repair registry metadata and add validation coverage. |

### Immediate Checks

Determine which runtime service selected the model, which registry record was used, and whether the selected version was in an allowed lifecycle state. Capture sanitized evidence only; provider API keys, prompt secrets, and tenant data must not be copied into incident records.

| Check | Evidence | Pass criterion |
|---|---|---|
| Registry state | Model ID, immutable version, lifecycle state, owner, approver. | Production traffic uses only `production` state records. |
| Eval gate | Golden trace, benchmark, and safety evidence linked to the registry record. | Required gates passed before promotion. |
| Runtime selection | Service config or audit event showing registry lookup. | Free-form model override is not used in production. |
| Rollback target | Previous production registry record. | Target is approved, monitored, and available. |

### Remediation Procedure

Set the affected model registry record to `blocked` or remove it from production routing if supported by the service. Roll back to the previous approved production version and confirm the runtime no longer accepts environment-variable model overrides. Run the golden-trace eval suite and compare cost, latency, and correctness deltas before reopening promotion.

### Closure Evidence

The incident can close only after runtime traffic uses the approved rollback or fixed production version, audit records link the change to an approver, eval evidence is attached, deprecation or block state is enforced, and the post-incident review identifies a prevention control such as stronger CI validation or runtime registry enforcement.
