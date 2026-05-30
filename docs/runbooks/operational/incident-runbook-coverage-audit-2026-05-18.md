# Incident Runbook Coverage Audit — 2026-05-18

## Purpose

Audit whether top incident classes have current, actionable, and gate-linked runbook coverage.

## Trigger

Scheduled runbook coverage review, launch readiness review, incident postmortem action, new service/gate introduction, or audit request.

## Severity

SEV-2 if a launch-critical incident class lacks coverage; SEV-3 for stale owner, routing, or evidence metadata.

## Preconditions

Current runbook inventory, alert routing template, escalation docs, CI gate list, and launch evidence checklist are available.

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

Runbook coverage and readiness gates: launch evidence validators, observability alert gates, deployment gates, tenant-isolation gates, backup/restore readiness gates, and agent evaluation gates for agent/prompt incident coverage.

## Related Runbooks

- [Alerting / Alertmanager Source-of-Truth Matrix](alerting-source-of-truth.md)
- [Launch-Ops Sign-off Checklist](launch-ops-signoff-checklist.md)

## Post-Incident Follow-Up

- Attach validation evidence and gate results to the incident record.
- File corrective actions for missing alerts, missing tests, stale documentation, or slow recovery steps.
- Update this runbook and related gates if the incident exposed drift or an undocumented dependency.

---

## Procedure Details

### Scope Validated

- `docs/runbooks/operational/`
- `docs/troubleshooting/runbooks/`
- `monitoring/alerting/rules-production.yml`
- `monitoring/alertmanager/alertmanager-production.yml`
- `monitoring/grafana/dashboards/value-fabric-operational.json`
- `monitoring/grafana/dashboards/value-fabric-overview.json`

### Top Incident Coverage Matrix

| Incident Class | Runbook Present | Alert Rule Coverage | Alert Includes Runbook Link | Dashboard Link Present | Notes |
|---|---|---|---|---|---|
| Auth failures/denials | ✅ `enterprise-oidc-sso-incident.md` | ✅ `AuthDeniedSpike` | ✅ Added | ✅ Added | Security-owned path validated |
| Postgres outage/pool exhaustion | ✅ `postgres-unreachable.md` | ✅ `DatabasePoolExhausted` | ✅ Added | ✅ Added | Pool exhaustion mapped to DB reachability runbook |
| Redis outage/backlog | ✅ `redis-unreachable.md` | ⚠️ indirect via queue overload/backlog | ✅ Added on queue backlog alerts | ✅ Added | Add dedicated Redis availability alert in follow-up |
| Neo4j outage | ✅ `neo4j-unreachable.md` | ⚠️ no dedicated Neo4j alert in production rules file | N/A | ✅ Added | Add dedicated Neo4j availability alert in follow-up |
| Workflow stalls | ✅ `agent-workflow-stall.md`, `workflow-stalled.md` | ✅ `CeleryQueueBacklog`, `CeleryWorkerOverload` | ✅ Added | ✅ Added | Layer 4 drill confirms workflow triage path |
| LLM provider outages | ✅ `llm-provider-outage.md` | ✅ `HighLLMCost`, `CriticalLLMCost` proxy signal | ✅ Added | ✅ Added | Add provider-health metric alert in follow-up |

### Alert Routing Template Validation

Validated that Slack templates now expose both:
- `runbook_url`
- `escalation_url`

Validated in:
- receiver text for critical/warning/team channels in production Alertmanager config
- shared Slack template file used by Alertmanager templating

### Escalation Documentation Reference

Canonical escalation doc linked in alert annotations:
- `https://wiki.internal/operations/severity-escalation-policy`

Launch readiness governance and owner/SLA matrix published in:
- `docs/runbooks/operational/launch-ops-signoff-checklist.md`

### Follow-up Items

1. Add explicit `Neo4jUnreachable` production alert rule with runbook URL.
2. Add explicit `RedisUnreachable` production alert rule with runbook URL.
3. Add provider API health-check metric alert (not only cost proxy alerts).
