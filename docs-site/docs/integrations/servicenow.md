---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# ServiceNow Integration

## Overview

The ServiceNow connector syncs incidents and configuration management database (CMDB) items with ValuePact. It supports IT service management (ITSM) teams that measure value through incident reduction and asset optimization.

## Who this is for

- <span class="vp-badge vp-badge--role">Admin</span>
- <span class="vp-badge vp-badge--role">Developer</span>
- <span class="vp-badge vp-badge--role">End User</span>

## Prerequisites

- ServiceNow instance (Quebec or later).
- `itil` and `cmdb_read` roles for the integration user.
- ValuePact Organization Admin role.

## Step-by-step instructions

### 1. Create the integration user

1. In ServiceNow, go to **User Administration > Users**.
2. Create a user named `valuepact.integration`.
3. Grant roles: `itil`, `cmdb_read`, and `rest_api_explorer`.
4. Generate a password or OAuth client credentials.

### 2. Connect ValuePact to ServiceNow

1. In ValuePact, open **Administration > Integrations > ServiceNow**.
2. Enter your instance URL (e.g., `https://yourinstance.service-now.com`).
3. Provide the integration user credentials.
4. Click **Test Connection**. Save on success.

### 3. Configure incident linking

1. Open **Incident Linking**.
2. Select the ServiceNow incident table filters:
   - `state != 6` (exclude canceled)
   - `priority IN (1,2)` (focus on critical and high)
3. Map fields:
   - `number` → External Reference ID
   - `short_description` → Risk Title
   - `resolved_at` → Resolution Date
4. Enable creation of risk records in ValuePact for new incidents.

### 4. Sync CMDB data

1. Open **CMDB Sync**.
2. Choose CI classes: `cmdb_ci_server`, `cmdb_ci_service`, or custom classes.
3. Map attributes to ValuePact custom fields:
   - `name` → Asset Name
   - `operational_status` → Status
   - `cost` → Asset Value
4. Set sync frequency: hourly or daily.

### 5. Validate the sync

1. Create a test incident in ServiceNow.
2. Confirm it appears in ValuePact **Risks** within the sync interval.
3. Update the incident state to **Resolved**.
4. Verify the resolution date and status update in ValuePact.

## Permissions required

| Role | Permission | Scope |
|------|-----------|-------|
| Admin | Configure integrations | Organization |
| Admin | Manage CMDB mapping | Organization |
| User | View linked incidents | Assigned initiatives |

## Limits and guardrails

- <span class="vp-badge vp-badge--limit">Limit</span> ServiceNow REST API rate: configurable via rate limiting policies.
- <span class="vp-badge vp-badge--limit">Limit</span> CMDB CIs per sync: 5,000.
- <span class="vp-badge vp-badge--limit">Limit</span> Incident sync interval: minimum 15 minutes.

## Troubleshooting

??? question "Issue: Incidents do not appear in ValuePact"
    **Cause:** The table filter is too restrictive, or the integration user lacks `itil` role.
    **Resolution:**
    1. Broaden the filter temporarily and re-sync.
    2. Verify the integration user roles in ServiceNow.
    3. Check **Audit Logs** for 403 errors.

??? question "Issue: CMDB sync is very slow"
    **Cause:** Large CI tables without indexed queries cause pagination timeouts.
    **Resolution:**
    1. Add `sys_updated_on` index to the target CI table in ServiceNow.
    2. Reduce the sync batch size to 250.
    3. Schedule CMDB sync during off-peak hours.

??? question "Issue: Resolved incidents remain open in ValuePact"
    **Cause:** The state mapping does not include the ServiceNow resolved state.
    **Resolution:**
    1. Open **Incident Linking > State Mapping**.
    2. Map `6` (Resolved) to **Closed** in ValuePact.
    3. Re-sync historical incidents.

## Related pages

- [Sync Failures Troubleshooting](../troubleshooting/sync-failures.md)
- [Missing Data Troubleshooting](../troubleshooting/missing-data.md)
- [Integration FAQ](../faq/integration-faq.md)

## Escalation path

| Severity | Condition | Contact |
|----------|-----------|---------|
| P3 | CMDB or incident mapping questions | #valuepact-support Slack |
| P2 | Sync failure affecting incident tracking | support@valuepact.ai |
| P1 | CMDB data exposure or misconfiguration | security@valuepact.ai |
