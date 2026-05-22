# Fabric_4L Type-Alignment Sprint 0 Backlog

**Author:** Manus AI  
**Sprint:** Sprint 0, stabilization and contract inventory  
**Purpose:** Convert repository discovery findings into executable follow-up work without pretending legacy drift has already been remediated.

## Backlog Summary

Sprint 0 discovery found that the repository has the core foundations needed for the planned migration: committed OpenAPI artifacts, generated TypeScript artifacts, a generation script, existing Zod validation utilities, a central API client, and custom contract lint infrastructure. It also found unresolved contract debt that should be migrated progressively rather than fixed through a risky broad rewrite.

| Backlog Theme | Priority | Owner | Status | Next Sprint Target |
|---|---|---|---|---|
| Reconcile OpenAPI exporter coverage with generated-client layer expectations | P0 | Backend Platform / Frontend Platform | Open | Sprint 1 |
| Classify generated DTO imports and prevent future UI leakage | P0 | Frontend Platform | Open | Sprint 0/Sprint 2/Sprint 11 |
| Classify hook-level L5 generated DTO usage | P0 | L5 Team / Frontend Platform | Open | Sprint 4 or Sprint 7 |
| Replace unvalidated event-stream `JSON.parse` with schema-safe parsing | P0 | L4 Agents Team / Frontend Platform | Open | Sprint 3 and Sprint 6 |
| Standardize API trust-boundary validation for Axios and fetch consumers | P0 | Frontend Platform | Open | Sprint 3 |
| Review existing `any`, `as any`, and `unknown as` exceptions | P1 | Frontend Platform | Open | Sprint 0 through Sprint 11 |
| Add generated DTO import boundary lint rule after adapters are established | P0 | Frontend Platform / DevOps | Open | Sprint 11 |

## Detailed Follow-Up Tickets

### S0-B1 — Reconcile OpenAPI Exporter and Generator Surfaces

**Priority:** P0  
**Owner:** Backend Platform / Frontend Platform  
**Type:** Backend Tooling / Contract Governance

The generated-client pipeline expects OpenAPI artifacts for L1 through L6 plus `signals`, and the repository currently contains those artifact files. Sprint 1 must verify whether `scripts/export_openapi.py` can deterministically regenerate every committed artifact or whether some artifacts are still produced by separate/manual paths.

| Required Action | Acceptance Criteria |
|---|---|
| Run the existing OpenAPI export script in a clean worktree context. | The command result is recorded, including whether it touches only L1-L4 or all committed surfaces. |
| Compare exporter outputs with `contracts/openapi/`. | Any missing L5, L6, or signals generation path is explicitly ticketed. |
| Decide canonical artifact naming for generator input. | Exporter output names and generator `LAYERS` expectations are aligned or documented. |
| Add deterministic export evidence. | Running export twice with no code changes produces no diff or a documented blocker. |

### S0-B2 — Classify Generated DTO Imports

**Priority:** P0  
**Owner:** Frontend Platform  
**Type:** Frontend Audit

Current generated DTO imports are concentrated in API and hook-level code. This is preferable to page/component leakage, but every location still needs a boundary classification.

| File | Current Import | Classification Needed | Recommended Action |
|---|---|---|---|
| `apps/web/src/api/packs.ts` | `./generated/l3-types` | API module | Keep allowed, but confirm response validation and mapper behavior. |
| `apps/web/src/api/valuePackFramework.ts` | `./generated/l3-types` | API module | Keep allowed, but confirm generated DTO does not leak into React consumers. |
| `apps/web/src/hooks/useGroundTruthGovernance.ts` | `@/api/generated/l5-types` | Hook boundary | Decide whether this is an API hook or UI-facing hook; if UI-facing, move DTO use behind an adapter. |

### S0-B3 — Harden Event and Stream JSON Parsing

**Priority:** P0  
**Owner:** L4 Agents Team / Frontend Platform  
**Type:** Runtime Validation

Discovery found `JSON.parse` usage in stream and workflow paths. These are high-risk because agent events, workflow checkpoints, and resume data are part of governed workflow execution. Sprint 3 should introduce shared parse helpers; Sprint 6 should migrate L4 event streams to discriminated Zod unions.

| Representative Location | Risk | Follow-Up |
|---|---|---|
| `apps/web/src/agui/AgentEventClient.ts` | Event stream payloads can be treated as valid without discriminated runtime validation. | Add event schema parsing and safe malformed-event handling. |
| `apps/web/src/hooks/useJobStream.ts` | Stream data can enter hook state without shared contract validation. | Parse through shared schema helpers when Sprint 3 utilities exist. |
| `apps/web/src/hooks/useWorkflows.ts` | Workflow events and updates need typed validation. | Align with Sprint 6 L4 event envelope migration. |

### S0-B4 — Classify Existing Unsafe Type Escape Hatches

**Priority:** P1  
**Owner:** Frontend Platform  
**Type:** Frontend Quality

The repository already enforces `@typescript-eslint/no-explicit-any` but still contains historical casts and test/mocking exceptions. Sprint 0 does not remove all of them because that would be a broad refactor. Instead, future work should classify each instance as production defect, approved framework boundary, test harness, or migration shim.

| Pattern | Count Found | Immediate Policy | Follow-Up |
|---|---:|---|---|
| `as any` | 24 | No new production usage without exception. | Classify and remove during feature migrations or Sprint 11 hardening. |
| `: any` | 3 | New usage blocked by existing lint unless explicitly disabled. | Review existing disabled generic utility patterns. |
| `unknown as` | 10 | Must remain boundary-local and justified. | Replace with schema-safe narrowing where practical. |
| `JSON.parse` | 12 | New API/stream parsing must use validation. | Convert high-risk streams first. |
| Direct `fetch` | 25 | Allowed only in approved transport or auth/session boundaries. | Prefer central API/validation patterns for feature data. |
| `axios` | 14 | Allowed in the central API client and error utilities. | Ensure successful responses are validated before domain use. |

### S0-B5 — Prepare Generated DTO Boundary Enforcement

**Priority:** P0  
**Owner:** Frontend Platform / DevOps  
**Type:** Lint / CI

Sprint 11 should enforce DTO import boundaries only after Sprint 2 through Sprint 4 provide reliable generated clients, validation helpers, and mapper conventions. The current Sprint 0 output gives the policy source for that future rule.

| Enforcement Target | Recommended Future Mechanism | Blocking Readiness |
|---|---|---|
| No generated DTO imports in `components`, `pages`, feature `components`, or feature `screens`. | Custom ESLint rule in `packages/eslint-plugin-fabric-contracts` or `no-restricted-imports` pattern with scoped overrides. | Boundary map approved and adapter locations standardized. |
| No unauthorized production `any` or `as any`. | Existing `no-explicit-any` plus additional cast-focused lint/grep check. | Existing exceptions classified. |
| No unvalidated response consumption in high-risk features. | Contract tests plus feature-level schema/mapper tests. | Sprint 3 validation utilities and Sprint 4 mapper pattern complete. |

## Deferred Items Not Completed in This Slice

| Deferred Item | Reason | Recommended Target |
|---|---|---|
| Full endpoint-by-endpoint L1-L6 inventory | Requires route-level contract discovery and layer-owner review. | Sprint 1 and each feature migration sprint. |
| React consumer mapping for every endpoint | Requires tracing hooks and component usage beyond a narrow Sprint 0 slice. | Sprint 4 through Sprint 10. |
| Hard lint rule for generated DTO import leakage | Enforcing before adapters exist could block legacy code unexpectedly. | Sprint 11. |
| Broad replacement of `JSON.parse`, direct `fetch`, or legacy casts | Too broad for stabilization; should follow schema helper and adapter creation. | Sprint 3 onward. |
| Onboarding documentation update | Kept out of this first implementation slice to keep the change reviewable. | Sprint 12 or next documentation pass. |
| Broad API error-model versioning retrofit across existing frontend consumers | Product/API compatibility risk; requires coordinated frontend + SDK rollout. Decision: dual-stack compatibility adapter with fixed deprecation window while `ErrorEnvelopeV1` becomes canonical immediately. | Start immediately; sunset legacy error shape support by 2026-08-31. |
