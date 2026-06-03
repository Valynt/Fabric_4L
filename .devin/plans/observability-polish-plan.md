# Observability Polish Plan

## Context
Request: "Observability polish: Remove old OTel config; add Jaeger datasource; complete dashboard panels; add frontend RUM spans per route"

---

## A. OTel Config Inventory

### Findings
| File | Status | Evidence |
|---|---|---|
| `apps/web/src/lib/opentelemetry.ts` | **ACTIVE** | Imported by `apps/web/src/main.tsx` at app startup. Initializes WebTracerProvider with OTLP exporter. |
| `k8s/monitoring/otel-collector-tls.yaml` | **ACTIVE** | Only collector manifest in repo. TLS-secured ConfigMap with OTLP receivers and Jaeger exporter. |
| `apps/web/package.json` `@opentelemetry/*` | **ACTIVE** | Required by `lib/opentelemetry.ts`. No orphan references found. |
| Insecure `opentelemetry-collector.yaml` | **NOT FOUND** | `find_by_name` and `grep` found no old insecure collector manifest. Already removed or never committed. |

### Decision
No old OTel config to remove. All existing OTel assets are active and required.

---

## B. Add Jaeger Datasource

### Problem
`monitoring/grafana/provisioning/datasources/loki.yml` references `datasourceUid: jaeger` in derived fields, but no Jaeger datasource file exists.

### Action
Create `monitoring/grafana/provisioning/datasources/jaeger.yml` with:
- `name: Jaeger`
- `type: jaeger`
- `uid: jaeger` (must match Loki's `datasourceUid`)
- `url: http://jaeger-query:16686` (or cluster-internal equivalent)
- `access: proxy`

---

## C. Complete Dashboard Panels

### Findings
- No dashboards contain TODO/placeholder/dummy panels.
- `frontend-performance.json` references `otel_web_*` metrics. These will show **no data** because the frontend currently exports **traces only** (no metrics pipeline). This is a documented gap, not a fake metric.
- Other dashboards (`layer1-ingestion`, `layer4-agents`, `value-fabric-operational`, `db-connection-pool`, `rate-limiting-observability`, `journey-launch-slos`) use real, existing Prometheus metrics.

### Action
1. **Add Jaeger trace panel** to `frontend-performance.json` so operators can browse actual frontend traces by service name (`fabric-4l-frontend`).
2. **Document metric dependency** in `frontend-performance.json`: add a `text` panel noting that `otel_web_*` histogram panels require a frontend OTLP metrics pipeline (currently traces-only).
3. Leave all other dashboards unchanged — they have real metrics and no placeholders.

---

## D. Frontend RUM Spans per Route

### Problem
`apps/web/src/lib/opentelemetry.ts` instruments document load, fetch, XHR, and user interactions, but does **not** create spans for React Router route changes. The `frontend-performance.json` "Route Change Timing" panel expects `otel_web_route_change_duration_bucket`, which will never populate without route-level instrumentation.

### Action
1. **Update `apps/web/src/lib/opentelemetry.ts`**:
   - Export a `getTracer()` helper so React components can create spans.
2. **Create `apps/web/src/lib/route-telemetry.tsx`**:
   - React component using `useLocation()` and `useMatches()` from `react-router-dom`.
   - On location change: start a span named `route_change`.
   - Add attributes: `route.path`, `route.analyticsRouteId` (from `handle`), `http.url`.
   - End span after navigation.
3. **Mount in router tree**:
   - Add `<RouteTelemetry />` inside `GlobalLayout` (or root layout route) so it sits inside the Router context.

### Span naming convention
- Span name: `route_change`
- Attributes:
  - `route.id` → `analyticsRouteId` from matched route handle
  - `route.path` → matched route path pattern
  - `http.url` → `window.location.href`

---

## E. Validation

- [ ] `pnpm --dir apps/web run check` passes (TypeScript)
- [ ] `pnpm --dir apps/web run lint` passes
- [ ] Dashboard JSON is valid (no syntax errors)
- [ ] No production P0 blockers introduced

---

## Out-of-scope / Documented Gaps
- Converting frontend traces to Prometheus histogram metrics (`otel_web_*` buckets) requires adding `@opentelemetry/sdk-metrics` and an OTLP metric exporter. Not in scope unless explicitly requested.
- Removing old OTel config: nothing found to remove.

## Plan Approval Required
Reply "APPROVED" or request changes before implementation begins.
