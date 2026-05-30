# Launch-Ops Sign-off Checklist

## Purpose

Coordinate final launch operations sign-off across engineering, security, SRE, compliance, and product stakeholders.

## Trigger

Launch readiness review, production release candidate, go/no-go meeting, or launch-blocker reassessment.

## Severity

SEV-1 if launch proceeds with unresolved production blocker; SEV-2 for missing required sign-off or gate evidence; SEV-3 for documentation gaps.

## Preconditions

Launch blocker register, environment evidence matrix, final testing checklist, CI evidence, rollback plan, and accountable owners are current.

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

Launch and deployment readiness gates: `make verify`, frontend verification, backend integrated release smoke, contract checks, tenant-isolation/security tests, backup/restore readiness, observability alert gates, and agent evaluation gates when prompts/agents changed.

## Related Runbooks

- [Deployment Rollout, Canary/Blue-Green Criteria, and Rollback](../deployment-rollout-and-rollback.md)
- [Alerting / Alertmanager Source-of-Truth Matrix](alerting-source-of-truth.md)
- [Quarterly Control Attestation Runbook](../compliance/quarterly-control-attestation.md)

## Post-Incident Follow-Up

- Attach validation evidence and gate results to the incident record.
- File corrective actions for missing alerts, missing tests, stale documentation, or slow recovery steps.
- Update this runbook and related gates if the incident exposed drift or an undocumented dependency.

---

## Procedure Details

Use this checklist before production launch approval. All owners are explicit and SLAs are measurable.

### Scope

- Incident categories: auth, data stores (Postgres/Redis/Neo4j), workflow stalls, and provider outages.
- Alerting stack: Prometheus alert rules, Alertmanager routing, Slack/PagerDuty templates, and dashboard/runbook linkage.

### Sign-off Owners and SLAs

| Area | Primary Owner | Backup Owner | Response SLA | Escalation SLA | Evidence Required |
|---|---|---|---|---|---|
| Authentication incidents and access-deny spikes | Alex Kim (Security On-call) | Priya Raman (Platform Security) | Acknowledge in 5 minutes | Escalate to Incident Commander in 10 minutes | Last 30-day alert sample + runbook validation |
| Postgres availability and pool exhaustion | Maya Patel (DBRE) | Jordan Lee (Platform SRE) | Acknowledge in 5 minutes | Escalate to DBRE manager in 15 minutes | Alert firing simulation + failover checklist |
| Redis availability and queue health | Jordan Lee (Platform SRE) | Ben Ortiz (Data Platform) | Acknowledge in 5 minutes | Escalate to Incident Commander in 15 minutes | Redis runbook drill log + dashboard screenshots |
| Neo4j availability and query degradation | Ben Ortiz (Data Platform) | Maya Patel (DBRE) | Acknowledge in 10 minutes | Escalate to Graph lead in 20 minutes | Neo4j alert test + query latency panel review |
| Layer 4 workflow stall detection | Nina Flores (Agent Platform) | Jordan Lee (Platform SRE) | Acknowledge in 10 minutes | Escalate to Platform Eng Manager in 20 minutes | Workflow stall drill artifact + remediation steps |
| LLM provider outage and fallback execution | Elena Cruz (AI Platform) | Nina Flores (Agent Platform) | Acknowledge in 10 minutes | Escalate to VP Engineering in 30 minutes | Provider failover test + incident comms template |
| Alert routing and notification templates | Jordan Lee (Platform SRE) | Alex Kim (Security On-call) | Config change reviewed in 1 business day | Emergency route patch in 15 minutes | `amtool check-config` + route walk-through |
| Runbook linkage in alerts/dashboards | Priya Raman (Platform Security) | Elena Cruz (AI Platform) | Missing-link fix in 1 business day | Hotfix in 30 minutes during active incident | Link-audit report |

### Checklist

- [ ] Auth incident alerts include canonical runbook links and ownership labels.
- [ ] Postgres/Redis/Neo4j alerts include runbook links and severity-appropriate routing.
- [ ] Workflow stall and provider outage alerts route to owning team channels and critical escalation paths.
- [ ] Alertmanager templates render `runbook_url` for Slack/PagerDuty messages.
- [ ] Dashboards for on-call include direct runbook links in panel descriptions or dashboard links.
- [ ] One game-day drill completed in the current quarter and evidence attached.
- [ ] Escalation policy reviewed against current on-call roster.
- [ ] Incident Commander handoff procedure tested and documented.

### Approval

| Role | Name | Date | Decision |
|---|---|---|---|
| Incident Commander |  |  | Approve / Block |
| Platform SRE Lead |  |  | Approve / Block |
| Security Lead |  |  | Approve / Block |
| AI Platform Lead |  |  | Approve / Block |
