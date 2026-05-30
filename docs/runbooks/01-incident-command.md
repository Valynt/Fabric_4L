# Incident Command Runbook

This is the canonical production procedure for coordinating an incident across Value Fabric services. Alert-specific runbooks remain in their existing locations and should be used as tactical response guides after the incident commander classifies the event.

## Scope

Use this runbook for any production incident that requires cross-functional coordination, customer communication, security review, data-governance review, or escalation beyond a single on-call responder.

## Owners

- **Primary owner:** Incident Commander / SRE on-call
- **Secondary owners:** Security on-call, Service owner for the affected layer, Customer Operations lead
- **Escalation references:** [`docs/operations/severity-escalation-policy.md`](../operations/severity-escalation-policy.md), [`docs/troubleshooting/runbooks/incident/severity-classification.md`](../troubleshooting/runbooks/incident/severity-classification.md)

## Severity default

Start at **SEV2** unless an alert-specific runbook, customer impact, tenant-isolation risk, data loss, or security indicator requires SEV1. Downgrade only after the incident commander records evidence in the incident timeline.

## Lifecycle phase

1. **Detect** — acknowledge the alert, incident report, or customer signal.
2. **Triage** — assign severity, affected service/layer, tenant scope, and immediate risk.
3. **Contain** — stop customer impact, tenant data exposure, unsafe deploys, or active abuse.
4. **Remediate** — apply the smallest safe fix or rollback.
5. **Recover** — validate SLOs, contracts, tenant isolation, and customer-facing behavior.
6. **Review** — publish the postmortem, corrective actions, and evidence links.

## Procedure

1. Open an incident channel and assign roles: incident commander, communications lead, technical lead, and scribe.
2. Classify severity using the severity matrix and record the initial severity, timestamp, impacted tenants, and affected layer(s).
3. Select the tactical runbook from [`00-runbook-index.md`](00-runbook-index.md), preferring canonical production procedures and then alert-specific runbooks.
4. Freeze non-essential production changes if the incident affects deploy safety, tenant isolation, data integrity, authentication, or customer-facing availability.
5. Record every mitigation, rollback, feature flag change, credential rotation, and customer communication in the timeline.
6. Before closure, validate the related gate listed in the index or document why the gate cannot be run during the incident.
7. Create a postmortem for SEV1/SEV2 incidents and any security, data-governance, or tenant-isolation incident.

## Closure checklist

- [ ] Customer impact and tenant scope are documented.
- [ ] Alert state, dashboards, and logs confirm recovery.
- [ ] Related deployment, contract, security, or DR gate passed or has an explicit exception.
- [ ] Customer communications are complete or have an owner.
- [ ] Postmortem owner and due date are assigned.
- [ ] Follow-up issues include owners, severity, and target dates.
