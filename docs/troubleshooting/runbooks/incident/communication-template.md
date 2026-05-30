# Incident Communication Templates

Use these templates for SEV1-SEV3 incidents. Keep communication factual, time-stamped, and free of speculation. Do not disclose tenant names, personal data, exploit details, or legal conclusions without Security and Legal approval.

## Internal Slack notification template

Post in `#incident-response` and the affected service channel. For SEV1 security incidents, also post in `#security-incidents`.

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

## Customer status page template

Use this for public or customer-facing updates. Replace bracketed text and remove sections that do not apply.

### Investigating

```text
Title: <Service degradation or outage title>
Status: Investigating
Time (UTC): <YYYY-MM-DD HH:MM>

We are investigating an issue affecting <affected product area>. Customers may experience <symptoms>. Our engineering team is actively investigating and will provide the next update by <YYYY-MM-DD HH:MM UTC>.
```

### Identified

```text
Title: <Service degradation or outage title>
Status: Identified
Time (UTC): <YYYY-MM-DD HH:MM>

We have identified the cause of the issue affecting <affected product area> and are working on mitigation. Current customer impact is <impact summary>. The next update will be provided by <YYYY-MM-DD HH:MM UTC>.
```

### Monitoring

```text
Title: <Service degradation or outage title>
Status: Monitoring
Time (UTC): <YYYY-MM-DD HH:MM>

A mitigation has been applied and we are monitoring recovery for <affected product area>. Customers should see <expected recovery behavior>. We will provide another update by <YYYY-MM-DD HH:MM UTC> or when the incident is resolved.
```

### Resolved

```text
Title: <Service degradation or outage title>
Status: Resolved
Time (UTC): <YYYY-MM-DD HH:MM>

This incident has been resolved. Impact began at <YYYY-MM-DD HH:MM UTC> and ended at <YYYY-MM-DD HH:MM UTC>. Affected customers experienced <impact summary>. We apologize for the disruption and will follow up with any required incident report or customer-specific communication.
```

## Security-specific customer holding statement

Use only after Security and Legal approve customer notification.

```text
We are investigating a security incident involving <high-level system or data category>. We have activated our incident response process, contained the currently known vector, and are assessing scope. We will notify affected customers directly if we determine their data or environment was impacted. We will provide the next update by <YYYY-MM-DD HH:MM UTC>.
```

## Post-mortem template

Create the post-mortem within 5 business days for every SEV1/SEV2 and any repeated SEV3.

```markdown
# Post-mortem: <incident title>

- Incident ID:
- Severity:
- Date/time detected (UTC):
- Date/time mitigated (UTC):
- Date/time resolved (UTC):
- Incident Commander:
- Technical Lead:
- Communications Lead:
- Services/layers affected:
- Customer impact:
- Data/security impact:

## Summary

<Brief factual summary of what happened and how it was resolved.>

## Timeline

| Time (UTC) | Event | Source |
|---|---|---|
| <YYYY-MM-DD HH:MM> | <event> | <alert/log/person> |

## Root cause

<Root cause and contributing factors. Avoid blame.>

## Detection

- How was the incident detected?
- Which alerts fired?
- Which expected alerts did not fire?

## Response

- What went well?
- What slowed response?
- Were severity, escalation, and communication cadences followed?

## Customer and data impact

- Affected tenants/customers:
- Duration:
- Data affected:
- Security/legal notifications required:

## Corrective actions

| Action | Owner | Due date | Priority | Tracking link |
|---|---|---|---|---|
| <action> | <owner> | <YYYY-MM-DD> | <P0/P1/P2> | <link> |

## Follow-up validation

- Regression tests added or updated:
- Monitoring/alerting changes:
- Runbook/docs changes:
- Evidence retained:
```

## Communication guardrails

- Communicate only confirmed facts and current mitigations.
- Use UTC timestamps.
- State when the next update will arrive and meet that commitment.
- Do not share secrets, exploit details, tenant identifiers, stack traces, or raw customer content.
- Route regulatory, contractual, or breach-notification language through Legal and Security.
