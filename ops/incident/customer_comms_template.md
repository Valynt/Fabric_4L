# Customer Communication Templates

Keep all communications factual, time-stamped, and free of speculation. Do not
share tenant names, personal data, secrets, exploit details, stack traces, raw
provider responses, or legal conclusions without Security and Legal approval.

## Internal Incident Declaration

```text
INCIDENT DECLARED - <SEV-1|SEV-2|SEV-3|SEV-4>

Incident: <short title>
Incident ID: <id>
Incident Commander: <name>
Technical Lead: <name>
Communications Lead: <name>
Scribe: <name>
Start time (UTC): <YYYY-MM-DD HH:MM>
Detected by: <alert/customer report/operator observation/deploy gate>
Affected services/layers: <API/Web/L1/L2/L3/L4/L5/L6/Billing/Auth/Infrastructure>
Customer impact: <known impact or "under investigation">
Data/security impact: <none known | suspected | confirmed | under investigation>
Current status: <investigating | mitigating | monitoring | resolved>
Primary runbook: <link>
War room: <link>
Next update by (UTC): <YYYY-MM-DD HH:MM>

Immediate actions underway:
- <action>
- <action>
```

## Customer Status Update - Investigating

```text
Title: <service degradation or outage title>
Status: Investigating
Time (UTC): <YYYY-MM-DD HH:MM>

We are investigating an issue affecting <product area>. Customers may experience
<symptoms>. Engineering is actively investigating. The next update will be
provided by <YYYY-MM-DD HH:MM UTC>.
```

## Customer Status Update - Identified

```text
Title: <service degradation or outage title>
Status: Identified
Time (UTC): <YYYY-MM-DD HH:MM>

We have identified the cause of the issue affecting <product area> and are
working on mitigation. Current customer impact is <impact summary>. The next
update will be provided by <YYYY-MM-DD HH:MM UTC>.
```

## Customer Status Update - Monitoring

```text
Title: <service degradation or outage title>
Status: Monitoring
Time (UTC): <YYYY-MM-DD HH:MM>

A mitigation has been applied and we are monitoring recovery for <product area>.
Customers should see <expected recovery behavior>. The next update will be
provided by <YYYY-MM-DD HH:MM UTC> or when the incident is resolved.
```

## Customer Status Update - Resolved

```text
Title: <service degradation or outage title>
Status: Resolved
Time (UTC): <YYYY-MM-DD HH:MM>

This incident has been resolved. Impact began at <YYYY-MM-DD HH:MM UTC> and
ended at <YYYY-MM-DD HH:MM UTC>. Affected customers experienced <impact
summary>. We apologize for the disruption and will follow up with any required
incident report or customer-specific communication.
```

## Security Or Privacy Holding Statement

Use only after Security and Legal approve customer notification.

```text
We are investigating a security or privacy incident involving <high-level system
or data category>. We have activated our incident response process, contained
the currently known risk, and are assessing scope. We will notify affected
customers directly if we determine their data or environment was impacted. The
next update will be provided by <YYYY-MM-DD HH:MM UTC>.
```

## Communication Guardrails

- Use UTC timestamps.
- State what is known, what is being done, and when the next update will arrive.
- Avoid root-cause speculation before evidence is reviewed.
- Route breach, regulatory, contractual, and tenant-specific language through
  Security and Legal.
- Preserve all customer-facing updates in the incident record.
