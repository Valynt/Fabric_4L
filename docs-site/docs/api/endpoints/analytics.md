---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Analytics API

Retrieve aggregated analytics including ROI, forecasts, trends, and benchmarks.

## Who this is for

<span class="vp-badge vp-badge--role">Developer</span>
<span class="vp-badge vp-badge--role">Admin</span>
<span class="vp-badge vp-badge--role">Executive</span>

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/v1/analytics/roi` | ROI analysis |
| GET | `/v1/analytics/forecasts` | Forecast accuracy |
| GET | `/v1/analytics/trends` | Trend analysis |
| GET | `/v1/analytics/benchmarks` | Peer benchmarking |
| GET | `/v1/analytics/realization` | Value realization |

## ROI analysis

```http
GET /v1/analytics/roi?initiative_id=init_abc123&period=annual
```

Response:

```json
{
  "initiative_id": "init_abc123",
  "period": "annual",
  "roi_percent": 245,
  "payback_months": 14,
  "npv": 1200000,
  "irr": 0.32,
  "confidence": "high",
  "sensitivity": {
    "best_case": { "roi_percent": 310 },
    "expected": { "roi_percent": 245 },
    "worst_case": { "roi_percent": 180 }
  }
}
```

## Benchmarking

```http
GET /v1/analytics/benchmarks?industry=manufacturing&metric=throughput
```

Compares your metrics against peer datasets from Layer 6 Benchmarks.

## Permissions

| Action | Required Permission |
|--------|---------------------|
| All analytics | `analytics:read` |

## Limits

<span class="vp-badge vp-badge--limit">Limit</span> Analytics queries: 30 per minute.

<span class="vp-badge vp-badge--limit">Limit</span> Historical data: 5 years maximum.

## Related pages

- [API Overview](../overview.md)
- [Analytics](../../analytics/index.md)
- [Core Concepts → Value Metrics](../../core-concepts/value-metrics.md)
