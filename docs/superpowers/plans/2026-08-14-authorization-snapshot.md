# Authorization Snapshot Implementation Plan

> **For agentic workers:** Implement inline with test-driven development; the user requires one autonomous pass and one focused final commit.

**Goal:** Make `GET /v1/authz/snapshot` the only frontend source of authorization grants.

**Architecture:** Layer 4 resolves a tenant-bound snapshot from authenticated `RequestContext` and the tenant repository. A strict frontend parser and TanStack Query hook expose a fail-closed resolution union; pure evaluators produce separate route decisions. The route guard consumes only those decisions, while the tier store remains display-only.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy, React, TypeScript, TanStack Query, Vitest, pytest, OpenAPI.

## Global Constraints

- Preserve unrelated work and tenant isolation.
- Roles and tiers never synthesize grants.
- Only a current `verified` snapshot exposes permissions, entitlements, membership, or account scope.
- Initial failure is `denied`; expiration and failed renewal are `expired`.
- Use pnpm 10.18.1 and Python 3.11+.

---

### Task 1: Backend trust boundary

**Files:** create `services/layer4-agents/src/layer4_agents/api/routes/authz.py`; modify router registration; test `services/layer4-agents/tests/test_authz_snapshot_route.py`.

- [ ] Add failing endpoint tests for success, tenant mismatch, incomplete/expired context, authoritative grants, registration, and schema.
- [ ] Run the test and confirm the endpoint is absent.
- [ ] Implement the authenticated route, deterministic normalization, tenant lookup, and fail-closed expiry validation.
- [ ] Run the backend tests and lint changed Python.

### Task 2: Frontend snapshot domain

**Files:** create `apps/web/src/auth/authorizationSnapshot.ts`, provider hook, and focused tests.

- [ ] Add failing parser/evaluator tests for malformed, mismatched, expired, unknown-role, grant, membership, account, and feature-flag behavior.
- [ ] Implement strict parsing and discriminated resolution/decision unions.
- [ ] Add fake-timer provider tests for expiration, one refresh, failed initial fetch, and tenant changes.
- [ ] Implement a TanStack Query snapshot hook with exact-tenant keys and no previous-data reuse.

### Task 3: Consumer migration

**Files:** modify permission/entitlement/account/membership hooks, `UnifiedRouteGuard.tsx`, route policy types/definitions, and tier store; update their tests.

- [ ] Add failing permission, guard, and tier compatibility tests.
- [ ] Make permissions and route requirements snapshot-only; remove persisted-tier authorization and independent authorization fetches.
- [ ] Preserve sign-in return URLs and render loading, denial, and expired states in place.
- [ ] Confirm feature flags only restrict an already-allowed snapshot decision.

### Task 4: Contracts, docs, and verification

**Files:** regenerate `contracts/openapi/layer4-agents.json` and `apps/web/src/api/generated/l4/index.ts`; create `docs/explanation/authorization-snapshot.md`; update relevant contract tests.

- [ ] Regenerate OpenAPI and frontend types; compare committed and runtime contracts semantically.
- [ ] Document the implemented trust boundary, states, expiry, scope, compatibility layer, and tests.
- [ ] Run targeted tests, formatting, typecheck, build, and `git diff --check`.
- [ ] Review for duplicate grant paths, commit once, and create the required pull request.
