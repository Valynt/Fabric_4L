---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# API Overview

The ValuePact REST API lets you programmatically manage initiatives, business cases, benefits, stakeholders, dashboards, and analytics. It is organized around standard HTTP verbs and returns JSON responses.

## Who this is for

<span class="vp-badge vp-badge--role">Developer</span>
<span class="vp-badge vp-badge--role">Admin</span>
<span class="vp-badge vp-badge--role">Support</span>

## Base URL

All API requests use the following base URL pattern:

```
https://api.valuepact.ai/v1
```

For sandbox or private deployments, replace the host with your configured API gateway endpoint.

## Authentication

Every request must include a valid bearer token in the `Authorization` header:

```http
Authorization: Bearer <your-jwt-token>
```

See [Authentication](authentication.md) for how to obtain and refresh tokens.

## Request format

- **Content-Type**: `application/json` for POST, PUT, and PATCH bodies.
- **Accept**: `application/json` for all requests.
- **Tenant context**: The API infers `tenant_id` from the authenticated JWT. Do not pass `tenant_id` in request bodies.

## Response format

All responses are JSON objects with a consistent envelope:

```json
{
  "data": { ... },
  "meta": {
    "request_id": "req_abc123",
    "timestamp": "2026-06-07T12:00:00Z"
  }
}
```

List endpoints include pagination metadata:

```json
{
  "data": [ ... ],
  "meta": {
    "request_id": "req_abc123",
    "timestamp": "2026-06-07T12:00:00Z",
    "pagination": {
      "page": 1,
      "page_size": 50,
      "total": 247,
      "total_pages": 5
    }
  }
}
```

## HTTP status codes

| Status | Meaning |
|--------|---------|
| 200 | Success — GET, PUT, PATCH |
| 201 | Created — POST |
| 204 | No Content — DELETE |
| 400 | Bad Request — validation error |
| 401 | Unauthorized — missing or invalid token |
| 403 | Forbidden — insufficient permissions |
| 404 | Not Found — resource does not exist |
| 409 | Conflict — resource already exists or state conflict |
| 422 | Unprocessable Entity — semantic validation failure |
| 429 | Rate Limit Exceeded — too many requests |
| 500 | Internal Server Error — unexpected failure |
| 503 | Service Unavailable — dependency degraded |

See [Errors](errors.md) for detailed error codes and resolution steps.

## Idempotency

POST endpoints that create resources support idempotency via the `Idempotency-Key` header:

```http
Idempotency-Key: <uuid-v4>
```

If a request with the same key is retried within 24 hours, the API returns the original response without creating a duplicate.

## Rate limits

See [Rate Limits](rate-limits.md) for tiered limits and burst behavior.

## Pagination

See [Pagination](pagination.md) for cursor-based and offset-based pagination options.

## SDKs and tools

- **OpenAPI spec**: Available at `/openapi.json` on any running service.
- **Postman collection**: Import the OpenAPI spec directly into Postman.
- **Swagger UI**: Interactive documentation is available at `/docs` on each service.

## Endpoints by domain

| Domain | Endpoints |
|--------|-----------|
| Initiatives | Create, list, get, update, archive initiatives |
| Business Cases | Build, approve, export, version business cases |
| Benefits | Track, update, reconcile benefit actuals |
| Stakeholders | Manage stakeholder records and engagement |
| Dashboards | Query dashboard data and report configurations |
| Analytics | Retrieve ROI, forecast, trend, and benchmark analytics |
| Users | Manage user profiles and organization membership |
| Roles | Query and assign roles and permissions |
| Integrations | Configure and monitor third-party connectors |
| Webhooks | Register, list, update, and delete webhook subscriptions |

See [Endpoints](endpoints/index.md) for detailed reference per domain.

## Changelog

API changes are documented in the [Release Notes](../release-notes/index.md). Breaking changes are announced 30 days in advance via the changelog and in-app notifications.

## Troubleshooting

??? question "I get 401 on every request"
    **Cause**: Token is missing, expired, or the `Authorization` header format is incorrect.
    **Resolution**: Verify the token is present and prefixed with `Bearer `. Check token expiry and refresh if needed. See [Authentication](authentication.md).

??? question "I get 403 even though my token is valid"
    **Cause**: The authenticated user lacks permission for the requested resource or tenant.
    **Resolution**: Confirm the user's role includes the required permission. Check that the resource belongs to the user's current tenant. See [Administration → Permissions](../administration/user-management/permissions.md).

??? question "My POST created a duplicate"
    **Cause**: The request was retried without an `Idempotency-Key` header.
    **Resolution**: Generate a UUID v4 for each logical operation and include it in the `Idempotency-Key` header.

## Related pages

- [Authentication](authentication.md)
- [Rate Limits](rate-limits.md)
- [Errors](errors.md)
- [Pagination](pagination.md)
- [Endpoints](endpoints/index.md)
- [Integrations → APIs](../integrations/apis.md)
