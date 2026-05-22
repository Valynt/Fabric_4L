# Generated DTO Import Boundaries

**Status:** Policy (enforced by ESLint in Sprint 11)

**Applies to:** `apps/web/src/api/generated/**`

---

## Purpose

Generated TypeScript DTOs are compile-time contracts derived from backend OpenAPI specifications. They are **not** UI components, domain models, or presentation-layer utilities. Importing them into the wrong layers creates:

- **Tight coupling** between backend schema churn and UI code.
- **Leaky abstractions** where OpenAPI field names (snake_case, nullable unions) propagate into JSX and component props.
- **Broken builds** when a schema rename forces changes across dozens of unrelated components.

This document defines where generated types may and may not be imported.

---

## Allowed Locations

### 1. API Adapters (`src/api/**`)

The API client layer is the primary consumer of generated types. It maps HTTP operations to typed requests/responses.

```typescript
// ✅ CORRECT: API adapter uses generated operation types
import type { operations } from '@/api/generated/l3';

export async function listPacks(): Promise<
  operations['list_packs_v1_packs_get']['responses'][200]['content']['application/json']
> {
  // ...
}
```

### 2. Feature API Modules (`src/features/**/api/**`)

Feature-scoped API modules may import generated types when they encapsulate layer-specific calls.

```typescript
// ✅ CORRECT: Feature API module
import type { components } from '@/api/generated/l4';

export type WorkflowDto = components['schemas']['WorkflowDefinition'];
```

### 3. Feature Adapters (`src/features/**/adapters/**`)

Adapters translate generated DTOs into domain models. Generated types are allowed here because this is the **boundary** where backend schema meets frontend domain.

```typescript
// ✅ CORRECT: Adapter normalizes DTO to domain model
import type { components } from '@/api/generated/l1';

export function normalizeTarget(
  dto: components['schemas']['ScrapingTargetDetail']
): DataSource {
  return {
    id: dto.id,
    name: dto.name,
    status: deriveConnectionStatus(dto.status),
  };
}
```

### 4. Domain Mappers (`src/features/**/domain/**/*.mapper.ts`)

Explicit mapper files within the domain layer may reference generated types when the mapping logic is complex enough to warrant a dedicated file.

```typescript
// ✅ CORRECT: Dedicated mapper file
import type { components } from '@/api/generated/l2';
import type { ExtractionJob } from './extractionJob.model';

export function mapJobDtoToModel(
  dto: components['schemas']['ScrapingJobDetail']
): ExtractionJob {
  // ...
}
```

---

## Disallowed Locations

### 1. Components (`src/components/**`)

Components must receive domain models or prop interfaces, not raw OpenAPI schemas.

```typescript
// ❌ INCORRECT: Component depends on generated schema
import type { components } from '@/api/generated/l3';

interface Props {
  entity: components['schemas']['KnowledgeGraphEntity']; // Don't do this
}
```

**Fix:** Define a component-specific prop interface or use a domain model.

```typescript
// ✅ CORRECT: Component uses domain model
import type { GraphNode } from '@/features/graph/domain/graphNode.model';

interface Props {
  entity: GraphNode;
}
```

### 2. Pages (`src/pages/**`)

Pages orchestrate features. They should not know about OpenAPI schema details.

```typescript
// ❌ INCORRECT: Page imports generated type
import type { components } from '@/api/generated/l5';

function GroundTruthPage() {
  const [item, setItem] = useState<components['schemas']['GroundTruthEntry']>();
}
```

**Fix:** Import the domain model from the feature module.

```typescript
// ✅ CORRECT: Page uses domain model
import type { GroundTruthEntry } from '@/features/groundTruth/domain/groundTruthEntry.model';

function GroundTruthPage() {
  const [item, setItem] = useState<GroundTruthEntry>();
}
```

### 3. Feature Components (`src/features/**/components/**`)

Same rule as `src/components/**`. Feature components are presentation layer.

```typescript
// ❌ INCORRECT: Feature component imports DTO
import type { components } from '@/api/generated/l4';

export function WorkflowCard({ workflow }: { workflow: components['schemas']['WorkflowSummary'] }) {
  // ...
}
```

### 4. Feature Screens (`src/features/**/screens/**`)

Screens compose components. They must remain agnostic to API schema details.

---

## Quick Reference

| Directory Pattern | Generated DTO Import | Reason |
|---|---|---|
| `src/api/**` | ✅ Allowed | API layer is the contract boundary |
| `src/features/**/api/**` | ✅ Allowed | Feature-scoped API modules |
| `src/features/**/adapters/**` | ✅ Allowed | DTO → domain translation |
| `src/features/**/domain/**/*.mapper.ts` | ✅ Allowed | Explicit mapper files |
| `src/components/**` | ❌ Disallowed | Presentation layer |
| `src/pages/**` | ❌ Disallowed | Page orchestration layer |
| `src/features/**/components/**` | ❌ Disallowed | Feature presentation layer |
| `src/features/**/screens/**` | ❌ Disallowed | Screen composition layer |
| `src/hooks/**` | ⚠️ Prefer domain types | Hooks should use domain models; exception for thin API wrappers |

---

## Enforcement

- **Sprint 2 (Now):** Policy documented; code review enforcement.
- **Sprint 11:** ESLint rule `fabric-contracts/no-generated-dto-in-ui` will enforce automatically.

## Related

- [ADR-007: OpenAPI TypeScript Generator Selection](../explanations/adr/ADR-007-openapi-typescript-generator-selection.md)
- `apps/web/src/api/generated/` — Generated type output
- `apps/web/scripts/generate-api-types.ts` — Generation pipeline
