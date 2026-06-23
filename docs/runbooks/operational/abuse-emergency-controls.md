# Abuse Emergency Controls Runbook

## Purpose

Activate emergency abuse controls such as blocklists, stricter tenant limits, or replay-protection escalation without weakening production safeguards.

## Trigger

Abuse spike, credential stuffing, scraping, replay attempts, tenant-specific misuse, anomalous traffic, or security incident commander request.

## Severity

SEV-1 for active abuse causing customer/security impact; SEV-2 for contained abuse or high-risk indicators; SEV-3 for preventive tuning.

## Preconditions

Incident commander approval, affected tenants/IPs/subjects, current rate-limit baselines, audit logging, and rollback criteria are available.

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

Tenant-isolation and observability gates: tenant boundary/security tests, rate-limit contract checks, production auth-bypass gate, abuse alert gates, and deployment gates if configuration is rolled through CI/CD.

## Related Runbooks

- [Enterprise OIDC / SSO Incident Runbook](enterprise-oidc-sso-incident.md)
- [Alerting / Alertmanager Source-of-Truth Matrix](alerting-source-of-truth.md)

## Post-Incident Follow-Up

- Attach validation evidence and gate results to the incident record.
- File corrective actions for missing alerts, missing tests, stale documentation, or slow recovery steps.
- Update this runbook and related gates if the incident exposed drift or an undocumented dependency.

---

## Procedure Details

### Purpose
Define emergency controls for abuse spikes (401/403/429 bursts, token replay signals) and how to safely tighten protections.

### Controls

#### 1) Blocklists
- Apply temporary IP/CIDR blocklists at edge/gateway.
- Apply API key / tenant blocklists in auth layer when repeated abusive patterns are confirmed.
- Expire blocklist entries by default (recommended TTL: 1-24h) and require incident ticket linkage.

#### 2) Temporary stricter limits
- Reduce route-class limits for:
  - Auth endpoints (`/auth`, `/v1/auth`)
  - Write-heavy endpoints (`/v1/ingest`, `/v1/sync`, `/v1/schema/init`)
  - Export/report endpoints (`/v1/export`, `/v1/report`)
- Increase WAF/gateway anomaly sensitivity only during active incident windows.
- Keep rollback criteria explicit (e.g., deny/error rates normalize for >=30 minutes).

#### 3) Replay protection escalation
- Rotate signing keys/session secrets if replay is broad or credential theft suspected.
- Force token re-issue for impacted tenants/users.
- Require nonce/jti replay cache checks in auth stack for elevated mode.

### Activation checklist
1. Confirm alert source and scope (layer, endpoint, tenant, API key, source IP).
2. Declare incident and assign commander.
3. Apply least-disruptive control first (key block > IP/CIDR block > global stricter limits).
4. Monitor 5-minute rolling rates for 401/403/429 and replay signals.
5. Escalate only if abuse persists.

### Rollback checklist
1. Remove temporary blocks in reverse order of application.
2. Restore normal route-class rate limits.
3. Verify error budgets and auth success rates return to baseline.
4. Publish incident summary with retained and removed controls.

### Related monitoring
- `AuthDeniedSpike` alert (401/403 surge)
- `RateLimit429Spike` alert (429 surge)
- `TokenReplaySuspected` alert (replay pattern)
