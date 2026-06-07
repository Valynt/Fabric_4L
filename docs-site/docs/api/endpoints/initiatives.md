---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Initiatives API

Manage strategic initiatives through their full lifecycle from creation to archive.

## Who this is for

<span class="vp-badge vp-badge--role">Developer</span>
<span class="vp-badge vp-badge--role">Admin</span>

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/v1/initiatives` | List initiatives |
| POST | `/v1/initiatives` | Create an initiative |
| GET | `/v1/initiatives/{id}` | Get an initiative |
| PUT | `/v1/initiatives/{id}` | Update an initiative |
| PATCH | `/v1/initiatives/{id}` | Partial update |
| DELETE | `/v1/initiatives/{id}` | Archive an initiative |
| POST | `/v1/initiatives/{id}/status` | Change status |

## List initiatives

```http
GET /v1/initiatives?page=1&page_size=50&status=active&industry=manufacturing
```

**Query parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | integer | 1 | Page number |
| `page_size` | integer | 50 | Items per page (max 200) |
| `status` | string | — | Filter by status |
| `industry` | string | — | Filter by industry |
| `sort` | string | `created_at` | Sort field |
| `order` | string | `desc` | Sort order |

**Response:**

```json
{
  "data": [
    {
      "id": "init_abc123",
      "name": "Manufacturing Efficiency Program",
      "description": "Reduce waste and improve throughput",
      "status": "active",
      "industry": "manufacturing",
      "segment": "enterprise",
      "owner_id": "user_def456",
      "created_at": "2026-01-15T10:00:00Z",
      "updated_at": "2026-06-01T14:30:00Z"
    }
  ],
  "meta": {
    "pagination": {
      "page": 1,
      "page_size": 50,
      "total": 247,
      "total_pages": 5
    }
  }
}
```

## Create an initiative

```http
POST /v1/initiatives
Content-Type: application/json

{
  "name": "Q3 Cloud Migration",
  "description": "Migrate on-premise workloads to cloud",
  "industry": "technology",
  "segment": "mid-market",
  "expected_start_date": "2026-07-01",
  "expected_end_date": "2026-12-31"
}
```

**Required fields:** `name`

**Optional fields:** `description`, `industry`, `segment`, `expected_start_date`, `expected_end_date`, `owner_id`

**Response:** `201 Created`

## Get an initiative

```http
GET /v1/initiatives/init_abc123
```

Returns the full initiative including related projects, stakeholders, and metrics.

## Update an initiative

```http
PUT /v1/initiatives/init_abc123
Content-Type: application/json

{
  "name": "Q3 Cloud Migration — Revised",
  "description": "Updated scope including data center exit",
  "status": "active"
}
```

## Change status

```http
POST /v1/initiatives/init_abc123/status
Content-Type: application/json

{
  "status": "in_review",
  "reason": "Ready for stakeholder review"
}
```

**Valid transitions:**

| From | To | Who |
|------|-----|-----|
| `draft` | `in_review` | Owner, Admin |
| `in_review` | `approved` | Admin, Executive |
| `in_review` | `rejected` | Admin, Executive |
| `approved` | `active` | Admin |
| `active` | `completed` | Admin, Owner |
| `active` | `archived` | Admin |
| `completed` | `archived` | Admin |

!!! warning "Irreversible transitions"
    `archived` status is final. Archived initiatives are read-only and excluded from active dashboards.

## Delete (archive) an initiative

```http
DELETE /v1/initiatives/init_abc123
```

Archives the initiative and all associated projects. This operation is irreversible.

## Permissions

| Action | Required Permission |
|--------|---------------------|
| List | `initiatives:read` |
| Create | `initiatives:write` |
| Get | `initiatives:read` |
| Update | `initiatives:write` |
| Change status | `initiatives:write` + role-based gate |
| Archive | `initiatives:delete` |

## Limits

<span class="vp-badge vp-badge--limit">Limit</span> Maximum 1,000 active initiatives per tenant.

<span class="vp-badge vp-badge--limit">Limit</span> Initiative name must be 1–200 characters.

## Troubleshooting

??? question "409 Conflict when creating"
    **Cause**: Initiative with the same name already exists in your tenant.
    **Resolution**: Use a unique name or check existing initiatives before creating.

??? question "Cannot change status to approved"
    **Cause**: User lacks the required role (Admin or Executive).
    **Resolution**: Request approval from an Admin or Executive. Check your role in **Profile → Organization**.

## Related pages

- [API Overview](../overview.md)
- [Core Concepts → Initiatives](../../core-concepts/initiatives.md)
- [Workflow Management → Statuses](../../workflow-management/statuses.md)
