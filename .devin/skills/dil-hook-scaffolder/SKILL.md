---
skill_id: dil-hook-scaffolder
name: dil-hook-scaffolder
version: 1.0.0
description: Scaffold TanStack Query hooks for DIL (Data Intelligence Layer) backend services that have zero frontend integration. Use when building frontend hooks for products, evidence, competitive-intel, roi, enrichment, value-hypotheses, narratives, or intelligence endpoints. Addresses 52 unintegrated backend endpoints identified in FRONTEND_AUDIT_REPORT.md.
side_effects: write
timeout_ms: 30000
required_context:
  - project_graph
allowed_agents:
  - "*"
---

# DIL Hook Scaffolder

Creates production-ready TanStack Query hooks for DIL backend services following `useAccounts.ts` patterns.

## When to Use

- You are asked to "wire up" a DIL service to the frontend
- A workspace tab needs to connect to its dedicated backend service
- FRONTEND_AUDIT_REPORT.md Part 2 services need integration

## Service Registry

| Service | Layer | Prefix | Endpoints | Route File |
|---------|-------|--------|-----------|------------|
| Product Portfolio | L3 | `/v1/products` | 8 | `layer3-knowledge/src/api/routes/products.py` |
| Evidence Library | L3 | `/v1/evidence` | 7 | `layer3-knowledge/src/api/routes/evidence.py` |
| Competitive Intel | L3 | `/v1/competitive-intel` | 10 | `layer3-knowledge/src/api/routes/competitive_intel.py` |
| ROI Calculator | L3 | `/v1/roi` | 8 | `layer3-knowledge/src/api/routes/roi.py` |
| Enrichment Pipeline | L4 | `/v1/enrichment` | 4 | `layer4-agents/src/api/routes/enrichment.py` |
| Value Hypothesis Engine | L4 | `/v1/value-hypotheses` | 6 | `layer4-agents/src/api/routes/value_hypotheses.py` |
| Narrative Builder | L4 | `/v1/narratives` | 5 | `layer4-agents/src/api/routes/narratives.py` |
| Intelligence Orchestrator | L4 | `/v1/intelligence` | 4 | `layer4-agents/src/api/routes/intelligence.py` |

## Workflow Steps

### Step 1: Read Backend Route File

Read the backend route file to extract endpoints, request/response Pydantic schemas.

Example for products:
```
Read: services/layer3-knowledge/src/api/routes/products.py
Extract: GET /v1/products, GET /v1/products/{id}, POST /v1/products, ...
```

### Step 2: Generate Types

Create TypeScript interfaces matching backend Pydantic schemas. Place inline in hook file (top, like `useAccounts.ts` lines 6-70).

Use `export interface` not `export type`. Match backend field names (snake_case). Optional fields use `?:`.

### Step 3: Add Query Keys

Add to `frontend/client/src/hooks/queryKeys.ts`:

```typescript
// DIL — {ServiceName}
{serviceName}: {
  all: ["{service-name}"] as const,
  list: (filters: {ServiceName}ListFilters) =>
    ["{service-name}", "list", stableKey(filters)] as const,
  detail: (id: string) => ["{service-name}", "detail", id] as const,
},
```

Also add filter type import: `import type { {ServiceName}ListFilters } from "./use{ServiceName}";`

### Step 4: Generate Hook File

Create `frontend/client/src/hooks/use{ServiceName}.ts`:

```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/api/client';
import { QK } from './queryKeys';
import { withApiError, BaseApiError, STALE_TIME, RETRY_CONFIG } from './useApiShared';

// Types
export interface {Entity} { /* from backend schema */ }
export interface {Entity}ListFilters { /* ... */ }

// Queries
export function use{Entity}List(filters: {Entity}ListFilters = {}) {
  return useQuery({
    queryKey: QK.{serviceName}.list(filters),
    queryFn: () => withApiError(
      apiClient.get('/api/v1/{endpoint}', { params: filters }),
      '{entity} list'
    ),
    staleTime: STALE_TIME.list,
    retry: RETRY_CONFIG.maxRetries,
    retryDelay: RETRY_CONFIG.retryDelay,
  });
}

export function use{Entity}Detail(id: string | undefined) {
  return useQuery({
    queryKey: QK.{serviceName}.detail(id!),
    queryFn: () => withApiError(
      apiClient.get(`/api/v1/{endpoint}/${id}`),
      '{entity} detail'
    ),
    enabled: !!id,
    staleTime: STALE_TIME.detail,
    retry: RETRY_CONFIG.maxRetries,
    retryDelay: RETRY_CONFIG.retryDelay,
  });
}

// Mutations
export function useCreate{Entity}() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: Create{Entity}Request) =>
      withApiError(apiClient.post('/api/v1/{endpoint}', data), 'create {entity}'),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QK.{serviceName}.all });
    },
    onError: (error: BaseApiError) => {
      console.error('[use{ServiceName}] Create failed:', error.message);
    },
  });
}
```

### Step 5: Export from Index

Add to `frontend/client/src/hooks/index.ts`: `export * from './use{ServiceName}';`

### Step 6: Verify

1. TypeScript: `cd frontend && pnpm tsc --noEmit`
2. Tests: `cd frontend && pnpm test --run`

## Pattern References

- `useAccounts.ts` (316 lines) — Full CRUD + sync + activity
- `useWorkflows.ts` — List + detail + mutations + SSE streaming
- `useFormulas.ts` — CRUD + governance approval flow

## Type Mapping

| Python | JSON Schema |
|--------|-------------|
| `str` | `"string"` |
| `int` | `"integer"` |
| `float` | `"number"` |
| `bool` | `"boolean"` |
| `list[T]` | `{"type": "array", "items": {"type": "T"}}` |
| `Optional[T]` | NOT in `required` array |
