# Blameless Postmortem Template

Use this template for every SEV-1, SEV-2, security/privacy incident,
tenant-isolation incident, data-loss incident, and repeated SEV-3. The purpose
is system improvement, not individual blame.

## Incident Summary

- **Incident ID:**
- **Title:**
- **Severity:**
- **Date opened (UTC):**
- **Date mitigated (UTC):**
- **Date resolved (UTC):**
- **Incident Commander:**
- **Technical Lead:**
- **Communications Lead:**
- **Impacted services/layers:**
- **Customer impact summary:**
- **Data/security/privacy impact:**
- **Current status:** Open / Mitigated / Resolved / Follow-up in progress

## Impact

- **Affected tenants/customers:**
- **Affected user journeys:**
- **Duration:**
- **Error budget impact:**
- **Revenue/billing impact:**
- **Regulatory or contractual impact:**

## Timeline

| Timestamp (UTC) | Event | Source | Owner |
|---|---|---|---|
| YYYY-MM-DD HH:MM | Detection | Alert/customer/support/operator | On-call |
| YYYY-MM-DD HH:MM | Incident declared | Incident channel | IC |
| YYYY-MM-DD HH:MM | Mitigation started | Runbook/command | Technical lead |
| YYYY-MM-DD HH:MM | Customer update posted | Status page/support | Communications lead |
| YYYY-MM-DD HH:MM | Service restored | Metrics/smoke test | Technical lead |

## Root Cause

- **Primary root cause:**
- **Contributing factors:**
- **Why existing controls did not prevent or detect this earlier:**
- **What evidence supports this conclusion:**

## Remediation

- **Immediate mitigation applied:**
- **Permanent fix required:**
- **Rollback or fallback used:**
- **Validation completed:**

## What Went Well

- 

## What Went Poorly

- 

## Action Items

Every postmortem must include at least one preventive or detective action item.

| Action ID | Type | Description | Owner | Priority | Due Date | Status | Evidence Link |
|---|---|---|---|---|---|---|---|
| AI-001 | Preventive/Detective/Corrective | | | P0/P1/P2 | YYYY-MM-DD | Open | |

## Follow-Up Verification

- **Runbook updated:** Yes / No / Not applicable
- **Alert updated:** Yes / No / Not applicable
- **Test or gate added:** Yes / No / Not applicable
- **Dashboard updated:** Yes / No / Not applicable
- **Customer follow-up completed:** Yes / No / Not applicable
- **Security/Legal review completed:** Yes / No / Not applicable

## Closure Criteria

- All P0 action items are complete or have documented executive risk acceptance.
- Owners and due dates exist for every open P1/P2 action item.
- Evidence links are attached for completed remediation.
- Incident commander approves closure.
