# Deployment Rollout, Canary/Blue-Green Criteria, and Rollback

## Purpose

Safely roll out, observe, and roll back Kubernetes and CI/CD deployments using canary or blue-green controls.

## Trigger

Production or staging deployment, smoke-check failure, rollout health regression, SLO breach after cutover, or emergency rollback request.

## Severity

SEV-1 for customer-impacting production outage after deployment; SEV-2 for failed canary/green health gates before broad impact; SEV-3 for non-production rollout drift.

## Preconditions

Rendered manifests are reviewed, CI required checks passed, secrets/config are present, rollback target is healthy, and an operator owns the cutover window.

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

Deployment gates: structural-preflight, per-layer lint/typecheck/test jobs, contract-checks, blue-green health gate, canonical chaos-testing gate when promoted to required, frontend verification, and backend integrated release smoke where applicable.

## Related Runbooks

- [Backup and Disaster Recovery Runbook](backup-disaster-recovery.md)
- [CI Infisical OIDC Recovery and Secret Rotation](operational/ci-infisical-oidc-recovery.md)
- [Layer 6 health vs readiness runbook](operational/layer6-health-readiness.md)

## Post-Incident Follow-Up

- Attach validation evidence and gate results to the incident record.
- File corrective actions for missing alerts, missing tests, stale documentation, or slow recovery steps.
- Update this runbook and related gates if the incident exposed drift or an undocumented dependency.

---

## Procedure Details

### Scope

This runbook applies to Kubernetes deployments under `k8s/base/`, `k8s/blue-green/`, and the CI/CD ephemeral deployment stage that:

1. Runs preflight checks.
2. Applies rendered manifests to an ephemeral Kubernetes cluster.
3. Executes post-deploy smoke checks for Layer 1–Layer 5 and the frontend.

---

### Blue-Green Operator Procedure (Required)

1. **Deploy green stack (no traffic yet)**
   - `kubectl apply -k k8s/blue-green/overlays/green`
   - Keep `Service/layer4-agents-active` selector on `track=blue`.
2. **Verify green health gates**
   - Run readiness/latency/error gate:
     - `python scripts/ci/blue_green_health_gate.py --health-url <green-health-url> --metrics-url <green-metrics-url> --max-error-rate 0.02 --max-p95-latency-ms 1200`
   - Gate must pass before traffic shift.
3. **Shift traffic (controlled switch)**
   - `kubectl apply -k k8s/blue-green/overlays/green` (service selector changes to `track=green`).
4. **Observe post-cutover window**
   - Observe for at least 15 minutes.
   - Rollback triggers:
     - readiness false for >60s
     - error rate >2% for 5 minutes
     - p95 latency >1200ms for 5 minutes
5. **Rollback criteria and command**
   - If any trigger breaches threshold and does not self-recover in 5 minutes:
     - `kubectl apply -k k8s/blue-green/overlays/blue`
   - Confirm health gate against blue before closing incident.

---

### Chaos Testing Gate

- Current workflow: `.github/workflows/chaos-testing.yml`.
- Command: `scripts/ci/run_chaos_smoke.sh` remains the lightweight local smoke entrypoint.
- Includes minimal repeatable scenarios:
  - Redis outage behavior on Layer 1 job submission.
  - Database latency spike behavior on Layer 2 extraction.
  - Downstream Layer 3 timeout impact on Layer 4 approval policy path.
- Promotion plan:
  1. Track flakes for two consecutive weeks.
  2. Keep required chaos evidence in the canonical `chaos-testing.yml` workflow.
  3. Add the canonical chaos-testing check name as required in branch protection policy if it becomes merge-blocking.

---

### Standard Rollback Procedure

If smoke checks fail or production SLOs regress:

1. **Freeze rollout**
   - Pause automation and stop additional promotions.
2. **Identify failing component**
   - Check deployment status and pod events.
   - Check readiness probe failures and error-rate dashboards.
3. **Rollback**
   - For a `Deployment`: `kubectl rollout undo deployment/<name> -n value-fabric`
   - For blue-green: switch traffic back to previous service selector (`track=blue` or `track=green`).
4. **Verify**
   - Wait for rollout completion.
   - Re-run smoke checks for L1–L5 and frontend.
5. **Escalate if persistent**
   - Follow service-specific runbook in this folder.
   - Open incident and include root cause plus corrective action.
