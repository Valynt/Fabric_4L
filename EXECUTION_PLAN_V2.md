# Fabric_4L Execution Plan V2

**Version:** 2.0
**Effective Date:** Post-Sprint 6 / Sprint 7 Kickoff
**Current Audit Score:** 7.4/10
**Remaining P0 Blockers:** 4
**Target Score (Post-Sprint 7):** 8.0+

---

## 1. Sprint 7: Launch Hardening (Current)

**Sprint Goal:** Eliminate all 4 remaining P0 blockers and complete P1 hardening items required for controlled GA.
**Duration:** 2 weeks
**Success Criteria:** 0 P0 blockers, all Launch Gates 1–4 at 100%, Gates 5–8 ≥ 80%.

### 1.1 P0 Blockers (Sprint 7 Commitment)

#### P0-1: Global Exception Handler
**Owner:** Backend Lead
**Estimate:** 2 days
**Current State:** `add_exception_handler` absent; unhandled exceptions leak raw stack traces.
**Deliverables:**
- FastAPI `add_exception_handler` registered in app factory for:
  - `HTTPException` → JSON error model with `error_code`, `message`, `request_id`
  - Unhandled `Exception` → sanitized 500 response (no stack trace, logged server-side)
  - `RequestValidationError` → 422 with field-level detail
- Response model: `ErrorResponse` Pydantic schema in `schemas/common.py`
- Request ID propagation via `X-Request-ID` header (UUID4 if not provided)
- All existing `str(e)` patterns in route files replaced with structured logging + `HTTPException` raise

**Acceptance:**
- [ ] Fuzz test with random `Exception` subclasses returns 500 with no `traceback` in JSON body
- [ ] `pytest` suite passes with new handler active
- [ ] `grep -r "add_exception_handler" backend/` returns ≥1 result

---

#### P0-2: `str(e)` Leakage Purge
**Owner:** Security Lead (with Backend Support)
**Estimate:** 3 days
**Current State:** 69 occurrences across 30 files (regression from 20+ files pre-Sprints 0–6).
**Root Cause:** Billing module (`billing.py`, `billing_service.py`, `webhook_security.py`) introduced fresh `str(e)` patterns.

**Deliverables:**
- Ruff rules `EM101` (raw-string-in-exception) and `TRY003` (raise-vanilla-args) added to `pyproject.toml` lint select
- CI lint gate fails on new violations
- Mechanical replacement of `str(e)` with structured patterns:
  - Routes: `raise HTTPException(status_code=..., detail=ErrorCodeEnum.XXX)`
  - Services: `logger.error("context", error=exc, request_id=...)` + re-raise custom domain exception
  - Webhooks: `logger.warning("stripe_webhook_error", error_type=type(e).__name__)` (never expose `str(e)` to caller)
- Billing module fully audited first (highest risk)

**Acceptance:**
- [ ] `grep -rn "str(e)" backend/ --include="*.py"` returns 0 results
- [ ] CI lint job with EM101/TRY003 passes on entire backend
- [ ] Security review sign-off on billing error paths

---

#### P0-3: Deprecated Import Policy Enforcement
**Owner:** Architecture Lead
**Estimate:** 2 days
**Current State:** 1,435 deprecated imports (regression from 217). Cross-layer coupling accelerating.

**Deliverables:**
- CI gate: `deprecation-check.sh` runs in `lint` job, fails build if new deprecated imports introduced
- Grandfather existing 1,435 imports with `# TODO-ARCH-003: migrate before v2.0` comments
- ADR amendment: cross-layer import requires architecture review approval
- Automated weekly report of deprecated import count trend (fail if count increases week-over-week)

**Acceptance:**
- [ ] Build fails on PR that adds new deprecated import
- [ ] `deprecated_imports.csv` artifact published in CI with file:line references
- [ ] No net increase in deprecated import count during Sprint 7

---

#### P0-4: L4 Billing Service Boundary
**Owner:** Architecture Lead + Backend Lead
**Estimate:** 3 days
**Current State:** Billing is a module in L4 monolith (263 files), not a bounded-context service.

**Deliverables:**
- `services/billing/` directory with:
  - Own `Dockerfile` (multi-stage, distroless final)
  - Own Alembic migration lineage (`migrations/billing/`)
  - Own `pytest` configuration and coverage gate (L-billing=80)
  - Explicit API surface: `BillingService` class, no back-calls to L4
- L4 calls billing via HTTP client (internal k8s service) or async message bus — not direct import
- Shared models in `packages/shared/billing_schemas/` (Pydantic only, no SQLAlchemy)

**Acceptance:**
- [ ] `docker build -f services/billing/Dockerfile` succeeds
- [ ] `pytest services/billing/` passes with ≥80% coverage
- [ ] `grep -r "from app.billing" backend/` returns 0 (no direct L4→billing imports)
- [ ] Architecture decision record ADR-021: Billing Service Extraction

---

### 1.2 P1 Hardening (Sprint 7 Commitment)

| ID | Item | Owner | Est | Acceptance |
|----|------|-------|-----|------------|
| P1-1 | SQLite default removal | Backend Lead | 0.5d | `database_uri` has no SQLite fallback; `pytest` uses `postgresql` test container |
| P1-2 | `analysis.py` E2E constants extraction | Backend Lead | 1d | UUIDs in `config/e2e.yaml`; production paths load from env; `pytest` overrides with fixture |
| P1-3 | Jaeger K8s persistent storage | DevOps Lead | 2d | K8s Jaeger uses `SPAN_STORAGE_TYPE=badger` with PVC; traces survive `kubectl rollout restart` |
| P1-4 | Legacy component removal (9 pages) | Frontend Lead | 2d | Zero imports of `LegacyTabs` / `LegacyDataTable`; visual QA on all 9 pages |
| P1-5 | Alt text completion | Frontend Lead | 1d | All `<img>` elements have `alt` prop; a11y lint rule `jsx-a11y/alt-text` = error |
| P1-6 | Vault dev mode `.env` enforcement | DevOps Lead | 0.5d | `docker-compose.full.yml` uses `${VAULT_DEV_ROOT_TOKEN_ID:-}` with empty default; documented in `DEVELOPMENT.md` |

---

### 1.3 Sprint 7 Team Capacity

| Role | Assignee | Allocation | Focus |
|------|----------|------------|-------|
| Backend Lead | TBD | 100% | P0-1, P0-2, P1-1, P1-2 |
| Security Lead | TBD | 80% (Mon–Thu) | P0-2 co-owner, P0-3 advisor, billing error review |
| Architecture Lead | TBD | 100% | P0-3, P0-4, ADR-021 |
| Frontend Lead | TBD | 80% (Mon–Thu) | P1-4, P1-5, FE code review |
| DevOps Lead | TBD | 60% (Mon–Wed) | P1-3, P1-6, CI gate configuration |
| QA Engineer | TBD | 50% (Mon–Wed) | Regression testing, gate verification |

**Total capacity:** ~47 person-days over 2 weeks (10 working days).
**Committed work:** P0s (10d) + P1s (7d) = 17 days of work, 30 days available with parallelism. Buffer absorbs estimation error and review cycles.

### 1.4 Sprint 7 Daily Standup Agenda

Each standup reports on:
1. `str(e)` count (target: downward only)
2. Deprecated import delta (target: ≤0 daily)
3. P0 blocker burn-down (target: 0 by Day 8)
4. Blockers / dependencies

### 1.5 Definition of Done (Sprint 7)

- [ ] Code merged to `main` via PR with ≥2 approvals
- [ ] CI passes: lint (including new EM101/TRY003 + deprecation gates), unit tests, integration tests
- [ ] Security review sign-off on P0-2 (billing error paths)
- [ ] Architecture review sign-off on P0-4 (billing boundary)
- [ ] QA validates Launch Gates 1–4 at 100%
- [ ] Deployment to staging successful
- [ ] 24-hour soak test on staging with no P1+ incidents

### 1.6 Sprint 7 Milestones

| Day | Milestone | Exit Criteria |
|-----|-----------|---------------|
| 3 | P0-1 + P0-2 complete | Exception handler active; `grep str(e)` = 0 |
| 5 | P0-3 + P1-1 + P1-2 complete | CI deprecation gate live; SQLite fallback removed |
| 8 | P0-4 structure complete | `services/billing/` builds and tests independently |
| 10 | P1-3 + P1-4 + P1-5 complete | Jaeger PVC live; Legacy components = 0; alt text = 100% |
| 10 | Integration + regression | All Launch Gates 1–4 at 100%; 5–8 ≥ 80% |

---

## 2. Sprint 8: Post-Launch Telemetry & Reliability (Weeks 1–2 Post-GA)

**Theme:** Close observability gaps, verify contracts, validate billing under real load.
**Trigger:** Sprint 7 P0s resolved and controlled GA released to early-access tenants.

### 2.1 Core Deliverables

| ID | Item | Owner | Est | Detail |
|----|------|-------|-----|--------|
| S8-1 | Pact provider verification | Backend Lead | 3d | FastAPI endpoint `/_pact/provider_states`; verify against frontend consumer pacts in CI |
| S8-2 | L3 tracer OTel interop path | Backend Lead | 3d | OTel Collector receiver adapter; documented migration path from custom format to OTLP |
| S8-3 | structlog backfill L2/L5/L6 | Backend Lead | 2d | Add `structlog` configure to L2 (ingestion), L5 (orchestration), L6 (presentation); enforce via coverage |
| S8-4 | Billing Stripe sandbox E2E | Backend Lead | 2d | Full subscription lifecycle against Stripe test mode; webhook signature verification |
| S8-5 | K8s chaos: workflow preemption | DevOps Lead | 2d | `chaos-mesh` or ` PowerfulSeal` pod-kill during active workflow; verify resume via checkpoint |
| S8-6 | CORS regression tests | Backend Lead | 1d | Parameterized `pytest` for allowed origins rejection, credential handling, preflight |

### 2.2 Sprint 8 Dependencies
- Sprint 7 P0s resolved and merged
- Early-access tenant onboarding complete (≥3 tenants)
- Staging environment stable for 48 hours
- Stripe test mode API keys available in CI secrets

### 2.3 Sprint 8 Detailed Plan

**Week 1: Contract & Observability**
- Day 1–2: Pact provider verification endpoint (`/_pact/provider_states`)
- Day 2–3: CORS regression test suite (parameterized origins, credentials, preflight)
- Day 3–5: OTel Collector adapter for L3 tracer; integration test trace → Collector → Jaeger

**Week 2: Resilience & Logging**
- Day 6–7: structlog backfill L2/L5/L6; coverage gates
- Day 7–8: Billing Stripe sandbox E2E (subscription create → invoice → cancel)
- Day 8–10: Chaos tests (pod-kill during workflow); verify checkpoint resume

### 2.4 Sprint 8 Success Criteria
- Pact provider verification green in CI
- OTel interop adapter passes integration test (trace ingestion → Collector → Jaeger)
- structlog present in all 6 layers (coverage gate ≥1 log line per layer in tests)
- Billing E2E runs in <5 minutes in CI pipeline
- Workflow survives 3 consecutive pod-kill chaos experiments

---

## 3. Sprint 9: Scale & Performance (Weeks 3–4 Post-GA)

**Theme:** Optimize for tenant growth, reduce latency, harden data layer.
**Trigger:** Early-access metrics show usage patterns; performance baseline established.

### 3.1 Core Deliverables

| ID | Item | Owner | Est | Detail |
|----|------|-------|-----|--------|
| S9-1 | Neo4j connection pool tuning | Backend Lead | 2d | Max connections, acquisition timeout, retry policy; load-test with 50 concurrent tenants |
| S9-2 | Frontend bundle splitting | Frontend Lead | 3d | Admin console lazy-loaded; `<React.Suspense>` boundaries; target: initial <200KB gzip |
| S9-3 | API rate-limiting hardening | Backend Lead | 2d | Tenant-aware rate limits (per-API-key); 429 responses with `Retry-After`; Redis-backed |
| S9-4 | `BenchmarkRepository` Cypher validation | Backend Lead | 3d | Route all queries through `cypher_query_service`; parameterized query audit log; remove raw `tx.run()` |
| S9-5 | ADR-021 follow-up: shared packages | Architecture Lead | 2d | Extract `packages/shared/` patterns into versioned internal packages; semantic versioning |

### 3.2 Sprint 9 Dependencies
- Sprint 8 complete; staging stable
- Early-access metrics available (query patterns, tenant counts, API latency baselines)
- Redis cluster available in staging for rate-limit testing
- Load-testing environment provisioned (50-tenant simulation)

### 3.3 Sprint 9 Detailed Plan

**Week 1: Backend Performance**
- Day 1–2: Neo4j connection pool tuning (max connections, acquisition timeout, retry)
- Day 2–3: `BenchmarkRepository` Cypher validation refactor (route through `cypher_query_service`)
- Day 3–5: API rate-limiting (tenant-aware, Redis-backed, 429 with `Retry-After`)

**Week 2: Frontend & Architecture**
- Day 6–8: Admin console bundle splitting (`React.lazy` + `Suspense`); target <200KB gzip initial
- Day 8–9: Shared packages versioning (`packages/shared/` → semantically versioned internal packages)
- Day 9–10: Load test validation (50 tenants, p99 <100ms)

### 3.4 Sprint 9 Success Criteria
- Neo4j p99 query latency <100ms under 50-tenant load test
- Admin console initial bundle <200KB gzip
- Rate limiting returns 429 correctly; no cross-tenant leakage in stress test
- `BenchmarkRepository` has 0 direct `tx.run()` calls

---

## 4. Sprint 10: Enterprise Polish (Month 2 Post-GA)

**Theme:** Compliance automation, advanced features, documentation.
**Trigger:** Product-market fit signals from early-access cohort.

### 4.1 Core Deliverables

| ID | Item | Owner | Est | Detail |
|----|------|-------|-----|--------|
| S10-1 | SOC-2 evidence automation | Security Lead | 3d | Automated screenshots of RBAC, audit logs, encryption-at-rest; compliance report generation |
| S10-2 | Tenant data portability | Backend Lead | 3d | GDPR Article 20 export API; JSON/CSV formats; 24-hour async generation |
| S10-3 | RBAC granularity audit | Security Lead | 2d | Review all 80 routes for role coverage; add missing `require_role` decorators |
| S10-4 | `ARCHITECTURE.md` v2 | Architecture Lead | 3d | Document L2.5, billing service, shared packages, decomposition roadmap; remove stale sections |
| S10-5 | `importlib` hackery removal | Architecture Lead | 3d | Static imports replace runtime `importlib`; type-checkable module graph |

### 4.2 Sprint 10 Dependencies
- Sprint 9 complete; performance baselines established
- SOC-2 Type II audit timeline confirmed
- Legal review of tenant data portability export format (GDPR Article 20)
- Design-system v2 components available for `importlib` replacement

### 4.3 Sprint 10 Detailed Plan

**Week 1: Compliance & Access**
- Day 1–2: RBAC granularity audit (all 80 routes reviewed; missing `require_role` added)
- Day 2–4: Tenant data portability API (async export generation; JSON/CSV; 24h SLA)
- Day 4–5: SOC-2 evidence automation (RBAC screenshots, audit log samples, encryption verification)

**Week 2: Documentation & Cleanup**
- Day 6–7: `ARCHITECTURE.md` v2 (L2.5, billing service, shared packages, decomposition roadmap)
- Day 7–9: `importlib` hackery removal (static imports; type-checkable module graph)
- Day 9–10: Full regression test; documentation peer review; v8.0 target assessment

### 4.4 Sprint 10 Success Criteria
- SOC-2 Type II evidence packet generates in <10 minutes
- Tenant export API tested with 10GB dataset; completes in <24h
- 100% of routes have explicit RBAC decorator
- `ARCHITECTURE.md` passes peer review; no references to deleted modules
- Zero `importlib` usage in L4

---

## 5. Updated Backlog (Comprehensive)

| ID | Item | Priority | Sprint | Category | Status |
|----|------|----------|--------|----------|--------|
| P0-1 | Global exception handler | P0 | 7 | API / Security | Open |
| P0-2 | `str(e)` purge (69 occ) | P0 | 7 | Security | Open |
| P0-3 | Deprecated import enforcement | P0 | 7 | Architecture | Open |
| P0-4 | L4 billing service extraction | P0 | 7 | Architecture | Open |
| P1-1 | SQLite default removal | P1 | 7 | Backend | Open |
| P1-2 | `analysis.py` E2E constants | P1 | 7 | Security | Open |
| P1-3 | Jaeger K8s persistent storage | P1 | 7 | Observability | Open |
| P1-4 | Legacy component removal | P1 | 7 | Frontend | Open |
| P1-5 | Alt text completion | P1 | 7 | Accessibility | Open |
| P1-6 | Vault dev mode `.env` gate | P1 | 7 | Security | Open |
| P1-7 | `BenchmarkRepository` Cypher validation | P1 | 8 | Data / Security | Open |
| P1-8 | L3 tracer OTel interop | P1 | 8 | Observability | Open |
| P2-1 | ADR numbering + ARCHITECTURE.md | P2 | 7 | Documentation | Open |
| P2-2 | CORS regression tests | P2 | 7 | Testing | Open |
| P2-3 | Pact provider verification | P2 | 8 | Testing | Open |
| P2-4 | structlog L2/L5/L6 backfill | P2 | 8 | Observability | Open |
| P2-5 | `importlib` hackery removal | P2 | 9 | Architecture | Open |
| P2-6 | L4 full decomposition plan | P2 | 9 | Architecture | Open |
| S8-1 | Billing Stripe sandbox E2E | P1 | 8 | SaaS | Open |
| S8-2 | K8s workflow chaos tests | P1 | 8 | Reliability | Open |
| S9-1 | Neo4j connection pool tuning | P2 | 9 | Performance | Open |
| S9-2 | Frontend bundle splitting | P2 | 9 | Performance | Open |
| S9-3 | API rate-limiting hardening | P2 | 9 | Security | Open |
| S9-4 | Shared packages versioning | P2 | 9 | Architecture | Open |
| S10-1 | SOC-2 evidence automation | P2 | 10 | Compliance | Open |
| S10-2 | Tenant data portability | P2 | 10 | Compliance | Open |
| S10-3 | RBAC granularity audit | P2 | 10 | Security | Open |
| S10-4 | `ARCHITECTURE.md` v2 | P2 | 10 | Documentation | Open |

---

## 6. Updated Launch Gate Checklist

### Gate 1: Security (100% required for GA)
- [ ] `str(e)` occurrences = 0
- [ ] Global exception handler returns sanitized JSON (no stack traces)
- [ ] CORS wildcard absent + regression tests pass
- [ ] No hardcoded secrets in production configs
- [ ] Vault dev mode gated behind `.env` override
- [ ] `analysis.py` E2E constants in test-only fixtures
- [ ] WebSocket auth returns 1008 on failure (verified)
- [ ] Token revocation end-to-end verified

### Gate 2: Architecture (100% required for GA)
- [ ] Deprecated imports < 200 (with CI gate)
- [ ] No orphaned code directories
- [ ] `importlib` hackery documented with timeline
- [ ] Billing service boundary defined (ADR-021)
- [ ] ADR numbering conflicts resolved

### Gate 3: API Contracts (100% required for GA)
- [ ] Response models on ≥75/80 routes (target 80/80)
- [ ] Pagination on all list routes
- [ ] Global exception handler operational
- [ ] `PaginatedResponse` schema consistent

### Gate 4: Frontend Quality (100% required for GA)
- [ ] `any` types < 15 (target <10)
- [ ] `LegacyTabs` / `LegacyDataTable` = 0 pages
- [ ] Alt text on all images
- [ ] `console.log` = 0 in production builds
- [ ] aria-label coverage maintained ≥144 files

### Gate 5: Testing (≥80% for controlled GA; 100% for full GA)
- [x] All 7 layers pass `fail_under` in CI
- [x] Cross-tenant hostile tests green
- [ ] CORS regression tests green (Sprint 7)
- [ ] Pact provider verification green (Sprint 8 OK for controlled GA)

### Gate 6: Infrastructure (100% required for GA)
- [x] PostgreSQL `scram-sha-256` in all envs
- [x] External Secrets Operator in K8s
- [x] Alembic migrations as K8s Jobs
- [ ] Jaeger persistent storage in K8s (Sprint 7)
- [x] Circuit breaker deployed with 74+ references
- [x] Cypher query limits enforced

### Gate 7: SaaS / Compliance (100% required for GA)
- [x] Stripe billing implemented
- [x] Super admin console operational
- [x] Impersonation with cross-tenant guards
- [x] DSAR 30-day SLA tracking
- [ ] Billing Stripe sandbox E2E green (Sprint 8 OK)
- [ ] SOC-2 evidence automation (Sprint 10)

### Gate 8: Observability (≥80% for controlled GA; 100% for full GA)
- [ ] structlog in all 6 layers (Sprint 8)
- [ ] Jaeger traces survive pod restart (Sprint 7)
- [x] Circuit breaker metrics exposed
- [ ] L3 tracer OTel interop path (Sprint 8)

---

## 7. Risk Register

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Sprint 7 scope creep on billing extraction | Medium | High | Time-box P0-4 to 3 days; fallback to module-boundary definition if extraction exceeds estimate |
| `str(e)` purge breaks error-sensitive billing flows | Medium | High | Comprehensive `pytest` on all billing error paths before merge; Stripe webhook negative testing |
| Deprecated import CI gate blocks urgent hotfix | Low | Medium | Emergency bypass process documented; requires Tech Lead + Security Lead approval |
| Frontend legacy component removal causes visual regression | Medium | Medium | Visual snapshot testing on all 9 pages before/after; stagger removal across 2 PRs |
| Jaeger persistent storage PVC causes K8s disk pressure | Low | Medium | Start with 10Gi PVC limit; monitoring alert at 70% usage |

---

## 8. Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| Sprint 7 | Billing extraction is P0, not P1 | L4 monolith at 263 files is an operational risk; billing is the most natural boundary |
| Sprint 7 | `str(e)` purge before billing feature work | Security audit timeline requires clean error handling before external review |
| Sprint 7 | Controlled GA viable with 0 P0s | Early-access tenants with direct support channel acceptable; full GA requires Gate 5–8 completion |
| Sprint 8 | Pact provider deferred from Sprint 7 | Frontend consumer tests exist; provider verification is hardening, not blocking |
| Sprint 8 | OTel interop deferred from Sprint 7 | Custom tracer works; interop is ecosystem enablement, not production stability |
| Sprint 9 | Neo4j tuning based on real metrics | Premature optimization avoided; tuning requires actual early-access query patterns |

---

## 9. Dependency Network

```
Sprint 7 (P0s)
├── P0-1 Global exception handler
│   └── Blocks: P0-2 str(e) cleanup (routes need handler to raise properly)
│   └── Unblocks: Gate 1 (Security), Gate 3 (API Contracts)
├── P0-2 str(e) purge
│   └── Depends on: P0-1 (handler provides correct raise pattern)
│   └── Blocks: S8-4 billing E2E (clean error paths required)
│   └── Unblocks: Gate 1 (Security)
├── P0-3 Deprecated import enforcement
│   └── Unblocks: Gate 2 (Architecture)
│   └── Enables: S9-5 shared packages versioning
└── P0-4 Billing service extraction
    └── Depends on: P0-3 (boundary definition needs import policy)
    └── Unblocks: Gate 2 (Architecture)
    └── Enables: S9-1 Neo4j tuning (separate deploy unit)

Sprint 7 (P1s)
├── P1-1 SQLite removal → Unblocks: Gate 3
├── P1-2 E2E constants → Unblocks: Gate 1
├── P1-3 Jaeger PVC → Unblocks: Gate 8
├── P1-4 Legacy components → Unblocks: Gate 4
├── P1-5 Alt text → Unblocks: Gate 4
└── P1-6 Vault .env → Unblocks: Gate 1

Sprint 8
├── S8-1 Pact provider → Depends on: P0-1 (stable error responses)
├── S8-2 OTel interop → Depends on: P1-3 (Jaeger stable)
├── S8-3 structlog backfill → Depends on: P0-3 (layer boundaries clean)
├── S8-4 Billing E2E → Depends on: P0-2 (clean errors)
├── S8-5 Chaos tests → Depends on: P0-4 (billing separate = blast radius contained)
└── S8-6 CORS tests → Independent

Sprint 9
├── S9-1 Neo4j tuning → Depends on: P0-4 (billing extracted = load isolated)
├── S9-2 Bundle splitting → Depends on: P1-4 (legacy components removed)
├── S9-3 Rate limiting → Depends on: P0-1 (handler returns 429 consistently)
├── S9-4 Cypher validation → Depends on: P0-3 (clean imports)
└── S9-5 Shared packages → Depends on: P0-3 (import policy enforced)

Sprint 10
├── S10-1 SOC-2 evidence → Depends on: S8-3 (all layers logging)
├── S10-2 Data portability → Depends on: S9-4 (validated Cypher queries)
├── S10-3 RBAC audit → Depends on: P0-1 (handler auth context stable)
├── S10-4 ARCHITECTURE.md v2 → Depends on: P0-4 + S9-5 (document extracted services)
└── S10-5 importlib removal → Depends on: S9-5 (static packages available)
```

---

**End of Execution Plan V2**
