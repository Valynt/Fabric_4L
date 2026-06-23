---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Integrations

ValuePact connects with your existing tools to streamline data flow, automate notifications, and embed value insights where your teams already work.

## Who this is for

<span class="vp-badge vp-badge--role">Admin</span>
<span class="vp-badge vp-badge--role">Developer</span>

## Available integrations

### CRM

| Integration | Direction | Use Case |
|-------------|-----------|----------|
| [Salesforce](salesforce.md) | Bidirectional | Sync accounts, opportunities, and value outcomes |
| [HubSpot](hubspot.md) | Bidirectional | Sync contacts, deals, and engagement data |

### Collaboration

| Integration | Direction | Use Case |
|-------------|-----------|----------|
| [Slack](slack.md) | Outbound | Notifications, approvals, alerts |
| [Microsoft Teams](teams.md) | Outbound | Notifications, tab embeds |

### Project Management

| Integration | Direction | Use Case |
|-------------|-----------|----------|
| [Jira](jira.md) | Bidirectional | Link initiatives to epics, sync status |
| [ServiceNow](servicenow.md) | Bidirectional | Link to incidents, CMDB sync |

### Custom

| Integration | Direction | Use Case |
|-------------|-----------|----------|
| [APIs](apis.md) | Bidirectional | Custom integrations via REST API |
| [Webhooks](webhooks.md) | Outbound | Real-time event subscriptions |

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  ValuePact  │────>│  Sync Hub   │────>│  External   │
│             │<────│  (L1/L2)    │<────│   Systems   │
└─────────────┘     └─────────────┘     └─────────────┘
```

The Sync Hub handles authentication, data mapping, conflict resolution, and retry logic. All sync operations are tenant-isolated and auditable.

## Security

- **OAuth 2.0**: All integrations use OAuth 2.0 for authentication.
- **Scoped permissions**: Each integration requests only the permissions it needs.
- **Data encryption**: Data in transit uses TLS 1.3. Data at rest is encrypted.
- **Audit logging**: All sync operations are logged for compliance.

## Permissions

| Action | Required Role |
|--------|--------------|
| View integrations | Admin, User |
| Configure integrations | Admin |
| Disconnect integration | Admin |
| View sync logs | Admin |
| Retry failed sync | Admin |

## Limits

<span class="vp-badge vp-badge--limit">Limit</span> Maximum 10 active integrations per tenant.

<span class="vp-badge vp-badge--limit">Limit</span> Sync frequency: minimum 5 minutes between polls.

<span class="vp-badge vp-badge--limit">Limit</span> Webhook payload size: 1 MB maximum.

## Troubleshooting

??? question "Integration connection fails"
    **Cause**: Invalid credentials, expired OAuth token, or insufficient permissions in the external system.
    **Resolution**: Re-authenticate the integration. Verify the connected account has admin access in the external system. Check the [Sync Logs](../administration/security/audit-logs.md) for detailed error messages.

??? question "Data not syncing"
    **Cause**: Sync schedule not configured, field mapping incomplete, or rate limit hit in external system.
    **Resolution**: Verify the sync schedule is active. Check field mappings in the integration settings. Review rate limit status in the external system.

## Related pages

- [API → Authentication](../api/authentication.md)
- [API → Webhooks](../api/endpoints/webhooks.md)
- [Administration → Audit Logs](../administration/security/audit-logs.md)
