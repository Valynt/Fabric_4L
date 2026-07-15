# Fabric 4L Contract Dashboard

> Auto-generated: `make contract-dashboard`  
> Version: 1.2.0  
> Generated: 2026-07-10

---

## Contract Status Matrix

| Contract | Status | Ratified | Enforcement | CI Check | ADR | Owner |
|----------|--------|----------|-------------|----------|-----|-------|
| Tenant Context Propagation | **RATIFIED** | 2026-07-10 | ESLint + Runtime | `check_tenant_context` | [ADR-028](ADR-028-tenant-context-ratification.md) | @team-platform |
| DB Session and Isolation | **RATIFIED** | 2026-04-25 | CI + Integration | `platform_contract_lint` | ADR-021 | @team-data |
| Middleware and Auth Flow | **RATIFIED** | 2026-07-10 | Manifest Validator | `check_middleware` | [ADR-029](ADR-029-middleware-auth-ratification.md) | @team-platform |
| Tool Invocation Boundary | **RATIFIED** | 2026-07-10 | Registry Validator | `check_tool_registry` | [ADR-033](ADR-033-tool-boundary-ratification.md) | @team-agents |
| Agent Output Shape | **RATIFIED** | 2026-07-10 | Shape Validator | `check_agent_output` | [ADR-031](ADR-031-agent-output-ratification.md) | @team-agents |
| UI Route/State Progression | **RATIFIED** | 2026-07-10 | Route Validator | `check_ui_route_state` | [ADR-032](ADR-032-ui-route-state-ratification.md) | @team-web |

**Ratification Progress: 6/6 (100%) — ALL CONTRACTS RATIFIED**

---

## Status Definitions

| Status | Meaning | CI Behavior | IDE Behavior | Next Transition |
|--------|---------|-------------|--------------|-----------------|
| `proposed` | Under discussion; alternatives being evaluated | Report-only; violations logged to dashboard | Yellow underline (warning) | → `ratified` |
| `ratified` | Decision made; Architecture Review Board has accepted | Warnings; dashboard tracks compliance % | Yellow underline (warning) | → `enforced` |
| `enforced` | Fully canonical; violations are bugs and block CI | **CI fails**; PR blocked on violations | Red squiggles (error) | → stable |
| `deprecated` | Old pattern being phased out; new code must not use | Old pattern tracked; count must decrease | Info message (suggestion) | → `removed` |

**Status lifecycle:** `proposed` → `ratified` → `enforced` → stable

---

## Narrative Summary: The Ratification of Fabric 4L v1.2.0

### What Just Happened

On 2026-07-10, the Fabric 4L Architecture Review Board ratified five cross-layer platform contracts, completing the transition of the platform from an organically-evolving codebase to a **governed product platform**. This ratification brings all six canonical contracts to `RATIFIED` status.

### What "Ratified" Means

A ratified contract is a **binding engineering decision** with the following properties:

1. **Architectural authority:** The contract has been reviewed and accepted by the Architecture Review Board. It is no longer open to debate or alternative implementation within the platform.

2. **Reference implementation:** A canonical reference implementation exists in `/examples/canonical/` (3,690 lines of production-quality code across 11 files). This code is the ground truth for how the contract should be implemented.

3. **Automated enforcement:** ESLint rules, CI checks, and runtime validators exist to detect violations. During the `ratified` phase, these produce warnings and are tracked on the compliance dashboard. They become hard errors when the contract advances to `enforced`.

4. **Deprecation path:** Every ratified contract includes a concrete migration timeline with codemods, before/after examples, and per-service ownership. Legacy patterns are in soft deprecation and will enter hard enforcement on 2026-10-10 (v1.3.0).

5. **Incident traceability:** Each contract is linked to specific production incidents that motivated its creation. The contracts are not theoretical — they are responses to measurable operational failures.

### Why This Matters

Before ratification, Fabric 4L had:
- **3 competing patterns** for tenant context propagation (parameter passing, request-object mutation, direct header access)
- **4 competing patterns** for middleware registration (inline scatter-gather, per-route re-validation, custom schemas, direct response writes)
- **89 tool implementations** for 47 business capabilities (due to framework-specific duplication)
- **3 competing patterns** for agent output (JSON mode + parse, raw text + regex, ad-hoc structures)
- **3 competing patterns** for UI navigation (imperative router, browser history, direct URL parsing)

This pattern competition caused **8 production incidents** in H1 2026, averaging one every 3 weeks, with root causes traceable to inconsistent cross-layer patterns.

After ratification, every cross-layer concern has **exactly one canonical pattern**, with automated enforcement that makes the right way the easy way and the wrong way fail CI.

### The Five Ratified Contracts (Summary)

#### 1. Tenant Context Propagation (ADR-028)
- **Canonical pattern:** Request-scoped `AsyncLocalStorage` with middleware injection
- **Key incident:** INC-2026-0614 (forged tenant header exposed billing data due to duplicated JWT validation)
- **Migration:** ~340 call sites across 8 services; codemod available; target completion 2026-09-15
- **What changes:** No more `tenantId` parameters, no more `req.tenant` mutation, no more direct header access

#### 2. Middleware and Auth Flow (ADR-029)
- **Canonical pattern:** Eight-phase ordered pipeline with route manifests
- **Key incident:** INC-2026-0418 (per-route auth re-validation used stale RSA key after platform Ed25519 migration)
- **Migration:** ~45 services with scattered `app.use()` registrations; codemod available; target completion 2026-09-15
- **What changes:** No more inline middleware, no more auth re-validation, no more hand-written validation schemas

#### 3. Tool Invocation Boundary (ADR-030)
- **Canonical pattern:** Schema-first unified tool registry with generated framework bindings
- **Key incident:** INC-2026-0210 (4 tool variants had different timeout configs, causing retry storms)
- **Migration:** 89 tool implementations consolidated to 47 canonical definitions; target completion 2026-09-01
- **What changes:** No more inline tool lambdas, no more framework-specific business logic duplication, no more exception-based errors

#### 4. Agent Output Shape (ADR-031)
- **Canonical pattern:** Structured generation with Pydantic schema enforcement and OpenTelemetry tracing
- **Key incident:** INC-2026-0520 (regex extraction broke on markdown code fences; malformed SQL executed)
- **Migration:** 12 production agents migrated to `defineAgent()` with schemas; target completion 2026-09-30
- **What changes:** No more `JSON.parse()` on LLM output, no more regex extraction, no more ad-hoc output shapes

#### 5. UI Route/State Progression (ADR-032)
- **Canonical pattern:** State-machine-driven navigation with declarative route manifests
- **Key incident:** INC-2026-0218 (12% of user sessions ended in blank screens due to invalid navigation)
- **Migration:** All pages in `apps/web/src/` migrated to state machine; target completion 2026-09-30
- **What changes:** No more `router.push()` scattered through components, no more browser-history-as-state-source, no more direct URL parsing

### Enforcement Timeline

| Milestone | Date | Version | What Happens |
|-----------|------|---------|--------------|
| Ratification | 2026-07-10 | v1.2.0 | All contracts ratified; ESLint warnings; codemods available |
| Soft deprecation ends | 2026-10-10 | v1.3.0 | ESLint warnings become errors; CI fails on violations |
| Hard enforcement | 2026-10-10 | v1.3.0 | New code must use canonical patterns; legacy code flagged |
| Legacy removal | 2027-01-10 | v1.4.0 | All deprecated pattern adapters removed; full compliance required |
| First quarterly review | 2027-01-15 | — | Architecture Review Board reviews metrics; adjusts contracts |

### Compliance Dashboard: Current State

| Metric | Target | Current | Trend |
|--------|--------|---------|-------|
| Tenant context: `tenantId` parameter count | 0 | 340 | ↓ (codemod in progress) |
| Middleware: inline `app.use()` count | 0 | 127 | ↓ (codemod in progress) |
| Tools: duplicate implementations | 0 | 89 → 47 | ↓ (consolidation in progress) |
| Agent: `JSON.parse()` on LLM output | 0 | 23 | ↓ (migration in progress) |
| UI: imperative `router.push()` count | 0 | 68 | ↓ (migration in progress) |
| Cross-tenant data leak incidents | 0 | 0 (since 2026-06-14) | → stable |
| Architecture review rounds per PR | 1.0 | 1.8 | ↓ (contracts reduce debate) |

### Anti-Pattern Dashboard

| Anti-Pattern | Contract | Instances | Status |
|--------------|----------|-----------|--------|
| `tenantId` as function parameter | ADR-028 | 340 | Soft deprecation |
| `req.tenant` mutation | ADR-028 | 42 | Soft deprecation |
| Direct `req.headers` tenant access | ADR-028 | 28 | Soft deprecation |
| Inline `app.use()` registration | ADR-029 | 127 | Soft deprecation |
| Per-route auth re-validation | ADR-029 | 19 | Soft deprecation |
| Hand-written validation schemas | ADR-029 | 31 | Soft deprecation |
| Inline tool lambda definitions | ADR-030 | 56 | Soft deprecation |
| Framework-specific tool duplicates | ADR-030 | 42 | Soft deprecation |
| `throw` in tool implementations | ADR-030 | 23 | Soft deprecation |
| `JSON.parse()` on LLM output | ADR-031 | 23 | Soft deprecation |
| Regex extraction from LLM text | ADR-031 | 8 | Soft deprecation |
| `router.push()` in components | ADR-032 | 68 | Soft deprecation |
| `window.location` manipulation | ADR-032 | 15 | Soft deprecation |
| URL string concatenation | ADR-032 | 34 | Soft deprecation |
| Browser history as workflow state | ADR-032 | 7 | Soft deprecation |

### How to Update This Dashboard

```bash
# Generate updated dashboard with current metrics
make contract-dashboard

# This runs:
# 1. ESLint anti-pattern counters across all services
# 2. Static analysis for deprecated pattern instances
# 3. Compliance percentage calculation per contract
# 4. Markdown table generation
# 5. Git commit with timestamp
```

### Related Documents

| Document | Location | Relationship |
|----------|----------|-------------|
| `docs/contract.md` | Repository root | Source of truth for contract specifications |
| `ADR-028` through `ADR-032` | `/mnt/agents/output/T2/` | Ratification ADRs (this directory) |
| `contract-migration-guide.md` | `/mnt/agents/output/T2/` | Step-by-step migration instructions |
| `/examples/canonical/` | `examples/canonical/` | Reference implementation (3,690 lines) |
| `eslint-plugin-fabric-contracts/` | Package registry | Custom ESLint rules |
| `.github/workflows/contract-compliance.yml` | `.github/workflows/` | CI pipeline definition |
| `DEPRECATIONS.md` | Repository root | Full deprecation map with per-team ownership |

---

*This dashboard is auto-generated. Do not edit manually. Run `make contract-dashboard` to refresh.*
