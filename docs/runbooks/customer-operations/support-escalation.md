# Support Escalation Runbook

## Purpose

Use this runbook to triage support requests consistently, collect actionable evidence, and route urgent customer-impacting problems without exposing sensitive tenant data in shared channels.

## Trigger

Support identifies security, availability, integrity, contractual, or repeated product impact that exceeds frontline handling.

## Severity

SEV1 for security/cross-tenant or broad outage; SEV2 for major customer impact; SEV3 for bounded degradation; SEV4 for routine follow-up.

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

- Observability alert gates; `tenant-isolation-gate` for access concerns; deployment/production-readiness gates for suspected regressions; agent evaluation gates for agent-output cases.

## Related Runbooks

- ./customer-incident-communication.md, ../01-incident-command.md, ../observability/alert-triage.md

## Post-Incident Follow-Up

Assign owners and due dates for the root-cause record, corrective tests/alerts/gates, control improvements, customer follow-up, and any required update to this runbook.

## Procedure Details

> **Scope:** Customer-reported issues, technical support handoffs, and escalation from Customer Operations to Engineering, Security, Data Governance, or FinOps.

### Purpose

Use this runbook to triage support requests consistently, collect actionable evidence, and route urgent customer-impacting problems without exposing sensitive tenant data in shared channels.

### Intake Checklist

Collect the following before escalation when possible:

- Customer/account name and tenant ID.
- Requester identity and authorization status.
- Environment, URL/page, workflow ID, business case ID, job ID, or API endpoint.
- Timestamp(s) in UTC and user-visible symptom.
- Severity requested by customer and actual business impact.
- Screenshots or exported logs with secrets and personal data redacted.
- Whether the issue affects one user, one tenant, multiple tenants, or all customers.
- Any suspected data/security/privacy impact.

### Severity Routing

| Severity | Examples | Escalation |
|---|---|---|
| P0 / SEV1 | Service unavailable for many customers, data exposure, tenant isolation concern, destructive data issue. | Page Incident Commander, Platform, Security if data/security impact. |
| P1 / SEV2 | Major workflow unavailable for one/more strategic tenants, wrong customer-visible generated output. | Page owning service team and Customer Operations lead. |
| P2 / SEV3 | Degraded feature, workaround available, isolated quality issue. | File engineering ticket and notify service channel. |
| P3 | Question, configuration request, documentation gap. | Support queue or Customer Success follow-up. |

### Escalation Paths

| Issue type | Primary owner | Runbook |
|---|---|---|
| LLM/provider failure | Platform / AI platform | `docs/runbooks/agents/llm-provider-outage.md` |
| Misbehaving agent | Layer 4 owner | `docs/runbooks/agents/disable-or-contain-misbehaving-agent.md` |
| Incorrect business case | Layer 4 + Layer 5 | `docs/runbooks/agents/investigate-hallucinated-business-case.md` |
| Prompt injection | Security + Layer 4 | `docs/runbooks/agents/respond-to-prompt-injection.md` |
| Graph/retrieval issue | Layer 3 owner | `docs/runbooks/reliability/rebuild-neo4j-projection.md` or `rebuild-vector-index.md` |
| Data export/deletion | Data Governance | `docs/runbooks/data-governance/customer-data-export-or-deletion.md` |
| Data corruption | Data Governance + service owner | `docs/runbooks/data-governance/investigate-data-corruption.md` |
| Customer-facing incident | Incident Commander + Comms | `docs/runbooks/customer-operations/customer-incident-communication.md` |

### Engineering Escalation Template

```text
Escalation: <short title>
Customer / tenant ID: <customer, tenant_id>
Severity: <P0/P1/P2/P3>
Impact: <what customer cannot do; number of users/tenants>
Started (UTC): <YYYY-MM-DD HH:MM or unknown>
Last observed (UTC): <YYYY-MM-DD HH:MM>
Affected area: <L1/L2/L3/L4/L5/L6/API/Web>
Identifiers: <workflow_id, business_case_id, job_id, request_id, trace_id>
Data/security concern: <none known | suspected | confirmed>
Repro steps: <steps or n/a>
Evidence link: <redacted logs/screenshots/support ticket>
Customer deadline / SLA: <time>
Requested action: <diagnose, mitigate, customer wording, join call>
Support owner: <name>
```

### Handling Rules

- Do not paste secrets, tokens, raw prompts, raw model outputs, or customer documents into Slack.
- Use tenant IDs and internal object IDs rather than customer personal data where possible.
- If the issue may involve cross-tenant access or data exposure, page Security immediately.
- If customer communication is needed, use the incident communication runbook and approved templates.
- Keep the support ticket as the customer-facing source of record and link the internal incident/ticket.

### Closure Checklist

- Customer symptom is resolved or workaround is confirmed.
- Engineering owner has documented root cause or next step.
- Customer-facing update sent with approved wording.
- Follow-up ticket exists for non-urgent corrective actions.
- Evidence is attached to the support ticket or incident record.
