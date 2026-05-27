# Canonical User Journeys

This document defines the core end-to-end user journeys for the Value Fabric platform. These journeys form the foundation of our 4-layer testing strategy, ensuring that critical business workflows are validated across the UI, backend contracts, and performance boundaries.

## Journey 1: Domain Ingestion to Value Tree Exploration (The "Happy Path")
This is the primary onboarding and discovery workflow for a new prospect.

**Workflow Steps:**
1. User logs in and establishes tenant context.
2. User navigates to the Command Center (`/home`).
3. User submits a new company domain for ingestion.
4. User monitors the ingestion job until completion.
5. User navigates to the Value Tree Explorer (`/context/value-trees/explorer`).
6. User validates that the newly ingested domain has generated expected nodes (Capabilities, Use Cases, Personas, Value Drivers).
7. User verifies that node statistics and confidence badges are displayed correctly.

**Key Invariants:**
- The ingestion job must successfully trigger the L1 -> L2 -> L3 pipeline.
- The resulting graph data must be strictly scoped to the user's `tenant_id`.

## Journey 2: Intelligence Workspace Synthesis
This journey validates the core agentic workflow where raw data is synthesized into actionable intelligence.

**Workflow Steps:**
1. User navigates to the Accounts list (`/accounts`).
2. User selects an account, entering the Intelligence Workspace (`/intelligence/:accountId/signals`).
3. User triggers the Agent Stream to synthesize recent signals.
4. User interacts with the agent (e.g., asks a follow-up question).
5. User navigates through the Intelligence tabs (Drivers, Evidence, Stakeholders) to verify that the synthesized data populates the respective views.

**Key Invariants:**
- The agent workflow must successfully transition through idle -> running -> finished states.
- The generated intelligence must be persisted and retrievable across tabs.

## Journey 3: Value Studio Deliverable Generation
This journey validates the creation of a business case or narrative from synthesized intelligence.

**Workflow Steps:**
1. User navigates to the Value Studio for a specific account (`/studio/:accountId/action-plan`).
2. User reviews the action plan and proceeds to the Value Model tab.
3. User adjusts a variable or formula within the value model.
4. User navigates to the Narrative tab and generates a narrative based on the updated model.
5. User exports or views the final deliverable (e.g., CFO View at `/deliverables/views/cfo`).

**Key Invariants:**
- Formula evaluations must correctly recalculate based on variable changes.
- The generated narrative must reflect the updated value model data.

## Journey 4: Governance and Trust Validation
This journey ensures that the platform's trust layer correctly tracks and audits decisions.

**Workflow Steps:**
1. User navigates to the Governance Decision Traces (`/governance/traces`).
2. User selects a recent agent decision or synthesis output.
3. User verifies the provenance of the data (linking back to the original ingested source).
4. User navigates to the Audit Log (`/governance/audit/log`) to verify that their recent actions (e.g., domain ingestion, model update) are recorded.

**Key Invariants:**
- Every AI-generated output must have a traceable provenance path.
- Audit logs must accurately capture user actions with correct timestamps and tenant scoping.

## Journey 5: Tier-Gated Access and Security
This journey validates that the platform correctly enforces RBAC and tier-based feature gating.

**Workflow Steps:**
1. User logs in with a "Standard" tier account.
2. User verifies that advanced features (e.g., Context Engine, Governance) are hidden from the navigation.
3. User attempts to directly access a restricted URL (e.g., `/context/ontology`) and is redirected to `/home`.
4. User logs out and logs back in with an "Admin" tier account.
5. User verifies that all features and settings are accessible.

**Key Invariants:**
- Route guards must strictly enforce tier requirements.
- API requests to restricted endpoints must return 403/401 if bypassed at the UI layer.


## Journey Inventory (Current Specs)

| Spec file | Feature area | Classification | Mode | Unique assertions | Canonical alignment |
|---|---|---|---|---|---|
| `j0-auth-session.spec.ts` | Auth/session lifecycle | happy path | mocked | redirect-to-login guard, persisted session after reload, token-expiry cleanup | Foundational precondition for J1–J5 |
| `j1-ingestion-to-value-tree.spec.ts` | Ingestion → value tree | happy path | mocked + backend-aware | ingestion submission, job lifecycle, value-tree node visibility | **Canonical J1 primary** |
| `j2-intelligence-workspace.spec.ts` | Signals synthesis workspace | happy path | mocked | agent stream state transitions, cross-tab signal persistence | **Canonical J2 primary** |
| `j3-value-studio-deliverable.spec.ts` | Value studio deliverables | happy path | mocked | model edit impacts narrative/export affordances | **Canonical J3 primary** |
| `j4-governance-trust.spec.ts` | Governance evidence/audit | happy path | mocked | provenance/trace + audit-log visibility | **Canonical J4 primary** |
| `j5-tier-gated-security.spec.ts` | Tier/RBAC gating | happy path + adversarial | mocked | restricted-route redirects, tier-specific nav exposure | **Canonical J5 primary** |
| `j1-golden-path-deep.spec.ts` | J1 deep reliability checks (GP-DEEP-001–019) | deep | mocked | full prospect-to-business-case lifecycle: account setup → ingestion → signals → hypotheses → ROI → approval; NaN/undefined regression guards; claim traceability | J1 deep variant — all 19 tests pass in mocked mode |
| `j1-golden-path-backend-integrated.spec.ts` | J1 backend realism | deep | integrated | fail-closed backend contract expectations for J1 chain | J1 integrated variant |
| `j7-calculation-evidence-deep.spec.ts` + `j7-value-realization-and-calculation.spec.ts` | Value realization/calculation | happy path + deep | mocked | unit normalization (weekly/monthly/annual), currency consistency | Consolidated under J3-adjacent value-model coverage |
| `j8-approval-review-deep.spec.ts` + `j8-approval-review-gates.spec.ts` | Approval/review gates | happy path + deep | mocked | approval gate enforcement across integrations/hand-offs | Consolidated governance extension of J4 |
| `j9-agent-grounding-deep.spec.ts` + `j9-agent-grounding-governance.spec.ts` | Agent grounding/trust | deep | mocked | grounding evidence and governance-aware refusal/trace behavior | Consolidated trust extension of J4 |
| `j10-layer-ui-validation.spec.ts` + `j10-layer-ui-validation-deep.spec.ts` | UI contract drift detection | happy path + deep | mocked | cross-layer data-shape resilience and PII redaction checks | Consolidated cross-cutting quality suite |
| `j11-golden-path-business-lifecycle.spec.ts` | End-to-end business lifecycle | deep | integrated (@backend) | approval-to-export-to-CRM and post-sale realization chain | Integrated super-journey spanning J1–J5 |
| `j12`–`j24` (excluding debug specs) | Domain extensions (resilience, narrative, CRM, personas, admin, adversarial) | happy path/deep/adversarial | mostly mocked; some backend-aware | scenario-specific assertions tied to feature module outcomes | Non-canonical extensions mapped to closest J1–J5 journey |
| `j6-account-tenant-switching.spec.ts` | Account/tenant switching | happy path | mocked + integrated | data scope updates, navigation context, API tenant context, session validity, deep link respect | **P0 production gate** — multi-tenant isolation |
| `j13-long-running-workflow-progress.spec.ts` | Long-running workflow progress | happy path | mocked | meaningful progress indicators, ETA/stage breakdown, cancel operations, progress persistence, error handling | **P1 production confidence** — UX for long operations |
| `j20-billing-entitlement-gates.spec.ts` | Billing/entitlement gates | happy path + adversarial | mocked + integrated | plan/entitlement gates, billing status, API failure degradation, webhook results, usage limits | **P0 production gate** — billing UX |
| `session-refresh-edge-cases.spec.ts` | Session refresh edge cases | happy path + edge case | mocked | silent token refresh, expiry during workflow, multi-tab sync, logout propagation, network recovery | **P1 production confidence** — session management |
| `api-failure-recovery-deep.spec.ts` | API failure recovery (deep) | resilience | mocked | timeout handling, 5xx errors, offline mode, partial failures, retry mechanisms, error recovery | **P1 production confidence** — degraded UX |
| `deep-link-tenant-isolation-deep.spec.ts` | Deep link tenant isolation (deep) | security | integrated (@backend) | deep link context respect, stale cache prevention, forged header blocking, expiry handling, cross-tenant blocking | **P0 production gate** — deep link security |
| `debug-sidebar.spec.ts`, `debug-ui.spec.ts`, `full-ui-debug.spec.ts` | Diagnostics only | debug | mocked/manual | route/surface diagnostics and exploratory smoke output | **Excluded from normal CI via `@debug` tag** |

## Consolidation Decisions

- Canonical ownership remains with `j1`–`j5` files (plus `j0` auth preflight) for required CI journey coverage.
- Overlapping variants are retained only as explicit depth modes:
  - `*-deep.spec.ts` = deeper assertions and regression probes.
  - `*-backend-integrated.spec.ts` and `@backend` tests = integrated fail-closed backend realism.
- Diagnostic scripts are explicitly tagged `@debug` and must be excluded from normal CI runs.
