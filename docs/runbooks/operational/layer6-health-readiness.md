# Layer 6 health vs readiness runbook

## Purpose

Triage Layer 6 liveness/readiness signals and dependency failures without masking unhealthy benchmark service state.

## Trigger

Layer 6 `/health` or `/ready` alert, benchmark API errors, readiness probe failure, dependency outage, or startup drift alert.

## Severity

SEV-1 for production benchmark service outage; SEV-2 for readiness failures draining traffic or degraded dependencies; SEV-3 for non-production probe drift.

## Preconditions

Access to readiness payloads, logs, dependency status, Kubernetes events, metrics dashboards, and recent deployment metadata is available.

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

Observability and readiness gates: Layer 6 health/readiness checks, `contracts/observability/layer6-metrics.json` validation, dashboard metric drift check, deployment gates, and benchmark service CI gates.

## Related Runbooks

- [Alerting / Alertmanager Source-of-Truth Matrix](alerting-source-of-truth.md)
- [Deployment Rollout, Canary/Blue-Green Criteria, and Rollback](../deployment-rollout-and-rollback.md)

## Post-Incident Follow-Up

- Attach validation evidence and gate results to the incident record.
- File corrective actions for missing alerts, missing tests, stale documentation, or slow recovery steps.
- Update this runbook and related gates if the incident exposed drift or an undocumented dependency.

---

## Procedure Details

### Endpoint contract

- `GET /health`: process liveness only. Returns `200` when the API process is alive.
- `GET /ready`: dependency readiness. Returns `200` only when critical dependencies are ready; returns `503` with deterministic not-ready payload when degraded.

Readiness checks are explicit and stable:

- `config`: startup settings validation succeeded.
- `neo4j`: graph connectivity check passed.
- `benchmark_store`: repository initialized and seeded datasets are queryable.
- `startup`: no critical startup dependency failure was recorded during service boot.

### Probe policy

- Kubernetes `livenessProbe` must target `/health`.
- Kubernetes `readinessProbe` and `startupProbe` must target `/ready`.

### Alerting expectations

- Alert on sustained readiness failures (`/ready` = 503) because traffic should be drained and operator action is required.
- Liveness failures (`/health` != 200) indicate process-level instability; page immediately if restart loops are detected.
- During dependency outages, expect `/health` to remain green while `/ready` is red. This is expected and prevents unnecessary restarts.

### Operator response

1. If `/health` fails, treat the issue as process liveness or crash-loop instability.
2. If `/ready` fails but `/health` stays green, inspect the `checks` object in the readiness payload first.
3. For `config` failures, correct the deployment environment or secret/config map inputs and restart the pod.
4. For `neo4j` or `benchmark_store` failures, restore dependency connectivity before forcing restarts; repeated restarts will not clear a downstream outage.

### Observability checks

- Layer 6 metrics and label contracts live in `contracts/observability/layer6-metrics.json`.
- Startup drift diagnosis should begin with the `layer6.startup` log record, which includes `version`, `build_sha`, and `config_fingerprint`.
- Dashboard and alert query drift can be checked with `python scripts/observability/check_layer6_dashboard_metrics.py`.
