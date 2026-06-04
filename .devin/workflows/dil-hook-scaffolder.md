---
workflow_id: dil-hook-scaffolder
name: DIL Hook Scaffolder
version: 1.0.0
description: Scaffold TanStack Query hooks for DIL (Data Intelligence Layer) backend services that have zero frontend integration. Use when building frontend hooks for products, evidence, competitive-intel, roi, enrichment, value-hypotheses, narratives, or intelligence endpoints. Addresses 52 unintegrated backend endpoints identified in FRONTEND_AUDIT_REPORT.md.
pattern: circuit-breaker
risk_level: low
---

# DIL Hook Scaffolder

Creates production-ready TanStack Query hooks for DIL backend services following the established patterns in `useAccounts.ts`, `useApiShared.ts`, and `queryKeys.ts`.

## When to Use

- You are asked to "wire up" a DIL service to the frontend
- A workspace tab needs to connect to its dedicated backend service
- The FRONTEND_AUDIT_REPORT.md Part 2 services need integration
- You need to create `useProducts`, `useEvidenceLibrary`, `useCompetitiveIntel`, `useROI`, `useEnrichment`, `useValueHypotheses`, `useNarratives`, or `useIntelligence` hooks

## Service Registry (8 services, 52 endpoints, 0% frontend coverage)

| Service | Layer | Endpoint Prefix | Endpoints | Route File |
|---------|-------|-----------------|-----------|------------|
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

Before generating the hook, read the backend route file to extract:
1. All endpoint paths and HTTP methods
2. Request body schemas (Pydantic models)
3. Response schemas (Pydantic models)
4. Query parameters and their types

For example, for the products service:
```
Read: services/layer3-knowledge/src/api/routes/products.py
Extract: GET /v1/products, GET /v1/products/{id}, POST /v1/products, ...
```

### Step 2: Generate TypeScript Types

Create types matching the backend Pydantic schemas. Place them inline in the hook file following the `useAccounts.ts` pattern:

```typescript
// Types derived from layer3-knowledge Pydantic schemas
export interface Product {
  id: string;
  tenant_id: string;
  name: string;
  // ... fields from backend ProductResponse model
}
```

**Pattern rules:**
- Types go at the top of the hook file (same as `useAccounts.ts` lines 6-70)
- Use `export interface` not `export type` for object shapes
- Match backend field names exactly (snake_case) — the API client does not transform
- Optional fields use `?:` syntax

### Step 3: Add Query Keys to queryKeys.ts

Add a new namespace to the `QK` object in `apps/web/src/hooks/queryKeys.ts`:

```typescript
// DIL — {ServiceName}
{serviceName}: {
  all: ["{service-name}"] as const,
  list: (filters: {ServiceName}ListFilters) =>
    ["{service-name}", "list", stableKey(filters)] as const,
  detail: (id: string) => ["{service-name}", "detail", id] as const,
  // Add service-specific keys as needed
},
```

Also add the filter type import at the top of `queryKeys.ts`:
```typescript
import type { {ServiceName}ListFilters } from "./use{ServiceName}";
```

### Step 4: Generate the Hook File

Create `apps/web/src/hooks/use{ServiceName}.ts` following this template:

```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/api/client';
import { QK } from './queryKeys';
import { withApiError, BaseApiError, STALE_TIME, RETRY_CONFIG } from './useApiShared';

// ── Types ────────────────────────────────────────────────────────────────────
// (Generated from backend Pydantic models in Step 2)

export interface {Entity} { /* ... */ }
export interface {Entity}ListFilters { /* ... */ }

// ── Queries ──────────────────────────────────────────────────────────────────

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

// ── Mutations ────────────────────────────────────────────────────────────────

export function useCreate{Entity}() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: Create{Entity}Request) =>
      withApiError(
        apiClient.post('/api/v1/{endpoint}', data),
        'create {entity}'
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QK.{serviceName}.all });
    },
    onError: (error: BaseApiError) => {
      console.error('[use{ServiceName}] Create failed:', error.message);
    },
  });
}
```

### Step 5: Export from Hook Index

Add the new hook to `apps/web/src/hooks/index.ts`:
```typescript
export * from './use{ServiceName}';
```

### Step 6: Verify

1. Check TypeScript compilation: `cd frontend && pnpm tsc --noEmit`
2. Run existing tests to ensure no regressions: `cd frontend && pnpm test --run`
3. Verify the hook file follows the same patterns as `useAccounts.ts`

## Canonical Hook Examples (for reference)

When scaffolding, use these existing hooks as pattern references:
- **`useAccounts.ts`** (316 lines) — Full CRUD + sync + activity: the gold standard
- **`useWorkflows.ts`** (316 lines) — List + detail + mutations + SSE streaming
- **`useFormulas.ts`** (284 lines) — CRUD + governance approval flow
- **`useProducts.ts`** (273 lines) — Already partially scaffolded with types

## Cache Invalidation Rules

Follow these cross-service invalidation rules when generating mutations:

| Mutation | Invalidate |
|----------|------------|
| Enrich account | `QK.accounts.detail(id)`, `QK.enrichment.all`, `QK.intelligence.all` |
| Generate hypothesis | `QK.valueHypotheses.all`, `QK.intelligence.all` |
| Calculate ROI | `QK.roi.all`, `QK.intelligence.all` |
| Generate narrative | `QK.narratives.all`, `QK.intelligence.all` |
| Update competitive intel | `QK.competitiveIntel.all`, `QK.intelligence.all` |

## Edge Cases

- **API prefix:** All DIL endpoints use `/api/v1/` prefix via the `apiClient` — do not double-prefix
- **Tenant context:** The API client injects tenant headers automatically — hooks should NOT pass `tenant_id`
- **Existing partial hooks:** `useProducts.ts`, `useEvidence.ts`, `useCompetitiveIntel.ts`, `useROICalculator.ts`, `useHypotheses.ts`, `useNarratives.ts` may already exist with partial implementations — read them first and extend rather than recreate
- **Filter types:** Export filter interfaces so `queryKeys.ts` can import them without circular dependencies
## Required State JSON

Every workflow MUST maintain and update an explicit state object. Agents read this state at the start of every turn.

```json
{
  "stage": "inspection|analysis|execution|validation|reporting",
  "agent_id": "dil-hook-scaffolder-001",
  "files_touched": [],
  "tests_run": [],
  "decisions_made": [],
  "blocked_by": null,
  "retry_count": 0,
  "circuit_breaker": {
    "tripped": false,
    "reason": null,
    "escalation_path": null
  }
}
```

## Circuit Breaker Configuration

```yaml
circuit_breaker:
  max_tool_errors: 3
  max_self_correction_loops: 2
  action_on_trip: halt_and_escalate
  escalation_path: "log_and_notify"
```

## Completion Checklist

- [ ] State JSON updated with current stage, touched files, tests, and decisions.
- [ ] Circuit breaker evaluated before retrying after tool errors or self-correction loops.
- [ ] Relevant validation commands run and recorded in the workflow state.
- [ ] No security, tenant-isolation, contract, governance, or frontend-design assertions weakened.
