# Customer Incident Communication Runbook

## Purpose

Operate this procedure safely while preserving tenant isolation, evidence, reversibility, and the existing service contract.

## Trigger

An incident commander declares customer-visible impact or requests coordinated stakeholder communication.

## Severity

Use the incident severity declared by incident command; security or tenant exposure is always handled as SEV1 until scoped.

## Preconditions

- Confirm the incident/request owner, affected environment, authorized tenant scope, and required approvals.
- Verify access to the relevant dashboards, audit records, secrets, backups, and deployment metadata.
- Capture the current version and state before making changes; destructive operations require explicit approval.

## Immediate Actions

1. Stop or freeze the smallest unsafe scope and declare the severity.
2. Preserve logs, traces, audit records, identifiers, configuration, and timestamps before mutation or restart.
3. Notify the owning on-call and Security when authorization, privacy, or tenant isolation may be affected.

## Diagnosis Steps

1. Confirm the trigger, timeline, affected tenants/customers, and last known-good state.
2. Correlate alerts, logs, traces, audit events, recent deployments, configuration changes, and dependency health.
3. Test whether impact is tenant-specific, regional, provider-specific, deployment-specific, or global.

## Resolution Steps

1. Apply the least-risk reversible correction described in the procedure details below.
2. Preserve fail-closed controls, tenant scope, contract compatibility, and auditability.
3. Record commands, approvals, state transitions, and the reason for the selected resolution.

## Validation

- Re-run the related gates and targeted service checks.
- Validate the affected customer path and a known-unaffected control tenant where tenant data is involved.
- Confirm alerts clear, audit evidence is complete, and no new errors or cross-tenant results appear.

## Rollback / Fallback

Return to the captured last known-good deployment, configuration, routing, or data artifact if validation fails. Keep the affected capability contained when no safe fallback preserves security and tenant isolation.

## Customer / Stakeholder Communication

Use the declared severity cadence. Report confirmed scope, customer impact, mitigation, residual risk, and next update time; never include secrets, raw customer data, or another tenant's identifiers.

## Evidence to Preserve

Preserve alert and dashboard snapshots, UTC timestamps, affected tenant/customer IDs, deployment SHAs, sanitized logs/traces, audit events, approvals, commands, gate outputs, and validation results in the incident or request record.

## Related Gates

- Production readiness and deployment gates for release status; observability alert gates for impact/recovery evidence; tenant-isolation gate for exposure incidents.

## Related Runbooks

- ../support-escalation.md, ../01-incident-command.md, ../security/respond-to-tenant-data-exposure.md

## Post-Incident Follow-Up

Assign owners and due dates for the root-cause record, corrective tests/alerts/gates, control improvements, customer follow-up, and any required update to this runbook.

## Procedure Details

> **Scope:** Internal and customer-facing communication for incidents affecting Value Fabric customers.  
> **Reused source:** Based on `docs/troubleshooting/runbooks/incident/communication-template.md`.

### Principles

- Be factual, time-stamped, and free of speculation.
- Use UTC timestamps and commit to the next update time.
- Do not disclose tenant names, personal data, secrets, exploit details, stack traces, prompts, raw customer content, or legal conclusions without approval.
- Route regulatory, contractual, or breach-notification language through Legal and Security.
- Keep one incident thread as the decision log.

### Roles

| Role | Responsibility |
|---|---|
| Incident Commander | Owns severity, timeline, decisions, and resolution. |
| Technical Lead | Owns diagnosis, mitigation, and technical validation. |
| Communications Lead | Owns internal updates, customer/status-page updates, and support scripts. |
| Customer Owner | Coordinates tenant-specific outreach and account context. |
| Security/Legal | Approves security, privacy, contractual, or regulatory language. |

### Internal Incident Announcement

Post in `#incident-response` and the affected service channel. For security incidents, also post in `#security-incidents`.

```text
:rotating_light: INCIDENT DECLARED — <SEV1|SEV2|SEV3|SEV4>

Incident: <short title>
Incident Commander: <name>
Technical Lead: <name>
Communications Lead: <name>
Start time (UTC): <YYYY-MM-DD HH:MM>
Detected by: <alert/customer report/manual observation>
Affected services/layers: <L1/L2/L3/L4/L5/L6/API/Web/Infrastructure>
Customer impact: <known impact; say "under investigation" if unknown>
Data/security impact: <none known | suspected | confirmed; include Security owner for suspected/confirmed>
Current status: <investigating | mitigating | monitoring | resolved>
Primary runbook: <link to runbook>
War room: <Slack huddle/Meet/Zoom link>
Status page owner: <name or n/a>
Next update by (UTC): <YYYY-MM-DD HH:MM>

Immediate actions underway:
- <action 1>
- <action 2>

Please route all incident work through this thread. Avoid side-channel decisions.
```

### Customer / Status Page Templates

#### Investigating

```text
Title: <Service degradation or outage title>
Status: Investigating
Time (UTC): <YYYY-MM-DD HH:MM>

We are investigating an issue affecting <affected product area>. Customers may experience <symptoms>. Our engineering team is actively investigating and will provide the next update by <YYYY-MM-DD HH:MM UTC>.
```

#### Identified

```text
Title: <Service degradation or outage title>
Status: Identified
Time (UTC): <YYYY-MM-DD HH:MM>

We have identified the cause of the issue affecting <affected product area> and are working on mitigation. Current customer impact is <impact summary>. The next update will be provided by <YYYY-MM-DD HH:MM UTC>.
```

#### Monitoring

```text
Title: <Service degradation or outage title>
Status: Monitoring
Time (UTC): <YYYY-MM-DD HH:MM>

A mitigation has been applied and we are monitoring recovery for <affected product area>. Customers should see <expected recovery behavior>. We will provide another update by <YYYY-MM-DD HH:MM UTC> or when the incident is resolved.
```

#### Resolved

```text
Title: <Service degradation or outage title>
Status: Resolved
Time (UTC): <YYYY-MM-DD HH:MM>

This incident has been resolved. Impact began at <YYYY-MM-DD HH:MM UTC> and ended at <YYYY-MM-DD HH:MM UTC>. Affected customers experienced <impact summary>. We apologize for the disruption and will follow up with any required incident report or customer-specific communication.
```

### Security-Specific Holding Statement

Use only after Security and Legal approval.

```text
We are investigating a security incident involving <high-level system or data category>. We have activated our incident response process, contained the currently known vector, and are assessing scope. We will notify affected customers directly if we determine their data or environment was impacted. We will provide the next update by <YYYY-MM-DD HH:MM UTC>.
```

### Update Cadence

| Severity | Internal updates | Customer/status updates |
|---|---|---|
| SEV1 | Every 15 minutes or on material change. | Every 30 minutes or as approved. |
| SEV2 | Every 30 minutes or on material change. | Every 60 minutes or as approved. |
| SEV3 | Every 60 minutes during active mitigation. | If customer-visible, every 2 hours or as agreed. |

### Resolution Checklist

- Technical lead confirms mitigation and monitoring period.
- Customer impact window is known or explicitly marked as best available estimate.
- Data/security impact is reviewed by Security.
- Customer-facing wording is approved by Communications and Legal/Security where required.
- Follow-up owner and postmortem requirement are documented.
