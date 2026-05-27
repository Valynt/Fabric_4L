# Tracing Taxonomy and Dashboard Mapping

## Required instrumentation attributes

All service spans must include:
- `tenant_id`
- `request_id`
- `service`
- `layer`
- `route`
- `error_code`

## Canonical span naming

Use HTTP span naming as: `<METHOD> <ROUTE>` (for example: `GET /health`).

## Dashboard mapping

- Grafana service dashboards should group by `service` and `layer`.
- Error dashboards should filter `error_code != none`.
- Tenant debug views should filter by `tenant_id` + `request_id`.

## Smoke validation coverage

`scripts/observability/tracing_smoke_check.py` verifies basic presence for:
- Health routes
- Key API route files
- One background workflow source file
