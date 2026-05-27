# Value Fabric — Production Launch Readiness Audit & Remediation Plan

> **Plan Mode:** This document is the implementation plan. Upon approval, the audit deliverable will be generated as a standalone markdown file in `docs/audit/` or `artifacts/audit/`.

---

## Implemented Fixes (Post-Audit)

The following P0 launch blockers were remediated immediately after audit approval:

1. **PROD-P0-006 — Admin Permission Wildcard**  
   - Replaced wildcard `permission.startswith("admin:")` and `"all"` patterns in `require_admin` with an explicit `_ADMIN_PERMISSION_ALLOWLIST`.
   - Added regression tests in `packages/shared/src/value_fabric/shared/identity/tests/test_dependencies.py`.
   - Files changed: `packages/shared/src/value_fabric/shared/identity/dependencies.py`

2. **PROD-P0-004 — Frontend Mock Fallback in Production Builds**  
   - Extended `apps/web/scripts/security/assert-no-dev-auth-bypass-in-production.mjs` to block `VITE_ENABLE_MOCK_FALLBACK` and `ENABLE_MOCK_FALLBACK` in production bundles.
   - File changed: `apps/web/scripts/security/assert-no-dev-auth-bypass-in-production.mjs`

3. **PROD-P0-005 — Duplicate Source Trees L1/L2**  
   - Canonicalized Layer 2 shim: removed `configure_structured_logging` from `value_fabric/layer2/__init__.py`, moved it to `services/layer2-extraction/src/layer2_extraction/logging_config.py`, and moved the smoke test to the canonical test tree.
   - `scripts/ci/check_duplicate_source_trees.py` now reports **zero violations**.
   - Files changed: `value_fabric/layer2/__init__.py`, `services/layer2-extraction/src/layer2_extraction/logging_config.py`, `services/layer2-extraction/tests/test_structured_logging_smoke.py`

4. **PROD-P0-003 — DEV_AUTH_BYPASS Hardening**  
   - Re-audited all service entrypoints: `validate_production_safety()` is **already called at startup** in L1–L6 and the API gateway. No code changes required; risk was overstated in initial assessment.

5. **PROD-P0-002 — Quarantined Tests**  
   - Audited `tests/quarantine/`: only one test remains (`test_docker_integration.py`), resolution date 2026-05-01 is **overdue by 26 days**. Updated README with escalation flag.
   - File changed: `tests/quarantine/README.md`

---

## Executive Summary

### Overall Production Readiness Score: **6.8 / 10**

**Confidence:** Medium-High

Value Fabric is a sophisticated, six-layer enterprise SaaS platform with exceptional governance discipline, contract-first architecture, and strong security foundations. The codebase demonstrates maturity far beyond typical pre-launch startups: 60+ CI workflows, comprehensive tenant isolation tests, provider-agnostic AI agent design, Kubernetes production manifests, and structured operational runbooks.

However, **the platform is not yet production-ready** for security-conscious enterprise customers without remediation. The gap between "strong governance on paper" and "production-hardened execution" is widest in three areas:

1. **Type safety and technical debt** in Layer 4 (the most business-critical agent orchestration layer) where ~100 modules have mypy overrides.
2. **Test flakiness and quarantine** — a non-trivial number of tests are isolated in `tests/quarantine/`, and the backend-integrated test suite requires live infrastructure that may not be fully stable.
3. **Frontend bundle weight and runtime validation** — heavy dependencies (Recharts, Framer Motion) and mock fallback enabled by default create performance and reliability risks.
4. **Layer 7 Billing is nascent** — missing full CI coverage and may not support production billing workflows.
5. **Duplicate source tree canonicalization** in L1/L2 indicates architectural migration is incomplete.

**Estimated launch readiness status:** **Beta-ready with controlled rollout**, conditional on completing Phase 0–2 of the remediation roadmap. Not yet suitable for broad enterprise GA.

### Top 10 Risks

| # | Risk | Severity | Evidence |
|---|------|----------|----------|
| 1 | Layer 4 mypy override debt (~130 modules, 35 error codes disabled) creates runtime type safety gaps | High | `services/layer4-agents/pyproject.toml` |
| 2 | `DEV_AUTH_BYPASS=true` in docker-compose.dev.yml could leak to prod-like environments | High | `docker-compose.dev.yml:213,250` |
| 3 | Frontend mock fallback enabled by default (`VITE_ENABLE_MOCK_FALLBACK=true`) risks serving stale mock data | Medium-High | `docker-compose.dev.yml:332` |
| 4 | Layer 3 monolith code freeze suggests unresolved architectural debt | Medium-High | `check_l3_monolith_freeze.py` in CI |
| 5 | Layer 7 Billing lacks CI coverage and production maturity | Medium | `services/layer7-billing/` minimal structure |
| 6 | Heavy frontend bundle deps (Recharts, Framer Motion) without strict budget enforcement in CI | Medium | `apps/web/package.json` deps |
| 7 | No root `pyproject.toml` complicates cross-service dependency management | Medium | Intentional but friction-heavy |
| 8 | `pytest.ini` sets `ALLOW_DEV_AUTH_BYPASS=I_UNDERSTAND_RISK` in test env — could mask production misconfig | Medium | `pytest.ini:101` |
| 9 | K8s overlay secret placeholders may leak to production | Medium | `k8s/base/kustomization.yaml:44-50` |
| 10 | Backend-integrated test suite stability is unknown | Medium | `tests/backend_integrated/` requires live stack |

### Top 10 Recommended Actions

1. **Mandatory mypy remediation sprint for Layer 4** — remove `disable_error_code` overrides module-by-module.
2. **Audit and restore or delete quarantined tests** — each test must have an owner and a remediation date.
3. **Harden DEV_AUTH_BYPASS enforcement** — add startup-time `ProductionSafetyValidator` to every service, not just L4.
4. **Disable mock fallback in production builds** — make `VITE_ENABLE_MOCK_FALLBACK=false` the build default.
5. **Complete L1/L2 source tree canonicalization** — eliminate duplicate logic, enforce via CI.
6. **Add Layer 7 Billing to PR checks** with coverage gate and security scan.
7. **Enforce bundle budget in CI** — fail PRs that exceed webpack/rollup budget.
8. **Run full backend-integrated test suite weekly** and trend pass rates.
9. **Validate all K8s overlays with real secret references** — currently some overlays use placeholder secrets.
10. **Create production runbook for incident response** with explicit on-call escalation paths.

---

## System Map

### Repo Structure

```
Fabric_4L/
├── apps/web/                    # React 19 + Vite + Tailwind + shadcn/ui frontend
├── services/
│   ├── api/                     # API gateway / auth enforcement
│   ├── layer1-ingestion/        # Playwright crawling, Celery, Redis (port 8001)
│   ├── layer2-extraction/       # Pydantic v2 extraction, RDF/OWL (port 8002)
│   ├── layer2-5-signal-refinery/# Signal bridge (port 8007)
│   ├── layer3-knowledge/        # Neo4j, GraphRAG, pgvector (port 8003)
│   ├── layer4-agents/           # LangGraph workflows, ROI calculator (port 8004)
│   ├── layer5-ground-truth/     # TruthObject validation (port 8005)
│   ├── layer6-benchmarks/       # Peer comparison, stats (port 8006)
│   └── layer7-billing/          # Emerging billing service
├── value_fabric/                # Runtime Python shims (ADR-027)
├── packages/
│   ├── shared/                  # Tenant context, base models
│   ├── platform-contract/       # Cross-layer contracts
│   └── eslint-plugin-fabric-contracts/
├── contracts/                   # OpenAPI specs, JSON Schemas
├── tests/                       # Cross-layer contract, security, e2e tests
├── k8s/                         # K8s manifests, HPA, network policies
├── monitoring/                  # Prometheus, Grafana, Loki, Alertmanager
├── docs/                        # Diátaxis docs, ADRs, runbooks
└── scripts/ci/                  # 100+ CI gate scripts
```

### Key Runtime Dependencies

| Concern | Technology |
|---------|-----------|
| Frontend framework | React 19, Vite 7, TypeScript 5.6 |
| Frontend state | TanStack Query 5, Zustand 5 |
| Frontend auth | Clerk React |
| Frontend UI | shadcn/ui, Radix primitives, Tailwind 4 |
| Backend framework | FastAPI (Python 3.11) |
| Async DB | asyncpg, SQLAlchemy 2 |
| Graph DB | Neo4j 5 + APOC |
| Cache/Queue | Redis 7, Celery |
| Vector DB | Qdrant (local), Pinecone (prod) |
| Object Storage | MinIO (local), S3 (prod) |
| Auth/IdP | Clerk (primary), Keycloak 25 (OIDC broker) |
| AI/LLM | LangGraph, LangChain, OpenAI, Anthropic, Together |
| Orchestration | Kubernetes + Kustomize |
| Observability | Prometheus, Grafana, Loki, Fluent-bit, Jaeger |

### Key Data Stores

- **PostgreSQL 15** — Per-layer databases (ingestion, extraction, signal_refinery, layer4_agents, ground_truth, benchmarks)
- **Neo4j 5** — Knowledge graph (Layer 3)
- **Redis 7** — Caching, Celery broker, pub/sub
- **Qdrant** — Vector search (development)
- **MinIO** — S3-compatible object storage (development)

### Main User Flows

1. **Ingestion** — User submits URL/document → L1 crawls/extracts → L2 structures entities → L3 builds graph → L4 runs agent workflow → L5 validates → L6 benchmarks
2. **Value Studio** — User creates formula/ontology → L4 calculates ROI → L5 validates claims → UI presents business case
3. **Account Management** — Clerk auth → tenant/workspace selection → RBAC-scoped data access
4. **Agent Grounding** — User reviews agent output → evidence traceability → L5 TruthObject approval

### Main API Flows

- Frontend → API Gateway (`services/api/`) → Layer-specific FastAPI services
- Inter-layer HTTP calls via configured `LAYERX_LAYERY_API_URL` env vars
- Internal auth via Fabric JWT (RS256) between gateway and downstream services

### Deployment Model

- **Local:** Docker Compose (`docker-compose.dev.yml`) with auth bypass
- **Production:** Kubernetes (Kustomize base + overlays), External Secrets Operator, HPA, PDB
- **CI:** GitHub Actions (60+ workflows), Infisical OIDC secret injection
- **Registry:** GHCR (`ghcr.io/bmsull560/fabric_4l/*`)

---

## Scorecard

| Category | Score | Confidence | Evidence | Main Blockers | Recommended Next Action |
|----------|-------|-----------|----------|---------------|------------------------|
| Architecture | 7.5 | High | Clear 6-layer boundaries, ADRs, canonical path policy | Duplicate source trees L1/L2, L3 monolith freeze, no root pyproject.toml | Complete canonicalization; unblock L3 refactor |
| Frontend | 7.0 | Medium-High | DESIGN.md governance, typed API client, a11y tests | Bundle weight, mock fallback default, heavy deps | Enforce bundle budget; disable mock fallback in prod |
| Backend | 7.5 | High | FastAPI, Pydantic v2, per-layer pyproject.toml, uv | L4 mypy override debt (~100 modules), L7 billing immature | L4 type safety sprint; mature L7 CI |
| Data Model & Migrations | 7.0 | High | Alembic per service, 88 migration files, PostgreSQL RLS | Missing migration for some layers? (L3, L6 no alembic.ini found) | Verify L3/L6 migration strategy; add if missing |
| Security | 8.0 | Medium-High | 60+ security workflows, bandit, pip-audit, gitleaks, semgrep, CodeQL, ZAP, tenant isolation tests | DEV_AUTH_BYPASS leakage risk, test env allows bypass | Harden bypass enforcement across all services |
| Multi-tenancy | 8.5 | High | Tenant isolation tests, RLS policies, JWT tenant claims, boundary static checks | Some legacy tenant access shims exist | Enforce shim lifecycle phase control |
| Testing | 7.0 | Medium-High | 40+ pytest markers, contract tests, Playwright E2E, k6 perf | Quarantined tests, flaky marker, backend-integrated needs live infra | Restore quarantine; stabilize integrated suite |
| Observability | 7.5 | High | Prometheus alerts, Grafana, Loki, runbooks, Jaeger runbook | Runbook URLs point to `wiki.internal` (not reachable) | Update runbook URLs to real docs; validate dashboards |
| Performance | 6.5 | Medium | k6 load tests, SLO evaluation, HPA configs, PgBouncer | No CDN config visible, bundle budget not enforced in CI | Add CDN; enforce bundle budget; run load tests |
| Infrastructure/Deployment | 7.5 | High | K8s manifests, HPA, PDB, network policies, backup cronjobs | Some overlays use placeholder secrets; no prod TLS/ingress detail visible | Validate all overlays with real secrets; add ingress TLS |
| CI/CD | 8.5 | High | 60+ workflows, Trivy scanning, SBOM generation, signed artifacts | Runtime-contract checks skip on fork PRs; integration checks fragile | Stabilize integration test job; reduce fork skip surface |
| Developer Experience | 6.5 | Medium | Makefile, dev containers, Infisical, pnpm | Complex setup (7+ steps), high barrier to entry | Simplify onboarding; add devcontainer verification |
| Documentation | 7.5 | High | Diátaxis structure, 38+ runbooks, ADRs, API reference | Some runbooks have TBD placeholders (enforced in CI but worth monitoring) | Complete any remaining TBDs |
| Product Completeness | 6.5 | Medium | 6 layers functional, L7 billing nascent | Billing not production-ready; some layers may have feature gaps | Mature L7; conduct product gap analysis |
| **Production Readiness Overall** | **6.8** | **Medium-High** | Strong governance, not yet hardened for broad GA | L4 type debt, quarantined tests, L7 immaturity, bundle weight | Execute Phase 0–2 of roadmap |

---

## P0 Launch Blockers

### PROD-P0-001: Layer 4 Mypy Override Debt Creates Runtime Type Safety Gaps
- **Severity:** P0
- **Category:** Backend / Type Safety
- **Description:** `services/layer4-agents/pyproject.toml` contains extensive `disable_error_code` overrides across ~100 modules. This masks type errors in the most business-critical layer (agent orchestration, ROI calculator, business case generation).
- **Why it matters:** Agent workflows handle customer data and financial calculations. Type errors at runtime can cause data corruption, wrong calculations, or agent loops.
- **Evidence:** `services/layer4-agents/pyproject.toml` mypy section
- **Acceptance criteria:** Reduce mypy overrides by 80%; all new code passes strict mypy; CI gate prevents new overrides.
- **Suggested implementation:** Module-by-module remediation sprint; add `mypy --strict` to CI with zero-tolerance for new overrides.
- **Suggested tests:** Existing `typecheck-layer4` target; add regression test that counts override lines.
- **Estimated effort:** L
- **Dependencies:** None
- **Owner suggestion:** Backend

### PROD-P0-002: Quarantined Tests Indicate Unstable Critical Paths
- **Severity:** P0
- **Category:** Testing / Reliability
- **Description:** `tests/quarantine/` directory exists with unknown contents. Quarantined tests represent critical paths that are known to fail or are unstable.
- **Why it matters:** Launching with unknown failing tests means unknown production failure modes.
- **Evidence:** `tests/quarantine/` directory; `pytest.ini:19` ignores this directory
- **Acceptance criteria:** Every quarantined test is either restored with owner-assigned fix date, or permanently deleted with documented rationale.
- **Suggested implementation:** Audit `tests/quarantine/`; create tickets for each test file; assign owners; set 2-week remediation SLA.
- **Suggested tests:** Run each quarantined test individually to understand failure mode.
- **Estimated effort:** M
- **Dependencies:** None
- **Owner suggestion:** QA / Backend

### PROD-P0-003: DEV_AUTH_BYPASS Could Leak to Production-Like Environments
- **Severity:** P0
- **Category:** Security / Auth
- **Description:** `DEV_AUTH_BYPASS=true` is present in `docker-compose.dev.yml` and `pytest.ini`. While CI checks for dev auth bypass in production compose files, there is no guarantee every service binary has `ProductionSafetyValidator` at startup.
- **Why it matters:** If a production-like environment accidentally inherits dev compose values, all tenant isolation and auth is bypassed.
- **Evidence:** `docker-compose.dev.yml:213,250`; `pytest.ini:101`; `.github/scripts/check-dev-auth-bypass.sh`
- **Acceptance criteria:** Every service (L1–L6, API, frontend build) fails startup if `DEV_AUTH_BYPASS` or `ALLOW_DEV_AUTH_BYPASS` is truthy and `ENVIRONMENT != development`. CI validates this with unit tests.
- **Suggested implementation:** Add `ProductionSafetyValidator` to `services/api/`, `services/layer1-ingestion/`, `services/layer2-extraction/`, `services/layer3-knowledge/`, `services/layer5-ground-truth/`, `services/layer6-benchmarks/` entrypoints.
- **Suggested tests:** `tests/security/test_production_safety_validator.py` for each service.
- **Estimated effort:** M
- **Dependencies:** None
- **Owner suggestion:** Security / Backend

### PROD-P0-004: Frontend Mock Fallback Enabled by Default in Docker Compose
- **Severity:** P0
- **Category:** Frontend / Reliability
- **Description:** `docker-compose.dev.yml` sets `VITE_ENABLE_MOCK_FALLBACK=true` for the frontend. If this value is accidentally promoted to staging or production, the frontend will serve mock data instead of calling real APIs.
- **Why it matters:** Users would see fake data, think the product works, and make business decisions on hallucinated outputs.
- **Evidence:** `docker-compose.dev.yml:332`
- **Acceptance criteria:** Production frontend builds fail if `VITE_ENABLE_MOCK_FALLBACK` is not explicitly `false`. Docker compose prod file defaults to `false`.
- **Suggested implementation:** Add build-time assertion in `vite.config.ts`; add CI check in `assert-no-dev-auth-bypass-in-production.mjs` (or equivalent).
- **Suggested tests:** `test:prod-auth-bypass` already exists; extend to cover mock fallback.
- **Estimated effort:** S
- **Dependencies:** None
- **Owner suggestion:** Frontend

### PROD-P0-005: Duplicate Source Trees in L1/L2 Create Drift Risk
- **Severity:** P0
- **Category:** Architecture / Maintainability
- **Description:** CI runs `check_duplicate_source_trees.py` for layers 1 and 2, indicating logic exists in both canonical `services/` paths and legacy `value_fabric/` shims.
- **Why it matters:** Bug fixes in one tree may not propagate to the other. Security patches could be missed.
- **Evidence:** `scripts/ci/check_duplicate_source_trees.py`; CI job in `pr-checks.yml`
- **Acceptance criteria:** Zero duplicate source trees reported by CI; `value_fabric/` contains only thin re-export shims.
- **Suggested implementation:** Canonicalization sprint for L1 and L2; move all logic to `services/`; update imports.
- **Suggested tests:** Existing CI gate already catches this; enforce as blocking.
- **Estimated effort:** L
- **Dependencies:** None
- **Owner suggestion:** Backend / Platform

### PROD-P0-006: Admin Permission Wildcard in RBAC Policy Registry
- **Severity:** P0
- **Category:** Security / Authorization
- **Description:** `require_admin` in the shared identity policy registry uses wildcard patterns (`"all"` and `startswith("admin:")`) to determine admin privileges. If JWT claim filtering is bypassed or a token is manipulated to include `"all"`, privilege escalation is possible.
- **Why it matters:** Admin endpoints handle sensitive operations (tenant management, billing, audit). A wildcard permission model increases blast radius of auth bypass.
- **Evidence:** `packages/shared/src/value_fabric/shared/identity/policy_registry.py`
- **Acceptance criteria:** Admin permissions use explicit allowlist (no wildcards); `require_admin` rejects tokens with `"all"` claim unless explicitly mapped in policy registry; regression tests cover wildcard rejection.
- **Suggested implementation:** Replace wildcard with explicit admin role enumeration; add validation that rejects `"all"` and `startswith("admin:")` patterns in JWT claims.
- **Suggested tests:** `tests/security/test_rbac.py` — add test that token with `"all"` claim is rejected by `require_admin`.
- **Estimated effort:** M
- **Dependencies:** None
- **Owner suggestion:** Security / Backend

---

## P1 Production Hardening

### PROD-P1-001: Layer 7 Billing Needs CI Coverage and Production Maturity
- **Severity:** P1
- **Category:** Backend / Product
- **Description:** `services/layer7-billing/` exists but has minimal structure compared to L1–L6. It is not included in per-layer PR checks.
- **Why it matters:** Enterprise SaaS requires reliable billing. An immature billing layer blocks monetization and creates legal/compliance risk.
- **Evidence:** `services/layer7-billing/` directory (minimal); `pr-checks.yml` has no `layer7-checks` job
- **Acceptance criteria:** Layer 7 has lint, typecheck, test, coverage, bandit, and pip-audit jobs in `pr-checks.yml`; coverage gate ≥70%.
- **Estimated effort:** M
- **Owner suggestion:** Backend / Product

### PROD-P1-002: Bundle Budget Not Enforced in CI
- **Severity:** P1
- **Category:** Frontend / Performance
- **Description:** `test:bundle-budget` exists but the CI `frontend-checks` job only runs `build:analyze`; it does not fail on budget overrun.
- **Why it matters:** Heavy deps (Recharts, Framer Motion) can bloat the bundle, degrading mobile performance and increasing hosting costs.
- **Evidence:** `apps/web/package.json:23`; `pr-checks.yml:1114` runs `build:analyze` but no budget gate
- **Acceptance criteria:** CI fails if bundle size exceeds budget thresholds for initial chunk and async routes.
- **Estimated effort:** S
- **Owner suggestion:** Frontend

### PROD-P1-003: Backend-Integrated Test Suite Stability
- **Severity:** P1
- **Category:** Testing / Reliability
- **Description:** `test-backend-integrated-validation` and `test-backend-integrated-release-smoke` require live Docker Compose stack. These tests are complex and may be flaky.
- **Why it matters:** If the integrated suite is unstable, engineers will ignore failures, allowing regressions to reach production.
- **Evidence:** `Makefile:223-228`; `tests/backend_integrated/` directory
- **Acceptance criteria:** Integrated test pass rate ≥95% over 4 consecutive weekly runs; no tests in `quarantine/` from this suite.
- **Estimated effort:** M
- **Owner suggestion:** QA / Platform

### PROD-P1-004: K8s Overlay Secret Placeholders
- **Severity:** P1
- **Category:** Infrastructure / Security
- **Description:** K8s base manifests include placeholder secrets and comments warning about production values. If overlays are not carefully maintained, placeholder secrets could be deployed.
- **Why it matters:** Deploying default/placeholder secrets compromises the entire tenant isolation model.
- **Evidence:** `k8s/base/kustomization.yaml:44-50`; `k8s/base/jwt-keys-secret.yaml`; `k8s/base/api-key-cache-secret.yaml`
- **Acceptance criteria:** Every overlay has validated External Secrets Operator references; CI dry-run fails on placeholder secrets.
- **Estimated effort:** M
- **Owner suggestion:** Platform / Security

### PROD-P1-005: Runbook URLs Point to Internal Wiki
- **Severity:** P1
- **Category:** Observability / Operations
- **Description:** Prometheus alert rules reference `https://wiki.internal/runbooks/...` which is not reachable outside the corporate network.
- **Why it matters:** On-call engineers need runbooks during incidents. Broken links increase MTTR.
- **Evidence:** `monitoring/layer1-alerts.yml:18,29,43,54,68,79,90` and similar in other alert files
- **Acceptance criteria:** All `runbook_url` annotations point to `docs/troubleshooting/runbooks/` markdown files in the repo or a public docs site.
- **Estimated effort:** S
- **Owner suggestion:** Platform / SRE

### PROD-P1-006: Layer 3 Monolith Code Freeze Debt
- **Severity:** P1
- **Category:** Architecture / Maintainability
- **Description:** CI enforces `check_l3_monolith_freeze.py` (ARCH-L3-007), indicating Layer 3 has architectural debt that is frozen to prevent further monolithic growth.
- **Why it matters:** A frozen monolith limits scalability and makes refactor risky. The freeze is a containment measure, not a fix.
- **Evidence:** `pr-checks.yml:643-648`
- **Acceptance criteria:** Publish L3 decomposition roadmap; remove freeze once bounded contexts are extracted.
- **Estimated effort:** L
- **Owner suggestion:** Backend / Architecture

### PROD-P1-007: PostgreSQL RLS Enforcement Gaps
- **Severity:** P1
- **Category:** Security / Data
- **Description:** While RLS policies exist for some layers, not all layers may have comprehensive RLS. The `test_rls_enforcement_postgres.py` is gated behind `requires_postgres` marker.
- **Why it matters:** Without RLS on every tenant-scoped table, a SQL injection or ORM bypass could expose cross-tenant data.
- **Evidence:** `services/layer1-ingestion/tests/security/test_rls_enforcement_postgres.py`; `pytest.ini:84` marker
- **Acceptance criteria:** Every tenant-scoped table in every layer has RLS policies; RLS tests run in CI (not skipped).
- **Estimated effort:** M
- **Owner suggestion:** Security / Data

### PROD-P1-008: Frontend Accessibility Keyboard-Flow Coverage
- **Severity:** P1
- **Category:** Frontend / Accessibility
- **Description:** Accessibility tests exist but keyboard-flow E2E may not cover all critical user journeys.
- **Why it matters:** Enterprise customers require WCAG 2.1 AA compliance for procurement.
- **Evidence:** `apps/web/package.json:39`; `pr-checks.yml:1173-1178`
- **Acceptance criteria:** Keyboard-flow tests cover ingestion, value studio, agent review, and account settings journeys.
- **Estimated effort:** M
- **Owner suggestion:** Frontend / QA

### PROD-P1-009: HSTS Header Missing from Application Middleware
- **Severity:** P1
- **Category:** Security / Headers
- **Description:** HSTS (HTTP Strict Transport Security) header is not set in application-level middleware. The project appears to rely on ingress-level HSTS, which may fail if ingress is misconfigured or bypassed.
- **Why it matters:** Without HSTS, clients may fall back to HTTP, enabling downgrade attacks and cookie theft.
- **Evidence:** Security middleware review; no `Strict-Transport-Security` in shared FastAPI app factory.
- **Acceptance criteria:** HSTS header (`max-age=31536000; includeSubDomains; preload`) is set by application middleware in all non-development environments; CI validates header presence.
- **Suggested implementation:** Add HSTS middleware to `packages/shared/src/value_fabric/shared/fastapi_framework/app.py`; gate behind `ENVIRONMENT != development`.
- **Suggested tests:** `tests/security/test_security_misconfiguration.py` — assert HSTS header present.
- **Estimated effort:** S
- **Dependencies:** None
- **Owner suggestion:** Security / Backend

### PROD-P1-010: External API Keys in Frontend Bundle (Frontend Forge, Analytics)
- **Severity:** P1
- **Category:** Security / Frontend
- **Description:** `VITE_FRONTEND_FORGE_API_KEY` and `VITE_FRONTEND_FORGE_API_URL` are referenced in `components/Map.tsx`; `VITE_ANALYTICS_ENDPOINT` and `VITE_ANALYTICS_WEBSITE_ID` in `lib/analytics.ts`. While these are public client-side values, they should be rotated regularly and scoped to the deployment domain.
- **Why it matters:** If keys are leaked or domains are not restricted, third parties could impersonate the application or consume API quota.
- **Evidence:** `apps/web/src/components/Map.tsx`; `apps/web/src/lib/analytics.ts`; `.env.example`
- **Acceptance criteria:** All external API keys are domain-restricted; rotation runbook exists; no unrestricted keys in `.env.example`.
- **Suggested implementation:** Verify domain restrictions on Frontend Forge and Analytics accounts; add key rotation to secret rotation workflow.
- **Suggested tests:** Manual verification of domain restrictions.
- **Estimated effort:** S
- **Dependencies:** None
- **Owner suggestion:** Security / Frontend

---

## P2 Quality and Maintainability

### PROD-P2-001: Root pyproject.toml Missing
- **Severity:** P2
- **Category:** Developer Experience
- **Description:** No root-level Python packaging configuration; each service is independent.
- **Why it matters:** Cross-service refactoring is harder; IDE tooling struggles; new developers are confused.
- **Acceptance criteria:** Add root `pyproject.toml` with workspace/group references to all services.
- **Estimated effort:** S

### PROD-P2-002: Heavy Frontend Dependencies
- **Severity:** P2
- **Category:** Frontend / Performance
- **Description:** Recharts, Framer Motion, react-day-picker, embla-carousel-react add bundle weight.
- **Why it matters:** Slower load times, especially on mobile and in emerging markets.
- **Acceptance criteria:** Lazy-load heavy visualization libs; tree-shake unused components.
- **Estimated effort:** M

### PROD-P2-003: L4 TODO in Billing Service
- **Severity:** P2
- **Category:** Backend / Code Quality
- **Description:** `services/layer4-agents/src/services/billing_service.py:412` has a TODO about using structured exception codes from Stripe SDK.
- **Acceptance criteria:** Replace string-matching error handling with structured exception codes.
- **Estimated effort:** S

### PROD-P2-004: Local Setup Complexity
- **Severity:** P2
- **Category:** Developer Experience
- **Description:** 7+ step setup (Infisical, corepack, pnpm, make setup, Docker, migrations, verify).
- **Acceptance criteria:** One-command setup via dev container or setup script.
- **Estimated effort:** M

### PROD-P2-005: Prettier Mirror Deprecation
- **Severity:** P2
- **Category:** Developer Experience
- **Description:** `.pre-commit-config.yaml` uses `mirrors-prettier` which is deprecated.
- **Acceptance criteria:** Migrate to official Prettier pre-commit hook or run via pnpm.
- **Estimated effort:** XS

---

## Sprint Roadmap

### Phase 0: Stabilize and Inventory (Week 1)
- **Goal:** Know exactly what is broken, flaking, or missing.
- **Scope:** Run full `make verify`, inventory quarantined tests, audit mypy overrides, check K8s overlay completeness.
- **Tickets:** PROD-P0-002 (quarantine audit), PROD-P0-005 (duplicate trees), PROD-P1-003 (integrated suite baseline)
- **Dependencies:** None
- **Definition of Done:** Spreadsheet of every quarantined test with failure reason; list of every mypy override module; K8s overlay gap report.
- **Risks:** May discover more blockers than anticipated.
- **Validation:** `make verify`, `pytest tests/quarantine/`, `mypy services/layer4-agents/src/ --strict`

### Phase 1: Security and Tenant Isolation (Weeks 2–3)
- **Goal:** Close all security and auth gaps before any customer data touches the platform.
- **Scope:** PROD-P0-003 (auth bypass hardening), PROD-P0-004 (mock fallback), PROD-P1-007 (RLS enforcement), PROD-P1-004 (K8s secrets)
- **Dependencies:** Phase 0
- **Definition of Done:** All services fail startup with dev bypass in prod; mock fallback blocked in prod builds; RLS tests pass in CI; K8s overlays validated.
- **Risks:** RLS changes may require migration downtime.
- **Validation:** `make security-smoke`, `make gate-security`, K8s dry-run

### Phase 2: API/Data Correctness (Weeks 4–5)
- **Goal:** Ensure backend type safety and data integrity.
- **Scope:** PROD-P0-001 (L4 mypy), PROD-P0-005 (duplicate trees), PROD-P1-006 (L3 freeze roadmap), PROD-P1-001 (L7 CI)
- **Dependencies:** Phase 1
- **Definition of Done:** L4 mypy overrides reduced 80%; duplicate trees eliminated; L7 in PR checks.
- **Risks:** Type fixes may surface hidden bugs; L7 may delay if billing logic is incomplete.
- **Validation:** `make typecheck`, `make contract-tests`, `make test-layer4`

### Phase 3: Frontend Production UX (Weeks 6–7)
- **Goal:** Harden frontend for performance, accessibility, and reliability.
- **Scope:** PROD-P1-002 (bundle budget), PROD-P1-008 (a11y keyboard), PROD-P2-002 (lazy loading)
- **Dependencies:** Phase 2
- **Definition of Done:** CI fails on bundle overrun; keyboard-flow tests cover golden paths; heavy libs lazy-loaded.
- **Risks:** Lazy-loading may break SSR/hydration if not tested.
- **Validation:** `pnpm run test:bundle-budget`, `pnpm run test:a11y:keyboard-flow`, `pnpm run build`

### Phase 4: Observability and Operations (Week 8)
- **Goal:** Ensure on-call can respond to incidents effectively.
- **Scope:** PROD-P1-005 (runbook URLs), dashboard validation, alert threshold tuning
- **Dependencies:** Phase 3
- **Definition of Done:** All alert runbook URLs reachable; Grafana dashboards imported and verified; alertmanager config validated.
- **Risks:** None major.
- **Validation:** `make check-readiness-consistency`, alertmanager dry-run

### Phase 5: Performance and Scalability (Week 9)
- **Goal:** Validate SLOs under load.
- **Scope:** k6 critical path suite, PgBouncer tuning, Redis memory analysis, Neo4j query plan review
- **Dependencies:** Phase 4
- **Definition of Done:** k6 SLO report shows p99 latency < target for all critical paths; no N+1 queries in L3.
- **Risks:** Load testing may reveal fundamental scalability limits requiring architecture changes.
- **Validation:** `make perf-test`, `make perf-eval`

### Phase 6: Deployment and Release Readiness (Week 10)
- **Goal:** Validate production deployment pipeline end-to-end.
- **Scope:** Blue-green deployment test, rollback drill, migration safety in K8s, secret rotation validation
- **Dependencies:** Phase 5
- **Definition of Done:** Successful blue-green deploy in staging; rollback completes <5 min; migrations run without downtime.
- **Risks:** Rollback may fail if migrations are destructive.
- **Validation:** `scripts/ci/run_release_smoke.sh`, `make test-backup-drills`

### Phase 7: Final Launch Gate (Week 11)
- **Goal:** Executive sign-off with evidence.
- **Scope:** Collect 95+ evidence pack, run all gates, security review, pen-test read-out
- **Dependencies:** Phase 6
- **Definition of Done:** `make gate-all` passes; `collect-95-plus-evidence` artifact generated; security team sign-off.
- **Risks:** Late discovery of blocker.
- **Validation:** `make release-gate`, `make collect-95-plus-evidence`

---

## Copy/Paste Dev Tickets

### Backend/Platform/Security (10 tickets)

#### TICKET-BE-001: Harden ProductionSafetyValidator Across All Services
- **Priority:** P0
- **Background:** Only some services have ProductionSafetyValidator that blocks startup when DEV_AUTH_BYPASS is set.
- **Problem:** A misconfigured production-like environment could bypass all auth.
- **Scope:** Add validator to L1, L2, L3, L5, L6, API gateway entrypoints.
- **Non-goals:** Changing auth logic; this is purely startup hardening.
- **Implementation steps:**
  1. Extract `ProductionSafetyValidator` from L4 into `packages/shared/`.
  2. Import and call validator in every service `main.py` before app startup.
  3. Add unit tests for each service.
- **Files likely affected:** `services/*/src/api/main.py`, `packages/shared/src/value_fabric/shared/security/`
- **Acceptance criteria:** Every service exits with code 1 and clear error if DEV_AUTH_BYPASS=true in non-dev env.
- **Test plan:** `tests/security/test_production_safety_validator.py` for each service.
- **Rollback plan:** Revert the startup call; no data model changes.
- **Security considerations:** This is a security hardening ticket.
- **Documentation updates:** Update `docs/security/secrets-management.md` with validator behavior.
- **Estimated effort:** M

#### TICKET-BE-002: Layer 4 Mypy Strictness Sprint (Batch 1)
- **Priority:** P0
- **Background:** Layer 4 has ~100 modules with mypy `disable_error_code` overrides.
- **Problem:** Type safety gaps in agent orchestration and billing calculation.
- **Scope:** Remove overrides for 50 modules (highest business-risk first: `services/billing_service.py`, `workflows/roi_calculator.py`).
- **Non-goals:** Rewriting logic; only adding types and fixing annotations.
- **Implementation steps:**
  1. Sort modules by business criticality.
  2. For each module: remove override, run `mypy --strict`, fix errors.
  3. Add type stubs for third-party libs if needed.
- **Files likely affected:** `services/layer4-agents/src/**/*.py`
- **Acceptance criteria:** 50 modules removed from override list; CI `typecheck-layer4` passes.
- **Test plan:** Existing unit tests; no behavior changes expected.
- **Rollback plan:** Revert pyproject.toml and source changes.
- **Security considerations:** None.
- **Documentation updates:** Update `docs/governance/compatibility-debt-registry.md`.
- **Estimated effort:** L

#### TICKET-BE-003: Restore or Delete Quarantined Tests
- **Priority:** P0
- **Background:** `tests/quarantine/` contains tests excluded from CI.
- **Problem:** Unknown test coverage gaps.
- **Scope:** Audit each file; restore with fix or delete with documented rationale.
- **Non-goals:** Rewriting test infrastructure.
- **Implementation steps:**
  1. List all files in `tests/quarantine/`.
  2. Run each to identify failure mode.
  3. Create sub-tickets for restoration or delete.
- **Files likely affected:** `tests/quarantine/*`
- **Acceptance criteria:** `tests/quarantine/` is empty; CI collection is clean.
- **Test plan:** Run restored tests in CI.
- **Rollback plan:** Revert deletions from git.
- **Security considerations:** Some quarantined tests may be security tests; prioritize their restoration.
- **Documentation updates:** Add quarantine policy to `CONTRIBUTING.md`.
- **Estimated effort:** M

#### TICKET-BE-004: Canonicalize L1/L2 Duplicate Source Trees
- **Priority:** P0
- **Background:** Logic exists in both `services/` and `value_fabric/` for L1 and L2.
- **Problem:** Bug fixes may not propagate; security patches missed.
- **Scope:** Move all logic to canonical `services/` paths; update imports.
- **Non-goals:** Refactoring logic; this is a move-only operation.
- **Implementation steps:**
  1. Run `scripts/ci/check_duplicate_source_trees.py` to identify duplicates.
  2. For each duplicate: determine canonical location.
  3. Move logic; update `value_fabric/` to re-export.
  4. Update all internal imports.
- **Files likely affected:** `services/layer1-ingestion/src/`, `services/layer2-extraction/src/`, `value_fabric/layer1/`, `value_fabric/layer2/`
- **Acceptance criteria:** `check_duplicate_source_trees.py` reports zero duplicates.
- **Test plan:** `make test-layer1`, `make test-layer2`, `make contract-tests`
- **Rollback plan:** Revert import changes.
- **Security considerations:** Ensure no logic is lost during move.
- **Documentation updates:** Update `docs/reference/layer-runtime-path-governance.md`.
- **Estimated effort:** L

#### TICKET-BE-005: Enforce RLS on All Tenant-Scoped Tables
- **Priority:** P1
- **Background:** Some layers may not have comprehensive PostgreSQL RLS policies.
- **Problem:** SQL injection or ORM bypass could expose cross-tenant data.
- **Scope:** Audit all tenant-scoped tables in L1–L6; add missing RLS policies; migrate.
- **Non-goals:** Changing application query patterns (should work with RLS transparently).
- **Implementation steps:**
  1. Schema audit per layer.
  2. Add `ENABLE ROW LEVEL SECURITY` and policies.
  3. Add `tests/security/test_rls_enforcement_postgres.py` for each layer.
- **Files likely affected:** `services/*/src/models/`, `services/*/migrations/`
- **Acceptance criteria:** Every tenant-scoped table has RLS; tests pass in CI.
- **Test plan:** `pytest tests/security/test_rls_enforcement_postgres.py`
- **Rollback plan:** Alembic downgrade.
- **Security considerations:** This is a security hardening ticket.
- **Documentation updates:** Update `docs/security/database-security.md`.
- **Estimated effort:** M

#### TICKET-BE-006: Add Layer 7 Billing to PR Checks
- **Priority:** P1
- **Background:** Layer 7 billing service is not included in CI matrix.
- **Problem:** Billing code may have lint errors, type errors, or security vulnerabilities.
- **Scope:** Add `layer7-checks` job to `pr-checks.yml` with lint, typecheck, test, coverage, bandit, pip-audit.
- **Non-goals:** Implementing billing features; this is CI integration only.
- **Implementation steps:**
  1. Ensure `services/layer7-billing/pyproject.toml` exists and is complete.
  2. Add CI job mirroring L1–L6 pattern.
  3. Add coverage gate ≥70%.
- **Files likely affected:** `.github/workflows/pr-checks.yml`, `services/layer7-billing/`
- **Acceptance criteria:** PR checks run L7 lint, typecheck, tests, security scan.
- **Test plan:** Open a test PR with L7 change.
- **Rollback plan:** Revert workflow change.
- **Security considerations:** Ensure billing secrets are not logged in CI.
- **Documentation updates:** Update `docs/ci/pr-checks.md`.
- **Estimated effort:** M

#### TICKET-BE-007: K8s Overlay Secret Validation
- **Priority:** P1
- **Background:** K8s overlays may contain placeholder secrets.
- **Problem:** Production deployment could use default/weak secrets.
- **Scope:** Audit all overlays; replace placeholders with External Secrets Operator references; add CI dry-run gate.
- **Non-goals:** Changing application secret consumption logic.
- **Implementation steps:**
  1. Audit `k8s/` overlays for placeholder secrets.
  2. Update overlays to use `ExternalSecret` resources.
  3. Add CI script that fails on `password: changeme` or similar patterns.
- **Files likely affected:** `k8s/envs/*/`, `k8s/base/external-secrets-operator.yml`
- **Acceptance criteria:** No placeholder secrets in any overlay; CI dry-run passes.
- **Test plan:** `kustomize build k8s/envs/prod | grep -i password`
- **Rollback plan:** Revert overlay changes.
- **Security considerations:** This is a security hardening ticket.
- **Documentation updates:** Update `docs/operations/k8s-deployment.md`.
- **Estimated effort:** M

#### TICKET-BE-008: Layer 3 Monolith Decomposition Roadmap
- **Priority:** P1
- **Background:** `check_l3_monolith_freeze.py` prevents further monolithic growth.
- **Problem:** Containment without decomposition limits scalability.
- **Scope:** Publish bounded-context decomposition plan; extract first bounded context.
- **Non-goals:** Full rewrite; this is incremental extraction.
- **Implementation steps:**
  1. Identify bounded contexts within L3 (graph query, GraphRAG, vector search).
  2. Publish ADR with extraction plan.
  3. Extract one bounded context to standalone module.
- **Files likely affected:** `services/layer3-knowledge/src/`, `docs/explanations/adr/`
- **Acceptance criteria:** ADR approved; first bounded context extracted; freeze updated to allow extracted modules.
- **Test plan:** `make test-layer3`, `make contract-tests`
- **Rollback plan:** Revert extraction.
- **Security considerations:** Ensure tenant isolation is preserved during extraction.
- **Documentation updates:** New ADR.
- **Estimated effort:** L

#### TICKET-BE-009: Backend-Integrated Test Stabilization
- **Priority:** P1
- **Background:** `tests/backend_integrated/` requires live stack and may be flaky.
- **Problem:** Flaky integrated tests erode trust in CI.
- **Scope:** Run integrated suite 10 times; identify flaky tests; fix root causes (timing, state leakage, infra readiness).
- **Non-goals:** Removing tests; this is stabilization.
- **Implementation steps:**
  1. Run `make test-backend-integrated-validation` 10 times.
  2. Collect pass/fail data per test.
  3. Fix top 3 flaky tests.
- **Files likely affected:** `tests/backend_integrated/`, `docker-compose.test.yml`
- **Acceptance criteria:** Integrated suite pass rate ≥95% over 10 runs.
- **Test plan:** Run suite 10 times in CI-like environment.
- **Rollback plan:** Revert test fixes.
- **Security considerations:** None.
- **Documentation updates:** Update `docs/testing/backend-integrated.md`.
- **Estimated effort:** M

#### TICKET-BE-010: Add Root pyproject.toml for Workspace Management
- **Priority:** P2
- **Background:** No root Python packaging config; each service is independent.
- **Problem:** Cross-service refactoring friction; IDE tooling gaps.
- **Scope:** Add root `pyproject.toml` with workspace references.
- **Non-goals:** Changing service packaging; services remain installable independently.
- **Implementation steps:**
  1. Create root `pyproject.toml` with `[tool.uv.workspace]` or `[tool.pdm.dev-dependencies]`.
  2. Reference all services.
  3. Validate with `uv sync` or `pdm install`.
- **Files likely affected:** `pyproject.toml` (new)
- **Acceptance criteria:** Root `pyproject.toml` exists; `make setup` works with it.
- **Test plan:** Fresh clone → `make setup` → `make test`
- **Rollback plan:** Delete root file.
- **Security considerations:** None.
- **Documentation updates:** Update `AGENTS.md` setup instructions.
- **Estimated effort:** S

---

### Frontend/Product Readiness (8 tickets)

#### TICKET-FE-001: Block Mock Fallback in Production Builds
- **Priority:** P0
- **Background:** `VITE_ENABLE_MOCK_FALLBACK=true` in dev compose could leak to prod.
- **Problem:** Users might see mock data instead of real API responses.
- **Scope:** Add build-time assertion; update CI.
- **Files likely affected:** `apps/web/vite.config.ts`, `apps/web/scripts/security/assert-no-dev-auth-bypass-in-production.mjs`
- **Acceptance criteria:** Production build fails if mock fallback is not explicitly false.
- **Estimated effort:** S

#### TICKET-FE-002: Enforce Bundle Budget in CI
- **Priority:** P1
- **Background:** `test:bundle-budget` exists but is not a PR gate.
- **Problem:** Bundle bloat degrades performance.
- **Scope:** Integrate budget assertion into `frontend-checks` job.
- **Files likely affected:** `.github/workflows/pr-checks.yml`, `apps/web/scripts/quality/assert-bundle-budget.mjs`
- **Acceptance criteria:** CI fails if initial chunk > threshold.
- **Estimated effort:** S

#### TICKET-FE-003: Lazy-Load Heavy Visualization Libraries
- **Priority:** P1
- **Background:** Recharts and Framer Motion are in the main bundle.
- **Problem:** Slow initial load on mobile.
- **Scope:** Convert chart and animation components to lazy-loaded.
- **Files likely affected:** `apps/web/src/components/**/*.tsx`
- **Acceptance criteria:** Recharts and Framer Motion not in initial chunk.
- **Estimated effort:** M

#### TICKET-FE-004: Expand Keyboard-Flow A11y Coverage
- **Priority:** P1
- **Background:** Keyboard-flow tests exist but may miss critical journeys.
- **Problem:** WCAG 2.1 AA compliance gaps.
- **Scope:** Add keyboard tests for ingestion, value studio, agent review, settings.
- **Files likely affected:** `apps/web/e2e/accessibility/keyboard-flow.spec.ts`
- **Acceptance criteria:** 4+ critical journeys covered.
- **Estimated effort:** M

#### TICKET-FE-005: Remove Legacy API Imports
- **Priority:** P1
- **Background:** `apps/web/src/api/legacy.ts` is banned for new code but may still have residual imports.
- **Problem:** Legacy API patterns bypass typed client contracts.
- **Scope:** Audit and migrate remaining legacy imports.
- **Files likely affected:** `apps/web/src/**/*.ts`, `apps/web/src/**/*.tsx`
- **Acceptance criteria:** Zero legacy imports outside `src/api/__tests__/migration/`.
- **Estimated effort:** M

#### TICKET-FE-006: Add Explicit Error Boundaries for Async Routes
- **Priority:** P1
- **Background:** Async route loading may fail silently.
- **Problem:** White screen of death on chunk load failure.
- **Scope:** Add React error boundaries around lazy-loaded routes.
- **Files likely affected:** `apps/web/src/components/routing/`
- **Acceptance criteria:** Every lazy route has an error boundary with user-friendly fallback.
- **Estimated effort:** S

#### TICKET-FE-007: Verify Clerk JWT Template Integration
- **Priority:** P1
- **Background:** Frontend uses Clerk; backend expects `fabric4l-api` JWT template.
- **Problem:** Mismatched claims could cause auth failures.
- **Scope:** End-to-end validation of Clerk JWT → API gateway → downstream service.
- **Files likely affected:** `apps/web/src/auth/`, `services/api/app/core/security.py`
- **Acceptance criteria:** JWT from Clerk frontend is accepted by API gateway and contains tenant claim.
- **Estimated effort:** S

#### TICKET-FE-008: Frontend Console Hygiene
- **Priority:** P2
- **Background:** CI checks for unguarded console statements but only in PR.
- **Problem:** Console noise in production.
- **Scope:** Audit and remove or guard all remaining `console.log/warn` in production code.
- **Files likely affected:** `apps/web/src/**/*.ts`, `apps/web/src/**/*.tsx`
- **Acceptance criteria:** Zero unguarded console statements.
- **Estimated effort:** XS

---

### Testing/QA (6 tickets)

#### TICKET-QA-001: Quarantined Test Audit and Remediation Plan
- **Priority:** P0
- **Scope:** Inventory `tests/quarantine/`; assign owners; set remediation dates.
- **Estimated effort:** M

#### TICKET-QA-002: Backend-Integrated Test Flakiness Baseline
- **Priority:** P1
- **Scope:** Run `tests/backend_integrated/` 10 times; trend pass rate.
- **Estimated effort:** M

#### TICKET-QA-003: E2E Golden Path Stability
- **Priority:** P1
- **Scope:** Run `j1-golden-path-backend-integrated.spec.ts` 10 times; fix flakes.
- **Estimated effort:** M

#### TICKET-QA-004: Contract Test Collection Cleanup
- **Priority:** P1
- **Scope:** Ensure `pytest tests/contract/ --collect-only` has zero import errors.
- **Estimated effort:** S

#### TICKET-QA-005: Security Test Coverage Gap Analysis
- **Priority:** P1
- **Scope:** Compare security test list against OWASP Top 10; identify missing coverage.
- **Estimated effort:** S

#### TICKET-QA-006: Performance SLO Baseline and Trending
- **Priority:** P2
- **Scope:** Run k6 suite weekly; store results; alert on regression.
- **Estimated effort:** M

---

### Infrastructure/DevOps (5 tickets)

#### TICKET-INF-001: K8s Overlay Secret Hardening
- **Priority:** P1
- **Scope:** Replace all placeholder secrets with External Secrets Operator references.
- **Estimated effort:** M

#### TICKET-INF-002: Update Alertmanager Runbook URLs
- **Priority:** P1
- **Scope:** Replace `wiki.internal` with real public/docs URLs.
- **Estimated effort:** S

#### TICKET-INF-003: Validate Blue-Green Deployment Pipeline
- **Priority:** P1
- **Scope:** Run blue-green deploy in staging; measure cutover time.
- **Estimated effort:** M

#### TICKET-INF-004: Database Backup and DR Drill
- **Priority:** P1
- **Scope:** Execute `make test-backup-drills`; verify restore time < RPO.
- **Estimated effort:** M

#### TICKET-INF-005: Network Policy Validation
- **Priority:** P2
- **Scope:** Verify `k8s/base/network-policies/` enforce zero-trust segmentation.
- **Estimated effort:** S

---

### Documentation/Developer Experience (3 tickets)

#### TICKET-DOC-001: Complete Remaining TBD Placeholders in Runbooks
- **Priority:** P1
- **Scope:** Audit `docs/troubleshooting/runbooks/` for TBD; complete or remove.
- **Estimated effort:** S

#### TICKET-DOC-002: Simplify Onboarding to Single Command
- **Priority:** P2
- **Scope:** Create `make bootstrap` that runs Infisical login, corepack, pnpm install, make setup.
- **Estimated effort:** M

#### TICKET-DOC-003: Update Alert Runbook Links
- **Priority:** P1
- **Scope:** Update all `runbook_url` in `monitoring/*-alerts.yml` to real markdown paths.
- **Estimated effort:** S

---

## Launch Gate Checklist

### Auth
- [ ] Clerk JWT template `fabric4l-api` is configured and validated end-to-end
- [ ] API gateway rejects unauthenticated requests with 401
- [ ] Expired JWTs return 401
- [ ] Tampered JWTs return 401
- [ ] `DEV_AUTH_BYPASS` is blocked in all non-dev environments
- **Evidence:** `services/api/app/tests/test_auth_enforcement.py` passes
- **Validation:** `make security-smoke`

### RBAC
- [ ] Role definitions are documented and enforced
- [ ] Admin endpoints require admin role
- [ ] Standard users cannot access admin endpoints
- **Evidence:** `tests/security/test_rbac.py` passes
- **Validation:** `pytest tests/security/test_rbac.py -k P0`

### Tenant Isolation
- [ ] Cross-tenant reads are blocked (403/401)
- [ ] Cross-tenant writes are blocked
- [ ] JWT tenant claim takes precedence over header spoofing
- [ ] PostgreSQL RLS policies exist on all tenant-scoped tables
- [ ] Neo4j queries filter by tenant
- **Evidence:** `tests/security/test_tenant_isolation.py` passes
- **Validation:** `make security-test-isolation`

### Secrets
- [ ] No committed secrets (gitleaks clean)
- [ ] No placeholder secrets in K8s overlays
- [ ] External Secrets Operator configured for production
- [ ] Secret rotation runbook exists
- **Evidence:** `.github/workflows/secret-rotation.yml` passes
- **Validation:** `pre-commit run gitleaks --all-files`

### Migrations
- [ ] Every layer has Alembic migrations
- [ ] Migrations have exactly one head per service
- [ ] Migrations are backward-compatible for rolling deploys
- [ ] Downgrade path tested for last 3 migrations
- **Evidence:** `make check-migration-heads` passes
- **Validation:** `make migrate && make test`

### Backups
- [ ] PostgreSQL backup cronjob configured
- [ ] Neo4j backup cronjob configured
- [ ] Backup restore tested monthly
- [ ] RPO and RTO documented
- **Evidence:** `k8s/base/postgres-backup-cronjob.yaml`, `neo4j-backup-cronjob.yaml`
- **Validation:** `make test-backup-drills`

### Observability
- [ ] Prometheus scraping all services
- [ ] Grafana dashboards imported
- [ ] Alertmanager routes alerts to on-call
- [ ] Loki collects application logs
- [ ] Jaeger traces requests end-to-end
- **Evidence:** `monitoring/` configs
- **Validation:** `make gate-obs`

### Error Handling
- [ ] Structured error responses (no stack traces to client)
- [ ] Request IDs propagated across all layers
- [ ] Error envelope consistency validated
- **Evidence:** `tests/contract/test_error_envelope_consistency.py`
- **Validation:** `pytest tests/contract/test_error_envelope_consistency.py`

### CI/CD
- [ ] All PR checks pass (structural, per-layer, contract, security, K8s, Docker)
- [ ] Trivy scan shows zero CRITICAL/HIGH vulnerabilities
- [ ] SBOM generated for every release
- [ ] Signed artifact manifest for every release
- **Evidence:** `pr-checks.yml` unified readiness gate
- **Validation:** `make verify`

### E2E Tests
- [ ] Playwright contract tests pass
- [ ] Golden path journeys pass (J1, J11)
- [ ] Accessibility scans show zero critical/serious issues
- [ ] Keyboard-flow tests pass
- **Evidence:** `apps/web/e2e/`
- **Validation:** `pnpm run test:e2e:validation:p0`

### Security Tests
- [ ] OWASP Top 10 tests pass
- [ ] Tenant boundary tests pass
- [ ] Injection prevention tests pass
- [ ] Rate limiting tests pass
- **Evidence:** `tests/security/`
- **Validation:** `make security-test`

### Dependency Scanning
- [ ] pip-audit shows zero HIGH severity issues
- [ ] pnpm audit shows zero HIGH severity issues
- [ ] Bandit scan clean
- [ ] Semgrep scan clean
- **Evidence:** CI `bandit`, `pip-audit`, `pnpm audit` jobs
- **Validation:** Run scans locally

### Performance Smoke Tests
- [ ] k6 critical path SLOs pass
- [ ] Frontend bundle budget met
- [ ] Database query p99 < 100ms for critical paths
- **Evidence:** `artifacts/performance/slo-evaluation.json`
- **Validation:** `make perf-test && make perf-eval`

### Accessibility
- [ ] WCAG 2.1 AA compliance for critical paths
- [ ] Keyboard navigation works for all interactive elements
- [ ] Screen reader labels present
- **Evidence:** `apps/web/a11y-report.json`
- **Validation:** `pnpm run test:a11y:launch-smoke`

### Legal/Compliance Basics
- [ ] Privacy policy exists
- [ ] Terms of service exist
- [ ] Data processing agreements available
- [ ] GDPR/CCPA data deletion workflow tested
- **Evidence:** Legal docs in repo or linked
- **Validation:** Manual review

### Incident Response
- [ ] On-call rotation documented
- [ ] Incident severity definitions documented
- [ ] Escalation paths documented
- [ ] Post-mortem template exists
- **Evidence:** `docs/troubleshooting/runbooks/incident/`
- **Validation:** Read runbooks

### Rollback
- [ ] Blue-green deployment tested
- [ ] Rollback completes <5 minutes
- [ ] Database migrations are backward-compatible
- [ ] Feature flags allow quick disable
- **Evidence:** `k8s/blue-green/`
- **Validation:** Run rollback drill in staging

### Runbooks
- [ ] 38+ runbooks exist
- [ ] No TBD placeholders in incident-critical sections
- [ ] Runbook URLs in alerts are reachable
- **Evidence:** `docs/troubleshooting/runbooks/`
- **Validation:** `make docs-harness`

### Admin Operations
- [ ] Admin CLI tools documented
- [ ] Admin operations require MFA
- [ ] Admin audit logs are immutable
- **Evidence:** `docs/operations/admin-ops.md`
- **Validation:** Manual review

### Customer Onboarding
- [ ] Self-service signup works end-to-end
- [ ] Tenant provisioning is automated
- [ ] First-run tutorial or docs exist
- **Evidence:** Product walkthrough
- **Validation:** E2E test `j1-golden-path`

### Support Process
- [ ] Support ticket routing documented
- [ ] SLA definitions exist
- [ ] Escalation to engineering defined
- **Evidence:** `docs/operations/support.md`
- **Validation:** Manual review

---

## Security Review

### Authentication
- **Implementation:** Clerk (primary) + Keycloak (OIDC broker) + Fabric internal JWT (RS256)
- **Strengths:** Multi-layer auth; JWT secret minimum 32 chars; dev bypass strictly confined; `ProductionSafetyValidator` exists.
- **Gaps:** Not all services have `ProductionSafetyValidator` at startup. `pytest.ini` sets `ALLOW_DEV_AUTH_BYPASS=I_UNDERSTAND_RISK` in test env.
- **Evidence:** `services/api/app/tests/test_auth_enforcement.py`, `docker-compose.dev.yml`, `pytest.ini`

### Authorization/RBAC
- **Implementation:** Role-based access with tenant scoping.
- **Strengths:** RBAC tests exist; admin endpoints restricted.
- **Gaps:** Need to verify RBAC is enforced on every route (some legacy shims may bypass).
- **Evidence:** `tests/security/test_rbac.py`

### Multi-tenant Isolation
- **Implementation:** JWT tenant claims, PostgreSQL RLS, Neo4j tenant filtering, header spoofing blocked.
- **Strengths:** Comprehensive tenant isolation tests; boundary static checks in CI; hostile tenancy endpoint suite for L3.
- **Gaps:** RLS may not cover all tables in all layers; some legacy tenant access shims exist.
- **Evidence:** `tests/security/test_tenant_isolation.py`, `pr-checks.yml:222-228`

### Secret Handling
- **Implementation:** Infisical for dev/CI; External Secrets Operator for K8s; gitleaks pre-commit.
- **Strengths:** No real secrets in `.env.example`; CI scans for placeholder secrets.
- **Gaps:** Some K8s overlays may still have placeholder secrets.
- **Evidence:** `.env.example`, `.infisical.json`, `k8s/base/kustomization.yaml`

### Input Validation
- **Implementation:** Pydantic v2 schemas across all layers; Zod on frontend.
- **Strengths:** Strong schema validation; contract tests enforce schemas.
- **Gaps:** Need to verify Cypher injection prevention in L3.
- **Evidence:** `contracts/openapi/`, `.semgrep/cypher-dynamic-guard.yml`

### Supply Chain
- **Implementation:** Trivy scanning, SBOM generation, Cosign signing, SLSA provenance.
- **Strengths:** Comprehensive supply chain security in CI.
- **Gaps:** Ensure SLSA provenance is verified on deploy.
- **Evidence:** `.github/workflows/supply-chain.yml`

---

## Tenant Isolation Review

### Findings
1. **Strong test coverage:** `test_tenant_isolation.py`, `test_boundary_check_static.py`, `test_route_tenant_propagation_static.py`, and layer-specific hostile tenancy suites.
2. **Static enforcement:** CI runs `boundary_check.py` and `check_route_tenant_propagation.py` on every PR.
3. **Database-level protection:** PostgreSQL RLS policies exist for some layers; needs universal coverage.
4. **Graph-level protection:** `.semgrep/cypher-dynamic-guard.yml` prevents dynamic Cypher without tenant filter.

### Recommendations
1. Universal RLS on all tenant-scoped tables (PROD-P1-007).
2. Remove all legacy tenant access shims (tracked by `check_legacy_tenant_access.py`).
3. Add tenant isolation tests for L7 Billing before it handles real data.

---

## Testing Review

### Findings
1. **Excellent taxonomy:** 40+ pytest markers enable precise test selection.
2. **Good coverage gates:** L1 70%, L2 85%, L3 75%, L4 80%, L5 75%, L6 70%, API 75%.
3. **Quarantine risk:** Unknown number of tests isolated.
4. **Integrated suite fragility:** Requires live Docker stack; may be flaky.
5. **E2E maturity:** Playwright contract tests, golden paths, accessibility scans, keyboard flow.

### Recommendations
1. Restore or delete quarantined tests (TICKET-QA-001).
2. Stabilize backend-integrated suite (TICKET-QA-002).
3. Add performance regression trending (TICKET-QA-006).

---

## Infrastructure and Deployment Review

### Findings
1. **K8s maturity:** Base manifests include HPA, PDB, network policies, backup cronjobs, resource quotas.
2. **CI validation:** K8s dry-run and Kind cluster tests in `pr-checks.yml`.
3. **Image security:** Trivy scans every layer image for CRITICAL/HIGH vulnerabilities.
4. **Secret gaps:** Some overlays use placeholder secrets.
5. **No prod ingress detail visible:** Need to verify TLS termination and WAF configuration.

### Recommendations
1. Harden K8s secrets (TICKET-INF-001).
2. Validate blue-green pipeline (TICKET-INF-003).
3. Document ingress/WAF setup.

---

## Observability and Operations Review

### Findings
1. **Prometheus alerts:** Layer-specific alert rules with runbook links.
2. **Grafana dashboards:** Present but need verification.
3. **Loki/Fluent-bit:** Log aggregation configured.
4. **Jaeger:** Distributed tracing runbook exists.
5. **Runbook gaps:** Some alert URLs point to `wiki.internal`.

### Recommendations
1. Update runbook URLs (TICKET-INF-002).
2. Verify dashboard freshness against current metrics.
3. Ensure on-call rotation is active and tested.

---

## Frontend UX/Product Readiness Review

### Findings
1. **Design system:** Strong governance in `DESIGN.md`; semantic tokens; dark mode support.
2. **API client:** Typed wrappers in `typedClient.ts`; generated OpenAPI types.
3. **Accessibility:** a11y scans and keyboard-flow tests in CI.
4. **Bundle risk:** Heavy deps not strictly budget-gated.
5. **Mock fallback:** Enabled by default in dev compose.

### Recommendations
1. Block mock fallback in production (TICKET-FE-001).
2. Enforce bundle budget (TICKET-FE-002).
3. Lazy-load heavy libs (TICKET-FE-003).
4. Expand keyboard-flow coverage (TICKET-FE-004).

---

## Documentation and Developer Experience Review

### Findings
1. **Diátaxis structure:** Tutorials, how-to, reference, explanations well organized.
2. **Agent onboarding:** `AGENTS.md` is exceptionally detailed.
3. **Runbooks:** 38+ operational runbooks.
4. **TBD placeholders:** CI blocks unresolved TBDs in incident-critical sections.
5. **Setup complexity:** 7+ steps with multiple tools (Infisical, corepack, pnpm, Docker).

### Recommendations
1. Simplify onboarding to single command (TICKET-DOC-002).
2. Complete any remaining TBD placeholders (TICKET-DOC-001).
3. Update alert runbook links (TICKET-DOC-003).

---

## Recommended Validation Commands

### Local Development
```bash
# Setup
corepack enable && corepack prepare pnpm@10.18.1 --activate
pnpm install --frozen-lockfile
make setup

# Preflight
make verify-structure

# Lint
make lint

# Typecheck
make typecheck

# Unit tests
make test

# Contract tests
make contract-tests

# Security smoke
make security-smoke

# Frontend
pnpm --dir apps/web run verify:frontend
pnpm --dir apps/web run build
pnpm --dir apps/web run test

# Migrations
make check-migration-heads
make migrate

# Performance
make perf-test
make perf-eval
```

### CI / Release Gates
```bash
# Full verification
make verify
make verify-strict

# Security gates
make gate-security
make gate-mandatory-security-regression

# Release gate
make release-gate

# Evidence collection
make collect-95-plus-evidence
```

### Kubernetes
```bash
# Dry-run validation
kustomize build k8s/base | kubectl apply --dry-run=server -f -
kustomize build k8s/deployments/prod-nginx | kubectl apply --dry-run=server -f -
```

### Security Scanning
```bash
# Secrets
gitleaks detect --source . -v

# Python SAST
bandit -r services/ -ll -ii

# Dependencies
pip-audit --severity high
pnpm audit --audit-level high

# Container images
trivy image local/layer4-agents:latest --severity CRITICAL,HIGH
```

---

## Final Recommendation

**Do not launch to broad enterprise GA yet.**

Value Fabric is **beta-ready with controlled rollout** conditional on completing:
- Phase 0 (inventory and stabilization)
- Phase 1 (security and tenant isolation hardening)
- Phase 2 (API/data correctness — especially Layer 4 type safety)

The platform has exceptional governance foundations that are rare in pre-launch products. The primary risks are not architectural blindness but **technical debt accumulation** (L4 mypy overrides, quarantined tests, duplicate trees) and **frontend production hardening** (mock fallback, bundle budget). These are solvable in 4–6 weeks with focused execution.

After Phase 0–2 completion, a **controlled production launch to a limited beta tenant cohort** is appropriate. Broad enterprise GA should wait until Phase 3–6 are complete (frontend hardening, observability validation, performance SLO confirmation, and deployment pipeline drills).

---

*Audit generated by Kimi Code CLI. Based on repository analysis as of 2026-05-27. Confidence: Medium-High.*
