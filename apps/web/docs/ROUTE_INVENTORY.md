# Frontend Route Inventory

> Auto-generated from `src/shell/router.tsx` and `src/navigation/navSchema.ts`
> Date: 2026-05-24

---

## Summary Statistics

| Category | Count |
|----------|-------|
| Total defined route entries in router | 101 |
| Unique page components | 52 |
| Active (tenant/account-scoped) routes | 78 |
| Legacy (`/workflow/*`, `/value-pilot/*`) routes | 10 |
| Global (non-tenant) routes | 12 |
| Redirect-only routes | 9 |
| Catch-all / 404 | 1 |
| Routes with `tenantAdminPolicy` | 26 |
| Routes with `tenantAdvPolicy` | 18 |
| Routes with `tenantStdPolicy` | 18 |
| Routes with `accountStdPolicy` | 14 |
| Routes with `accountAdvPolicy` | 0 |
| Routes with `homePolicy` | 13 |
| Routes with `authPolicy` | 2 |

---

## 1. Authentication & Onboarding Routes

| # | Path | Component | Layout | Access Policy | Tenant/Account Scoped | Status |
|---|------|-----------|--------|---------------|----------------------|--------|
| 1 | `/sign-in` | `ClerkSignInPage` | None | `authPolicy` (no auth) | No | Active |
| 2 | `/sign-up` | `ClerkSignUpPage` | None | `authPolicy` (no auth) | No | Active |
| 3 | `/workspaces` | `SelectOrganizationPage` | None | `authPolicy` + requiresAuth | No | Active |
| 4 | `/onboarding` | `OnboardingPage` | None | `authPolicy` + requiresAuth | No | Active |

---

## 2. Global Layout Routes (non-tenant-scoped)

These routes render inside `GlobalLayout` + `RequireClerkAuth`.

| # | Path | Component | Access Policy | Tenant/Account Scoped | Status | Notes |
|---|------|-----------|---------------|----------------------|--------|-------|
| 5 | `/` | `RootRedirect` | — | No | Active | Redirects to `/home` or `/sign-in` |
| 6 | `/home` | `ValueNarrativeHome` | `homePolicy` | No | **Active** | Primary dashboard |
| 7 | `/command-center` | `CommandCenter` | `homePolicy` | No | Active | Global command palette |
| 8 | `/tasks` | `TasksPage` | `homePolicy` | No | Active | Task management |
| 9 | `/collaboration/comments` | `CollaborationCommentsPage` | `homePolicy` | No | Active | Collaboration hub |
| 10 | `/notifications` | `NotificationsPage` | `homePolicy` | No | Active | Notification center |

---

## 3. Legacy Workflow Wizard (`/workflow/*`)

> **Status: Legacy** — preserved for backward compatibility. Prefer tenant-scoped routes.

| # | Path | Component | Access Policy | Tenant/Account Scoped | Status |
|---|------|-----------|---------------|----------------------|--------|
| 11 | `/workflow` | `WorkflowProspectSetup` | `homePolicy` | No | **Legacy** |
| 12 | `/workflow/prospect` | Redirect → `/workflow` | — | No | Legacy (redirect) |
| 13 | `/workflow/intelligence` | `WorkflowIntelligence` | `homePolicy` | No | Legacy |
| 14 | `/workflow/ai-model` | `WorkflowAIModel` | `homePolicy` | No | Legacy |
| 15 | `/workflow/driver-tree` | `WorkflowDriverTree` | `homePolicy` | No | Legacy |
| 16 | `/workflow/evidence` | `WorkflowEvidence` | `homePolicy` | No | Legacy |
| 17 | `/workflow/calculator` | `WorkflowCalculator` | `homePolicy` | No | Legacy |
| 18 | `/workflow/value-case` | `WorkflowValueCase` | `homePolicy` | No | Legacy |

---

## 4. Legacy Value Pilot (`/value-pilot/*`)

> **Status: Legacy** — preserved for backward compatibility.

| # | Path | Component | Access Policy | Tenant/Account Scoped | Status |
|---|------|-----------|---------------|----------------------|--------|
| 19 | `/value-pilot` | `ValuePilotProspectSetup` | `homePolicy` | No | **Legacy** |
| 20 | `/value-pilot/prospect` | Redirect → `/value-pilot` | — | No | Legacy (redirect) |

---

## 5. Account Management (Tenant-Scoped)

| # | Path | Component | Access Policy | Tenant/Account Scoped | Status |
|---|------|-----------|---------------|----------------------|--------|
| 21 | `/t/:tenantSlug/accounts` | `Accounts` | `tenantStdPolicy` | Tenant | **Active** |
| 22 | `/t/:tenantSlug/accounts/:accountId` | `AccountOverviewRedirect` | — | Both | Active | Redirects to `.../overview` |
| 23 | `/t/:tenantSlug/accounts/:accountId/overview` | `Accounts` | `accountStdPolicy` | Both | Active |

---

## 6. Intelligence Workspace (Account-Scoped)

> Rendered by `IntelligenceWorkspace` with internal tab routing (`:tabId`).
> NAV_SCHEMA lists 12 sub-tabs; router handles them via a single dynamic route.

| # | Path | Component | Access Policy | Tenant/Account Scoped | Status |
|---|------|-----------|---------------|----------------------|--------|
| 24 | `/t/:tenantSlug/accounts/:accountId/intelligence` | Redirect → `signals` | `accountStdPolicy` | Both | Active |
| 25 | `/t/:tenantSlug/accounts/:accountId/intelligence/:tabId` | `IntelligenceWorkspace` | `accountStdPolicy` | Both | Active |

### NAV_SCHEMA Intelligence Children (handled by `:tabId`)

| Tab ID | Label | Tier | Explicit Router Entry? |
|--------|-------|------|------------------------|
| `signals` | Signals | standard | No (handled by `:tabId`) |
| `enrichment` | Enrichment | advanced | No (handled by `:tabId`) |
| `stakeholders` | Stakeholders | standard | No (handled by `:tabId`) |
| `ontology-match` | Value Ontology | advanced | No (handled by `:tabId`) |
| `hypotheses` | Value Hypotheses | standard | No (handled by `:tabId`) |
| `discovery-questions` | Discovery Questions | standard | No (handled by `:tabId`) |
| `persona-fit` | Persona Fit | standard | No (handled by `:tabId`) |
| `assumptions` | Assumptions | standard | No (handled by `:tabId`) |
| `drivers` | Value Drivers | standard | No (handled by `:tabId`) |
| `evidence` | Evidence | standard | No (handled by `:tabId`) |
| `alternatives` | Alternatives | advanced | No (handled by `:tabId`) |
| `solution-cost` | Solution Cost | advanced | No (handled by `:tabId`) |

---

## 7. Value Studio Workspace (Account-Scoped)

> Rendered by `StudioShell` with internal tab routing (`:tabId`).
> NAV_SCHEMA lists 7 sub-tabs; router handles them via a single dynamic route.

| # | Path | Component | Access Policy | Tenant/Account Scoped | Status |
|---|------|-----------|---------------|----------------------|--------|
| 26 | `/t/:tenantSlug/accounts/:accountId/studio` | Redirect → `action-plan` | `accountStdPolicy` | Both | Active |
| 27 | `/t/:tenantSlug/accounts/:accountId/studio/:tabId` | `StudioShell` | `accountStdPolicy` | Both | Active |

### NAV_SCHEMA Studio Children (handled by `:tabId`)

| Tab ID | Label | Tier | Explicit Router Entry? |
|--------|-------|------|------------------------|
| `action-plan` | Action Plan | standard | No (handled by `:tabId`) |
| `value-model` | Value Model | standard | No (handled by `:tabId`) |
| `driver-tree` | Driver Tree | standard | No (handled by `:tabId`) |
| `calculator` | Calculator | standard | No (handled by `:tabId`) |
| `narrative` | Narrative | standard | No (handled by `:tabId`) |
| `value-case` | Value Case | standard | No (handled by `:tabId`) |
| `value-realization` | Realization | standard | No (handled by `:tabId`) |

---

## 8. Deliverables (Account-Scoped)

| # | Path | Component | Access Policy | Tenant/Account Scoped | Status |
|---|------|-----------|---------------|----------------------|--------|
| 28 | `/t/:tenantSlug/accounts/:accountId/deliverables` | Redirect → `business-cases` | `accountStdPolicy` | Both | Active |
| 29 | `/t/:tenantSlug/accounts/:accountId/deliverables/business-cases` | `BusinessCaseList` | `accountStdPolicy` | Both | Active |
| 30 | `/t/:tenantSlug/accounts/:accountId/deliverables/business-cases/:caseId` | `BusinessCase` | `accountStdPolicy` | Both | Active |
| 31 | `/t/:tenantSlug/accounts/:accountId/deliverables/proposals` | `BusinessCaseList` | `accountStdPolicy` | Both | Active |
| 32 | `/t/:tenantSlug/accounts/:accountId/deliverables/exports` | `BusinessCaseList` | `accountStdPolicy` | Both | Active |
| 33 | `/t/:tenantSlug/accounts/:accountId/deliverables/views/cfo` | `CFOView` | `accountStdPolicy` | Both | Active |
| 34 | `/t/:tenantSlug/accounts/:accountId/deliverables/views/executive` | `ExecutiveView` | `accountStdPolicy` | Both | Active |
| 35 | `/t/:tenantSlug/accounts/:accountId/deliverables/views/technical` | `TechnicalView` | `accountStdPolicy` | Both | Active |

---

## 9. Agents & Workflows (Account-Scoped)

| # | Path | Component | Access Policy | Tenant/Account Scoped | Status |
|---|------|-----------|---------------|----------------------|--------|
| 36 | `/t/:tenantSlug/accounts/:accountId/agents` | `AgentWorkflows` | `accountStdPolicy` | Both | Active |
| 37 | `/t/:tenantSlug/accounts/:accountId/agents/threads/:threadId` | `AgentWorkflows` | `accountStdPolicy` | Both | Active |
| 38 | `/t/:tenantSlug/accounts/:accountId/workflows` | `AgentWorkflows` | `accountStdPolicy` | Both | Active |
| 39 | `/t/:tenantSlug/accounts/:accountId/workflows/:workflowRunId` | `AgentWorkflows` | `accountStdPolicy` | Both | Active |

---

## 10. Context Engine (Tenant-Scoped)

| # | Path | Component | Access Policy | Tenant/Account Scoped | Status |
|---|------|-----------|---------------|----------------------|--------|
| 40 | `/t/:tenantSlug/context` | Redirect → `sources` | `tenantStdPolicy` | Tenant | Active |
| 41 | `/t/:tenantSlug/context/packs` | `ValuePacks` | `tenantStdPolicy` | Tenant | Active |
| 42 | `/t/:tenantSlug/context/models` | `MyModels` | `tenantStdPolicy` | Tenant | Active |
| 43 | `/t/:tenantSlug/context/formulas` | `FormulaList` | `tenantAdvPolicy` | Tenant | Active |
| 44 | `/t/:tenantSlug/context/formulas/new` | `FormulaBuilder` (isNew) | `tenantAdvPolicy` | Tenant | Active |
| 45 | `/t/:tenantSlug/context/formulas/:formulaId` | `FormulaBuilder` | `tenantAdvPolicy` | Tenant | Active |
| 46 | `/t/:tenantSlug/context/value-trees/explorer` | `ValueTreeExplorer` | `tenantAdvPolicy` | Tenant | Active |
| 47 | `/t/:tenantSlug/context/agents` | `AgentWorkflows` | `tenantAdvPolicy` | Tenant | Active |
| 48 | `/t/:tenantSlug/context/ontology` | `OntologyEditor` | `tenantAdvPolicy` | Tenant | Active |
| 49 | `/t/:tenantSlug/context/ontology/entities` | `EntityBrowser` | `tenantAdvPolicy` | Tenant | Active |
| 50 | `/t/:tenantSlug/context/ontology/entities/:entityId` | `EntityDetail` | `tenantAdvPolicy` | Tenant | Active |
| 51 | `/t/:tenantSlug/context/ontology/graph` | `GraphExplorer` | `tenantAdvPolicy` | Tenant | Active |
| 52 | `/t/:tenantSlug/context/ingestion/jobs` | `IngestionJobs` | `tenantStdPolicy` | Tenant | Active |
| 53 | `/t/:tenantSlug/context/extraction` | `ExtractionEngine` | `tenantAdvPolicy` | Tenant | Active |
| 54 | `/t/:tenantSlug/context/integrations` | `Integrations` | `tenantAdminPolicy` | Tenant | Active |
| 55 | `/t/:tenantSlug/context/sources` | `SourceConfiguration` | `tenantAdminPolicy` | Tenant | Active |
| 56 | `/t/:tenantSlug/context/targets` | `TargetsAdmin` | `tenantAdminPolicy` | Tenant | Active |

---

## 11. Governance (Tenant-Scoped)

| # | Path | Component | Access Policy | Tenant/Account Scoped | Status |
|---|------|-----------|---------------|----------------------|--------|
| 57 | `/t/:tenantSlug/governance` | Redirect → `traces` | `tenantStdPolicy` | Tenant | Active |
| 58 | `/t/:tenantSlug/governance/traces` | `DecisionTracePage` | `tenantStdPolicy` | Tenant | Active |
| 59 | `/t/:tenantSlug/governance/evidence` | `GovernanceEvidencePage` | `tenantStdPolicy` | Tenant | Active |
| 60 | `/t/:tenantSlug/governance/provenance` | `DecisionTracePage` | `tenantAdvPolicy` | Tenant | Active |
| 61 | `/t/:tenantSlug/governance/compliance` | `GovernanceCompliancePage` | `tenantAdvPolicy` | Tenant | Active |
| 62 | `/t/:tenantSlug/governance/formulas` | `FormulaList` | `tenantAdvPolicy` | Tenant | Active |
| 63 | `/t/:tenantSlug/governance/formulas/:formulaId` | `FormulaBuilder` | `tenantAdvPolicy` | Tenant | Active |
| 64 | `/t/:tenantSlug/governance/benchmarks` | `BenchmarkPoliciesPage` | `tenantAdminPolicy` | Tenant | Active |
| 65 | `/t/:tenantSlug/governance/benchmarks/:benchmarkId` | `BenchmarkPoliciesPage` | `tenantAdminPolicy` | Tenant | Active |
| 66 | `/t/:tenantSlug/governance/value-packs` | `ValuePacks` | `tenantStdPolicy` | Tenant | Active |
| 67 | `/t/:tenantSlug/governance/value-packs/:packId` | `ValuePacks` | `tenantStdPolicy` | Tenant | Active |
| 68 | `/t/:tenantSlug/governance/policies` | `GovernancePolicies` | `tenantAdminPolicy` | Tenant | Active |
| 69 | `/t/:tenantSlug/governance/audit-log` | `GovernanceAuditLogPage` | `tenantAdminPolicy` | Tenant | Active |
| 70 | `/t/:tenantSlug/governance/health` | `HealthMonitorPage` | `tenantAdminPolicy` | Tenant | Active |

---

## 12. Settings — Personal (Global)

> Rendered inside `SettingsLayout`.

| # | Path | Component | Access Policy | Tenant/Account Scoped | Status |
|---|------|-----------|---------------|----------------------|--------|
| 71 | `/settings` | Redirect → `/settings/profile` | `homePolicy` | No | Active |
| 72 | `/settings/profile` | `PersonalProfile` | `homePolicy` | No | Active |
| 73 | `/settings/security` | `PersonalSecurity` | `homePolicy` | No | Active |
| 74 | `/settings/preferences` | `PersonalPreferences` | `homePolicy` | No | Active |
| 75 | `/settings/notifications` | `PersonalNotifications` | `homePolicy` | No | Active |
| 76 | `/settings/sessions` | `PersonalSessions` | `homePolicy` | No | Active |
| 77 | `/settings/activity` | `PersonalActivity` | `homePolicy` | No | Active |

---

## 13. Settings — Tenant / Workspace / Admin

> Rendered inside `SettingsLayout`. All require `tenantAdminPolicy`.

| # | Path | Component | Access Policy | Tenant/Account Scoped | Status |
|---|------|-----------|---------------|----------------------|--------|
| 78 | `/t/:tenantSlug/settings` | Redirect → `workspace` | `tenantAdminPolicy` | Tenant | Active |
| 79 | `/t/:tenantSlug/settings/workspace` | `BillingWorkspace` | `tenantAdminPolicy` | Tenant | Active |
| 80 | `/t/:tenantSlug/settings/billing` | `BillingSubscription` | `tenantAdminPolicy` | Tenant | Active |
| 81 | `/t/:tenantSlug/settings/billing/subscription` | `BillingSubscription` | `tenantAdminPolicy` | Tenant | Active |
| 82 | `/t/:tenantSlug/settings/billing/usage` | `BillingUsage` | `tenantAdminPolicy` | Tenant | Active |
| 83 | `/t/:tenantSlug/settings/billing/payment-methods` | `BillingPaymentMethods` | `tenantAdminPolicy` | Tenant | Active |
| 84 | `/t/:tenantSlug/settings/billing/invoices` | `BillingInvoices` | `tenantAdminPolicy` | Tenant | Active |
| 85 | `/t/:tenantSlug/settings/users` | `TeamMembers` | `tenantAdminPolicy` | Tenant | Active |
| 86 | `/t/:tenantSlug/settings/roles` | `TeamRoles` | `tenantAdminPolicy` | Tenant | Active |
| 87 | `/t/:tenantSlug/settings/permissions` | `TeamPermissions` | `tenantAdminPolicy` | Tenant | Active |
| 88 | `/t/:tenantSlug/settings/api-keys` | `TeamApiKeys` | `tenantAdminPolicy` | Tenant | Active |
| 89 | `/t/:tenantSlug/settings/data-sources` | `DataSources` | `tenantAdminPolicy` | Tenant | Active |
| 90 | `/t/:tenantSlug/settings/integrations` | `DataIntegrations` | `tenantAdminPolicy` | Tenant | Active |
| 91 | `/t/:tenantSlug/settings/variables` | `DataVariables` | `tenantAdminPolicy` | Tenant | Active |
| 92 | `/t/:tenantSlug/settings/value-packs` | `DataValuePacks` | `tenantAdminPolicy` | Tenant | Active |
| 93 | `/t/:tenantSlug/settings/ingestion-rules` | `DataIngestionRules` | `tenantAdminPolicy` | Tenant | Active |
| 94 | `/t/:tenantSlug/settings/governance` | Redirect → `policies` | `tenantAdminPolicy` | Tenant | Active |
| 95 | `/t/:tenantSlug/settings/governance/policies` | `GovernancePolicies` | `tenantAdminPolicy` | Tenant | Active |
| 96 | `/t/:tenantSlug/settings/governance/compliance` | `GovernanceCompliance` | `tenantAdminPolicy` | Tenant | Active |
| 97 | `/t/:tenantSlug/settings/governance/health` | `GovernanceHealth` | `tenantAdminPolicy` | Tenant | Active |
| 98 | `/t/:tenantSlug/settings/governance/audit` | `GovernanceAuditTrail` | `tenantAdminPolicy` | Tenant | Active |
| 99 | `/t/:tenantSlug/settings/governance/admin` | `GovernanceAdminControls` | `tenantAdminPolicy` | Tenant | Active |

---

## 14. Developer Tools

| # | Path | Component | Access Policy | Tenant/Account Scoped | Status |
|---|------|-----------|---------------|----------------------|--------|
| 100 | `/dev/integration` | `IntegrationDashboard` | `tenantAdminPolicy` | No | Active |

---

## 15. Catch-All

| # | Path | Component | Access Policy | Tenant/Account Scoped | Status |
|---|------|-----------|---------------|----------------------|--------|
| 101 | `*` | `NotFound` | — | No | Active |

---

## Route Guard & Policy Definitions

```
authPolicy        → requiresAuth: false, tenantScoped: false, fallback: "/sign-in"
homePolicy        → requiresAuth: true,  tenantScoped: false, fallback: "/sign-in"
tenantStdPolicy   → requiresAuth: true,  tenantScoped: true,  requiredTier: "standard", fallback: "/home"
tenantAdvPolicy   → requiresAuth: true,  tenantScoped: true,  requiredTier: "advanced", fallback: "/home"
tenantAdminPolicy → requiresAuth: true,  tenantScoped: true,  requiredTier: "admin",    fallback: "/home"
accountStdPolicy  → requiresAuth: true,  tenantScoped: true,  accountScoped: true, requiredTier: "standard", fallback: "/home"
accountAdvPolicy  → requiresAuth: true,  tenantScoped: true,  accountScoped: true, requiredTier: "advanced", fallback: "/home"
```

---

## Discrepancies & Findings

### 1. NAV_SCHEMA vs Router Mismatches

| NAV_SCHEMA Entry | Router Equivalent | Discrepancy |
|------------------|-------------------|-------------|
| `intelligence` children (12 tabs) | Single route with `:tabId` | NAV_SCHEMA lists granular tabs; router handles via dynamic param. **No drift** — this is by design. |
| `studio` children (7 tabs) | Single route with `:tabId` | Same pattern as intelligence. **By design.** |
| `deliverables` | Multiple explicit routes | NAV_SCHEMA has one entry; router has 8 explicit sub-routes. **Consider adding children to NAV_SCHEMA.** |
| `context-engine` | 17 explicit sub-routes | NAV_SCHEMA has one entry; router has deep hierarchy. **Consider adding children to NAV_SCHEMA.** |
| `governance` | 14 explicit sub-routes | NAV_SCHEMA has one entry; router has deep hierarchy. **Consider adding children to NAV_SCHEMA.** |
| `settings` | 2 separate branches (`/settings/*` and `/t/:tenantSlug/settings/*`) | NAV_SCHEMA only lists `/settings` (global personal settings). **Missing tenant-scoped settings entry.** |

### 2. Router-Only Routes (not in NAV_SCHEMA)

The following routes exist in the router but have **no corresponding NAV_SCHEMA entry**:

- `/command-center`
- `/tasks`
- `/collaboration/comments`
- `/notifications`
- All `/workflow/*` routes (legacy)
- All `/value-pilot/*` routes (legacy)
- `/t/:tenantSlug/accounts/:accountId/agents` and sub-routes
- `/t/:tenantSlug/accounts/:accountId/workflows` and sub-routes
- `/dev/integration`
- All settings sub-routes (personal and tenant)

### 3. Potential Issues

| Issue | Severity | Location | Details |
|-------|----------|----------|---------|
| Duplicate component usage | Low | `FormulaList` | Used at both `/t/:tenantSlug/context/formulas` and `/t/:tenantSlug/governance/formulas`. Same for `FormulaBuilder`. |
| Duplicate component usage | Low | `AgentWorkflows` | Used at `/t/:tenantSlug/context/agents`, `/t/:tenantSlug/accounts/:accountId/agents`, and `/t/:tenantSlug/accounts/:accountId/workflows`. |
| Duplicate component usage | Low | `DecisionTracePage` | Used at both `/t/:tenantSlug/governance/traces` and `/t/:tenantSlug/governance/provenance`. |
| Duplicate component usage | Low | `ValuePacks` | Used at `/t/:tenantSlug/context/packs` and `/t/:tenantSlug/governance/value-packs`. |
| Missing `accountAdvPolicy` usage | Info | Router | `accountAdvPolicy` is defined but **never used** in any route. All account-scoped routes use `accountStdPolicy`. |
| NAV_SCHEMA tier mismatch | Medium | `settings` | NAV_SCHEMA marks `settings` as `admin` tier, but `/settings/*` (personal settings) uses `homePolicy` which has no tier check. Tenant settings correctly use `tenantAdminPolicy`. |

---

## Component Inventory

| Component | Route Count | Used In |
|-----------|-------------|---------|
| `AgentWorkflows` | 4 | Context agents, Account agents, Account workflows |
| `BusinessCaseList` | 3 | Deliverables business-cases, proposals, exports |
| `FormulaList` | 2 | Context formulas, Governance formulas |
| `FormulaBuilder` | 3 | Context formulas new, Context formula detail, Governance formula detail |
| `ValuePacks` | 2 | Context packs, Governance value-packs |
| `DecisionTracePage` | 2 | Governance traces, Governance provenance |
| `GovernancePolicies` | 2 | Governance policies, Settings governance policies |
| `BillingSubscription` | 2 | Settings billing, Settings billing/subscription |

---

## Coverage Recommendations for Playwright E2E

### High-Priority Journeys (Active Routes)

1. **Auth flow**: `/sign-in` → `/home`
2. **Account lifecycle**: `/t/:tenantSlug/accounts` → `/t/:tenantSlug/accounts/:accountId/overview`
3. **Intelligence workspace**: `/t/:tenantSlug/accounts/:accountId/intelligence/signals` + tab switching
4. **Studio workspace**: `/t/:tenantSlug/accounts/:accountId/studio/action-plan` + tab switching
5. **Deliverables**: `/t/:tenantSlug/accounts/:accountId/deliverables/business-cases` → detail view
6. **Settings personal**: `/settings/profile` + sub-pages
7. **Settings tenant**: `/t/:tenantSlug/settings/workspace` + sub-pages

### Medium-Priority

8. **Context engine**: `/t/:tenantSlug/context/sources`, `/t/:tenantSlug/context/formulas`
9. **Governance**: `/t/:tenantSlug/governance/traces`, `/t/:tenantSlug/governance/evidence`
10. **Global utilities**: `/command-center`, `/tasks`, `/notifications`

### Legacy / Deprecation Tests

11. **Legacy workflow redirects**: Verify `/workflow/*` still renders
12. **Legacy value-pilot**: Verify `/value-pilot` still renders

### Negative / Edge Cases

13. **Unauthorized access**: Unauthenticated hit on `/home` → redirect to `/sign-in`
14. **Missing tenant**: Access `/t/:tenantSlug/...` without valid tenant context
15. **Missing account**: Access `/t/:tenantSlug/accounts/:accountId/...` without valid account
16. **Tier enforcement**: Standard user accessing `tenantAdvPolicy` or `tenantAdminPolicy` routes
17. **404 handling**: Unknown path `/*` renders `NotFound`

---

## Phase 1A Deliverables — Route/Nav/Policy Alignment

> Completed: 2026-05-25

### 1. Canonical Route Decision Table

| Decision | Before | After | Rationale |
|----------|--------|-------|-----------|
| Settings split | Single `settings` entry with `tier: "admin"` pointing to `/settings` | `personal-settings` (`tier: "standard"`, `/settings`) + `tenant-settings` (`tier: "admin"`, `/t/:tenantSlug/settings`) | Personal settings were user-level but incorrectly admin-gated in NAV_SCHEMA, causing standard users to lose the Settings nav link while the router allowed access. |
| Deliverables children | Flat entry only | Added 6 children (business-cases, proposals, exports, CFO/executive/technical views) | Router had deep hierarchy; breadcrumbs and nav needed schema entries. |
| Context Engine children | Flat entry only | Added 13 children (packs, models, formulas, value-trees, agents, ontology, entities, graph, ingestion, extraction, integrations, sources, targets) | Router had 17 explicit sub-routes; nav schema must reflect product surface. |
| Governance children | Flat entry only | Added 10 children (traces, evidence, provenance, compliance, formulas, benchmarks, value-packs, policies, audit-log, health) | Router had 14 explicit sub-routes; nav schema must reflect product surface. |

### 2. NAV_SCHEMA Alignment Table

| Top-Level Entry | Children Added | Router Sub-Routes Covered |
|-----------------|----------------|---------------------------|
| `deliverables` | 6 | `/deliverables/business-cases`, `/proposals`, `/exports`, `/views/cfo`, `/views/executive`, `/views/technical` |
| `context-engine` | 13 | `/context/packs`, `/models`, `/formulas`, `/value-trees/explorer`, `/agents`, `/ontology`, `/ontology/entities`, `/ontology/graph`, `/ingestion/jobs`, `/extraction`, `/integrations`, `/sources`, `/targets` |
| `governance` | 10 | `/governance/traces`, `/evidence`, `/provenance`, `/compliance`, `/formulas`, `/benchmarks`, `/value-packs`, `/policies`, `/audit-log`, `/health` |
| `personal-settings` | 0 | `/settings/profile`, `/security`, `/preferences`, `/notifications`, `/sessions`, `/activity` |
| `tenant-settings` | 0 | `/t/:tenantSlug/settings/*` (all tenant admin sub-routes) |

### 3. Missing Route Classification Table

| Route | Classification | NAV_SCHEMA Entry? | Action |
|-------|---------------|-------------------|--------|
| `/command-center` | utility route | No | Keep as utility; add to NAV_SCHEMA if promoted to primary nav |
| `/tasks` | utility route | No | Keep as utility; consider adding to NAV_SCHEMA if task UX is primary |
| `/collaboration/comments` | utility route | No | Keep as utility |
| `/notifications` | utility route | No | Keep as utility |
| `/dev/integration` | dev-only route | No | **Hide from production nav**; keep router entry for dev builds |
| `/workflow/*` (all 8 routes) | legacy route | No | **Deprecated** — keep for compatibility, hide from nav, add backlog sunset ticket |
| `/value-pilot/*` | legacy route | No | **Deprecated** — keep for compatibility, hide from nav, add backlog sunset ticket |
| `/t/:tenantSlug/accounts/:accountId/agents` | secondary account-scoped route | No | Intentional — same component used in primary (`/context/agents`) and account context |
| `/t/:tenantSlug/accounts/:accountId/workflows` | secondary account-scoped route | No | Intentional — same component used in primary and account context |
| `/t/:tenantSlug/accounts/:accountId/agents/threads/:threadId` | detail route | No | Not needed in primary nav |
| `/t/:tenantSlug/accounts/:accountId/workflows/:workflowRunId` | detail route | No | Not needed in primary nav |
| `/t/:tenantSlug/accounts/:accountId/deliverables/business-cases/:caseId` | detail route | No | Not needed in primary nav |
| `/t/:tenantSlug/context/formulas/new` | detail route | No | Not needed in primary nav |
| `/t/:tenantSlug/context/formulas/:formulaId` | detail route | No | Not needed in primary nav |
| `/t/:tenantSlug/context/ontology/entities/:entityId` | detail route | No | Not needed in primary nav |
| `/t/:tenantSlug/governance/formulas/:formulaId` | detail route | No | Not needed in primary nav |
| `/t/:tenantSlug/governance/benchmarks/:benchmarkId` | detail route | No | Not needed in primary nav |
| `/t/:tenantSlug/governance/value-packs/:packId` | detail route | No | Not needed in primary nav |

### 4. Duplicate Route/Component Classification Table

| Component | Routes | Classification | Action |
|-----------|--------|----------------|--------|
| `FormulaList` | `/context/formulas`, `/governance/formulas` | **Same component, different context** | Intentional alias — Context Engine formulas vs Governance formulas. Both are valid product surfaces. |
| `FormulaBuilder` | `/context/formulas/new`, `/context/formulas/:id`, `/governance/formulas/:id` | **Same component, different context** | Intentional alias — builder reused across contexts. |
| `AgentWorkflows` | `/context/agents`, `/accounts/:accountId/agents`, `/accounts/:accountId/workflows` | **Same component, different scope** | Intentional — agent console reused at tenant context and account context. Keep both. |
| `DecisionTracePage` | `/governance/traces`, `/governance/provenance` | **Legacy alias** | Provenance used to be a separate concept but now shares the trace UI. **Decision**: keep both; add redirect from `/provenance` to `/traces` if product wants to unify. |
| `ValuePacks` | `/context/packs`, `/governance/value-packs` | **Same component, different context** | Intentional alias — pack browser reused in Context Engine and Governance. |
| `GovernancePolicies` | `/governance/policies`, `/t/:tenantSlug/settings/governance/policies` | **Same component, different context** | Intentional — policy admin view reused in Governance hub and Settings workspace. |
| `BillingSubscription` | `/t/:tenantSlug/settings/billing`, `/t/:tenantSlug/settings/billing/subscription` | **Redirect alias** | `/billing` redirects to `/billing/subscription` in router; NAV_SCHEMA should point to canonical path. |

### 5. Legacy Route Policy

| Legacy Route | Status | Policy |
|--------------|--------|--------|
| `/workflow/*` (8 routes) | **Deprecated, keep for compatibility** | Hide from primary nav. Add backlog ticket for graceful sunset. Do not redirect (no canonical tenant/account context available). |
| `/value-pilot/*` (2 routes) | **Deprecated, keep for compatibility** | Hide from primary nav. Add backlog ticket for graceful sunset. |

### 6. Policy Mismatch Resolution

| Mismatch | Resolution | Status |
|----------|------------|--------|
| NAV_SCHEMA `settings` had `tier: "admin"` but personal `/settings/*` used `homePolicy` | Split into `personal-settings` (`tier: "standard"`) and `tenant-settings` (`tier: "admin"`) | **Resolved** |
| `accountAdvPolicy` defined but unused | Added TODO comment in `router.tsx` documenting it as reserved for future advanced account-scoped gating | **Documented** |
| `ROUTE_TIER_MAP` in `userTierStore.ts` uses stale paths (e.g. `/discover/*`, `/library/*`, `/context` without tenant prefix) | **Identified as dead code** — not consumed by `UnifiedRouteGuard` or `LeftNavigation`. Needs cleanup in separate tech-debt pass. | **Backlogged** |

### 7. P0/P1 Fixes Made

| Fix | File | Lines |
|-----|------|-------|
| Split settings entry into personal-settings (standard) and tenant-settings (admin) | `src/navigation/navSchema.ts` | 110–123 |
| Added deliverables children to NAV_SCHEMA | `src/navigation/navSchema.ts` | 60–67 |
| Added context-engine children to NAV_SCHEMA | `src/navigation/navSchema.ts` | 75–89 |
| Added governance children to NAV_SCHEMA | `src/navigation/navSchema.ts` | 97–108 |
| Updated NAV_ICONS map for renamed/new entries | `src/components/layout/LeftNavigation.tsx` | 24–34 |
| Documented accountAdvPolicy as reserved | `src/shell/router.tsx` | 150–152 |

### 8. Remaining Backlog

| Item | Priority | Owner | Notes |
|------|----------|-------|-------|
| Clean up stale `ROUTE_TIER_MAP` in `userTierStore.ts` | P2 | Tech debt | Dead code — not used by route guard or nav |
| Add backlog ticket for legacy route sunset (`/workflow/*`, `/value-pilot/*`) | P2 | Product | Hide from nav; plan graceful deprecation |
| Investigate `/provenance` → `/traces` redirect | P2 | Product | Both use `DecisionTracePage`; may want to unify |
| Evaluate `/command-center`, `/tasks`, `/notifications` for primary nav promotion | P3 | UX | Currently utility routes; may deserve NAV_SCHEMA entries |
| Ensure `LeftNavigation` handles account-scoped agents/workflows as secondary nav | P2 | Engineering | These routes exist but are not in primary sidebar |

---

*End of Phase 1A — Route/Nav/Policy Alignment*

