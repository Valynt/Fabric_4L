# Goal: Stage 2 — Evidence-to-Value Vertical Slice (Golden Journey)

## User Request

Implement the first complete, production-quality Fabric_4L vertical slice that demonstrates the core evidence-to-value thesis:

> Evidence enters the Fabric as observations. Fabric determines the economic meaning. Every material conclusion remains traceable to evidence, assumptions, calculations, and approvals.

A signed-in tenant user must be able to complete the golden journey end-to-end on real persisted application state (not static JSON embedded in UI components):

1. Create or select an account
2. Provide basic company context
3. Ingest evidence about the account
4. Inspect normalized evidence
5. View extracted business facts
6. See facts in the account knowledge model
7. Generate economic hypotheses
8. Convert hypotheses into explicit value drivers
9. Construct a quantified business case
10. Inspect evidence and assumptions behind every important number
11. Modify assumptions without changing source observations
12. Run scenarios (Conservative / Expected / Upside)
13. Submit the business case for review
14. Approve or reject it
15. Produce an approved value artifact
16. Revisit lineage for any material claim

## Refined Goal

Transform the existing Fabric_4L SaaS foundation (shell, auth, tenancy, billing, multi-layer services, frontend pages) into a **genuinely functional evidence-to-value system** where the golden journey works end-to-end with real persisted state.

The project already contains extensive infrastructure across L1–L6 services, frontend pages, contracts, and tests. **Do not rebuild working infrastructure.** Instead:

1. **Audit** what already exists in the backend APIs, frontend pages, database models, and orchestration
2. **Close gaps** — connect disconnected CRUD screens into a cohesive workflow with real state flow
3. **Implement missing pieces** — deterministic calculation engine, explicit assumption registry, evidence-to-value lineage, review/approval workflow, scenario modeling, deliverable generation
4. **Harden** — tenant isolation, authorization, audit trail, deterministic economics (no LLM-as-calculator), unit safety, schema contracts
5. **Verify** — golden journey E2E test passes, targeted backend tests pass, build passes, runtime verification succeeds

Preserve the repository's six-layer architecture, DESIGN.md frontend governance, and existing conventions. Reuse existing pages, APIs, and patterns where they already work; replace weak scaffolding only where necessary.

## Acceptance Criteria

- [ ] Criterion 1 — **Account workspace functional**: A signed-in tenant user can create/select an account, view account context, and see current journey state with next-best-action guidance.
- [ ] Criterion 2 — **Evidence ingestion → extraction → knowledge pipeline works**: Evidence can be added (manual account context, document/text evidence, URL evidence where safe). Evidence is normalized into `EvidenceItem`/`ExtractedFact` with immutable lineage back to source. Extracted facts appear in the account knowledge model (graph or relational, matching repository's approved persistence strategy).
- [ ] Criterion 3 — **Hypothesis generation and acceptance**: The system can propose hypotheses from evidence. Hypotheses have explicit status lifecycle (`PROPOSED` → `SUPPORTED` / `NEEDS_EVIDENCE` / `ACCEPTED` / `REJECTED`). Accepted hypotheses feed into value-driver creation. Contradictory evidence is surfaced, not discarded.
- [ ] Criterion 4 — **Value drivers with deterministic calculation**: Value drivers separate `observed inputs`, `assumed inputs`, `benchmark inputs`, `formula`, and `output`. A deterministic calculation engine executes formulas (addition, subtraction, multiplication, division, percentage, annualization, baseline vs target, delta). LLMs propose structures and candidate formulas; the application code is the authoritative calculator.
- [ ] Criterion 5 — **Scenario modeling**: Conservative / Expected / Upside scenarios override explicit model variables and trigger deterministic recalculation. Scenario definitions are persisted.
- [ ] Criterion 6 — **Business case aggregate**: A business case contains account scope, hypotheses, value drivers, assumptions, scenarios, benefits, costs, risks, timeline, evidence lineage, and approval state. It calculates annual benefit, implementation cost, net benefit, ROI, and payback period.
- [ ] Criterion 7 — **Evidence-to-value lineage is inspectable**: From any calculated number, a user can trace backward through assumptions → value driver → hypothesis → evidence → source without leaving the workflow. Lineage is a reusable structured representation, not reconstructed from display strings.
- [ ] Criterion 8 — **Review and approval workflow**: Business cases transition through `DRAFT` → `READY_FOR_REVIEW` → `IN_REVIEW` → `APPROVED` / `REJECTED` / `CHANGES_REQUESTED`. Approval captures reviewer, timestamp, artifact version, calculation version, material assumptions, decision, and comment. Changing material assumptions after approval invalidates/supersedes the approval. Agents cannot self-approve.
- [ ] Criterion 9 — **Approved deliverable generation**: Approved business cases produce a durable artifact (structured executive summary, value summary, or approved JSON snapshot). The structured snapshot remains authoritative; any export is a representation.
- [ ] Criterion 10 — **Tenant isolation and authorization**: Every tenant-owned resource is scoped from server-side authenticated authorization context. Negative tests prove hostile cross-tenant access is rejected. UI hiding is not authorization — server-side policy enforcement is.
- [ ] Criterion 11 — **Deterministic calculation tests pass**: Formulas calculate correctly, changes propagate, scenarios recalculate, invalid units fail, divide-by-zero fails safely.
- [ ] Criterion 12 — **Golden journey E2E test passes**: An automated browser or API-level test exercises the full flow from sign-in → account creation → evidence ingestion → hypothesis → value driver → business case → scenario change → submission → approval → approved artifact retrieval, validating meaningful domain outcomes (not just page navigation).
- [ ] Criterion 13 — **Build and runtime verification**: `pnpm --dir apps/web run build` succeeds. Backend services start. The application responds at root. Authentication works. Protected routes reject unauthenticated access. Demo account can be loaded. Evidence, hypothesis, value model, and review workflow persist correctly.
- [ ] Criterion 14 — **Audit trail for material actions**: Events are captured for evidence added, hypothesis created/accepted, assumption changed, scenario changed, model recalculated, review submitted, approval granted/revoked, deliverable generated. No secrets or sensitive content in audit logs.
- [ ] Criterion 15 — **Semantic classification preserved**: Every material piece of information has a semantic class (`OBSERVED`, `EXTRACTED`, `INFERRED`, `ASSUMED`, `CALCULATED`, `BENCHMARKED`, `USER_PROVIDED`, `APPROVED`). Provenance quality is tracked (`TRACEABLE`, `PARTIALLY_TRACEABLE`, `OPAQUE`). OPAQUE information never silently receives the same confidence as traceable evidence.
- [ ] Criterion 16 — **No synthetic truth leakage**: If demo data is used, it is explicitly marked `DEMO` and impossible to confuse with production evidence. AI-generated text is not represented as evidence merely because it sounds plausible.
- [ ] Criterion 17 — **UI coheres around user jobs**: The account workspace uses the existing DESIGN.md shell patterns (horizontal tabs, right-rail detail panels, shared primitives). Navigation is Overview → Evidence → Knowledge → Hypotheses → Value Drivers → Business Case → Review → Activity. Pages are not disconnected database table viewers.

## Scope Boundaries

**In scope:**
- Backend domain models, APIs, and persistence for: accounts, evidence/sources/items/facts, knowledge entities (organization, product, process, metric, pain point, capability, etc.), hypotheses, value drivers, assumptions, business cases, scenarios, reviews/approvals, lineage
- Deterministic calculation engine with typed variables, units, formulas, dependency graphs, recalculation, validation, scenario overrides
- Tool registry formalization with declared schemas, permissions, tenant scope, audit requirements
- Event catalog formalization with versioned schemas for the vertical slice
- Schema registry / contracts for API, event, tool, and agent payloads
- Frontend account workspace pages and components cohering the journey
- Review/approval workflow UI and backend
- Evidence-to-value lineage visualization
- Scenario controls in Value Studio
- Golden reference demo account (fictional company, explicitly marked DEMO)
- Golden journey E2E test
- Tenant isolation negative tests
- Deterministic calculation tests
- Audit trail instrumentation for material operations
- Agent run contracts for material agent executions
- Critic/verification pass before `READY_FOR_REVIEW`

**Out of scope:**
- Introducing a new database system if the repository's approved strategy already supports the needed persistence (e.g., adding Neo4j if only PostgreSQL is currently approved, unless Neo4j is already configured)
- PDF generation unless already available in the codebase
- Live external enrichment provider integrations (may be represented behind interfaces)
- Multi-year NPV / DCF unless underlying variables already support it
- Comprehensive benchmark dataset population (provider abstraction + normalized contract is enough)
- Full RBAC/ABAC policy engine beyond the permissions needed for the golden journey
- Rewriting working frontend components that already conform to DESIGN.md
- Rewriting working backend services that already provide the needed capabilities
- Fixing pre-existing unrelated bugs unless they block the golden journey

## Applicable Project Conventions

**Quality gate commands:**
- `make verify` (full platform verification)
- `pnpm --dir apps/web run build`
- `pnpm --dir apps/web run test`
- `pnpm --dir apps/web run test:e2e` or `pnpm --dir apps/web run test:e2e:golden:j1:canonical`
- `pytest services/layer3-knowledge/tests/security/ -p no:randomly`
- `pytest tests/contract/`
- `pytest tests/security/`
- `python scripts/ci/check_layer3_cypher_scope.py services/layer3-knowledge/src --report-json`
- `make check-behavior-contract`
- `pnpm run check:contract-compliance`

**Commit convention:**
- Conventional commits, title ≤72 chars, imperative mood
- Builder commits: `type(scope): [B] description` + `Assisted-by: OpenAI:GPT-5.6 Luna`
- Inspector commits: `chore(scope): [I] description` + `Assisted-by: OpenAI:GPT-5.6 Sol`
- Trailer: `Co-authored-by: Copilot App <223556219+Copilot@users.noreply.github.com>`

**Guidelines:**
- `AGENTS.md` (root and per-service)
- `DESIGN.md` (frontend governance)
- `docs/contract.md` (platform contract)
- `docs/development/DISCOVERY_MAP.md` (issue-to-implementation routing)
- `docs/governance.md` (engineering governance)
- `docs/governance/behavior-first-testing.md`

**Rules:**
- Preserve six-layer architecture boundaries
- Tenant isolation is a hard invariant — every data read/write must be scoped by authenticated tenant context
- Deterministic calculations only — LLMs propose structures, application code executes math
- Contract-first — update OpenAPI/JSON Schema/TypeScript types when API behavior changes
- Do not use `npm install` or `yarn install` — pnpm only
- Do not commit secrets
- Do not weaken auth, RBAC, tenant isolation, rate limiting, audit logging, or governance middleware
- Semantic classes must be preserved: `OBSERVED != EXTRACTED != INFERRED != ASSUMED != CALCULATED != BENCHMARKED != USER_PROVIDED != APPROVED`
