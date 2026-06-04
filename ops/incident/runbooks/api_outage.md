# API Outage Runbook

## Purpose

Restore customer-critical API access while preserving auth, tenant isolation,
contract compatibility, and audit evidence.

## Trigger

- Sustained 5xx responses or failed readiness checks for `services/api` or
  layer APIs.
- Customer reports that core workflows cannot load or submit.
- Gateway, ingress, deployment, or service health alerts indicate outage.

## Severity

- SEV-1 when the API is unavailable for most customers, auth is bypassed or
  failing open, data exposure is suspected, or multiple layers are unreachable.
- SEV-2 when one major API family is degraded with a workaround.
- SEV-3 when impact is isolated to a tenant or non-critical route and no
  security, privacy, or data-integrity risk exists.

## Preconditions

- Access to deployment status, service logs, traces, metrics, ingress/gateway
  dashboards, audit logs, and recent release artifacts.
- Incident commander approval before rollback, traffic cutover, or broad config
  changes.

## Immediate Actions

1. Declare severity and open the incident channel.
2. Capture first-bad timestamp, affected routes, impacted tenants, deploy SHA,
   active alerts, and recent config or secret changes.
3. Freeze non-essential production deploys.
4. Check whether auth, tenant context, or audit emission is affected.
5. Route customer updates through the communications lead.

## Diagnosis Steps

1. Confirm whether failures are gateway-wide, service-specific, route-specific,
   tenant-specific, or dependency-driven.
2. Compare ingress, API gateway, layer service, database, Redis, and auth
   metrics for the first-bad window.
3. Inspect recent deployment, feature flag, secret, certificate, DNS, and
   configuration changes.
4. Verify error response shapes remain contract-aligned and no stack traces or
   sensitive data are exposed.
5. Check logs and traces using request IDs from affected customer reports.

## Resolution Steps

1. Apply the least-risk reversible mitigation: restart unhealthy pods, roll back
   the last bad deploy, revert config, drain bad instances, or fail over traffic.
2. Do not disable auth, tenant checks, audit logging, rate limiting, or
   governance middleware to restore availability.
3. If dependency degradation is the cause, follow the matching database, queue,
   auth, or infrastructure runbook.
4. Record every command, approval, config change, and deployment action.

## Validation

- Confirm health and readiness endpoints recover.
- Confirm representative customer-critical API routes succeed.
- Confirm auth-required routes reject unauthenticated traffic.
- Confirm tenant-scoped reads do not cross tenant boundaries.
- Confirm logs, metrics, traces, and audit events show recovery.

## Rollback / Fallback

- Prefer rollback to the last known-good deployment or config when a recent
  change correlates with the outage.
- If rollback is unsafe, drain affected instances and route traffic to healthy
  capacity.

## Customer / Stakeholder Communication

- SEV-1 updates every 15 minutes; SEV-2 updates every 30 minutes.
- Report symptoms, affected product areas, mitigation status, and next update
  time. Avoid unverified root-cause claims.

## Evidence to Preserve

- Alert payloads, dashboard screenshots or links, deployment SHA, image digest,
  ingress config, sanitized logs, traces, request IDs, audit records, and
  validation command output.

## Escalation

- Escalate to API gateway owner, affected layer owner, SRE, Security for auth or
  tenant risk, and Legal/Privacy for data exposure concerns.

## Related Runbooks

- [Incident response workflow](../README.md)
- [Database degradation](database_degradation.md)
- [Queue backlog](queue_backlog.md)
- [Auth failure](auth_failure.md)
- [Production incident command](../../../docs/runbooks/01-incident-command.md)

## Post-Incident Follow-Up

- Update alerts, dashboards, contract tests, readiness probes, or deployment
  gates that failed to prevent or detect the outage.
- Assign owners and due dates in the postmortem.
