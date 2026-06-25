# Frontend Workflow Coverage Matrix

**Owner:** Frontend Platform  
**Last updated:** June 5, 2026  
**Purpose:** This matrix is the source of truth for deciding whether user-facing frontend workflows are functioning as expected. It complements Playwright, Vitest, contract tests, accessibility scans, and bundle checks by making the expected workflow proof explicit.

## Release Gate Policy

A workflow is considered release-significant when it appears in the **P0** or **P1** tables below. Release-significant workflow tests must fail closed: they must not use `test.skip`, `test.fixme`, backend skip valves, or placeholder assertions. A green workflow result means the tested user can reach the intended business state, the route persists the expected context across navigation or reload, invalid actions are blocked before mutation, and API failures expose recoverable UI states.

| Gate | Required evidence |
|---|---|
| Type safety | `pnpm run check` passes. |
| Contract safety | `pnpm run test:contracts` passes and schema drift checks validate canonical OpenAPI fixtures. |
| P0 workflow safety | `pnpm run test:e2e:validation:p0` and `pnpm run test:e2e:guard` pass in CI-capable environments. |
| P1 workflow safety | `pnpm run test:e2e:validation:p1` and `pnpm run test:e2e:guard` pass in CI-capable environments. |
| Broad workflow safety | `pnpm run test:e2e:validation` passes before release candidate sign-off and includes P0 plus P1 evidence owners. |
| Accessibility and resilience | P0 flows include keyboard, error, and role-state assertions through focused E2E or component tests. |
| UI design readiness | `pnpm run test:ui-readiness` passes and confirms release-significant paths keep documented state, accessibility, and placeholder guardrails. |
| Build and bundle confidence | `pnpm run build` and `pnpm run test:bundle-budget` pass. |
| Master workflow traceability | `docs/validation/product_workflow_validation_inventory.md` remains aligned to P0/P1 evidence owners in this matrix. |
| Executable workflow contracts | `docs/frontend-workflow-contracts.json` defines actions, UI proof, backend proof, security invariants, audit invariants, failure cases, and evidence files for each P0/P1 workflow; `pnpm run test:workflow-contracts` enforces the contract. |
| Route inventory safety | `pnpm run test:route-inventory` verifies `TieredNav` destinations resolve to canonical router entries, protected/admin routes carry access-policy metadata, and legacy redirects target real tenant-scoped routes. |
| Release evidence supplement | `pnpm run verify:frontend:release` requires `FRONTEND_RELEASE_EVIDENCE` to point at a redacted JSON file shaped like `docs/frontend-release-evidence.template.json`; `pnpm run test:frontend-release-evidence` fails closed unless the evidence records exact commit SHA, image digest, production-build status, live P0 browser journeys against real internal infra, no unexpected browser errors, no HTTP 5xx, no unhandled mock requests, no failed background jobs, authorization-matrix pass counts, API and retrieval tenant-isolation results, approval/export/audit results, live-provider smoke, post-deploy synthetics, trace retention, and canonical release evidence packet status. |

## Alignment With Comprehensive Workflow Inventory

The repository now treats the comprehensive validation inventory as the product-level backlog and this frontend matrix as the browser-test execution map. The inventory defines six validation suites: **Golden Path E2E**, **Layer-by-Layer Validation**, **Security/Tenant Isolation**, **Agent Grounding and Governance**, **Calculation and Evidence Integrity**, and **Operational Resilience**. The P0 rows below cover the highest production-readiness workflows, while the P1 rows provide route and journey owners for the broader uploaded scope.

| Uploaded inventory priority | Frontend gate mapping |
|---|---|
| Account setup → ingestion → extraction → graph → hypotheses → value tree → calculator → business case | `P0-ACCOUNT-LIFECYCLE`, `P0-LAYER-VALIDATION`, `P0-CALC-EVIDENCE` |
| Evidence-to-claim traceability from final output back to raw source | `P0-CALC-EVIDENCE`, `P0-APPROVAL-EXPORT`, `P0-AGENT-GOVERNANCE` |
| Tenant isolation across every layer | `P0-AGENT-GOVERNANCE`, `P1-SETTINGS`, `P1-SEARCH-SECURITY` |
| Agent refusal and grounding under adversarial input | `P0-AGENT-GOVERNANCE`, `P1-ADVERSARIAL` |
| Formula correctness and scenario reproducibility | `P0-CALC-EVIDENCE`, `P1-CONTEXT` |
| Review/approval gates before export or CRM push | `P0-APPROVAL-EXPORT`, `P1-INTEGRATIONS` |
| Recovery from failed jobs and partial workflows | `P0-LAYER-VALIDATION`, `P1-RESILIENCE` |


## Route-layer dependency map

For Layer 1–6 backend ownership and required UI fallback contracts per P0/P1 route family, see [`route-layer-dependency-map.md`](./route-layer-dependency-map.md).

## P0 Workflows

| ID | Workflow | Primary routes | Required test evidence | Persona coverage | Resilience proof | Accessibility proof | Owner |
|---|---|---|---|---|---|---|---|
| P0-ACCOUNT-LIFECYCLE | Account-to-approved-business-case lifecycle | `/accounts`, `/workflow/prospect`, `/workflow/value-case`, `/value-case/:accountId`, `/deliverables/cases/:caseId` | `e2e/journeys/j6-account-prospect-lifecycle.spec.ts`; `e2e/journeys/j11-golden-path-business-lifecycle.spec.ts`; `e2e/journeys/j1-golden-path-backend-integrated.spec.ts` | Admin, seller, reviewer | Reload preserves account/workflow context; duplicate or invalid account submissions are blocked. | Primary forms, account picker, review dialog, and export CTA are keyboard-reachable. | Frontend Platform |
| P0-CALC-EVIDENCE | Value realization, calculation, and evidence | `/calculator/:accountId`, `/calculator/:accountId/roi`, `/workflow/calculator`, `/workflow/evidence`, `/realization/:accountId` | `e2e/journeys/j7-value-realization-and-calculation.spec.ts`; `e2e/journeys/j7-calculation-evidence-deep.spec.ts` | Seller, reviewer | Failed recalculation and missing evidence states are visible and recoverable. | Numeric inputs, validation messages, and evidence upload controls are announced. | Value Workflow |
| P0-APPROVAL-EXPORT | Approval-gated deliverables and export | `/governance`, `/governance/traces`, `/deliverables`, `/deliverables/cases/:caseId` | `e2e/journeys/j8-approval-review-gates.spec.ts`; `e2e/journeys/j8-approval-review-deep.spec.ts`; `e2e/export-workflows.spec.ts`; `e2e/export/export-workflows-deep.spec.ts` | Seller, reviewer, admin | Export remains blocked until approval; rejected items can be remediated. | Review decision controls and blocked-export messages are keyboard and screen-reader visible. | Governance |
| P0-AGENT-GOVERNANCE | Agent grounding, prompt-injection handling, and tenant-safe evidence | `/workflow/intelligence`, `/context/agents`, `/governance/evidence`, `/governance/traces` | `e2e/journeys/j9-agent-grounding-governance.spec.ts`; `e2e/journeys/j9-agent-grounding-deep.spec.ts`; `e2e/security/tenant-isolation-validation.spec.ts`; `e2e/security/tenant-isolation-deep.spec.ts` | Seller, admin, restricted user | Prompt injection is rejected; cross-tenant data is not shown; trace failure states explain remediation. | Agent response, citation, and trace regions expose useful labels and status. | AI Experience |
| P0-LAYER-VALIDATION | Layered product navigation and UI state validation | `/context/*`, `/workflow/*`, `/studio/:accountId/*`, `/command-center` | `e2e/journeys/j10-layer-ui-validation.spec.ts`; `e2e/journeys/j10-layer-ui-validation-deep.spec.ts`; `e2e/navigation.spec.ts` | Admin, seller, restricted user | Loading, empty, error, unauthorized, and success states are asserted for each layer. | Navigation, sidebar, tabs, and fallback routes are keyboard-reachable. | Frontend Platform |

## P1 Workflows

| ID | Workflow | Primary routes | Required test evidence | Risk to monitor |
|---|---|---|---|---|
| P1-INTELLIGENCE | Intelligence workspace enrichment, stakeholders, signals, and ontology match | `/intelligence/:accountId`, `/intelligence/:accountId/enrichment`, `/intelligence/:accountId/stakeholders`, `/intelligence/:accountId/signals`, `/intelligence/:accountId/ontology-match` | `e2e/journeys/j2-intelligence-workspace.spec.ts`; `e2e/contracts/account-scoped-workspaces.spec.ts` | Data freshness, account context drift, stale enrichment status. |
| P1-STUDIO | Studio workspace parity with modern workflows | `/studio/:accountId`, `/studio/:accountId/action-plan`, `/studio/:accountId/value-model`, `/studio/:accountId/narrative`, `/studio/:accountId/roi`, `/studio/:accountId/evidence` | `e2e/journeys/j3-value-studio-deliverable.spec.ts`; `e2e/value-tree-explorer.spec.ts` | Legacy route drift and inconsistent account scoping. |
| P1-CONTEXT | Context sources, extraction, ontology, formulas, models, and value packs | `/context/sources`, `/context/extraction`, `/context/ontology`, `/context/formulas`, `/context/models`, `/context/packs` | `e2e/journeys/j1-ingestion-to-value-tree.spec.ts`; `e2e/journeys/j14-value-pack-governance.spec.ts`; `src/pages/ExtractionEngine.test.tsx`; `src/pages/ValuePacks.test.tsx`; `src/pages/formulaBuilderLogic.test.ts` | CRUD drift, importer failures, stale schema fixtures, value-pack version drift. |
| P1-STAKEHOLDERS | Stakeholder map and account relationship validation | `/intelligence/:accountId/stakeholders`, `/workflow/intelligence`, `/studio/:accountId` | `e2e/journeys/j13-stakeholder-mapping.spec.ts`; `e2e/journeys/j2-intelligence-workspace.spec.ts` | Relationship evidence drift and missing role-specific messaging states. |
| P1-NARRATIVE-PROPOSAL | Narrative, proposal, executive email, and mutual action plan generation | `/studio/:accountId/narrative`, `/deliverables`, `/workflow/value-case` | `e2e/journeys/j15-narrative-proposal.spec.ts`; `e2e/business-case.spec.ts`; `e2e/business-case-list.spec.ts` | Unsupported claim leakage, stale regeneration after model changes, export parity. |
| P1-COLLABORATION | Comments, mentions, shared visibility, edit conflict handling, and task handoff | `/accounts`, `/personal/notifications`, `/personal/tasks`, `/settings/team/*` | `e2e/journeys/j16-collaboration.spec.ts`; `e2e/collaboration/collaboration-notifications-tasks.spec.ts` | Notification reliability, restricted-account leakage, unresolved edit conflicts. |
| P1-SEARCH-SECURITY | Search and retrieval with tenant and role constraints | `/command-center`, `/context/*`, `/governance/evidence`, `/governance/traces` | `e2e/journeys/j18-search-retrieval.spec.ts`; `e2e/security/tenant-isolation-validation.spec.ts`; `e2e/security/tenant-isolation-deep.spec.ts` | Cross-tenant leakage, result-to-context routing drift, role-filter bypass. |
| P1-NOTIFICATIONS-TASKS | Notification and task lifecycle | `/personal/notifications`, `/personal/tasks`, `/accounts`, `/workflow/*` | `e2e/journeys/j19-notifications-tasks.spec.ts`; `e2e/collaboration/collaboration-notifications-tasks.spec.ts` | Missed completion states, stale badge counts, overdue-task filtering gaps. |
| P1-ADMIN-CONFIG | Tenant, user, value-pack, governance, retention, audit, and integration administration | `/settings/*`, `/settings/team/*`, `/settings/governance/*`, `/settings/data/*`, `/context/packs` | `e2e/journeys/j20-admin-configuration.spec.ts`; `e2e/admin.spec.ts`; `e2e/admin-system.spec.ts`; `e2e/contracts/settings-governance.spec.ts` | Sensitive action exposure, policy rollback gaps, audit export drift. |
| P1-RESILIENCE | Error, empty-state, retry, partial-state, and recovery workflows | `/context/*`, `/workflow/*`, `/calculator/:accountId`, `/deliverables`, `/realization/:accountId` | `e2e/journeys/j12-resilience-error-recovery.spec.ts`; `e2e/resilience/operational-resilience.spec.ts`; `e2e/journeys/j10-layer-ui-validation.spec.ts` | Happy-path-only regressions, unrecoverable failed jobs, unsaved-work loss. |
| P1-ADVERSARIAL | Full adversarial path with noisy data, prompt injection, weak evidence, and tenant controls | `/context/sources`, `/workflow/intelligence`, `/governance/evidence`, `/governance/traces`, `/deliverables` | `e2e/journeys/j22-adversarial-e2e.spec.ts`; `e2e/journeys/j9-agent-grounding-governance.spec.ts`; `e2e/security/tenant-isolation-deep.spec.ts` | Unsafe document-instruction handling, unsupported claims, hidden cross-tenant exposure. |
| P1-PERSONAS | Persona-based journeys for seller, value engineer, sales leader, CSM, admin, and executive buyer | `/accounts`, `/workflow/*`, `/studio/:accountId/*`, `/realization/:accountId`, `/settings/*`, `/deliverables/cases/:caseId` | `e2e/journeys/j21-persona-journeys.spec.ts`; `e2e/personas/persona-journeys.spec.ts` | Persona permissions drifting away from actual role-based UI behavior. |
| P1-SETTINGS | Tenant, team, billing, data, and governance settings | `/settings/*`, `/settings/team/*`, `/settings/billing/*`, `/settings/governance/*`, `/settings/data/*` | `e2e/admin.spec.ts`; `e2e/admin-system.spec.ts`; `e2e/contracts/settings-governance.spec.ts` | Role leakage, sensitive action exposure, audit gaps. |
| P1-PERSONAL | User profile, sessions, security, preferences, and notifications | `/personal/*` | `e2e/journeys/j23-personal-settings.spec.ts`; `e2e/collaboration/collaboration-notifications-tasks.spec.ts`; `src/components/layout/GlobalLayout.test.tsx` | Session-state drift, stale audit activity, and notification preference regression. |
| P1-INTEGRATIONS | CRM and external integration lifecycle | `/settings/data/integrations`, `/context/integrations`, `/dev/integration` | `e2e/integrations/crm-external-integrations.spec.ts`; `e2e/journeys/j17-crm-integration.spec.ts` | Mock/real API divergence and secret-handling UX. |

## P2 Watchlist

| Route or workflow | Required action |
|---|---|
| `/formula-builder` | Ensure the standalone route has explicit component or E2E coverage beyond broad navigation. |
| `/graph-explorer` | Ensure the standalone graph route has assertions for empty, success, and error states. |
| `/signup` and `/login/callback` | Keep auth lifecycle tests aligned with the deployed identity provider behavior. |
| `/dev/integration` | Keep development-only route gated and excluded from production-sensitive navigation. |
| Business-case document export variants | Keep PDF, DOCX, and slide export parity aligned with approval gates and evidence traceability. |
| Versioning and immutable audit reports | Expand frontend evidence once immutable-record views are productized. |
| Value realization post-sale measurement | Preserve CSM workflow coverage as realization planning moves beyond mocks. |

## Sprint Acceptance Checklist

| Sprint | Acceptance criteria |
|---|---|
| Sprint 1 | TypeScript, contract tests, full Vitest, build, and critical E2E guard pass locally. |
| Sprint 2 | Every P0 workflow has an owning test file, route list, persona expectation, resilience proof, and accessibility proof in this matrix. |
| Sprint 3 | Every P1 workflow has a route-family test owner and a documented risk to monitor. |
| Sprint 4 | P0 workflows include persona, accessibility, responsive navigation, and API failure-state coverage expectations. |
| Sprint 5 | Release confidence is automated through `verify:frontend`, workflow-matrix validation, bundle-budget validation, and fail-closed E2E guard checks. |
| Master inventory integration | Every uploaded production-readiness workflow maps to a P0/P1 owner, a P2 watchlist item, or a backend/platform validation matrix before release-candidate sign-off. |
