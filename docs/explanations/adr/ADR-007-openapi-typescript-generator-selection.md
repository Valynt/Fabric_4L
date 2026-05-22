---
title: "ADR-007: OpenAPI TypeScript Generator Selection"
category: "explanations"
audience: "advanced"
last-reviewed: "2026-05-05"
freshness: "current"
related: ["../../reference/layer1-ingestion-api", "../../deployment/ci-cd"]
---

# ADR-007: OpenAPI TypeScript Generator Selection

**Status:** ✅ Accepted

**Date:** 2026-05-05

**Deciders:** Architecture Team, Frontend Platform Team

---

## Context

Fabric_4L exposes six layered REST APIs (L1–L6) plus a Signals service. Each layer maintains an OpenAPI 3.1 specification under `contracts/openapi/`. The frontend (apps/web) consumes these APIs and requires TypeScript DTOs that:

1. Stay synchronized with backend schema changes.
2. Support OpenAPI 3.1 features (e.g., `anyOf`, `oneOf`, nullable unions).
3. Are deterministic so CI can detect stale generated artifacts.
4. Work with our React Query data layer without adding heavy runtime overhead.
5. Can be generated reproducibly in CI and locally.

We evaluated four candidate generators against these criteria.

## Decision

We will standardize on **openapi-typescript** (v7.x) for Sprint 2.

## Alternatives Evaluated

### 1. openapi-typescript (Selected)

**Pros:**
- Native OpenAPI 3.1 support (the spec version we already use).
- Generates pure TypeScript types with zero runtime overhead.
- Deterministic output: same input always produces identical output (verified).
- Fast: generates ~400 KB L3 spec in <2 seconds.
- Well-maintained by the OpenAPI Initiative ecosystem; used by GitHub, Stripe, and Supabase.
- Integrates cleanly with `openapi-fetch` if we later want a typed fetch client.
- CLI and programmatic API both available.

**Cons:**
- No built-in React Query hook generation (we layer React Query manually in `src/hooks/`).
- No built-in runtime validation; types are compile-time only.

**Verdict:** Best fit. We already use it successfully for L1–L6 + Signals. The lack of built-in React Query generation is acceptable because our hook layer enforces custom caching, error normalization, and domain mapping that generic generators cannot produce.

### 2. Hey API (formerly @hey-api/openapi-ts)

**Pros:**
- Generates typed fetch clients (axios/fetch) out of the box.
- Optional React Query plugin available.
- Plugin architecture allows custom output.

**Cons:**
- React Query plugin adds opinionated hook shapes that conflict with our standardized `useApiShared` patterns (error normalization, retry config, stale times).
- Output is less stable between minor versions; diff noise in PRs observed during evaluation.
- Larger bundle size due to generated client wrappers.
- OpenAPI 3.1 support is newer and less battle-tested than openapi-typescript.

**Verdict:** Rejected. The React Query plugin does not align with our custom hook conventions, and output stability is inferior.

### 3. Orval

**Pros:**
- Mature React Query / SWR / Vue Query plugin ecosystem.
- Generates MSW mocks automatically (useful for testing).
- Good community adoption.

**Cons:**
- React Query output is heavily opinionated: generates one hook per operation with hard-coded query keys and caching.
- Our query key factory (`queryKeys.ts`) and shared API config (`useApiShared.ts`) would be bypassed or duplicated.
- Mock generation is attractive but our MSW handlers need custom domain logic that auto-generated mocks cannot satisfy.
- OpenAPI 3.1 support requires experimental flags.

**Verdict:** Rejected. Too opinionated for our architecture; would force us to abandon established hook patterns.

### 4. openapi-zod-client

**Pros:**
- Generates Zod schemas alongside TypeScript types, enabling runtime validation.
- Could replace our hand-written API validation schemas.

**Cons:**
- Adds runtime bundle cost (Zod is ~10 KB gzipped).
- OpenAPI 3.1 support is partial; complex `anyOf` unions fail during generation.
- Slower generation due to Zod schema construction.
- We already have lightweight AJV-based contract tests (`src/api/__tests__/contract/`) that catch drift without runtime overhead.

**Verdict:** Rejected for Sprint 2. May be re-evaluated in a future sprint if runtime validation becomes a higher priority, but current AJV contract tests provide sufficient safety.

## Comparison Matrix

| Criteria | openapi-typescript | Hey API | Orval | openapi-zod-client |
|---|---|---|---|---|
| OpenAPI 3.1 support | ✅ Excellent | ⚠️ Good | ⚠️ Experimental | ❌ Partial |
| Type quality | ✅ Excellent | ✅ Good | ✅ Good | ✅ Good |
| React Query support | ❌ None (manual) | ✅ Plugin | ✅ Plugin | ❌ None |
| Runtime validation | ❌ None | ❌ None | ❌ None | ✅ Zod |
| Deterministic output | ✅ Yes | ⚠️ Minor drift | ✅ Yes | ✅ Yes |
| Maintenance risk | ✅ Low | ⚠️ Medium | ⚠️ Medium | ⚠️ Medium |
| Bundle overhead | ✅ Zero | ⚠️ Small | ⚠️ Small | ❌ ~10 KB |
| CI reproducibility | ✅ Yes | ⚠️ Fragile | ✅ Yes | ✅ Yes |

## Consequences

### Positive
- **Zero bundle overhead**: Only TypeScript types are emitted; they erase at compile time.
- **Fast CI**: Generation completes in <10 seconds for all six layers.
- **Stable diffs**: Deterministic output means PR diffs show only meaningful schema changes.
- **Future-compatible**: Can adopt `openapi-fetch` later without regenerating types.

### Negative
- **Manual React Query hooks**: We must continue writing `useQuery`/`useMutation` hooks by hand. This is mitigated by our established `useApiShared` patterns.
- **No runtime validation**: Type safety is compile-time only. Mitigated by contract tests and future ADR if needed.

## Migration Notes

1. Generation script lives at `apps/web/scripts/generate-api-types.ts`.
2. Output directories: `apps/web/src/api/generated/l1/` … `l6/`.
3. Root command: `pnpm generate:api` (runs from monorepo root).
4. CI freshness check runs `pnpm generate:api` and fails on `git diff`.

## Related Decisions

- ADR-002: Six-Layer Architecture (defines why we have six OpenAPI specs).
- CONTRACT.md §2.3: Type Synchronization Contract (mandates generated types stay in sync).
