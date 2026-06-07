---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Dashboards API

Query dashboard data and configure report settings programmatically.

## Who this is for

<span class="vp-badge vp-badge--role">Developer</span>
<span class="vp-badge vp-badge--role">Admin</span>

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/v1/dashboards` | List available dashboards |
| GET | `/v1/dashboards/{id}` | Get dashboard data |
| GET | `/v1/dashboards/{id}/widgets` | Get widget configurations |
| POST | `/v1/dashboards/{id}/export` | Export dashboard |

## Get dashboard data

```http
GET /v1/dashboards/exec_rollup?period=quarter&date=2026-Q2
```

**Dashboard types:**

| ID | Type | Description |
|----|------|-------------|
| `exec_rollup` | Executive | Portfolio-level KPIs and trends |
| `portfolio_health` | Portfolio | Initiative health, risk flags |
| `team_status` | Team | Project status, milestones |
| `individual_work` | Individual | My initiatives, tasks, approvals |

**Query parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `period` | string | `month` | `week`, `month`, `quarter`, `year` |
| `date` | string | current | Period identifier (e.g., `2026-Q2`) |
| `filters` | object | — | Additional filters |

## Export dashboard

```http
POST /v1/dashboards/exec_rollup/export
Content-Type: application/json

{
  "format": "pdf",
  "include_charts": true,
  "recipients": ["exec@example.com"]
}
```

## Permissions

| Action | Required Permission |
|--------|---------------------|
| List | `analytics:read` |
| Get data | `analytics:read` |
| Export | `analytics:read` |

## Limits

<span class="vp-badge vp-badge--limit">Limit</span> Dashboard queries: 30 per minute.

<span class="vp-badge vp-badge--limit">Limit</span> Export size: 50 MB maximum.

## Related pages

- [API Overview](../overview.md)
- [Dashboards & Reporting](../../dashboards-reporting/index.md)
