---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# HubSpot Integration

## Overview

The HubSpot connector syncs companies, deals, and contacts into ValuePact. It is ideal for marketing and sales operations teams that track pipeline value and customer lifecycle metrics.

## Who this is for

- <span class="vp-badge vp-badge--role">Admin</span>
- <span class="vp-badge vp-badge--role">Developer</span>
- <span class="vp-badge vp-badge--role">End User</span>

## Prerequisites

- HubSpot Professional or Enterprise subscription (API access required).
- Private app with `crm.objects.contacts.read`, `crm.objects.deals.read`, and `crm.objects.companies.read` scopes.
- ValuePact Organization Admin role.

## Step-by-step instructions

### 1. Create a private app in HubSpot

1. In HubSpot, go to **Settings > Integrations > Private Apps**.
2. Click **Create a private app**.
3. Name it `ValuePact Integration`.
4. Enable the CRM scopes listed above.
5. Generate and copy the access token.

### 2. Connect ValuePact to HubSpot

1. In ValuePact, open **Administration > Integrations > HubSpot**.
2. Paste the access token.
3. Click **Test Connection**. A green checkmark confirms success.
4. Save the connection.

### 3. Configure sync scope

1. Select entities: **Companies**, **Deals**, **Contacts**.
2. Choose sync direction. Most customers use inbound for deals and bidirectional for contacts.
3. Set the sync interval: 15 minutes or hourly.

### 4. Map fields

1. Open **Field Mapping**.
2. Map required fields:
   - `dealname` → `Initiative Name`
   - `amount` → `Benefit Value`
   - `dealstage` → `Status`
   - `company.name` → `Stakeholder Organization`
3. Map custom HubSpot properties to ValuePact custom fields.
4. Save and run a test sync.

### 5. Set filters and deduplication

1. In **Sync Rules**, exclude deals with `pipeline = 'Internal'` if they are not value-tracked.
2. Set deduplication key to `dealId` for deals and `email` for contacts.
3. Enable **Incremental Sync** to process only changed records.

## Permissions required

| Role | Permission | Scope |
|------|-----------|-------|
| Admin | Configure integrations | Organization |
| Admin | Manage field mapping | Organization |
| User | View synced records | Assigned initiatives |

## Limits and guardrails

- <span class="vp-badge vp-badge--limit">Limit</span> HubSpot API: 100 calls per 10 seconds per app.
- <span class="vp-badge vp-badge--limit">Limit</span> Records per sync batch: 100.
- <span class="vp-badge vp-badge--limit">Limit</span> Daily call budget: configurable alert at 80%.

## Troubleshooting

??? question "Issue: Sync fails with 'RATE_LIMITS_REACHED'"
    **Cause:** Other integrations or workflows are consuming the HubSpot API budget.
    **Resolution:**
    1. Review HubSpot API usage in **Settings > API Usage**.
    2. Reduce ValuePact sync frequency to hourly.
    3. Stagger other integrations to off-peak hours.

??? question "Issue: Custom property values are blank in ValuePact"
    **Cause:** The private app lacks scope for the custom property's object type.
    **Resolution:**
    1. In HubSpot, edit the private app.
    2. Add `crm.schemas.deals.read` or the relevant schema scope.
    3. Re-run the sync.

??? question "Issue: Duplicate contacts after sync"
    **Cause:** The deduplication key was not set, or contacts exist with multiple email addresses.
    **Resolution:**
    1. Set the deduplication key to `hs_object_id` instead of `email`.
    2. Merge duplicates in HubSpot before re-syncing.

## Related pages

- [Sync Failures Troubleshooting](../troubleshooting/sync-failures.md)
- [Missing Data Troubleshooting](../troubleshooting/missing-data.md)
- [Integration FAQ](../faq/integration-faq.md)

## Escalation path

| Severity | Condition | Contact |
|----------|-----------|---------|
| P3 | Mapping or filter tuning | #valuepact-support Slack |
| P2 | Sync halted due to rate limits | support@valuepact.ai |
| P1 | Complete HubSpot disconnect | On-call page with subject "P1 HubSpot Integration" |
