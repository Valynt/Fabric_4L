---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Rate Limits

The ValuePact API enforces rate limits to ensure fair usage and platform stability. Limits vary by plan tier and authentication method.

## Who this is for

<span class="vp-badge vp-badge--role">Developer</span>
<span class="vp-badge vp-badge--role">Admin</span>

## Limit tiers

| Plan | Requests/minute | Burst | Concurrent |
|------|----------------|-------|------------|
| Starter | 100 | 20 | 5 |
| Professional | 500 | 50 | 10 |
| Enterprise | 2,000 | 200 | 25 |
| Enterprise Plus | Custom | Custom | Custom |

!!! note "Burst behavior"
    Burst limits allow short spikes above the sustained rate. The bucket refills at the sustained rate per minute.

## Per-endpoint limits

Some endpoints have additional limits:

| Endpoint | Limit |
|----------|-------|
| `POST /v1/initiatives` | 10/minute |
| `POST /v1/business-cases` | 10/minute |
| `POST /v1/bulk/*` | 5/minute |
| `GET /v1/analytics/*` | 30/minute |
| `POST /v1/webhooks` | 20/minute |

## Rate limit headers

Every API response includes rate limit headers:

```http
X-RateLimit-Limit: 500
X-RateLimit-Remaining: 489
X-RateLimit-Reset: 1717761600
X-RateLimit-Retry-After: 45
```

| Header | Description |
|--------|-------------|
| `X-RateLimit-Limit` | Maximum requests allowed in the window |
| `X-RateLimit-Remaining` | Requests remaining in current window |
| `X-RateLimit-Reset` | Unix timestamp when the limit resets |
| `X-RateLimit-Retry-After` | Seconds until you can retry |

## Handling rate limits

When you hit a limit, the API returns:

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 60

{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded. Please retry after 60 seconds.",
    "request_id": "req_abc123"
  }
}
```

### Best practices

1. **Monitor headers**: Check `X-RateLimit-Remaining` before making requests.
2. **Exponential backoff**: Start with 1 second, double on each retry, max 60 seconds.
3. **Respect Retry-After**: Use the header value when present.
4. **Batch operations**: Use bulk endpoints instead of individual calls.
5. **Cache responses**: Cache read-heavy data locally.
6. **Queue requests**: Use a job queue for high-volume operations.

### Backoff example

```python
import time
import requests

def api_request_with_backoff(url, headers, max_retries=3):
    for attempt in range(max_retries):
        response = requests.get(url, headers=headers)
        if response.status_code != 429:
            return response
        
        retry_after = int(response.headers.get('Retry-After', 2 ** attempt))
        time.sleep(retry_after)
    
    return response
```

## Webhook rate limits

Webhook delivery has separate limits:

| Metric | Limit |
|--------|-------|
| Delivery attempts | 3 per event |
| Retry interval | 5 minutes between attempts |
| Timeout | 30 seconds per attempt |
| Payload size | 1 MB |

See [Integrations → Webhooks](../integrations/webhooks.md) for webhook-specific handling.

## Increasing limits

To request a limit increase:

1. Contact your account manager or support.
2. Provide your use case, expected request volume, and peak patterns.
3. For Enterprise Plus, limits are negotiated per contract.

## Troubleshooting

??? question "I'm hitting limits during normal usage"
    **Cause**: Inefficient API usage pattern or missing caching.
    **Resolution**: Review your integration for:
    - Unnecessary polling — use webhooks instead.
    - Missing caching — cache read-heavy data.
    - N+1 queries — use list endpoints with filtering.

??? question "429 errors after a burst of imports"
    **Cause**: Bulk import exceeded burst limit.
    **Resolution**: Use the bulk import endpoint (`POST /v1/bulk/import`) which has higher limits. Spread imports over time or request a temporary limit increase.

## Related pages

- [API Overview](overview.md)
- [Authentication](authentication.md)
- [Errors](errors.md)
- [Integrations → Webhooks](../integrations/webhooks.md)
