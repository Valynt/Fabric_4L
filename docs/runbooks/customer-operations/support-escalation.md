# Support Escalation Runbook

> **Scope:** Customer-reported issues, technical support handoffs, and escalation from Customer Operations to Engineering, Security, Data Governance, or FinOps.

## Purpose

Use this runbook to triage support requests consistently, collect actionable evidence, and route urgent customer-impacting problems without exposing sensitive tenant data in shared channels.

## Intake Checklist

Collect the following before escalation when possible:

- Customer/account name and tenant ID.
- Requester identity and authorization status.
- Environment, URL/page, workflow ID, business case ID, job ID, or API endpoint.
- Timestamp(s) in UTC and user-visible symptom.
- Severity requested by customer and actual business impact.
- Screenshots or exported logs with secrets and personal data redacted.
- Whether the issue affects one user, one tenant, multiple tenants, or all customers.
- Any suspected data/security/privacy impact.

## Severity Routing

| Severity | Examples | Escalation |
|---|---|---|
| P0 / SEV1 | Service unavailable for many customers, data exposure, tenant isolation concern, destructive data issue. | Page Incident Commander, Platform, Security if data/security impact. |
| P1 / SEV2 | Major workflow unavailable for one/more strategic tenants, wrong customer-visible generated output. | Page owning service team and Customer Operations lead. |
| P2 / SEV3 | Degraded feature, workaround available, isolated quality issue. | File engineering ticket and notify service channel. |
| P3 | Question, configuration request, documentation gap. | Support queue or Customer Success follow-up. |

## Escalation Paths

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

## Engineering Escalation Template

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

## Handling Rules

- Do not paste secrets, tokens, raw prompts, raw model outputs, or customer documents into Slack.
- Use tenant IDs and internal object IDs rather than customer personal data where possible.
- If the issue may involve cross-tenant access or data exposure, page Security immediately.
- If customer communication is needed, use the incident communication runbook and approved templates.
- Keep the support ticket as the customer-facing source of record and link the internal incident/ticket.

## Closure Checklist

- Customer symptom is resolved or workaround is confirmed.
- Engineering owner has documented root cause or next step.
- Customer-facing update sent with approved wording.
- Follow-up ticket exists for non-urgent corrective actions.
- Evidence is attached to the support ticket or incident record.
