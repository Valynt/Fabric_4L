---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Errors

The ValuePact API returns structured error responses to help you diagnose and handle failures programmatically.

## Who this is for

<span class="vp-badge vp-badge--role">Developer</span>
<span class="vp-badge vp-badge--role">Support</span>
<span class="vp-badge vp-badge--role">Admin</span>

## Error response format

All errors follow a consistent JSON structure:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "The request failed validation",
    "request_id": "req_abc123def456",
    "details": {
      "field": "email",
      "reason": "Invalid email format"
    }
  }
}
```

| Field | Description |
|-------|-------------|
| `code` | Machine-readable error code |
| `message` | Human-readable description |
| `request_id` | Unique identifier for tracing — include this when contacting support |
| `details` | Additional context (field-level errors, allowed values, etc.) |

## Error codes

### Authentication errors

| Code | HTTP | Meaning |
|------|------|---------|
| `AUTHENTICATION_ERROR` | 401 | Missing or invalid credentials |
| `TOKEN_EXPIRED` | 401 | JWT token has expired |
| `TOKEN_INVALID` | 401 | Token signature or format invalid |

### Authorization errors

| Code | HTTP | Meaning |
|------|------|---------|
| `AUTHORIZATION_ERROR` | 403 | Insufficient permissions |
| `TENANT_ISOLATION_ERROR` | 403 | Cross-tenant access attempted |

### Validation errors

| Code | HTTP | Meaning |
|------|------|---------|
| `VALIDATION_ERROR` | 422 | Input failed semantic validation |
| `INVALID_PARAMETER` | 400 | Query or path parameter invalid |
| `MISSING_REQUIRED_FIELD` | 400 | Required field not provided |
| `INVALID_FORMAT` | 400 | Data format incorrect |

### Resource errors

| Code | HTTP | Meaning |
|------|------|---------|
| `NOT_FOUND` | 404 | Resource does not exist |
| `ENTITY_NOT_FOUND` | 404 | Specific entity not found |
| `RESOURCE_GONE` | 410 | Resource permanently deleted |
| `CONFLICT` | 409 | Resource already exists or state conflict |
| `ALREADY_EXISTS` | 409 | Duplicate creation attempt |

### Rate limiting

| Code | HTTP | Meaning |
|------|------|---------|
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `THROTTLED` | 429 | Request throttled |
| `QUOTA_EXCEEDED` | 429 | Plan quota exceeded |

### Server errors

| Code | HTTP | Meaning |
|------|------|---------|
| `INTERNAL_ERROR` | 500 | Unexpected server error |
| `SERVICE_UNAVAILABLE` | 503 | Dependency degraded or down |
| `DATABASE_ERROR` | 500 | Database operation failed |
| `EXTERNAL_SERVICE_ERROR` | 502 | Upstream service error |
| `TIMEOUT_ERROR` | 504 | Request timed out |

### Graph errors

| Code | HTTP | Meaning |
|------|------|---------|
| `NEO4J_ERROR` | 500 | Knowledge graph query failed |
| `CYPHER_SYNTAX_ERROR` | 400 | Graph query syntax invalid |
| `GRAPH_CONSTRAINT_VIOLATION` | 422 | Graph constraint violated |

## Validation error details

When a request fails validation, the `details` field contains field-level errors:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "request_id": "req_abc123",
    "details": {
      "errors": [
        {
          "field": "name",
          "message": "Name must be between 1 and 200 characters",
          "value": ""
        },
        {
          "field": "start_date",
          "message": "Start date must be in ISO 8601 format",
          "value": "2026-13-45"
        }
      ]
    }
  }
}
```

## Retry behavior

| Error code | Retryable | Strategy |
|------------|-----------|----------|
| `RATE_LIMIT_EXCEEDED` | Yes | Exponential backoff, respect `Retry-After` header |
| `THROTTLED` | Yes | Exponential backoff |
| `TIMEOUT_ERROR` | Yes | Retry up to 3 times with backoff |
| `SERVICE_UNAVAILABLE` | Yes | Retry with longer backoff |
| `INTERNAL_ERROR` | Yes | Retry once, then escalate |
| `DATABASE_ERROR` | No | Do not retry — contact support |
| `VALIDATION_ERROR` | No | Fix request and retry |
| `AUTHENTICATION_ERROR` | No | Refresh token and retry |
| `AUTHORIZATION_ERROR` | No | Check permissions |

## Request IDs

Every API response includes a `request_id` in the headers and error body:

```http
X-Request-ID: req_abc123def456
```

Include this ID when contacting support or checking logs. It enables end-to-end tracing across all six platform layers.

## Error handling example

```python
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

session = requests.Session()
retries = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET", "POST", "PUT", "PATCH"]
)
session.mount("https://", HTTPAdapter(max_retries=retries))

response = session.get(
    "https://api.valuepact.ai/v1/initiatives",
    headers={"Authorization": "Bearer <token>"}
)

if not response.ok:
    error = response.json()["error"]
    print(f"Error {error['code']}: {error['message']}")
    print(f"Request ID: {error['request_id']}")
    if error["code"] == "RATE_LIMIT_EXCEEDED":
        retry_after = int(response.headers.get("Retry-After", 60))
        print(f"Retry after {retry_after} seconds")
```

## Troubleshooting

??? question "I receive 500 errors consistently"
    **Cause**: Possible bug or dependency degradation.
    **Resolution**: Check the [Status Page](https://status.valuepact.ai) for incidents. Include the `request_id` when contacting support. Do not retry indefinitely.

??? question "Validation errors don't specify which field"
    **Cause**: Some validation failures are cross-field or schema-level.
    **Resolution**: Check the `message` field for the overall reason. Review the API schema in the OpenAPI spec. Ensure all required fields are present and correctly formatted.

??? question "I get 429 even though I'm under the rate limit"
    **Cause**: Burst limit exceeded or concurrent request limit reached.
    **Resolution**: Implement request queuing and respect the `Retry-After` header. Consider using batch endpoints for bulk operations.

## Escalation path

1. Check [Status Page](https://status.valuepact.ai) for known incidents.
2. Search the [FAQ](../faq/index.md) for related issues.
3. Contact support with `request_id`, timestamp, and endpoint.
4. For production-impacting errors, open a P1 ticket via support@valuepact.ai.

## Related pages

- [API Overview](overview.md)
- [Authentication](authentication.md)
- [Rate Limits](rate-limits.md)
- [Pagination](pagination.md)
