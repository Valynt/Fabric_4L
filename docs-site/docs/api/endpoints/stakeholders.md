---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Stakeholders API

Manage stakeholder records, map influence, and track engagement across initiatives.

## Who this is for

<span class="vp-badge vp-badge--role">Developer</span>
<span class="vp-badge vp-badge--role">Admin</span>

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/v1/stakeholders` | List stakeholders |
| POST | `/v1/stakeholders` | Create a stakeholder |
| GET | `/v1/stakeholders/{id}` | Get a stakeholder |
| PUT | `/v1/stakeholders/{id}` | Update a stakeholder |
| DELETE | `/v1/stakeholders/{id}` | Remove a stakeholder |
| POST | `/v1/stakeholders/{id}/engagement` | Log engagement |

## Create a stakeholder

```http
POST /v1/stakeholders
Content-Type: application/json

{
  "initiative_id": "init_abc123",
  "name": "Sarah Chen",
  "email": "sarah.chen@example.com",
  "role": "cfo",
  "influence": "high",
  "interest": "high",
  "department": "finance",
  "notes": "Key decision maker for budget approval"
}
```

**Influence levels:** `low`, `medium`, `high`, `critical`

**Interest levels:** `low`, `medium`, `high`

## Log engagement

```http
POST /v1/stakeholders/sh_ghi789/engagement
Content-Type: application/json

{
  "type": "meeting",
  "date": "2026-06-07",
  "notes": "Reviewed Q3 forecast, expressed concerns about timeline",
  "sentiment": "cautious"
}
```

**Engagement types:** `meeting`, `email`, `call`, `presentation`, `survey`, `other`

**Sentiment:** `positive`, `neutral`, `cautious`, `negative`

## Permissions

| Action | Required Permission |
|--------|---------------------|
| List | `stakeholders:read` |
| Create | `stakeholders:write` |
| Update | `stakeholders:write` |
| Delete | `stakeholders:delete` |
| Log engagement | `stakeholders:write` |

## Limits

<span class="vp-badge vp-badge--limit">Limit</span> Maximum 500 stakeholders per initiative.

## Related pages

- [API Overview](../overview.md)
- [Core Concepts → Stakeholders](../../core-concepts/stakeholders.md)
- [End User Guides → Managing Stakeholders](../../end-user-guides/managing-stakeholders.md)
