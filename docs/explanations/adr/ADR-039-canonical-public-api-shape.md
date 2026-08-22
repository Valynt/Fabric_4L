<!-- ADR-039: Canonical Public API Shape and Route Contract -->

# ADR-039: Canonical Public API Shape and Route Contract

**Status:** Accepted
**Date:** 2026-07-29
**Deciders:** Platform Architecture Committee
**Reviewers:** Platform Engineering, Frontend Engineering, Security Team

---

## Context

The Fabric_4L repository currently exposes **four materially different external routing schemes** (A-01, Critical):

| Surface                                               | Route Pattern                                                                                             | Target                      |
| ----------------------------------------------------- | --------------------------------------------------------------------------------------------------------- | --------------------------- |
| Frontend API client (`apps/web/src/lib/apiConfig.ts`) | `/api/v1/{ingest,extract,graph,agents,truths,benchmarks}/*`                                               | Layer-prefixed segments     |
| Vite dev proxy (`apps/web/vite.config.ts`)            | `/api/v1/*` → gateway (`/v1`)                                                                             | Strips `/api/v1` only       |
| K8s NGINX ingress (`k8s/routing/nginx/ingress.yaml`)  | `/layer1`–`/layer6` → layer services directly                                                             | No prefix rewrite           |
| Unified API gateway (`services/api/app/main.py`)      | `/v1/accounts/...`, `/v1/hypotheses/...`, `/v1/evidence/...`, `/v1/calculator/...`, `/v1/value-cases/...` | Domain routes under gateway |

**Consequences:**

- A route passing frontend tests can fail in dev, staging, or production depending on proxy configuration
- No single source of truth for the public API contract
- Browser code must know layer names (`agents`, `graph`, `truths`) — layer names are implementation details, not product-domain URLs
- Gateway (`services/api`) duplicates Layer 4 routes instead of delegating

The route contract registry (`contracts/route-contracts.json`) exists but only covers `/v1/*` patterns. Account-scoped sub-routes (`/v1/accounts/{account_id}/hypotheses*`, etc.) were missing and have been added.

## Decision

### 1. Single Public Host, Single Route Contract

**Canonical browser API base:** `/api/v1/` on the public application host.
The edge rewrites that prefix to `/v1/` on the **unified API gateway**
(`services/api`).

All browser and external API traffic enters through the gateway. The gateway is
the sole public API backend; `/` on the same host is the frontend fallback.

### 2. Public Route Shape — Product-Domain, Not Layer-Prefixed

| Product Domain             | Canonical Public Route                                              |
| -------------------------- | ------------------------------------------------------------------- |
| Accounts & Identity        | `/v1/accounts*`, `/v1/auth*`                                        |
| Sources & Ingestion        | `/v1/sources*`, `/v1/ingestion*`                                    |
| Intelligence & Extraction  | `/v1/intelligence*`, `/v1/extractions*`                             |
| Hypotheses & Reasoning     | `/v1/hypotheses*`, `/v1/workflows*`                                 |
| Value Cases & ROI          | `/v1/value-cases*`, `/v1/calculator*`, `/v1/roi*`                   |
| Evidence & Signals         | `/v1/evidence*`, `/v1/signals*`                                     |
| Ground Truth & Validation  | `/v1/truths*`                                                       |
| Benchmarks & Comparison    | `/v1/benchmarks*`                                                   |
| Governance & Reviews       | `/v1/governance*`, `/v1/reviews*`                                   |
| Platform Config & Internal | `/v1/tenant*`, `/v1/privacy*`, `/v1/billing*`, `/v1/subscriptions*` |

**Layer names (`layer1`, `layer2`, `agents`, `graph`, `truths`) do not appear in public URLs.** They are internal implementation details.

### 3. Gateway Delegation — Not Duplication

The gateway **delegates** to owning services via internal service-to-service calls:

| Public Route                            | Gateway Delegates To (Internal)                                  |
| --------------------------------------- | ---------------------------------------------------------------- |
| `/v1/hypotheses*`                       | `layer4-agents` `/v1/hypotheses*`                                |
| `/v1/accounts*`                         | `layer4-agents` `/v1/accounts*` (CRM sync) + gateway CRUD        |
| `/v1/value-cases*`                      | `layer4-agents` `/v1/value-cases*` (if added) or gateway compute |
| `/v1/benchmarks*`                       | `layer6-benchmarks` `/v1/benchmarks*`                            |
| `/v1/truths*`                           | `layer5-ground-truth` `/api/v1/truths*`                          |
| `/v1/intelligence*`, `/v1/extractions*` | `layer2-extraction` `/v1/extract*`                               |
| `/v1/sources*`, `/v1/ingestion*`        | `layer1-ingestion` `/api/v1/ingestion*`                          |

**Gateway must not implement its own hypothesis generation, ROI calculation, evidence extraction, or value-case generation logic.** It may provide read models, projections, and aggregation — explicitly labeled as such.

### 4. Route Contract Registry is Authoritative

`contracts/route-contracts.json` is the **single source of truth** for route ownership. It is enforced by `scripts/ci/router_contract_gate.py` in CI.

All public routes **must** have an entry in the registry with:

- `path` (fnmatch pattern)
- `method`
- `owner` (service name: `api-gateway`, `layer4-agents`, `layer1-ingestion`, etc.)

The registry already includes the account-scoped patterns added in this change:

- `/v1/accounts/{account_id}/hypotheses*`
- `/v1/accounts/{account_id}/evidence*`
- `/v1/accounts/{account_id}/scenarios*`
- `/v1/accounts/{account_id}/calculator*`
- `/v1/accounts/{account_id}/roi*`
- `/v1/accounts/{account_id}/value-cases*`

### 5. Frontend Generates Routes from Contract

Frontend API client (`apps/web/src/api/typedClient.ts`) **must** derive its endpoint URLs from the ratified route contract (via generated OpenAPI or a shared route manifest), not from hardcoded layer prefixes.

`apps/web/src/lib/apiConfig.ts` layer prefixes (`L1_PREFIX=/ingest`, `L4_PREFIX=/agents`, etc.) are **deprecated** and will be replaced by a single gateway base URL.

### 6. K8s Ingress Routes to Gateway, Not Direct to Layers

Every supported production routing mode routes external `/api/v1/*` to the
`api-gateway` service on port 8000 and rewrites the prefix to `/v1/*`. The API
rule precedes the `/` frontend fallback on the same application host.

Direct public `/layerN` paths are prohibited. L1–L6 Services remain internal
`ClusterIP` backends and are reachable only through approved in-cluster paths.

### 7. Vite Dev Proxy Aligns with Gateway

`apps/web/vite.config.ts` proxy configuration:

- `/api/v1/*` → `VITE_PROXY_API_GATEWAY_URL` (rewrites `/api/v1` → `/v1`)
- Debug direct-layer proxies (`VITE_PROXY_DEBUG_DIRECT_LAYERS`) are **development-only** and must not be used as the canonical path.

## Alternatives Considered

| Alternative                                                | Why Rejected                                                                                                         |
| ---------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| Keep layer-prefixed frontend routes (`/api/v1/agents/...`) | Leaks implementation details; couples UI to internal architecture; requires proxy rewrite that varies by environment |
| Direct browser-to-layer via K8s ingress `/layerN`          | Bypasses gateway auth, quotas, aggregation, idempotency; no single contract; security surface explosion              |
| Multiple public hosts (one per layer)                      | Same problems as above; operational overhead; no unified auth/session                                                |

## Consequences

### Positive

- **One canonical public API** — browser, mobile, CLI, and partners all use the same contract
- **Gateway owns external concerns** — auth, quotas, idempotency, aggregation, versioning
- **Layers own domain logic** — no duplication of hypothesis generation, ROI, evidence extraction
- **Route contract gate** prevents drift — CI fails if a route is added without registry entry
- **Frontend decoupled from layer topology** — layer renames/decompositions don't break UI

### Negative

- **Gateway becomes a critical path** — must be highly available, low latency
- **Delegation latency** — one extra network hop for delegated calls (mitigated: same VPC, connection pooling)
- **Migration effort** — frontend, K8s, dev proxy, tests must align

## Compliance and Migration

### Migration Owner

Platform Engineering + Frontend Engineering

### Phased Migration

1. **Phase 0 (this ADR):** Ratify contract, update route registry, deprecate layer prefixes in frontend config
2. **Phase 1:** Route external `/api/v1/*` to gateway `/v1/*`; remove all public `/layerN` paths
3. **Phase 2:** Update Vite dev proxy to only use gateway; remove debug direct-layer proxies
4. **Phase 3:** Gateway implements delegation clients for all public routes; remove gateway-local implementations of hypothesis/ROI/evidence/value-case generation
5. **Phase 4:** Frontend regenerates API client from gateway OpenAPI; remove `apiConfig.ts` layer prefixes
6. **Phase 5:** Archive `/layerN` ingress paths; verify all environments use single contract

### Enforcement Mechanism

- **CI:** `router_contract_gate.py` validates all registered routes exist in OpenAPI and vice versa
- **Static analysis:** Frontend build fails if hardcoded layer prefixes detected in API calls
- **Contract test:** Gateway delegation integration tests verify each public route reaches correct layer

### Rollback Strategy

- Vite proxy and K8s ingress can be reverted independently
- Gateway delegation can be toggled per-route via feature flag
- Facade routes in gateway preserve old paths during transition

## Related Decisions

- ADR-032: UI Route/State Progression Contract Ratification (frontend routing)
- ADR-028: Tenant Context Propagation Contract (gateway context handling)
- `contracts/route-contracts.json` (authoritative registry)
- `scripts/ci/router_contract_gate.py` (enforcement)

---

**Last Updated:** 2026-07-29
