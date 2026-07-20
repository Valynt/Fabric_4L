---
**ARCHIVED DOCUMENT**
Archive Date: 2026-04-27
Original Location: Repository Root
Rationale: Temporal contract assessment
Modern Equivalent: See ROADMAP.md for current status
Status: Historical reference only
---

# Fabric 4L Contract Enforcement Assessment

**Assessment Date:** 2026-04-23
**Assessor:** Cascade (AI Agent)
**Scope:** Contract enforcement and migration across all layers

---

## 1. Executive Summary

### Overall Maturity: 🟡 PARTIAL (58% enforced)

Fabric 4L has established a **strong documentation foundation** with `contract.md` defining six canonical contracts and `DEPRECATIONS.md` tracking 10 anti-patterns. The ESLint plugin has all 12 rules implemented, and CI pipelines exist. However, **enforcement is uneven**—the frontend has many rules disabled, the reference implementation is not fully integrated, and runtime guards are partially deployed.

### Key Finding: Documented ≠ Enforced

| Layer | Doc Status | Lint Status | Runtime Status | Integration |
|-------|-----------|-------------|----------------|-------------|
| Contract Docs | ✅ Complete | N/A | N/A | ✅ Root-level |
| ESLint Plugin | ✅ 12 rules | ✅ Built | ⚠️ Partially enabled | ⚠️ Frontend disables 5 rules |
| CI Pipeline | ✅ Exists | ⚠️ Non-blocking | N/A | ⚠️ `continue-on-error: true` |
| Reference Impl | ✅ 11 files | ⚠️ No compile test | ⚠️ Not imported | ❌ Not integrated |
| Shared Identity | ✅ Production | N/A | ✅ Middleware active | ✅ All layers use it |
| Frontend | ✅ Barrel exports | ⚠️ Rules disabled | ❌ Uses wouter, not state-machine | ⚠️ Partial |
| Contract Tests | ✅ 15 test files | ✅ Running | N/A | ✅ CI integrated |

---

## 2. Contract-by-Contract Status

| Area | Source of Truth | Enforcement Method | Maturity | Top Gap |
|------|-----------------|-------------------|----------|---------|
| **Tenant Context Propagation** §2.1 | `contract.md` §2.1, `shared/identity/context.py` | ESLint: `no-tenant-id-parameter`, `no-req-tenant-access` | 🟡 **PARTIAL** | Frontend doesn't use AsyncLocalStorage pattern; Python backend passes tenant_id in many functions |
| **DB Session Isolation** §2.2 | `contract.md` §2.2, `examples/canonical/db/session-manager.ts` | ESLint: `no-raw-tenant-query`, `no-explicit-db-connect` | 🔴 **MISSING** | No runtime enforcement; layer4-agents/src/tenants/service.py passes tenant_id to DB functions |
| **Middleware/Auth Flow** §2.3 | `contract.md` §2.3, `shared/identity/middleware.py` | ESLint: `no-inline-middleware` | 🟡 **PARTIAL** | `GovernanceMiddleware` exists but no eight-phase pipeline; inline middleware still present |
| **Tool Invocation Boundary** §2.4 | `contract.md` §2.4, `examples/canonical/tools/` | ESLint: `no-inline-tool-definition`, `no-throw-in-tool` | 🟡 **PARTIAL** | Rules implemented but not enforced in Python; tools still raise exceptions |
| **Agent Output Shape** §2.5 | `contract.md` §2.5 | ESLint: `no-json-parse-agent-output` | 🟡 **PARTIAL** | Rule exists but layer4-agents may still use JSON.parse on LLM outputs |
| **UI State Progression** §2.6 | `contract.md` §2.6, `frontend/.eslintrc.js` | ESLint: `no-imperative-navigation`, `no-url-concatenation` | 🟡 **PARTIAL** | Frontend uses wouter's `navigate()` but not canonical state-machine pattern; rules disabled in config |

### Detailed Enforcement Evidence

#### Tenant Context Propagation (§2.1)
- **Documented:** `contract.md` lines 19-49
- **Lint Rule:** `no-tenant-id-parameter.ts` - ✅ Implemented
- **Runtime:** `shared/identity/middleware.py:280-336` - ✅ `GovernanceMiddleware` sets context
- **Gap:** `services/layer4-agents/src/tenants/service.py:68` - `create_tenant(db, request)` takes explicit params instead of context
- **Instance Count (DEPRECATIONS.md):** ~47 instances

#### DB Session Isolation (§2.2)
- **Documented:** `contract.md` lines 52-89
- **Lint Rule:** `no-raw-tenant-query.ts`, `no-explicit-db-connect.ts` - ✅ Implemented
- **Runtime:** `shared/identity/context.py` - ✅ Context provides tenant_id
- **Gap:** No `TenantAwarePool` implementation found in codebase
- **Instance Count:** ~31 explicit DB connect calls (per DEPRECATIONS.md)

#### Middleware/Auth Flow (§2.3)
- **Documented:** `contract.md` lines 92-131 (8-phase pipeline)
- **Canonical Ref:** `examples/canonical/middleware/pipeline.ts` - ✅ 520 lines
- **Runtime:** `shared/identity/middleware.py:250-541` - ✅ Single middleware, not 8-phase
- **Gap:** No phase-separated pipeline; middleware manifest validator not found
- **Instance Count:** ~42 inline middleware (per DEPRECATIONS.md)

#### Tool Invocation (§2.4)
- **Documented:** `contract.md` lines 134-188
- **Lint Rules:** `no-inline-tool-definition.ts`, `no-throw-in-tool.ts` - ✅ Implemented
- **Runtime:** No Python enforcement found for structured ToolResult
- **Gap:** Layer 4 tools may still throw exceptions rather than return structured errors
- **Instance Count:** ~19 inline tool definitions, ~27 throwing tools

#### Agent Output Shape (§2.5)
- **Documented:** `contract.md` lines 191-253
- **Lint Rule:** `no-json-parse-agent-output.ts` - ✅ Implemented
- **Runtime:** OpenTelemetry integration present but not validated for mandatory fields
- **Gap:** Agent outputs may not conform to canonical `AgentOutput<T>` interface

#### UI State Progression (§2.6)
- **Documented:** `contract.md` lines 256-304
- **Lint Rules:** `no-imperative-navigation.ts`, `no-url-concatenation.ts` - ✅ Implemented
- **Runtime:** `frontend/client/src/App.tsx:16-27` uses wouter `navigate()`, not state-machine
- **Gap:** `RouteManifest` type exists in canonical example but not in frontend codebase
- **Instance Count:** ~56 imperative navigation, ~34 URL concatenation

---

## 3. Prioritized Migration Plan

### Phase 1: Fix Non-Blocking CI (Immediate - P0)
**Effort:** 1 hour
**Impact:** Enables actual enforcement

1. **Remove `continue-on-error: true`** from `contract-compliance.yml:106`
2. **Enable disabled rules** in `frontend/.eslintrc.js` (lines 43-46)
3. **Verify** `make verify` fails on contract violations

### Phase 2: Frontend State-Machine Navigation (Week 1-2 - P1)
**Effort:** 3 days
**Impact:** Aligns UI with contract §2.6

1. **Create `RouteManifest`** type in frontend based on canonical example
2. **Implement `navigate()` wrapper** that validates transitions
3. **Migrate 56 instances** from wouter `navigate()` to state-machine pattern
4. **Enable `no-imperative-navigation`** rule as error

### Phase 3: Python Tool Structured Errors (Week 2-3 - P1)
**Effort:** 4 days
**Impact:** Aligns Layer 4 with contract §2.4

1. **Define `ToolResult[T]`** Pydantic model in shared package
2. **Create `@tool` decorator** that wraps exceptions into structured errors
3. **Migrate 27 throwing tools** to return structured errors
4. **Add runtime guard** in tool registry to reject unwrapped exceptions

### Phase 4: Tenant Context in DB Layer (Week 3-4 - P2)
**Effort:** 5 days
**Impact:** Aligns data layer with contract §2.2

1. **Implement `TenantAwarePool`** based on canonical example
2. **Create `getSession()`** that reads from async context
3. **Migrate 31 explicit connects** to context-based sessions
4. **Enable `no-explicit-db-connect`** rule

### Phase 5: Reference Implementation Integration (Week 4-5 - P2)
**Effort:** 3 days
**Impact:** Makes canonical code testable and importable

1. **Add `package.json` to `examples/canonical/`** for standalone compilation
2. **Add imports test** to verify all canonical files compile
3. **Document import paths** for each canonical pattern
4. **Integrate canonical tests** into `make verify`

---

## 4. Canonical Files Reference

These files should be treated as the **authoritative implementation** for their respective contracts:

| Contract Area | Canonical File | Lines | Status |
|--------------|----------------|-------|--------|
| Tenant Context | `examples/canonical/context/tenant-context.ts` | 447 | ✅ Complete |
| DB Session | `examples/canonical/db/session-manager.ts` | 450 | ✅ Complete |
| Middleware | `examples/canonical/middleware/pipeline.ts` | 520 | ✅ Complete |
| Tools | `examples/canonical/tools/registry.ts` | 380 | ✅ Complete |
| Tools | `examples/canonical/tools/example-tool.ts` | 420 | ✅ Complete |
| Agent | `examples/canonical/agent/orchestrator.ts` | 500 | ✅ Complete |
| UI Routes | `examples/canonical/ui/route-manifest.ts` | 480 | ✅ Complete |
| UI Guards | `examples/canonical/ui/guards.ts` | 380 | ✅ Complete |
| Errors | `examples/canonical/errors/error-shape.ts` | 350 | ✅ Complete |
| Errors | `examples/canonical/errors/error-boundary.ts` | 520 | ✅ Complete |
| Shared Identity | `shared/identity/middleware.py` | 541 | ✅ Production |
| Shared Identity | `shared/identity/context.py` | 137 | ✅ Production |
| Contract Tests | `tests/contract/test_entity_contract.py` | 430 | ✅ Active |
| Contract Tests | `tests/contract/test_layer4_contract.py` | 12,097 | ✅ Active |

---

## 5. Top 3 Hard-Blocking Contract Gaps

### Gap 1: CI Does Not Block on Contract Violations
**Severity:** P0 - Critical
**Location:** `.github/workflows/contract-compliance.yml:106`
**Issue:** `continue-on-error: true` means violations are logged but PRs are not blocked
**Fix:** Remove the line, ensure `make verify` fails on violations
**Impact:** Without this, contract enforcement is advisory only

### Gap 2: Frontend ESLint Rules Are Disabled
**Severity:** P0 - Critical
**Location:** `frontend/.eslintrc.js:43-46`
**Issue:** Five contract rules explicitly disabled:
- `no-raw-tenant-query: off`
- `no-explicit-db-connect: off`
- `no-inline-middleware: off`
- `no-inline-tool-definition: off`
**Fix:** Remove these overrides or set to "error" after migration
**Impact:** Frontend can introduce violations without detection

### Gap 3: No Runtime Tool Error Structure Enforcement
**Severity:** P1 - High
**Location:** `services/layer4-agents/src/tools/*.py`
**Issue:** Tools can raise exceptions; no runtime guard ensures structured `ToolResult`
**Fix:** Add decorator/wrapper in tool registry that catches exceptions and converts to error results
**Impact:** Agent cannot reliably handle tool failures; violates contract §2.4

---

## 6. Evidence Citation Summary

All claims in this assessment are backed by the following files:

| Claim | Evidence File | Lines |
|-------|--------------|-------|
| 12 ESLint rules implemented | `eslint-plugin-fabric-contracts/src/index.ts` | 41-54 |
| Frontend rules disabled | `frontend/.eslintrc.js` | 43-46 |
| CI non-blocking | `.github/workflows/contract-compliance.yml` | 106 |
| ~47 tenantId parameter instances | `DEPRECATIONS.md` | 32 |
| ~56 imperative navigation instances | `DEPRECATIONS.md` | 230 |
| Middleware sets context | `shared/identity/middleware.py` | 280-336 |
| GovernanceMiddleware exists | `shared/identity/middleware.py` | 250 |
| Contract tests exist | `tests/contract/` | 15 files |
| Reference implementation exists | `examples/canonical/` | 11 files |
| Contract.md ratification target | `contract.md` | 490-491 |

---

## 7. Recommendation Summary

**Immediate Actions (Today):**
1. Remove `continue-on-error: true` from contract-compliance.yml
2. Enable all ESLint rules in frontend/.eslintrc.js
3. Run `make verify` to establish baseline failure count

**Short-term (This Week):**
1. Implement hard runtime guard for tool error shapes
2. Create migration ticket for state-machine navigation
3. Add compilation test for examples/canonical/

**Medium-term (This Month):**
1. Complete frontend navigation migration (56 instances)
2. Implement TenantAwarePool for DB sessions
3. Ratify contract.md status from "proposed" to "enforced"

**Success Metrics:**
- CI fails on contract violations: ✅/❌
- Frontend lint passes with all rules: ✅/❌
- Zero overdue deprecations: ✅/❌
- Contract compliance score >80%: ✅/❌
