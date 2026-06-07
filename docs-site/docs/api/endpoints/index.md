---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# API Endpoints

This section provides detailed reference documentation for every ValuePact API endpoint group.

## Who this is for

<span class="vp-badge vp-badge--role">Developer</span>

## Endpoint groups

| Group | Description | Key Operations |
|-------|-------------|----------------|
| [Initiatives](initiatives.md) | Strategic programs and their lifecycle | CRUD, status transitions, archive |
| [Business Cases](business-cases.md) | Packaged value arguments and deliverables | Create, approve, export, version |
| [Benefits](benefits.md) | Expected and realized benefits tracking | Track, update, reconcile, report |
| [Stakeholders](stakeholders.md) | People and roles mapped to initiatives | Manage, map influence, engagement |
| [Dashboards](dashboards.md) | Dashboard data and report configurations | Query, configure, export |
| [Analytics](analytics.md) | Aggregated analytics and insights | ROI, forecast, trend, benchmark |
| [Users](users.md) | User profiles and organization membership | List, update, deactivate |
| [Roles](roles.md) | Roles and permission assignments | List, assign, query permissions |
| [Integrations](integrations.md) | Third-party connector configuration | Connect, configure, monitor |
| [Webhooks](webhooks.md) | Webhook subscription management | Register, list, update, delete |

## Common patterns

Every endpoint group follows these conventions:

- **Base path**: `/v1/{group}`
- **List**: `GET /v1/{group}` — supports pagination, filtering, sorting
- **Create**: `POST /v1/{group}` — returns 201 with the created resource
- **Get**: `GET /v1/{group}/{id}` — returns 200 or 404
- **Update**: `PUT /v1/{group}/{id}` or `PATCH /v1/{group}/{id}` — full or partial update
- **Delete**: `DELETE /v1/{group}/{id}` — returns 204

## Request and response schemas

For complete request and response schemas, refer to the [Generated API Docs](../generated.md) which renders the canonical OpenAPI specification interactively.

## Error handling

All endpoints return the standard [error format](../errors.md). Common errors per group:

| Group | Common errors |
|-------|--------------|
| Initiatives | `VALIDATION_ERROR` (invalid status transition), `NOT_FOUND` |
| Business Cases | `CONFLICT` (already approved), `AUTHORIZATION_ERROR` |
| Benefits | `INVALID_PARAMETER` (date range), `NOT_FOUND` |
| Stakeholders | `ALREADY_EXISTS` (duplicate email), `VALIDATION_ERROR` |
| Analytics | `RATE_LIMIT_EXCEEDED`, `SERVICE_UNAVAILABLE` |

## Rate limits

See [Rate Limits](../rate-limits.md) for tiered limits. Analytics endpoints have lower limits due to computation cost.

## Related pages

- [API Overview](../overview.md)
- [Authentication](../authentication.md)
- [Generated API Docs](../generated.md)
- [Errors](../errors.md)
