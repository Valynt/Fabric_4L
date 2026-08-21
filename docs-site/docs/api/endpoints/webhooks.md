---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Webhooks API

Register and manage webhook subscriptions for real-time event notifications.

## Who this is for

<span class="vp-badge vp-badge--role">Developer</span>

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/v1/webhooks` | List webhooks |
| POST | `/v1/webhooks` | Create a webhook |
| GET | `/v1/webhooks/{id}` | Get a webhook |
| PUT | `/v1/webhooks/{id}` | Update a webhook |
| DELETE | `/v1/webhooks/{id}` | Delete a webhook |
| POST | `/v1/webhooks/{id}/test` | Send test event |

## Create a webhook

```http
POST /v1/webhooks
Content-Type: application/json

{
  "url": "https://myapp.com/webhooks/valuepact",
  "events": ["initiative.created", "business_case.approved"],
  "secret": "whsec_test_dummy_mysecret",
  "active": true
}
```

## Event types

| Event | Description |
|-------|-------------|
| `initiative.created` | New initiative created |
| `initiative.status_changed` | Initiative status changed |
| `business_case.approved` | Business case approved |
| `business_case.rejected` | Business case rejected |
| `stakeholder.engagement` | New stakeholder engagement logged |
| `benefit.actual_recorded` | Actual benefit value recorded |
| `user.invited` | New user invited |
| `user.deactivated` | User deactivated |

## Signature verification

Webhooks include a signature header for verification:

```http
X-Webhook-Signature: sha256=abc123...
```

Verify using your webhook secret:

```python
import hmac
import hashlib

def verify_signature(payload, signature, secret):
    expected = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)
```

## Retry behavior

| Attempt | Delay | Action |
|---------|-------|--------|
| 1 | Immediate | First delivery |
| 2 | 5 minutes | Retry |
| 3 | 25 minutes | Final retry |

After 3 failures, the webhook is automatically disabled.

## Permissions

| Action | Required Permission |
|--------|---------------------|
| All | `admin:config` |

## Limits

<span class="vp-badge vp-badge--limit">Limit</span> Maximum 20 webhooks per tenant.

<span class="vp-badge vp-badge--limit">Limit</span> Payload size: 1 MB maximum.

## Related pages

- [API Overview](../overview.md)
- [Integrations → Webhooks](../../integrations/webhooks.md)
