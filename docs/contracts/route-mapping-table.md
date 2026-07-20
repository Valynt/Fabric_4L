# Route Mapping & Alias Audit

> **Audit note (2026-07-18):** The mismatch registry below contains stale entries. R-04 (`GET /workflows?type=business_case` "not in OpenAPI") and R-05 (`POST /workflows/{id}/archive` "not found in backend code") have been resolved in the current Layer 4 code and OpenAPI spec. The Layer 5 double-prefix analysis is also outdated because the frontend now routes L5 calls through the Layer 4 `/v1/ground-truth/*` proxy. Review and prune the resolved rows.

> Compare frontend route expectations against backend canonical paths. Flag mismatches, missing aliases, and gateway rewrite requirements.

---

## Audit Methodology

1. **Frontend route** = path segment sent by `apiClient` (includes layer prefix from `LAYER_PREFIXES`).
2. **Dev proxy rewrite** = Vite `proxy` config in `frontend/vite.config.ts`.
3. **Backend canonical** = actual FastAPI router path in layer source code or OpenAPI spec.
4. **Gateway rewrite** = K8s Gateway API / Nginx config in `k8s/routing/`.
5. **Current result** = `working` if request reaches intended backend handler; `broken` if 404 or wrong handler; `partial` if path works but shape differs.

---

## Layer 1 — Ingestion

| Frontend Route | Dev Proxy Rewrite | Backend Route | Gateway Route | Rewrite Needed? | Current Result | Layer Owner | Notes |
|----------------|-------------------|---------------|---------------|-----------------|----------------|-------------|-------|
| `/api/v1/ingest/jobs` | `/api/v1/ingest/*` → `/api/v1/ingestion/*` | `/api/v1/ingestion/jobs` | `/layer1/*` | No | `working` | L1 | Clean mapping through dev proxy. |
| `/api/v1/ingest/targets` | `/api/v1/ingest/*` → `/api/v1/ingestion/*` | `/api/v1/ingestion/targets` | `/layer1/*` | No | `working` | L1 | — |
| `/api/v1/ingest/compliance/logs` | `/api/v1/ingest/*` → `/api/v1/ingestion/*` | `/api/v1/ingestion/compliance/logs` | `/layer1/*` | No | `working` | L1 | — |

---

## Layer 2 — Extraction

| Frontend Route | Dev Proxy Rewrite | Backend Route | Gateway Route | Rewrite Needed? | Current Result | Layer Owner | Notes |
|----------------|-------------------|---------------|---------------|-----------------|----------------|-------------|-------|
| `/api/v1/extract/status/{id}` | Strip `/api/v1/extract` | `/v1/extract/status/{job_id}` | `/layer2/*` | No | `working` | L2 | Frontend must use canonical route. Legacy `/jobs/{id}` alias removed. |
| `/api/v1/extract` | Strip `/api/v1/extract` | `/v1/extract` | `/layer2/*` | No | `working` | L2 | — |
| `/api/v1/extract/signals` | Strip `/api/v1/extract` | `/v1/extract/signals` | `/layer2/*` | No | `working` | L2 | — |

**✅ Resolved:**
```
Frontend:  GET /api/v1/extract/status/123
Proxy:     → GET localhost:8002/extract/status/123
Backend:   GET /v1/extract/status/123
Result:    200 OK
```

**Migration note:** The legacy backend alias `/v1/jobs/{job_id}` and the L3 alias `/v1/ingest/{id}/status` have been removed. Frontend must use canonical routes.

---

## Layer 3 — Knowledge Graph

| Frontend Route | Dev Proxy Rewrite | Backend Route | Gateway Route | Rewrite Needed? | Current Result | Layer Owner | Notes |
|----------------|-------------------|---------------|---------------|-----------------|----------------|-------------|-------|
| `/api/v1/graph/query/graph` | `/api/v1/graph/*` → `/v1/*` | `/v1/query/graph` | `/layer3/*` | No | `working` | L3 | Clean mapping. |
| `/api/v1/graph/entity/{id}/context` | `/api/v1/graph/*` → `/v1/*` | `/v1/entity/{entity_id}/context` | `/layer3/*` | No | `working` | L3 | — |
| `/api/v1/graph/entity/traverse` | `/api/v1/graph/*` → `/v1/*` | `/v1/entity/traverse` | `/layer3/*` | No | `working` | L3 | — |
| `/api/v1/graph/subgraph` | `/api/v1/graph/*` → `/v1/*` | `/v1/subgraph` | `/layer3/*` | No | `working` | L3 | — |
| `/api/v1/graph/entities` | `/api/v1/graph/*` → `/v1/*` | `/v1/entities` | `/layer3/*` | No | `working` | L3 | — |
| `/api/v1/graph/formulas` | `/api/v1/graph/*` → `/v1/*` | `/v1/formulas` | `/layer3/*` | No | `working` | L3 | — |
| `/api/v1/graph/packs` | `/api/v1/graph/*` → `/v1/*` | `/v1/packs` | `/layer3/*` | No | `working` | L3 | — |
| `/api/v1/graph/valuepacks/*` | `/api/v1/graph/*` → `/v1/*` | `/v1/valuepacks/*` | `/layer3/*` | No | `working` | L3 | — |
| `/api/v1/graph/models` | `/api/v1/graph/*` → `/v1/*` | `/v1/models` | `/layer3/*` | No | `working` | L3 | — |
| `/api/v1/graph/value-trees/*` | `/api/v1/graph/*` → `/v1/*` | `/v1/value-trees/*` | `/layer3/*` | No | `working` | L3 | — |
| `/api/v1/graph/products` | `/api/v1/graph/*` → `/v1/*` | `/v1/products` | `/layer3/*` | No | `working` | L3 | — |
| `/api/v1/graph/case-studies` | `/api/v1/graph/*` → `/v1/*` | `/v1/case-studies` | `/layer3/*` | No | `partial` | L3 | Frontend evidence hooks may not call this exact path. |
| `/api/v1/graph/competitors` | `/api/v1/graph/*` → `/v1/*` | `/v1/competitors` | `/layer3/*` | No | `partial` | L3 | Frontend competitive hooks may not call this exact path. |
| `/api/v1/graph/calculate` | `/api/v1/graph/*` → `/v1/*` | `/v1/calculate` | `/layer3/*` | No | `partial` | L3 | ROI calculator routes. |

---

## Layer 4 — Agents

| Frontend Route | Dev Proxy Rewrite | Backend Route | Gateway Route | Rewrite Needed? | Current Result | Layer Owner | Notes |
|----------------|-------------------|---------------|---------------|-----------------|----------------|-------------|-------|
| `/api/v1/agents/workflows` | `/api/v1/agents/*` → `/v1/*` | `/v1/workflows` | `/layer4/*` | No | `working` | L4 | — |
| `/api/v1/agents/workflows/active` | `/api/v1/agents/*` → `/v1/*` | `/v1/workflows/active` | `/layer4/*` | No | `working` | L4 | — |
| `/api/v1/agents/workflows/{id}/events` | `/api/v1/agents/*` → `/v1/*` | `/v1/workflows/{id}/events` | `/layer4/*` | No | `working` | L4 | SSE stream. |
| `/api/v1/agents/accounts` | `/api/v1/agents/*` → `/v1/*` | `/v1/accounts` | `/layer4/*` | No | `working` | L4 | — |
| `/api/v1/agents/integrations` | `/api/v1/agents/*` → `/v1/*` | `/v1/integrations` | `/layer4/*` | No | `working` | L4 | — |
| `/api/v1/agents/tenants` | `/api/v1/agents/*` → `/v1/*` | `/v1/tenants` | `/layer4/*` | No | `working` | L4 | — |
| `/api/v1/agents/users` | `/api/v1/agents/*` → `/v1/*` | `/v1/users` | `/layer4/*` | No | `working` | L4 | — |
| `/api/v1/agents/api-keys` | `/api/v1/agents/*` → `/v1/*` | `/v1/api-keys` | `/layer4/*` | No | `working` | L4 | — |
| `/api/v1/agents/tenant/settings` | `/api/v1/agents/*` → `/v1/*` | `/v1/tenant/settings` | `/layer4/*` | No | `working` | L4 | — |
| `/api/v1/agents/v1/intelligence/*` | `/api/v1/agents/*` → `/v1/*` | `/v1/intelligence/*` | `/layer4/*` | No | `working` | L4 | Frontend path includes double `/v1` in hook: `GET l4 /v1/intelligence/...`. Proxy strips `/api/v1/agents` leaving `/v1/intelligence/...`. Clean. |
| `/api/v1/agents/v1/narratives/*` | `/api/v1/agents/*` → `/v1/*` | `/v1/narratives/*` | `/layer4/*` | No | `working` | L4 | Same double-/v1 pattern as intelligence. |
| `/api/v1/agents/billing/*` | `/api/v1/agents/*` → `/v1/*` | `/v1/billing/*` | `/layer4/*` | No | `working` | L4 | — |
| `/api/v1/agents/agent-stream/chat` | `/api/v1/agents/*` → `/v1/*` | `/v1/agent-stream/chat` | `/layer4/*` | No | `working` | L4 | — |
| `/api/v1/agents/c1/stream` | `/api/v1/agents/*` → `/v1/*` | `/v1/c1/stream` | `/layer4/*` | No | `working` | L4 | — |
| `/api/v1/agents/analysis/roi` | `/api/v1/agents/*` → `/v1/*` | `/v1/analysis/roi` | `/layer4/*` | No | `working` | L4 | — |
| `/api/v1/agents/analysis/whitespace` | `/api/v1/agents/*` → `/v1/*` | `/v1/analysis/whitespace` | `/layer4/*` | No | `working` | L4 | — |
| `/api/v1/agents/auth/*` | `/api/v1/agents/*` → `/v1/*` | `/v1/auth/*` | `/layer4/*` | No | `working` | L4 | Raw `fetch` bypasses axios but hits same proxy. |

---

## Layer 5 — Ground Truth

| Frontend Route | Dev Proxy Rewrite | Backend Route | Gateway Route | Rewrite Needed? | Current Result | Layer Owner | Notes |
|----------------|-------------------|---------------|---------------|-----------------|----------------|-------------|-------|
| `/api/v1/truths/api/v1/truths` | Strip `/api/v1/truths` | `/api/v1/truths` | `/layer5/*` | **YES** | `partial` | L5 | **Double-prefix risk.** See detailed analysis below. |
| `/api/v1/truths/api/v1/truths/{id}/audit` | Strip `/api/v1/truths` | `/api/v1/truths/{id}/audit` | `/layer5/*` | **YES** | `partial` | L5 | Same double-prefix issue. |

**🟡 Layer 5 Path Analysis:**

The frontend L5 client constructs URLs as `{baseURL}{path}` where `baseURL = {API_BASE}{L5_PREFIX}`.

Scenario A (`client/.env.example` values):
- `API_BASE=/api`, `L5_PREFIX=/v1/truths` → baseURL = `/api/v1/truths`
- Hook calls `apiClient.get('l5', '/api/v1/truths')` → full path = `/api/v1/truths/api/v1/truths`
- Vite proxy matches `/api/v1/truths` prefix → strips it → backend gets `/api/v1/truths`
- **Result:** Works, but relies on prefix matching the first occurrence only.

Scenario B (`frontend/.env.example` values):
- `API_BASE=/api/v1`, `L5_PREFIX=/truths` → baseURL = `/api/v1/truths`
- Hook calls `apiClient.get('l5', '/api/v1/truths')` → full path = `/api/v1/truths/api/v1/truths`
- Same proxy behavior.

Scenario C (fallbacks from `client.ts`):
- `API_BASE=/api`, `L5_PREFIX=/truths` → baseURL = `/api/truths`
- Hook calls `apiClient.get('l5', '/api/v1/truths')` → full path = `/api/truths/api/v1/truths`
- Vite proxy **does not match** `/api/truths` → request may 404 or hit wrong handler.

**Fix options:**
1. **Standardize env:** Use `API_BASE=/api/v1`, `L5_PREFIX=/truths` everywhere. Update hooks to call `/truths/*` instead of `/api/v1/truths/*`.
2. **Gateway rewrite:** `/api/truths/*` → `/api/v1/*` on L5 service.
3. **Frontend fix:** Remove `/api/v1` from hook paths; let baseURL carry the full prefix.

---

## Layer 6 — Benchmarks

| Frontend Route | Dev Proxy Rewrite | Backend Route | Gateway Route | Rewrite Needed? | Current Result | Layer Owner | Notes |
|----------------|-------------------|---------------|---------------|-----------------|----------------|-------------|-------|
| `/api/v1/benchmarks/v1/benchmarks` | `/api/v1/benchmarks/*` → `/v1/benchmarks/*` | `/v1/benchmarks` | `/layer6/*` | **YES** | `partial` | L6 | Similar double-prefix risk as L5. Frontend hook patterns not yet strongly defined. |

---

## Special Routes Summary

| Route Family | Frontend Alias | Backend Canonical | Gateway Match | Status |
|--------------|----------------|-------------------|---------------|--------|
| Intelligence | `/api/intelligence/*` | `/v1/intelligence/*` (L4) | `/layer4/*` | `partial` — frontend uses `/api/v1/agents/v1/intelligence/*`; no dedicated `/api/intelligence` proxy entry. |
| Value Models | `/api/value-models/*` | `/v1/models/*` (L3) | `/layer3/*` | `unknown` — no frontend hook uses this exact alias. |
| Evidence | `/api/evidence/*` | `/v1/case-studies/*` (L3) | `/layer3/*` | `unknown` — no dedicated proxy entry; frontend calls via `/api/v1/graph`. |
| Benchmarks | `/api/benchmarks/*` | `/v1/benchmarks/*` (L6) | `/layer6/*` | `partial` — double-prefix risk; no dedicated proxy entry outside `/api/v1/benchmarks`. |
| Agent Stream | `/api/agent-stream/*` | `/v1/agent-stream/*` (L4) | `/layer4/*` | `working` — routed through `/api/v1/agents` proxy. |

---

## Gateway Configuration Gap Analysis

### Current K8s Gateway API (`k8s/routing/gateway-api/httproute.yaml`)

```yaml
/layer1 → layer1-ingestion:8000
/layer2 → layer2-extraction:8000
/layer3 → layer3-knowledge:8003
/layer4 → layer4-agents:8000
/layer5 → layer5-ground-truth:8005
/layer6 → layer6-benchmarks:8006
```

**Problem:** Frontend expects `/api/v1/{layer}` paths. Gateway routes `/layerN`. There is **no documented rewrite** from `/api/*` to `/layerN/*` in the K8s Gateway API manifest. The Nginx routing config (`k8s/routing/nginx/routing-config.yaml`) is a Kustomize template with placeholders — actual rewrite rules are environment-dependent and not checked into this repo.

**Implication:** In production, some other gateway layer (cloud load balancer, CDN, or injected nginx config) must perform the `/api/v1/ingest` → `/layer1` translation. This is an **undocumented operational dependency**.

### Recommended Gateway Aliases

| Frontend Prefix | Target Service | Rewrite Rule |
|-----------------|----------------|--------------|
| `/api/v1/ingest/*` | `layer1-ingestion:8000` | `/*` → `/api/v1/ingestion/*` |
| `/api/v1/extract/*` | `layer2-extraction:8000` | `/*` → `/v1/*` |
| `/api/v1/graph/*` | `layer3-knowledge:8003` | `/*` → `/v1/*` |
| `/api/v1/agents/*` | `layer4-agents:8000` | `/*` → `/v1/*` |
| `/api/v1/truths/*` | `layer5-ground-truth:8005` | `/*` → `/api/v1/*` |
| `/api/v1/benchmarks/*` | `layer6-benchmarks:8006` | `/*` → `/v1/*` |
| `/api/v1/audit/*` | `layer4-agents:8000` | `/*` → `/v1/audit/*` |

---

## Mismatch Registry

| ID | Frontend Path | Expected Backend | Actual Backend | Impact | Proposed Fix |
|----|---------------|------------------|----------------|--------|--------------|
| R-01 | `GET l2 /jobs/{id}` | `/v1/jobs/{id}` | `/v1/extract/status/{id}` | 🔴 High — 404 | Add backend alias or update frontend. |
| R-02 | `GET l5 /api/v1/truths/*` | `/api/v1/truths/*` | Same, but double-prefix in dev | 🟡 Medium — env-dependent | Standardize env vars and hook paths. |
| R-03 | `GET l6 /api/v1/benchmarks/*` | `/v1/benchmarks/*` | Same, but double-prefix in dev | 🟡 Medium — env-dependent | Standardize env vars and hook paths. |
| R-04 | `GET l4 /workflows?type=business_case` | `/v1/workflows?type=business_case` | Route exists but not in OpenAPI | 🟡 Medium — spec drift | Update `layer4-agents.json` OpenAPI spec. |
| R-05 | `POST l4 /workflows/{id}/archive` | `/v1/workflows/{id}/archive` | Not found in backend code | 🟡 Medium — feature gap | Implement backend route or remove frontend call. |
| R-06 | Various L3 DIL routes | `/v1/products`, `/v1/case-studies`, etc. | Routes exist in backend | 🟢 Low — coverage gap | Add typed frontend hooks and tests. |
