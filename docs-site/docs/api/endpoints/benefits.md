---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Benefits API

Track, update, and reconcile expected versus realized benefits for initiatives and projects.

## Who this is for

<span class="vp-badge vp-badge--role">Developer</span>
<span class="vp-badge vp-badge--role">Admin</span>

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/v1/benefits` | List benefits |
| POST | `/v1/benefits` | Create a benefit |
| GET | `/v1/benefits/{id}` | Get a benefit |
| PUT | `/v1/benefits/{id}` | Update a benefit |
| POST | `/v1/benefits/{id}/actuals` | Record actual value |
| GET | `/v1/benefits/{id}/variance` | Get variance analysis |

## Create a benefit

```http
POST /v1/benefits
Content-Type: application/json

{
  "initiative_id": "init_abc123",
  "name": "Reduced Infrastructure Cost",
  "category": "cost_reduction",
  "expected_value": 500000,
  "currency": "USD",
  "expected_start_date": "2026-07-01",
  "measurement_frequency": "monthly",
  "unit": "dollars"
}
```

## Record actuals

```http
POST /v1/benefits/ben_def456/actuals
Content-Type: application/json

{
  "value": 45000,
  "period": "2026-07",
  "notes": "Savings from decommissioned servers",
  "evidence_url": "https://finance.company.com/reports/july2026"
}
```

## Get variance

```http
GET /v1/benefits/ben_def456/variance
```

Response:

```json
{
  "benefit_id": "ben_def456",
  "expected_ytd": 150000,
  "actual_ytd": 135000,
  "variance": -15000,
  "variance_percent": -10,
  "trend": "behind",
  "periods": [
    {"period": "2026-07", "expected": 50000, "actual": 45000, "variance": -5000},
    {"period": "2026-08", "expected": 50000, "actual": 47000, "variance": -3000},
    {"period": "2026-09", "expected": 50000, "actual": 43000, "variance": -7000}
  ]
}
```

## Permissions

| Action | Required Permission |
|--------|---------------------|
| List | `benefits:read` |
| Create | `benefits:write` |
| Update | `benefits:write` |
| Record actuals | `benefits:write` |

## Limits

<span class="vp-badge vp-badge--limit">Limit</span> Maximum 100 benefits per initiative.

<span class="vp-badge vp-badge--limit">Limit</span> Actual values can be recorded monthly or quarterly per benefit.

## Troubleshooting

??? question "Variance shows unexpected negative trend"
    **Cause**: Actuals may be recorded incorrectly or expected values may need adjustment.
    **Resolution**: Verify actual value sources. Review and update expected values if assumptions changed.

## Related pages

- [API Overview](../overview.md)
- [Core Concepts → Benefits Tracking](../../core-concepts/benefits-tracking.md)
- [End User Guides → Tracking Benefits](../../end-user-guides/tracking-benefits.md)
