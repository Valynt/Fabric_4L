---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Governance

## Overview

Strong governance ensures that value claims are auditable, approvals are defensible, and documentation standards are maintained across teams and tenants.

## Who this is for

- <span class="vp-badge vp-badge--role">Admin</span>
- <span class="vp-badge vp-badge--role">Executive</span>
- <span class="vp-badge vp-badge--role">End User</span>

## Prerequisites

- Admin access to **Administration > Configuration > Workflows**.
- Defined RACI (Responsible, Accountable, Consulted, Informed) matrix for value management.

## Step-by-step instructions

### 1. Define approval gates

1. Map each initiative type to a workflow.
2. Set minimum approver counts and role requirements.
3. Require approval for: creation over a value threshold, baseline changes, and benefit actuals over a variance limit.

### 2. Enforce documentation standards

1. Require a business case description of at least 100 characters.
2. Mandate stakeholder identification before submission.
3. Use custom fields to tag initiatives by risk level, strategic pillar, and regulatory scope.

### 3. Maintain audit readiness

1. Lock baselines at approval time.
2. Prevent deletion of approved initiatives; allow archival instead.
3. Export audit logs quarterly and store them in your document management system.

### 4. Conduct access reviews

1. Quarterly, run the **User Access Report** from **Administration > User Management**.
2. Verify that former employees and contractors are deactivated.
3. Confirm role assignments match current job functions.

### 5. Document exceptions

1. Create a custom field named `Governance Exception`.
2. When a workflow rule is bypassed, require the bypasser to select a reason.
3. Review all exceptions monthly in the governance committee meeting.

## Permissions required

| Role | Permission | Scope |
|------|-----------|-------|
| Admin | Configure workflows | Organization |
| Admin | Manage audit logs | Organization |
| Executive | Approve high-value initiatives | Organization |

## Limits and guardrails

- <span class="vp-badge vp-badge--limit">Limit</span> Workflow stages: 10 per workflow.
- <span class="vp-badge vp-badge--limit">Limit</span> Approvers per stage: 5.
- <span class="vp-badge vp-badge--limit">Limit</span> Audit log retention: 7 years.

## Troubleshooting

??? question "Issue: Workflow bottlenecks at one approver"
    **Cause:** The approver is on leave, or the notification was filtered to spam.
    **Resolution:**
    1. Set delegate approvers in user profiles.
    2. Enable Slack or Teams notifications as a secondary channel.
    3. Allow escalation after 48 hours of inactivity.

??? question "Issue: Audit log export is incomplete"
    **Cause:** The date range spans the retention boundary, or the export hit the row limit.
    **Resolution:**
    1. Break the export into 90-day chunks.
    2. Use the API for full historical extraction.

## Related pages

- [Admin FAQ](../faq/admin-faq.md)
- [Security FAQ](../faq/security-faq.md)
- [Portfolio Reviews](portfolio-reviews.md)

## Escalation path

| Severity | Condition | Contact |
|----------|-----------|---------|
| General | Workflow design questions | Customer Success Manager |
| Urgent | Governance breach or audit finding | support@valuepact.ai |
