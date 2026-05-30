# Alerting / Alertmanager Source-of-Truth Matrix

## Purpose

Maintain the authoritative alerting and Alertmanager source of truth across environments and prevent monitoring drift.

## Trigger

Alert routing drift, missing page, noisy alert, monitoring configuration change, release readiness review, or observability incident.

## Severity

SEV-1 if critical production alerts are not routed; SEV-2 for degraded or noisy alerting on production services; SEV-3 for non-production or documentation drift.

## Preconditions

Environment inventory, alert rule sources, Alertmanager configuration, dashboard links, and owning teams are known.

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

Observability alert gates: alert rule validation, Alertmanager routing source-of-truth checks, Layer 5/Layer 6 observability contract checks, launch evidence validators, and deployment gates for monitoring changes.

## Related Runbooks

- [Layer 6 health vs readiness runbook](layer6-health-readiness.md)
- [Launch-Ops Sign-off Checklist](launch-ops-signoff-checklist.md)
- [Quarterly Control Attestation Runbook](../compliance/quarterly-control-attestation.md)

## Post-Incident Follow-Up

- Attach validation evidence and gate results to the incident record.
- File corrective actions for missing alerts, missing tests, stale documentation, or slow recovery steps.
- Update this runbook and related gates if the incident exposed drift or an undocumented dependency.

---

## Procedure Details

This runbook defines the **authoritative edit paths** for alerting by environment.
Only these paths should be edited directly.

### Canonical per environment

| Environment | Alertmanager source of truth | Prometheus alert rules source of truth |
|---|---|---|
| Dev | `monitoring/alertmanager/alertmanager.yml` | `monitoring/alerting/rules.yml` |
| Staging | `monitoring/alertmanager/alertmanager-enhanced.yml` | `monitoring/alerting/rules.yml` |
| Prod | `monitoring/alertmanager/alertmanager-production.yml` | `monitoring/alerting/rules-production.yml` |

### Alternates (non-authoritative)

- `monitoring/alerting/alertmanager.yml` — **deprecated** legacy duplicate path. Do not edit.
- `k8s/monitoring-alertmanager.yml` — **derived compatibility manifest**. Regenerate from `k8s/base/monitoring-alertmanager.yml`; do not hand edit.
- `k8s/alertmanager.yml` — **deprecated** and blocked in CI.

### CI enforcement

- `scripts/ci/check_deprecated_alertmanager_manifest.py` fails when deprecated manifests reappear.
- The same check blocks PRs that edit non-authoritative duplicates unless the regeneration signal file is also changed.

### Regeneration expectation

When you intentionally regenerate compatibility artifacts, include the regeneration command/script update in the same PR so CI can verify intent.

### Layer 5 observability governance binding

Layer 5 alert rules and dashboard queries for validation latency, transition failures, and KG sync outcomes are contract-bound to:

- `docs/reference/layer5-observability-schema.md`

Any rename of Layer 5 structured log keys or metric names/labels defined there requires explicit governance review in the same PR.
