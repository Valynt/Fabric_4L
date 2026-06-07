---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Salesforce Integration

## Overview

The Salesforce connector bidirectionally syncs accounts, opportunities, and contacts with ValuePact. This enables automatic population of pipeline data, stakeholder lists, and realized value tracking.

## Who this is for

- <span class="vp-badge vp-badge--role">Admin</span>
- <span class="vp-badge vp-badge--role">Developer</span>
- <span class="vp-badge vp-badge--role">End User</span>

## Prerequisites

- Salesforce Enterprise, Unlimited, or Developer Edition.
- Admin access to **Setup > App Manager** in Salesforce.
- ValuePact Organization Admin role.

## Step-by-step instructions

### 1. Install the connected app

1. In ValuePact, go to **Administration > Integrations > Salesforce**.
2. Click **Connect**.
3. You are redirected to Salesforce OAuth. Log in with an admin account.
4. Approve the requested scopes: `api`, `refresh_token`.
5. Return to ValuePact. The status indicator turns green.

### 2. Configure sync scope

1. Open the Salesforce connector settings in ValuePact.
2. Select entities to sync: **Accounts**, **Opportunities**, **Contacts**.
3. Choose sync direction: **Inbound**, **Outbound**, or **Bidirectional**.
4. Set the sync schedule: every 15 minutes, hourly, or daily.

### 3. Map fields

1. Click **Field Mapping**.
2. Drag Salesforce fields to corresponding ValuePact attributes.
3. Required mappings:
   - `Account.Name` → `Stakeholder Organization`
   - `Opportunity.Amount` → `Benefit Value`
   - `Opportunity.StageName` → `Initiative Status`
4. Save the mapping. Run a test sync to validate.

### 4. Set sync rules

1. Open **Sync Rules**.
2. Add a filter: `Opportunity.StageName IN ('Closed Won', 'Closed Lost')`.
3. Exclude records owned by integration users to prevent noise.
4. Enable **Conflict Resolution**: Salesforce wins, ValuePact wins, or manual review.

### 5. Verify the first sync

1. Trigger a manual sync.
2. Open **Data Explorer** and compare record counts.
3. Review the sync log for validation errors.
4. Fix mapping issues and re-sync.

## Permissions required

| Role | Permission | Scope |
|------|-----------|-------|
| Admin | Configure integrations | Organization |
| Admin | Manage field mapping | Organization |
| User | View synced records | Assigned initiatives |

## Limits and guardrails

- <span class="vp-badge vp-badge--limit">Limit</span> Salesforce API calls: 100,000 per 24 hours per connected app.
- <span class="vp-badge vp-badge--limit">Limit</span> Records per sync batch: 2,000.
- <span class="vp-badge vp-badge--limit">Limit</span> Field mappings per entity: 50.
- <span class="vp-badge vp-badge--limit">Limit</span> Sync frequency: minimum 15 minutes.

## Troubleshooting

??? question "Issue: OAuth token expired and sync stopped"
    **Cause:** The Salesforce admin password changed, or the connected app was blocked.
    **Resolution:**
    1. In ValuePact, click **Reconnect**.
    2. Re-authenticate with Salesforce.
    3. Verify the connected app is not in "Blocked" status in Salesforce Setup.

??? question "Issue: Opportunity amounts appear in wrong currency"
    **Cause:** The mapping pulled `Amount` without referencing `CurrencyIsoCode`.
    **Resolution:**
    1. Add `CurrencyIsoCode` to the field map.
    2. Enable multi-currency in **Administration > Configuration > Currency**.
    3. Re-run the sync.

??? question "Issue: Sync shows 'INSUFFICIENT_ACCESS_OR_READONLY'"
    **Cause:** The connected app user lacks read permission on a mapped object or field.
    **Resolution:**
    1. In Salesforce, open the profile for the integration user.
    2. Grant read access to the object and field-level security for mapped fields.
    3. Re-run the sync.

## Related pages

- [Sync Failures Troubleshooting](../troubleshooting/sync-failures.md)
- [Missing Data Troubleshooting](../troubleshooting/missing-data.md)
- [Integration FAQ](../faq/integration-faq.md)

## Escalation path

| Severity | Condition | Contact |
|----------|-----------|---------|
| P3 | Field mapping or filter questions | #valuepact-support Slack |
| P2 | Sync failure affecting reporting | support@valuepact.ai |
| P1 | Complete Salesforce disconnect with data loss risk | On-call page with subject "P1 Salesforce Integration" |
