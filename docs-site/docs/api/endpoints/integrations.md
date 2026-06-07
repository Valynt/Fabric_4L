---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Integrations API

Configure and monitor third-party connectors.

## Who this is for

<span class="vp-badge vp-badge--role">Developer</span>
<span class="vp-badge vp-badge--role">Admin</span>

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/v1/integrations` | List integrations |
| POST | `/v1/integrations` | Connect an integration |
| GET | `/v1/integrations/{id}` | Get integration status |
| PUT | `/v1/integrations/{id}` | Update configuration |
| DELETE | `/v1/integrations/{id}` | Disconnect |
| GET | `/v1/integrations/{id}/syncs` | Get sync history |
| POST | `/v1/integrations/{id}/sync` | Trigger manual sync |

## Connect an integration

```http
POST /v1/integrations
Content-Type: application/json

{
  "provider": "salesforce",
  "name": "Production Salesforce",
  "config": {
    "instance_url": "https://mycompany.salesforce.com",
    "oauth_token": "..."
  },
  "sync_schedule": {
    "frequency": "hourly",
    "timezone": "America/New_York"
  }
}
```

## Trigger manual sync

```http
POST /v1/integrations/int_abc123/sync
```

## Permissions

| Action | Required Permission |
|--------|---------------------|
| All | `admin:config` |

## Limits

<span class="vp-badge vp-badge--limit">Limit</span> Maximum 10 active integrations per tenant.

## Related pages

- [API Overview](../overview.md)
- [Integrations](../../integrations/index.md)
