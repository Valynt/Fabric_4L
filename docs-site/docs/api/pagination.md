---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Pagination

List endpoints in the ValuePact API support two pagination strategies: offset-based (default) and cursor-based.

## Who this is for

<span class="vp-badge vp-badge--role">Developer</span>

## Offset-based pagination

Use `page` and `page_size` query parameters:

```http
GET /v1/initiatives?page=2&page_size=50
```

Response:

```json
{
  "data": [ ... ],
  "meta": {
    "pagination": {
      "page": 2,
      "page_size": 50,
      "total": 247,
      "total_pages": 5,
      "has_next": true,
      "has_previous": true
    }
  }
}
```

| Parameter | Default | Min | Max | Description |
|-----------|---------|-----|-----|-------------|
| `page` | 1 | 1 | — | Page number (1-indexed) |
| `page_size` | 50 | 1 | 200 | Items per page |

!!! warning "Offset pagination limits"
    Offset pagination is limited to the first 10,000 results. For larger datasets, use cursor-based pagination.

## Cursor-based pagination

Use `cursor` and `limit` parameters:

```http
GET /v1/initiatives?cursor=eyJpZCI6Ijk5OSJ9&limit=50
```

Response:

```json
{
  "data": [ ... ],
  "meta": {
    "pagination": {
      "next_cursor": "eyJpZCI6IjEwNDkifQ==",
      "previous_cursor": null,
      "has_next": true,
      "has_previous": false
    }
  }
}
```

| Parameter | Default | Min | Max | Description |
|-----------|---------|-----|-----|-------------|
| `cursor` | — | — | — | Opaque cursor from previous response |
| `limit` | 50 | 1 | 200 | Items per page |

!!! tip "Cursor stability"
    Cursor-based pagination is stable under insertions and deletions. Use it for real-time data or large datasets.

## Sorting

Most list endpoints support `sort` and `order` parameters:

```http
GET /v1/initiatives?sort=created_at&order=desc&page_size=25
```

| Parameter | Values | Default |
|-----------|--------|---------|
| `sort` | `created_at`, `updated_at`, `name`, `status` | `created_at` |
| `order` | `asc`, `desc` | `desc` |

## Filtering

Combine pagination with filters:

```http
GET /v1/initiatives?status=active&industry=manufacturing&page=1&page_size=25
```

Filter parameters are endpoint-specific. See individual endpoint documentation for available filters.

## Iterating through all results

### Offset-based (small datasets)

```python
import requests

all_items = []
page = 1
while True:
    response = requests.get(
        "https://api.valuepact.ai/v1/initiatives",
        headers={"Authorization": "Bearer <token>"},
        params={"page": page, "page_size": 200}
    )
    data = response.json()
    all_items.extend(data["data"])
    if not data["meta"]["pagination"]["has_next"]:
        break
    page += 1
```

### Cursor-based (large datasets)

```python
import requests

all_items = []
cursor = None
while True:
    params = {"limit": 200}
    if cursor:
        params["cursor"] = cursor
    
    response = requests.get(
        "https://api.valuepact.ai/v1/initiatives",
        headers={"Authorization": "Bearer <token>"},
        params=params
    )
    data = response.json()
    all_items.extend(data["data"])
    
    if not data["meta"]["pagination"]["has_next"]:
        break
    cursor = data["meta"]["pagination"]["next_cursor"]
```

## Troubleshooting

??? question "Cursor returns stale data"
    **Cause**: Cursors expire after 5 minutes of inactivity.
    **Resolution**: Restart pagination from the beginning or reduce the time between requests.

??? question `"has_next" is true but next page is empty`
    **Cause**: Records were deleted between pages.
    **Resolution**: This is expected with offset pagination. Use cursor-based pagination for stable iteration.

## Related pages

- [API Overview](overview.md)
- [Errors](errors.md)
- [Rate Limits](rate-limits.md)
