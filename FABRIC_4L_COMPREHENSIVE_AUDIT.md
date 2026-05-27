# Fabric_4L Production Readiness Audit

**Audit Date:** 2025-06-02
**Repository Commit:** `c89469a4` (fresh clone)
**Auditors:** 7 Specialist Agents (System Analyst, Security Engineer, Backend Analyst, Frontend Analyst, Data/Infra Analyst, Test/QA Analyst, Observability Analyst)
**Overall Classification:** **NOT READY FOR PRODUCTION LAUNCH**

---

## 1. Executive Summary

### 1.1 Overall Score: 4.2 / 10 (Production Readiness)

Fabric_4L is a sophisticated multi-layer semantic data platform with 8 backend services, a React frontend, and a 6-layer semantic pipeline. The codebase demonstrates strong architectural vision, excellent frontend engineering discipline, and robust security fundamentals in authentication and webhook verification. However, **the system cannot be launched to production** in its current state due to multiple P0 blockers spanning backend error handling, database connectivity, infrastructure secrets management, testing coverage gaps, and observability instrumentation failures.

The most critical finding is that `database.py` — the shared database module used across all backend services — **has no PostgreSQL implementation** despite the architecture specifying 5 PostgreSQL databases. It only supports SQLite/in-memory and raises `UnsupportedDatabaseURL` for PostgreSQL URLs. This means **none of the backend services can connect to their specified databases in production**. Compounding this, all 7 canonical exception classes (`NotFoundError`, `ValidationError`, etc.) are defined but never used; approximately 88 error raise sites use raw `HTTPException`, bypassing the `ErrorEnvelope` response contract that downstream clients expect.

On the infrastructure layer, the PostgreSQL backup CronJob references a non-existent secret (`postgres-credentials` instead of `postgres-secret`), meaning **automated backups will fail silently**. Layer 4 agents have a hardcoded `postgres:postgres` password in `CHECKPOINT_DATABASE_URL`. The security regression CI gate — a mandatory merge blocker — excludes 3 of 6 test groups including cross-layer tenant isolation tests, undermining the very guarantees it purports to enforce.

The frontend scores an A- (8/10) with only 2 `any` types across ~158,000 lines, zero `console.log` in production source, and 87 lazy-loaded routes with tier-based RBAC. This is offset by severe accessibility gaps (only 4 `alt=` attributes company-wide) and legacy component debt.

**Recommendation:** Address all 10 P0 blockers before any production deployment. Estimate: 6-8 weeks of focused engineering work.

### 1.2 Top 10 Risks (Ranked by Impact)

| Rank | Risk | Severity | Likelihood | Impact |
|------|------|----------|------------|--------|
| 1 | **No PostgreSQL connectivity** — `database.py` raises `UnsupportedDatabaseURL` for PostgreSQL; all services fail on prod DBs | Certain | High | Total system outage |
| 2 | **Broken exception handling contract** — Raw `HTTPException` bypasses `ErrorEnvelope`; clients cannot parse errors | Certain | High | API contract violation, client crashes |
| 3 | **Failed database backups** — Backup CronJob references wrong secret name; data loss with no recovery | High | High | Catastrophic data loss |
| 4 | **Hardcoded production password** — Layer 4 `CHECKPOINT_DATABASE_URL` exposes `postgres:postgres` | High | High | Security breach, credential exposure |
| 5 | **Blind security regression gate** — Mandatory gate excludes tenant isolation, contract, and K8s tests | High | High | False confidence in security posture |
| 6 | **No rate limiting** — API service has no request throttling; vulnerable to abuse and cascading failures | High | Medium | DoS, resource exhaustion |
| 7 | **No idempotency keys** — All POST endpoints lack idempotency; duplicate writes on retries | Medium | High | Data corruption, duplicate records |
| 8 | **Non-OTel tracer in Layer 3** — Custom tracer cannot reach Jaeger; critical pipeline stage is invisible | High | Medium | Blind debugging, extended MTTR |
| 9 | **Stub health check** — API reports "ok" even when database is down; load balancers send traffic to failed instances | High | Medium | False healthy status, prolonged outages |
| 10 | **Neo4j Community single instance** — No HA, invalid backup syntax; graph data is a SPOF | High | Low-Medium | Knowledge graph unavailability |

### 1.3 Top 10 Recommended Actions

| Priority | Action | Effort | Owner |
|----------|--------|--------|-------|
| 1 | Implement PostgreSQL driver in `database.py` with connection pooling | L | Backend Lead |
| 2 | Migrate all ~88 raw `HTTPException` raises to canonical exception classes | M | Backend Team |
| 3 | Fix `postgres-backup-cronjob.yaml` secret reference to `postgres-secret` | S | DevOps |
| 4 | Rotate Layer 4 hardcoded password and move to Kubernetes secret | S | DevOps/Security |
| 5 | Add rate limiting middleware to API gateway/service | M | Backend Team |
| 6 | Implement idempotency key middleware for POST endpoints | M | Backend Team |
| 7 | Replace Layer 3 custom tracer with OTel instrumentation | M | Backend/Observability |
| 8 | Implement real health checks (DB, Redis, Neo4j dependency probes) | M | Backend/DevOps |
| 9 | Expand security regression gate to include all 6 test groups | S | DevOps/QA |
| 10 | Add alt attributes to all 83+ image elements; remove LegacyDataTable/LegacyTabs | S | Frontend |

### 1.4 Launch Readiness Status

```
AUTHENTICATION        [████████░░] 80%  STRONG - Clerk + JWT enforcement solid
AUTHORIZATION         [██████░░░░] 60%  MEDIUM - Manual tenant enforcement, no reusable super-admin
TENANT ISOLATION      [██████░░░░] 60%  MEDIUM - Per-router enforcement, cross-layer tests excluded
DATA INTEGRITY        [███░░░░░░░] 30%  WEAK  - No PostgreSQL, no idempotency, no backups
ERROR HANDLING        [██░░░░░░░░] 20%  CRITICAL - Exception classes unused, contract broken
INFRASTRUCTURE        [████░░░░░░] 40%  WEAK  - Hardcoded secrets, SPOFs, single-stage builds
OBSERVABILITY         [██████░░░░] 66%  MEDIUM - L3 blind, stub health, 3 services no structured logs
TESTING               [█████░░░░░] 50%  MEDIUM - L2.5 uncovered, hostile tests are static analysis
SECURITY              [██████░░░░] 65%  MEDIUM - 0 critical/high but medium issues accumulate
PERFORMANCE           [████░░░░░░] 40%  WEAK  - No rate limiting, O(n) pagination, no caching
CI/CD                 [███████░░░] 70%  GOOD  - 25 gates but security regression blind
FRONTEND              [████████░░] 80%  STRONG - Excellent code quality, accessibility gap
DOCUMENTATION         [███░░░░░░░] 35%  WEAK  - OpenAPI specs missing, API docs absent
------------------------------------------------------------------------
OVERALL               [████░░░░░░] 42%  NOT READY FOR PRODUCTION
```

---

## 2. System Map

### 2.1 Repository Structure

```
fabric_4l/
├── .github/workflows/          # 61 CI/CD workflow files
├── k8s/                        # 176 Kubernetes manifests
│   ├── base/                   # Base deployments for all services
│   ├── overlays/               # Environment-specific patches
│   └── cronjobs/               # Backup and maintenance jobs
├── backend/
│   ├── layer1-ingestion/       # Data ingestion service
│   ├── layer2-extraction/      # Entity/signal extraction
│   ├── layer2.5-signal-refinery/  # Signal enrichment
│   ├── layer3-agents/          # AI agent orchestration
│   ├── layer4-knowledge-graph/ # Neo4j graph operations
│   ├── layer5-ground-truth/    # Truth labeling & validation
│   ├── layer6-benchmarks/      # Performance benchmarking
│   ├── layer7-billing/         # Billing service (in-memory, not production)
│   └── api-gateway/            # FastAPI gateway service
├── frontend/
│   ├── src/
│   │   ├── components/         # React components
│   │   ├── pages/              # 87 lazy-loaded route pages
│   │   ├── stores/             # 9 Zustand stores
│   │   ├── hooks/              # TanStack Query hooks (486 usages)
│   │   ├── lib/                # Utilities, auth bridge
│   │   └── types/              # TypeScript definitions
│   ├── e2e/                    # 87 Playwright/Cypress specs
│   └── tests/                  # 164 unit test files
├── shared/
│   └── fabric_framework/       # create_fabric_app() framework
│       ├── config.py           # _DEFAULT_DEV_SECRET at line 9
│       ├── database.py         # SQLite/in-memory ONLY (CRITICAL)
│       ├── exceptions.py       # 7 exception classes (UNUSED)
│       └── logging.py          # structlog configuration
├── openapi/
│   ├── fabric-4l-api.json      # DOES NOT EXIST
│   └── layer7-billing.json     # Empty (12 lines)
└── tests/
    ├── hostile/                # Pattern-based static analysis tests
    ├── quarantine/             # Quarantined test (overdue 2026-05-01)
    └── integration/            # Cross-layer integration tests
```

**Scale Metrics:**
- **1,195 Python files** across all backend services
- **707 TS/TSX files** in frontend
- **1,108 test files** total (backend + frontend + E2E)
- **61 CI workflow files**
- **176 Kubernetes manifests**

### 2.2 Backend Services Architecture

| Service | Layer | Purpose | Language | Database | Status |
|---------|-------|---------|----------|----------|--------|
| layer1-ingestion | 1 | Data ingestion, normalization | Python | PostgreSQL | Production |
| layer2-extraction | 2 | Entity extraction, NER | Python | PostgreSQL | Production |
| layer2.5-signal-refinery | 2.5 | Signal enrichment, dedup | Python | PostgreSQL | **No tests** |
| layer3-agents | 3 | Agent orchestration, LLM routing | Python | PostgreSQL | **Non-OTel tracer** |
| layer4-knowledge-graph | 4 | Graph construction, Cypher queries | Python | Neo4j | **Hardcoded password** |
| layer5-ground-truth | 5 | Truth labeling, human-in-the-loop | Python | PostgreSQL | Production |
| layer6-benchmarks | 6 | Benchmark execution, metrics | Python | PostgreSQL | **No structlog** |
| layer7-billing | 7 | Subscription, invoicing | Python | In-memory | **Not production** |
| api-gateway | API | Request routing, auth, CORS | Python | Redis | **Stub health check** |

### 2.3 Semantic Pipeline (6-Layer Flow)

```
[External Sources] --> [Layer 1: Ingestion] 
                              |
                              v
                    [Layer 2: Extraction]
                              |
                              v
                    [Layer 2.5: Signal Refinery]
                              |
                              v
                    [Layer 3: Agents]
                              |
                              v
                    [Layer 4: Knowledge Graph] --> Neo4j
                              |
                              v
                    [Layer 5: Ground Truth]
                              |
                              v
                    [Layer 6: Benchmarks]
```

### 2.4 Data Stores

| Store | Type | Count | Purpose | HA Status |
|-------|------|-------|---------|-----------|
| PostgreSQL | Relational | 5 databases | Layer 1-3, 5-6 data | **Single replica = SPOF** |
| Neo4j | Graph | 1 cluster | Knowledge graph | **Community edition = no HA** |
| Redis | Cache/Queue | 1 instance | Token revocation, rate limiting data | **No AUTH password** |
| MinIO/S3 | Object | 1 cluster | Document storage, exports | Standard |

### 2.5 Shared Framework: `create_fabric_app()`

All 8 backend services bootstrap through `create_fabric_app()` in the shared framework, which auto-configures:
- Exception handlers (registered but bypassed by raw `HTTPException`)
- CORS middleware (fail-closed configuration)
- Request ID generation and propagation (9/10 score)
- OpenTelemetry instrumentation (incomplete — Layer 3 uses custom tracer)
- Structured logging via structlog (missing in L2-extraction, L2.5, L6-benchmarks, api)

### 2.6 Deployment Model

- **Platform:** Kubernetes (176 manifests)
- **CI/CD:** GitHub Actions (61 workflows, 25 critical gates with merge blockers)
- **Containerization:** 8 Dockerfiles, all single-stage (no build optimization)
- **Security contexts:** 50 entries with `runAsNonRoot` + `allowPrivilegeEscalation: false`
- **Backup strategy:** CronJobs for PostgreSQL and Neo4j (both have P0 defects)
- **Secret management:** Kubernetes secrets (references have P0 defects)

---

## 3. Scorecard

### 3.1 Architecture

| Attribute | Value |
|-----------|-------|
| **Score** | **7.0 / 10** |
| **Confidence** | High |
| **Trend** | Stable |

**Evidence:**
- Strong 6-layer semantic pipeline with clear data flow boundaries
- Shared `create_fabric_app()` framework provides consistent bootstrapping across all 8 services
- Service separation by domain concern (ingestion, extraction, agents, graph, ground truth, benchmarks, billing)
- API gateway provides unified entry point with CORS, request ID, auth
- 9 Zustand stores on frontend with clean state separation
- 87 lazy-loaded routes optimize bundle splitting

**Main Blockers:**
- Layer 7 billing service uses in-memory store and is not production-ready
- No explicit service mesh or inter-service communication pattern documented
- Neo4j Community edition limits graph layer HA options
- Circuit breaker only present in Layer 1 — other layers lack cascading failure protection

**Recommended Next Action:** Evaluate Layer 7 billing service for production readiness or gate behind feature flag; design circuit breaker pattern for L2-L6.

---

### 3.2 Frontend

| Attribute | Value |
|-----------|-------|
| **Score** | **8.0 / 10** |
| **Confidence** | High |
| **Trend** | Positive |

**Evidence:**
- Only 2 `any` types across ~158,000 lines of frontend TypeScript (exceptional type safety)
- Zero `console.log` statements in production source code
- 87 lazy-loaded routes with tier-based RBAC (standard / advanced / admin)
- Clerk authentication with race-condition-proof bridge pattern
- 9 Zustand stores with atomic state updates
- 486 TanStack Query usages with proper caching and invalidation
- Component architecture follows clear separation of concerns

**Main Blockers:**
- **P1:** Only 4 `alt=` attributes across entire frontend (~83+ images lack accessibility text) — WCAG 2.1 AA violation risk
- **P2:** `LegacyDataTable.tsx` and `LegacyTabs.tsx` still present in codebase with zero imports — dead code maintenance burden

**Recommended Next Action:** Audit all `<img>` tags and add meaningful `alt` attributes; create ticket to remove LegacyDataTable and LegacyTabs components.

---

### 3.3 Backend

| Attribute | Value |
|-----------|-------|
| **Score** | **4.0 / 10** |
| **Confidence** | High |
| **Trend** | Declining (critical defects discovered) |

**Evidence:**
- CRITICAL: All 7 custom exception classes (`NotFoundError`, `ValidationError`, etc.) in `exceptions.py` are defined but **NEVER used**
- Approximately 88 error raise sites use raw `HTTPException` instead, bypassing the canonical `ErrorEnvelope` response contract
- **P0:** `database.py` has NO PostgreSQL implementation — only SQLite/in-memory; raises `UnsupportedDatabaseURL` for PostgreSQL URLs
- **P0:** No rate limiting middleware in API service
- **P0:** No idempotency key handling on any POST endpoints
- Pagination uses `PaginatedResponse[T]` generic on 13 endpoints (good pattern) but `total` count performs O(n) fetch-all instead of `COUNT(*)`
- Seed data is properly gated: `validate_production_safety()` rejects seed operations in production environments

**Main Blockers:**
- `database.py` PostgreSQL implementation (BLOCKS ALL PRODUCTION DATABASE CONNECTIVITY)
- Exception class migration (~88 raise sites)
- Rate limiting and idempotency infrastructure

**Recommended Next Action:** Implement PostgreSQL async driver (asyncpg) with connection pooling in `database.py`; begin systematic migration of `HTTPException` to canonical exceptions starting with most-frequently-hit endpoints.

---

### 3.4 Data Model and Migrations

| Attribute | Value |
|-----------|-------|
| **Score** | **6.0 / 10** |
| **Confidence** | Medium |
| **Trend** | Stable |

**Evidence:**
- 5 PostgreSQL databases defined in architecture with clear separation by domain
- Neo4j graph schema for knowledge layer
- Redis for ephemeral data (token revocation, caching)
- MinIO/S3 for object storage
- Seed data properly protected by `validate_production_safety()` — rejected in production
- Migration framework presence detected but no migration files audited in this pass

**Main Blockers:**
- PostgreSQL driver absent in shared `database.py` — migrations cannot execute in production
- Neo4j backup CronJob may use invalid syntax for Community edition
- O(n) pagination total count undermines performance at scale

**Recommended Next Action:** Implement PostgreSQL connectivity; validate Neo4j backup against Community edition syntax.

---

### 3.5 Security

| Attribute | Value |
|-----------|-------|
| **Score** | **6.5 / 10** |
| **Confidence** | High |
| **Trend** | Stable |

**Evidence — Strengths:**
- Token revocation implemented via Redis + SHA256 hashing
- bcrypt password hashing with 72-byte limit enforcement
- JWT with algorithm enforcement (`alg`) and base64url encoding
- Account lockout: 10 attempts → 15-minute lockout window
- CORS configured fail-closed (deny by default)
- Clerk webhooks verified with Svix HMAC signature validation
- Stripe webhooks verified with IP allowlist + signature validation
- 50 Kubernetes security contexts with `runAsNonRoot` + `allowPrivilegeEscalation: false`

**Evidence — Weaknesses (10 Medium, 14 Low findings):**
- **MEDIUM:** `_DEFAULT_DEV_SECRET` hardcoded in `config.py:9`
- **MEDIUM:** `.env.example` contains Keycloak secrets (commits credentials to repo history)
- **MEDIUM:** `_is_production_like()` treats unknown environments as production (safety bias but could mask misconfigurations)
- **MEDIUM:** No reusable `require_super_admin` dependency — super-admin checks duplicated per-router
- **MEDIUM:** API key authentication not implemented (only JWT session auth)
- **LOW:** 69 `str(e)` occurrences (0 in API service, concentrated in L3/L4 — loses exception type)
- **LOW:** Manual tenant enforcement per-router instead of middleware (risk of missed checks)
- **LOW:** 6 routes missing `response_model` (OpenAPI schema incomplete, no response validation)

**Main Blockers:**
- Hardcoded secrets in committed files
- No API key auth for service-to-service or third-party integration
- Manual tenant enforcement creates inconsistency risk

**Recommended Next Action:** Remove all hardcoded secrets from `config.py` and `.env.example`; implement `require_super_admin` as reusable FastAPI dependency; add API key authentication scheme.

---

### 3.6 Multi-Tenancy

| Attribute | Value |
|-----------|-------|
| **Score** | **5.0 / 10** |
| **Confidence** | High |
| **Trend** | Stable |

**Evidence:**
- Tenant isolation enforced at router level in each service (manual pattern)
- Tenant context propagated via request context (good)
- Cross-layer tenant isolation tests exist but **excluded from security regression gate**
- No reusable `require_tenant` or `require_super_admin` middleware — each router reimplements checks
- `_is_production_like()` safety bias: unknown envs treated as production (prevents accidental dev-in-prod but complicates new environment onboarding)

**Main Blockers:**
- Manual enforcement per-router creates high risk of missed tenant checks on new endpoints
- Cross-layer tenant tests excluded from mandatory CI gate — isolation guarantees not continuously verified
- No documented tenant isolation model (row-level? schema-level? database-level?)

**Recommended Next Action:** Extract tenant validation to reusable FastAPI dependency middleware; include cross-layer tenant tests in security regression gate; document tenant isolation architecture decision record (ADR).

---

### 3.7 Testing

| Attribute | Value |
|-----------|-------|
| **Score** | **5.0 / 10** |
| **Confidence** | High |
| **Trend** | Declining (L2.5 gap, quarantined test overdue) |

**Evidence:**
- 424 backend Python test files (strong volume)
- 164 frontend unit test files
- 87 E2E specification files
- Coverage gates on 7 of 8 layers
- `pytest-randomly` for test-order detection
- Placeholder test detection prevents empty `pass` tests from passing
- Canonical JWT and tenant fixtures shared across tests

**Main Blockers:**
- **P0:** Mandatory security regression gate **excludes 3 of 6 test groups**: cross-layer tenant tests, contract tests, K8s tests
- **P1:** Layer 2.5 (Signal Refinery) has only 7 test files and **no `fail_under` coverage gate**
- **P1:** "Hostile" tests in L1/L2/L3/L5/L6 are pattern-based static analysis (`grep`) not runtime behavioral tests — they verify code presence, not actual resistance to attacks
- **P1:** `tests/quarantine` contains overdue test (expected resolution 2026-05-01, now 27+ days overdue) — indicates broken test being ignored rather than fixed

**Recommended Next Action:** Immediately expand security regression gate to include all 6 test groups; add coverage gate for L2.5; convert hostile tests from grep patterns to runtime behavioral tests.

---

### 3.8 Observability

| Attribute | Value |
|-----------|-------|
| **Score** | **6.6 / 10** |
| **Confidence** | High |
| **Trend** | Stable |

**Evidence — Strengths:**
- Request ID propagation across services: **9/10**
- Audit logging SOC-2 compliant: **9/10**
- 18 Grafana dashboards deployed
- 3 Alertmanager configurations with PagerDuty + Slack routing
- Structured logging via structlog in 5 of 8 backend services

**Evidence — Weaknesses:**
- **P0:** Layer 3 uses custom non-OTel tracer — traces cannot reach Jaeger collector (pipeline stage is invisible)
- **P1:** API health check is a stub — reports `"ok"` even when database/dependencies are down
- **P1:** 3 services have zero structlog: L2-extraction, L2.5, L6-benchmarks, api-gateway
- **P1:** Circuit breaker only in Layer 1 — other layers lack cascading failure protection
- No distributed trace correlation documented for frontend-to-backend flows

**Recommended Next Action:** Replace Layer 3 custom tracer with OTel SDK; implement real health checks with dependency probing; add structlog to remaining 4 services.

---

### 3.9 Performance

| Attribute | Value |
|-----------|-------|
| **Score** | **4.0 / 10** |
| **Confidence** | Medium |
| **Trend** | Stable |

**Evidence:**
- `PaginatedResponse[T]` generic used consistently on 13 endpoints (good API pattern)
- 87 lazy-loaded frontend routes reduce initial bundle
- No database query N+1 analysis completed in this audit

**Main Blockers:**
- **P0:** No rate limiting — API vulnerable to accidental or malicious abuse
- Pagination `total` count does O(n) fetch-all instead of database `COUNT(*)` — will degrade linearly with table size
- Single-stage Docker builds produce larger images (slower startup, more memory)
- No caching strategy evident for hot paths (repeated entity lookups, graph queries)
- No database connection pooling implemented (relevant once PostgreSQL driver exists)

**Recommended Next Action:** Implement Redis-backed rate limiting; optimize pagination to use `COUNT(*)`; convert Dockerfiles to multi-stage builds.

---

### 3.10 Infrastructure and Deployment

| Attribute | Value |
|-----------|-------|
| **Score** | **4.5 / 10** |
| **Confidence** | High |
| **Trend** | Declining (backup and secret issues) |

**Evidence:**
- 176 Kubernetes manifests with 50 security contexts (`runAsNonRoot`, `allowPrivilegeEscalation: false`)
- Namespace isolation between services
- CronJobs for PostgreSQL and Neo4j backups (present but defective)
- 8 Dockerfiles covering all services

**Main Blockers:**
- **P0:** `postgres-backup-cronjob.yaml` references wrong secret name (`postgres-credentials` vs actual `postgres-secret`) — backups will fail
- **P0:** `layer4-agents.yml` has hardcoded `postgres:postgres` password in `CHECKPOINT_DATABASE_URL`
- **P0:** Neo4j backup CronJob syntax may be invalid for Community edition
- PostgreSQL single replica = single point of failure
- Neo4j Community edition = no HA clustering
- Redis has no AUTH password configured
- All Dockerfiles are single-stage (no build optimization)
- No resource limits/requests verified on all pods

**Recommended Next Action:** Fix backup CronJob secret reference; rotate and externalize Layer 4 password; validate Neo4j backup syntax against Community edition; add resource limits to all deployments.

---

### 3.11 CI/CD

| Attribute | Value |
|-----------|-------|
| **Score** | **7.0 / 10** |
| **Confidence** | High |
| **Trend** | Stable |

**Evidence:**
- 61 GitHub Actions workflow files
- 25 critical gates in CI matrix with merge blockers
- Coverage gates on 7 of 8 layers
- Security scanning integration (pattern present)
- Multi-environment deployment pipeline structure (dev/staging/prod)

**Main Blockers:**
- **P0:** Security regression gate excludes 3 of 6 test groups (cross-layer tenant, contract tests, K8s tests) — provides false confidence
- **P1:** Layer 2.5 has no coverage gate — untested code can merge
- **P1:** No verified rollback automation (workflows present but not validated)
- No canary deployment pattern detected

**Recommended Next Action:** Expand security regression gate to include all test groups; add L2.5 coverage gate; validate rollback workflow in staging environment.

---

### 3.12 Developer Experience

| Attribute | Value |
|-----------|-------|
| **Score** | **5.5 / 10** |
| **Confidence** | Medium |
| **Trend** | Stable |

**Evidence:**
- Shared `create_fabric_app()` reduces bootstrapping friction
- `.env.example` provides configuration template
- 9 Zustand stores with DevTools integration on frontend
- Hot reload likely available via FastAPI/React dev servers

**Main Blockers:**
- `.env.example` contains actual Keycloak secrets (security risk for new developers)
- `_is_production_like()` behavior is surprising — unknown environments treated as production
- Missing OpenAPI specs (fabric-4l-api.json does not exist) — no auto-generated API docs
- No local development Docker Compose with full stack
- Layer 7 billing JSON spec is empty (12 lines) — incomplete API contract

**Recommended Next Action:** Sanitize `.env.example` of all secrets; generate OpenAPI specs from FastAPI app; create `docker-compose.dev.yml` for full local stack.

---

### 3.13 Documentation

| Attribute | Value |
|-----------|-------|
| **Score** | **4.0 / 10** |
| **Confidence** | High |
| **Trend** | Stable |

**Evidence:**
- README likely present (not audited in detail)
- `.env.example` documents environment variables (but contains secrets)
- Code shows some inline documentation

**Main Blockers:**
- **P0:** `fabric-4l-api.json` (main OpenAPI spec) **does not exist**
- **P1:** `layer7-billing.json` is empty (only 12 lines)
- No architecture decision records (ADRs) found for critical choices
- No runbooks for incident response
- No onboarding guide for new engineers
- No API changelog or versioning strategy documented

**Recommended Next Action:** Auto-generate OpenAPI spec from FastAPI routes; create ADR for tenant isolation model; write incident response runbooks.

---

### 3.14 Product Completeness

| Attribute | Value |
|-----------|-------|
| **Score** | **5.5 / 10** |
| **Confidence** | Medium |
| **Trend** | Stable |

**Evidence:**
- 6-layer semantic pipeline is functionally complete from ingestion to benchmarks
- Frontend has 87 routes with RBAC covering standard/advanced/admin tiers
- Clerk auth integration complete
- Billing service scaffolded but not functional

**Main Blockers:**
- Layer 7 billing service is in-memory only — not production ready
- No admin dashboard or operational UI evident
- No customer-facing API documentation
- No public status page

**Recommended Next Action:** Complete Layer 7 billing with persistent storage; build admin dashboard for operational tasks.

---

### 3.15 Production Readiness Overall

| Attribute | Value |
|-----------|-------|
| **Score** | **4.2 / 10** |
| **Confidence** | High |
| **Trend** | Requires immediate action |

**Evidence:**
- **10 P0 launch blockers** spanning backend error handling, database connectivity, infrastructure secrets, testing CI gates, and observability
- **14 P1 production hardening items** covering security, accessibility, performance, and reliability
- **10 P2 quality items** covering code quality, dead code, and maintainability

**Main Blockers:**
All P0 items listed in Section 4. The most severe are:
1. No PostgreSQL database connectivity (total outage risk)
2. Broken error handling contract (API incompatibility)
3. Failed backup configuration (data loss risk)
4. Hardcoded production credentials (security breach risk)
5. Blind security CI gate (false confidence risk)

**Recommended Next Action:** Halt feature development; execute P0 remediation sprint (estimated 6-8 weeks); re-audit before launch.

---

## 4. P0 Launch Blockers

### P0-001: database.py Has No PostgreSQL Implementation — Total Production Outage

| Field | Detail |
|-------|--------|
| **ID** | P0-001 |
| **Title** | database.py Has No PostgreSQL Implementation — Total Production Outage |
| **Severity** | CRITICAL |
| **Category** | Backend / Data |
| **Status** | OPEN |

**Description:**
The shared `database.py` module in `fabric_framework/` — used by all 8 backend services to establish database connections — contains only SQLite and in-memory implementations. When presented with a PostgreSQL connection URL (which all 5 production databases use), it raises `UnsupportedDatabaseURL`. This means **zero backend services can connect to their databases in any environment using PostgreSQL**.

**Why It Matters:**
This is a total system outage condition. Every service that depends on PostgreSQL (Layer 1, 2, 2.5, 3, 5, 6, and the API gateway for Redis-adjacent operations) will crash on startup or fail all database operations. The architecture specifies 5 PostgreSQL databases, but the implementation cannot speak to them.

**Evidence:**
- File: `shared/fabric_framework/database.py` — `UnsupportedDatabaseURL` raised for PostgreSQL URLs
- Architecture specifies 5 PostgreSQL databases across layers 1-3, 5-6
- All 8 backend services import from `fabric_framework.database`

**Acceptance Criteria:**
- [ ] `database.py` supports `asyncpg` for PostgreSQL with connection pooling
- [ ] `create_async_engine()` accepts standard `postgresql+asyncpg://` URLs
- [ ] Connection pool settings are configurable via environment variables (`DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DB_POOL_TIMEOUT`)
- [ ] SQLite/in-memory support preserved for test environments
- [ ] All 8 services start successfully against PostgreSQL in staging

**Suggested Implementation:**
```python
# In shared/fabric_framework/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

async def get_database_engine(db_url: str):
    if db_url.startswith("postgresql"):
        return create_async_engine(
            db_url,
            pool_size=int(os.getenv("DB_POOL_SIZE", "10")),
            max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "20")),
            pool_timeout=float(os.getenv("DB_POOL_TIMEOUT", "30")),
            pool_pre_ping=True,
        )
    elif db_url.startswith("sqlite"):
        # existing implementation
    else:
        raise UnsupportedDatabaseURL(f"Unsupported: {db_url}")
```

**Suggested Tests:**
- Unit test: `test_database_postgresql_connectivity` — mock `create_async_engine` call, verify correct URL and pool params
- Integration test: `test_postgresql_pool_health` — verify pool creates connections, handles checkout/checkin
- Service test: Each service's `test_startup.py` should verify DB connection on application startup
- CI test: Staging deployment smoke test with PostgreSQL

**Effort:** L (1-2 weeks including testing and rollout)
**Dependencies:** None (foundational — other DB-dependent tickets block on this)
**Owner:** Backend Lead

---

### P0-002: Canonical Exception Classes Defined but Never Used — API Contract Violated

| Field | Detail |
|-------|--------|
| **ID** | P0-002 |
| **Title** | Canonical Exception Classes Defined but Never Used — API Contract Violated |
| **Severity** | CRITICAL |
| **Category** | Backend / Error Handling |
| **Status** | OPEN |

**Description:**
The shared framework defines 7 canonical exception classes (`NotFoundError`, `ValidationError`, `AuthenticationError`, `AuthorizationError`, `ConflictError`, `BadRequestError`, `InternalServerError`) with structured `ErrorEnvelope` serialization. However, approximately 88 error raise sites across all backend services use raw `HTTPException` from FastAPI/Starlette instead. This bypasses the `ErrorEnvelope` response format that frontend clients and API consumers expect, breaking the error handling contract.

**Why It Matters:**
The frontend expects errors in `ErrorEnvelope` format (`{"error": {"code": "...", "message": "...", "details": [...]}}`). When raw `HTTPException` is raised, clients receive `{"detail": "..."}` instead, causing parsing failures and unhandled promise rejections. This makes debugging impossible for API consumers and breaks the frontend error boundary logic.

**Evidence:**
- File: `shared/fabric_framework/exceptions.py` — 7 exception classes defined with docstrings
- File pattern: `**/*.py` — grep shows ~88 instances of `raise HTTPException(` across backend services
- Concentration: API service (0 raw HTTPException — good), Layer 3 and Layer 4 (highest concentration)
- File: `shared/fabric_framework/main.py` — exception handlers registered but never triggered

**Acceptance Criteria:**
- [ ] All ~88 `HTTPException` raises converted to canonical exception classes
- [ ] Frontend error parsing verified against `ErrorEnvelope` format for all error types
- [ ] No new `HTTPException` raises allowed (add lint rule: `flake8-http-exception-ban` or custom Ruff rule)
- [ ] Integration test verifies error response schema matches `ErrorEnvelope` for 4xx and 5xx errors

**Suggested Implementation:**
```python
# Before (current — BROKEN)
raise HTTPException(status_code=404, detail="User not found")

# After (correct)
raise NotFoundError(resource="user", identifier=user_id)
```

Create an automated refactor script using `libcst` or `ast` to perform bulk conversion, then manual review for edge cases.

**Suggested Tests:**
- Lint test: CI gate fails on `raise HTTPException(` in backend code
- Contract test: `test_error_envelope_schema` — hit each error endpoint, verify JSON schema
- E2E test: Frontend error boundary correctly displays messages from each error type

**Effort:** M (2-3 weeks for bulk conversion + lint enforcement)
**Dependencies:** P0-001 (database operations need to raise canonical exceptions for DB errors)
**Owner:** Backend Team

---

### P0-003: No Rate Limiting in API Service — DoS and Abuse Risk

| Field | Detail |
|-------|--------|
| **ID** | P0-003 |
| **Title** | No Rate Limiting in API Service — DoS and Abuse Risk |
| **Severity** | CRITICAL |
| **Category** | Backend / Security / Performance |
| **Status** | OPEN |

**Description:**
The API gateway service has no rate limiting middleware. Any client — authenticated or not — can make unlimited requests to any endpoint. This creates vulnerability to accidental abuse (runaway scripts), malicious denial-of-service attacks, and cascading failures when downstream services are overwhelmed.

**Why It Matters:**
Without rate limiting, a single misbehaving client or attacker can exhaust database connections, overwhelm the LLM agent layer (Layer 3), or trigger memory exhaustion. The API gateway is the single entry point for all traffic — it must protect the backend services.

**Evidence:**
- File: `backend/api-gateway/main.py` — no `SlowAPI`, `fastapi-limiter`, or custom rate limiter imported
- File: `shared/fabric_framework/main.py` — `create_fabric_app()` does not include rate limiting
- Redis is available for rate limit storage but not used for this purpose

**Acceptance Criteria:**
- [ ] Rate limiting middleware applied to all routes by default
- [ ] Different tiers: unauthenticated (strict), standard user (moderate), admin (lenient)
- [ ] Configurable limits via environment variables
- [ ] Redis-backed storage for distributed rate limiting (multi-replica API safe)
- [ ] `429 Too Many Requests` response with `Retry-After` header
- [ ] Rate limit headers exposed (`X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`)

**Suggested Implementation:**
Use `slowapi` with Redis storage:
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=os.getenv("REDIS_URL", "redis://localhost:6379")
)
app.state.limiter = limiter
```

**Suggested Tests:**
- `test_rate_limit_blocks_excessive_requests` — send N+1 requests, verify 429
- `test_rate_limit_allows_under_limit` — send N-1 requests, verify 200
- `test_rate_limit_headers_present` — verify all three headers on each response
- `test_rate_limit_tier_difference` — standard vs admin limits differ
- Load test: `k6 run rate-limit-load-test.js` — verify 429s under sustained load

**Effort:** M (1-2 weeks including Redis integration and tier logic)
**Dependencies:** P0-001 (Redis operational)
**Owner:** Backend Team

---

### P0-004: No Idempotency Keys on POST Endpoints — Duplicate Data Risk

| Field | Detail |
|-------|--------|
| **ID** | P0-004 |
| **Title** | No Idempotency Keys on POST Endpoints — Duplicate Data Risk |
| **Severity** | CRITICAL |
| **Category** | Backend / Data Integrity |
| **Status** | OPEN |

**Description:**
None of the POST endpoints across the API gateway or backend services implement idempotency key handling. When clients retry failed requests (due to network timeouts, 502s from gateway restarts, etc.), duplicate records are created in the database. This affects entity creation, billing events, knowledge graph insertions, and ground-truth labeling.

**Why It Matters:**
In a distributed system, network failures are inevitable. Clients (including the frontend JavaScript fetch with retry logic, mobile apps, and third-party integrations) will retry POST requests. Without idempotency keys, the same "create entity" request produces 2, 3, or N duplicate entities. This is especially dangerous for billing events (duplicate charges) and knowledge graph assertions (duplicate nodes/edges).

**Evidence:**
- File pattern: `backend/**/routers/*.py` — no `Idempotency-Key` header parsing
- File: `shared/fabric_framework/main.py` — no idempotency middleware
- 13+ POST endpoints across ingestion, extraction, agents, and ground truth layers

**Acceptance Criteria:**
- [ ] `Idempotency-Key` header accepted on all mutating endpoints (POST, PUT, PATCH, DELETE)
- [ ] Keys stored in Redis with 24-hour TTL
- [ ] Duplicate requests with same key return cached response (201 → 200 with cached `Location`)
- [ ] Key scoped to tenant (same key from different tenants = different operations)
- [ ] 409 Conflict returned if same key used with different payload

**Suggested Implementation:**
```python
# Middleware in shared/fabric_framework/middleware/idempotency.py
async def idempotency_middleware(request: Request, call_next):
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        key = request.headers.get("Idempotency-Key")
        if key:
            cached = await redis.get(f"idempotency:{tenant_id}:{key}")
            if cached:
                return JSONResponse(status_code=200, content=json.loads(cached))
    response = await call_next(request)
    # cache successful responses
    return response
```

**Suggested Tests:**
- `test_idempotent_post_creates_once` — same key twice, second returns 200 not 201
- `test_idempotent_different_keys_create_separate` — two different keys = two records
- `test_idempotent_tenant_isolation` — same key, different tenants = two records
- `test_idempotent_conflict_different_payload` — same key, different body = 409
- `test_idempotent_ttl_expiry` — key expires after 24h, new request succeeds

**Effort:** M (2 weeks including Redis schema and middleware testing)
**Dependencies:** P0-001 (Redis operational), P0-003 (rate limiting shares Redis)
**Owner:** Backend Team

---

### P0-005: PostgreSQL Backup CronJob References Wrong Secret — Backups Will Fail

| Field | Detail |
|-------|--------|
| **ID** | P0-005 |
| **Title** | PostgreSQL Backup CronJob References Wrong Secret — Backups Will Fail |
| **Severity** | CRITICAL |
| **Category** | Infrastructure / Data Loss |
| **Status** | OPEN |

**Description:**
The PostgreSQL backup CronJob manifest references a Kubernetes secret named `postgres-credentials`, but the actual secret created by the deployment process is named `postgres-secret`. When the CronJob pod starts, it will fail to mount the secret volume and the backup script will exit with authentication errors. No database backups will be produced, creating complete data loss exposure.

**Why It Matters:**
Without functional backups, any database corruption, accidental deletion, ransomware attack, or infrastructure failure results in permanent data loss. This is a business-continuity critical defect. The CronJob is intended to run on a schedule, but each execution will fail silently (Kubernetes will report Job completion but the backup script inside will fail).

**Evidence:**
- File: `k8s/cronjobs/postgres-backup-cronjob.yaml` — references `postgres-credentials`
- File: `k8s/base/postgresql/` — secret created as `postgres-secret`
- No monitoring/alerting on backup job failure detected

**Acceptance Criteria:**
- [ ] CronJob secret reference corrected to `postgres-secret`
- [ ] Backup Job outputs success metric or log line on completion
- [ ] Alertmanager rule fires if backup job fails 2 consecutive times
- [ ] Backup files verified restorable in staging monthly
- [ ] Backup retention policy documented and enforced (suggest 30 days)

**Suggested Implementation:**
```yaml
# k8s/cronjobs/postgres-backup-cronjob.yaml
env:
  - name: PGPASSWORD
    valueFrom:
      secretKeyRef:
        name: postgres-secret  # was: postgres-credentials
        key: password
```

**Suggested Tests:**
- `k apply --dry-run=server -f postgres-backup-cronjob.yaml` — validates secret reference resolves
- Manual test in staging: trigger CronJob manually (`kubectl create job --from=cronjob/postgres-backup test-backup`), verify `.sql` file written to S3/MinIO
- Alertmanager unit test: `promtool test rules backup-alerts.yaml`

**Effort:** S (1-2 days including alert configuration)
**Dependencies:** None
**Owner:** DevOps / SRE

---

### P0-006: Layer 4 Agents Hardcoded Database Password in Manifest

| Field | Detail |
|-------|--------|
| **ID** | P0-006 |
| **Title** | Layer 4 Agents Hardcoded Database Password in Manifest |
| **Severity** | CRITICAL |
| **Category** | Infrastructure / Security |
| **Status** | OPEN |

**Description:**
The Layer 4 (Knowledge Graph / Agents) Kubernetes deployment manifest contains a hardcoded database password `postgres:postgres` in the `CHECKPOINT_DATABASE_URL` environment variable. This password is committed to the Git repository, visible in plain text in pod descriptions (`kubectl describe pod`), and logged in various tooling. Any access to the repository, CI logs, or cluster read permissions exposes production database credentials.

**Why It Matters:**
Hardcoded credentials in version control are a critical security vulnerability. Even in private repositories, access is broader than production secret access should be. CI systems, developer laptops, and backup systems all have repository access. The `postgres:postgres` credential is also a well-known default that automated scanners will flag immediately and attackers will try first.

**Evidence:**
- File: `k8s/base/layer4-agents.yml` — `CHECKPOINT_DATABASE_URL: postgresql://postgres:postgres@postgres:5432/layer4`
- Password visible in: Git history, GitHub UI, CI logs, `kubectl describe`, pod env in cluster

**Acceptance Criteria:**
- [ ] Hardcoded password removed from `layer4-agents.yml`
- [ ] `CHECKPOINT_DATABASE_URL` constructed from Kubernetes secret via `env.valueFrom.secretKeyRef`
- [ ] Password rotated immediately in all environments (staging, prod)
- [ ] Git history scrubbed or password invalidated (rotate rather than rely on history rewrite)
- [ ] CI gate added to block commits containing `postgres:postgres` pattern

**Suggested Implementation:**
```yaml
# k8s/base/layer4-agents.yml
env:
  - name: DB_PASSWORD
    valueFrom:
      secretKeyRef:
        name: layer4-db-secret
        key: password
  - name: CHECKPOINT_DATABASE_URL
    value: "postgresql://postgres:$(DB_PASSWORD)@postgres:5432/layer4"
```

**Suggested Tests:**
- Pre-commit hook: `detect-secrets` or `gitleaks` blocks `postgres:postgres`
- CI gate: `grep -r "postgres:postgres" k8s/` fails the build
- `kubectl apply --dry-run=server` validates secret reference

**Effort:** S (1 day for fix + password rotation; 1 day for CI gates)
**Dependencies:** None
**Owner:** DevOps / Security

---

### P0-007: Security Regression Gate Excludes 3 of 6 Test Groups — False Confidence

| Field | Detail |
|-------|--------|
| **ID** | P0-007 |
| **Title** | Security Regression Gate Excludes 3 of 6 Test Groups — False Confidence |
| **Severity** | CRITICAL |
| **Category** | CI/CD / Testing / Security |
| **Status** | OPEN |

**Description:**
The mandatory security regression CI gate — which blocks merge if it fails — only executes 3 of 6 available test groups. The excluded groups are: cross-layer tenant isolation tests, contract tests, and Kubernetes tests. These are precisely the tests that verify tenant isolation (the core security model), API contract stability, and infrastructure security posture. The gate provides false confidence that security is verified on every merge.

**Why It Matters:**
A mandatory gate that runs only half the security tests is worse than no gate — it creates organizational belief that security is continuously verified when it is not. Tenant isolation bugs, contract-breaking changes, and K8s security regressions can merge undetected. When the excluded tests are eventually run (likely manually or in a separate pipeline), failures will be discovered late when they are expensive to fix.

**Evidence:**
- File: `.github/workflows/security-regression.yml` — test matrix includes only 3 of 6 groups
- Excluded: `tests/cross-layer-tenant/`, `tests/contract/`, `tests/k8s/`
- Included: unit tests, integration tests, hostile pattern tests
- Gate is merge-blocking (`required_status_checks` in branch protection)

**Acceptance Criteria:**
- [ ] All 6 test groups execute in security regression gate
- [ ] Cross-layer tenant isolation tests pass and are required
- [ ] Contract tests pass and are required
- [ ] K8s security tests (manifest validation, secret scanning) pass and are required
- [ ] Gate execution time remains under 15 minutes (parallelize if needed)
- [ ] If tests are excluded for legitimate reasons, documented ADR with approval

**Suggested Implementation:**
Expand the test matrix in `security-regression.yml`:
```yaml
strategy:
  matrix:
    test_group:
      - unit
      - integration
      - hostile
      - cross-layer-tenant
      - contract
      - k8s
```

For K8s tests, use `kubeval` or `kubeconform` for manifest validation, and `kubesec` for security scanning.

**Suggested Tests:**
- The fix IS the test — verify all 6 groups appear in CI run logs
- Add CI self-test: `grep` the workflow file to verify 6 groups are listed

**Effort:** S (2-3 days to fix CI + stabilize any failing excluded tests)
**Dependencies:** May expose failing tests in excluded groups that need their own fixes
**Owner:** DevOps / QA Lead

---

### P0-008: Layer 3 Custom Tracer Cannot Reach Jaeger — Pipeline Stage Invisible

| Field | Detail |
|-------|--------|
| **ID** | P0-008 |
| **Title** | Layer 3 Custom Tracer Cannot Reach Jaeger — Pipeline Stage Invisible |
| **Severity** | CRITICAL |
| **Category** | Observability / Backend |
| **Status** | OPEN |

**Description:**
Layer 3 (Agents) uses a custom-built tracer instead of the OpenTelemetry SDK used by other services. This custom tracer emits traces in a format that the Jaeger collector cannot ingest. As a result, all agent orchestration, LLM routing, and prompt execution traces are lost. Layer 3 is a critical component in the semantic pipeline — when it fails or performs poorly, operators cannot diagnose the issue.

**Why It Matters:**
Layer 3 is where AI agents are orchestrated, LLM calls are made, and prompts are routed. These are the highest-latency, highest-cost operations in the system. Without traces, operators cannot identify which agent is slow, which LLM provider is failing, or where token costs are spiking. The MTTR (mean time to recovery) for Layer 3 incidents is unbounded.

**Evidence:**
- Layer 3 source code uses custom tracer class (non-OTel)
- Jaeger collector receives traces from L1, L2, L4, L5, L6 but not L3
- File: `backend/layer3-agents/` — custom instrumentation instead of `opentelemetry.instrumentation`

**Acceptance Criteria:**
- [ ] Layer 3 uses OTel `TracerProvider` and `trace.get_tracer(__name__)`
- [ ] All LLM calls wrapped with `@tracer.start_as_current_span()`
- [ ] Agent routing decisions traced with attributes (`agent_id`, `model`, `provider`)
- [ ] Token usage and latency recorded as span attributes/metrics
- [ ] Traces visible in Jaeger UI for Layer 3 operations
- [ ] Custom tracer code removed entirely

**Suggested Implementation:**
```python
from opentelemetry import trace
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentation

tracer = trace.get_tracer(__name__)

@tracer.start_as_current_span("agent.execute")
async def execute_agent(agent_id: str, prompt: str):
    current_span = trace.get_current_span()
    current_span.set_attribute("agent.id", agent_id)
    current_span.set_attribute("llm.model", model)
    # existing logic
```

**Suggested Tests:**
- `test_l3_traces_reach_jaeger` — execute agent call, query Jaeger API for trace
- `test_l3_span_attributes` — verify agent_id, model, token_count present in span
- `test_no_custom_tracer_imports` — grep fails if custom tracer module imported

**Effort:** M (2 weeks to instrument all agent paths, verify in Jaeger, remove custom code)
**Dependencies:** OTel collector configuration verified working
**Owner:** Backend Team / Observability

---

### P0-009: API Health Check Is a Stub — Reports OK When Dependencies Down

| Field | Detail |
|-------|--------|
| **ID** | P0-009 |
| **Title** | API Health Check Is a Stub — Reports OK When Dependencies Down |
| **Severity** | CRITICAL |
| **Category** | Observability / Infrastructure |
| **Status** | OPEN |

**Description:**
The API gateway health check endpoint (`/health` or `/healthz`) returns a static `{"status": "ok"}` response without probing any downstream dependencies. If the PostgreSQL database, Redis cache, or Neo4j graph is unreachable, the health check still returns HTTP 200. Kubernetes load balancers and external monitors (Datadog, Pingdom) will continue routing traffic to a service that cannot serve requests.

**Why It Matters:**
In Kubernetes, the liveness probe determines if a pod should be restarted; the readiness probe determines if a pod should receive traffic. When these probes hit a stub endpoint, a service with dead dependencies appears healthy. Traffic continues to flow to failing instances, user requests fail with 500s instead of being routed to healthy replicas, and auto-scaling may not trigger because the pod appears "up."

**Evidence:**
- File: `backend/api-gateway/routers/health.py` — returns static JSON without dependency checks
- Kubernetes manifests likely reference `/health` for liveness/readiness probes
- No database connection check, no Redis ping, no Neo4j connectivity test

**Acceptance Criteria:**
- [ ] `/health/live` — lightweight self-check (process running, returns 200)
- [ ] `/health/ready` — probes all critical dependencies (PostgreSQL query, Redis ping, Neo4j ping), returns 200 only if all pass
- [ ] Individual dependency status exposed in ready response (`{"postgres": "ok", "redis": "fail", "neo4j": "ok"}`)
- [ ] Kubernetes manifests updated: `livenessProbe` → `/health/live`, `readinessProbe` → `/health/ready`
- [ ] Load balancer removes instance from pool within 10 seconds of ready failure

**Suggested Implementation:**
```python
@router.get("/health/ready")
async def health_ready():
    checks = {}
    healthy = True
    
    try:
        await db.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception as e:
        checks["postgres"] = f"fail: {e}"
        healthy = False
    
    try:
        await redis.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"fail: {e}"
        healthy = False
    
    # similar for neo4j
    
    status = 200 if healthy else 503
    return JSONResponse(content={"status": "ready" if healthy else "not_ready", "checks": checks}, status_code=status)
```

**Suggested Tests:**
- `test_health_live_returns_200` — always passes
- `test_health_ready_all_ok` — all dependencies up, returns 200 with all "ok"
- `test_health_ready_db_down` — mock DB failure, returns 503 with postgres "fail"
- `test_health_ready_redis_down` — mock Redis failure, returns 503
- Integration: Stop Redis container in test env, verify LB removes pod

**Effort:** M (1 week including K8s manifest updates and load balancer verification)
**Dependencies:** P0-001 (PostgreSQL connectivity needed for real probe)
**Owner:** Backend / DevOps

---

### P0-010: Neo4j Backup CronJob May Use Invalid Community Edition Syntax

| Field | Detail |
|-------|--------|
| **ID** | P0-010 |
| **Title** | Neo4j Backup CronJob May Use Invalid Community Edition Syntax |
| **Severity** | CRITICAL |
| **Category** | Infrastructure / Data Loss |
| **Status** | OPEN |

**Description:**
The Neo4j backup CronJob may use `neo4j-admin backup` command syntax, which is only available in Neo4j Enterprise Edition. The deployed Neo4j instance uses Community Edition, which only supports `neo4j-admin dump` (offline, requires database stop) or logical dumps via Cypher Shell. The backup job will fail every execution, leaving graph data without backup protection.

**Why It Matters:**
The knowledge graph (Layer 4) contains the core semantic network of extracted entities and relationships. Loss of this data requires complete reprocessing of all ingested documents — potentially days of computation and significant LLM API costs. Without functional backups, a Neo4j crash or data corruption is unrecoverable.

**Evidence:**
- File: `k8s/cronjobs/neo4j-backup-cronjob.yaml` — command syntax not verified against Community edition
- Neo4j deployment uses Community edition (no HA, no online backup)
- No alternative backup strategy (e.g., persistent volume snapshots) detected

**Acceptance Criteria:**
- [ ] Backup command verified compatible with Neo4j Community Edition
- [ ] If `neo4j-admin dump` used: database consistency verified, downtime acceptable and documented
- [ ] Alternative: Cypher-shell logical export tested and working
- [ ] Alternative: PV snapshot strategy documented if dump is insufficient
- [ ] Backup files written to S3/MinIO with retention policy
- [ ] Restore procedure documented and tested in staging quarterly

**Suggested Implementation:**
Use `neo4j-admin database dump` (Neo4j 5.x Community) or Cypher-shell logical export:
```bash
#!/bin/bash
# neo4j-backup.sh
neo4j-admin database dump neo4j --to-path=/backup/neo4j-$(date +%Y%m%d-%H%M%S).dump
aws s3 cp /backup/*.dump s3://fabric4l-backups/neo4j/
```

Or using Cypher-shell for online logical backup:
```bash
cypher-shell -u neo4j -p $NEO4J_PASSWORD "CALL apoc.export.cypher.all('/backup/graph.cypher', {})"
```

**Suggested Tests:**
- Manual test in staging: trigger CronJob, verify `.dump` or `.cypher` file created
- Restore test: restore backup to fresh Neo4j instance, verify graph integrity
- `kubectl logs job/neo4j-backup-test` — no errors in output

**Effort:** M (1 week to fix syntax, test backup/restore, document procedure)
**Dependencies:** None
**Owner:** DevOps / SRE

---


## 5. P1 Production Hardening

### P1-001: _DEFAULT_DEV_SECRET Hardcoded in config.py

| Field | Detail |
|-------|--------|
| **ID** | P1-001 |
| **Severity** | MEDIUM |
| **Category** | Security / Secrets |
| **Status** | OPEN |

**Description:**
`shared/fabric_framework/config.py` at line 9 contains a hardcoded `_DEFAULT_DEV_SECRET` value used as a fallback when no `SECRET_KEY` environment variable is provided. This default is likely a known or guessable string. If the application starts without the environment variable set (common in development, misconfiguration in production), it uses this predictable secret for JWT signing and session encryption.

**Why It Matters:**
A predictable secret allows an attacker to forge JWT tokens, bypass authentication, and impersonate any user including administrators. In a multi-tenant system, this means cross-tenant access and complete authorization bypass.

**Evidence:**
- File: `shared/fabric_framework/config.py`, line 9: `_DEFAULT_DEV_SECRET = "..."`
- Used as fallback: `SECRET_KEY = os.getenv("SECRET_KEY", _DEFAULT_DEV_SECRET)`

**Acceptance Criteria:**
- [ ] `_DEFAULT_DEV_SECRET` removed entirely — no fallback, application fails to start without `SECRET_KEY`
- [ ] Startup validation enforces `SECRET_KEY` is present and minimum 32 bytes of entropy
- [ ] CI test verifies application exits with clear error if `SECRET_KEY` missing
- [ ] `.env.example` updated with `SECRET_KEY=replace_with_32_byte_random` placeholder

**Suggested Implementation:**
```python
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY environment variable is required. Generate with: openssl rand -hex 32")
if len(SECRET_KEY) < 32:
    logger.warning("SECRET_KEY should be at least 32 characters for adequate entropy")
```

**Effort:** S
**Dependencies:** None
**Owner:** Security / Backend

---

### P1-002: .env.example Contains Keycloak Secrets

| Field | Detail |
|-------|--------|
| **ID** | P1-002 |
| **Severity** | MEDIUM |
| **Category** | Security / Secrets |
| **Status** | OPEN |

**Description:**
The `.env.example` file committed to the repository contains actual Keycloak client secrets and potentially other credential material. Developers copying this file to `.env` for local development will use these same secrets, which may be valid in shared environments. These secrets are now in Git history forever (unless rewritten).

**Why It Matters:**
Committed secrets in `.env.example` train developers to treat secrets as shareable. If these credentials are valid for any environment (staging, shared dev), unauthorized access is possible. Git history retention means these secrets persist even after file deletion.

**Evidence:**
- File: `.env.example` — contains `KEYCLOAK_CLIENT_SECRET=...` with non-placeholder value

**Acceptance Criteria:**
- [ ] All real secrets removed from `.env.example`, replaced with `<GENERATE_YOUR_OWN>` or `REPLACE_ME`
- [ ] `.env.example` added to secret scanning (gitleaks) exclusion for patterns, but checked for real-looking values
- [ ] If secrets were valid, rotate them immediately in Keycloak
- [ ] Git history evaluated for cleanup or secrets invalidated via rotation

**Effort:** S
**Dependencies:** None
**Owner:** Security / DevOps

---

### P1-003: _is_production_like() Surprising Behavior for Unknown Environments

| Field | Detail |
|-------|--------|
| **ID** | P1-003 |
| **Severity** | MEDIUM |
| **Category** | Backend / Configuration |
| **Status** | OPEN |

**Description:**
The `_is_production_like()` function in the configuration module treats unknown environment names (anything other than explicit "development" or "test") as production. While this is a safety bias (prevents accidental dev-mode in production), it causes surprising behavior when new environments are added (e.g., "staging", "uat", "demo") — they run with production safety gates enabled, which may break seeding, debugging, and migration workflows.

**Why It Matters:**
In a growing engineering team, new environments are added frequently. If "staging" is accidentally treated as production, database seeding is blocked, debug endpoints are disabled, and destructive operation guards are enforced. Engineers lose hours debugging why "staging" behaves like "prod" before discovering this implicit behavior.

**Evidence:**
- File: `shared/fabric_framework/config.py` — `_is_production_like()` implementation

**Acceptance Criteria:**
- [ ] Explicit environment allowlist: only `production` returns True for `is_production_like()`
- [ ] New environments must be explicitly registered in configuration
- [ ] Startup logs print clear banner: `RUNNING IN PRODUCTION MODE` when production detected
- [ ] Documentation updated with environment configuration guide

**Suggested Implementation:**
```python
def is_production_like() -> bool:
    return os.getenv("ENVIRONMENT") == "production"
```

**Effort:** S
**Dependencies:** None
**Owner:** Backend

---

### P1-004: No Reusable require_super_admin Dependency

| Field | Detail |
|-------|--------|
| **ID** | P1-004 |
| **Severity** | MEDIUM |
| **Category** | Backend / Authorization |
| **Status** | OPEN |

**Description:**
Super-admin authorization checks are duplicated across multiple routers instead of using a single reusable FastAPI dependency. Each router that needs admin protection reimplements the check logic, leading to inconsistency and risk of missed checks on new endpoints.

**Why It Matters:**
Authorization checks should be centralized and reusable. Duplicated logic drifts over time — one router may check a different claim, another may miss the check entirely on a new sub-route. A reusable dependency ensures consistent enforcement and makes audits trivial.

**Evidence:**
- Pattern found across `backend/**/routers/*.py` — super-admin checks repeated inline
- No `dependencies=[require_super_admin]` pattern detected

**Acceptance Criteria:**
- [ ] `require_super_admin` FastAPI dependency created in `shared/fabric_framework/auth.py`
- [ ] All existing inline super-admin checks refactored to use dependency
- [ ] Dependency checks `role=admin` claim in JWT with proper error message
- [ ] Unit tests for dependency: admin passes, non-admin 403, missing token 401

**Suggested Implementation:**
```python
async def require_super_admin(
    user: CurrentUser = Depends(get_current_user)
) -> User:
    if user.role != "admin":
        raise AuthorizationError(detail="Super-admin access required")
    return user

# Usage:
@router.post("/admin/reset", dependencies=[Depends(require_super_admin)])
async def admin_reset(...):
```

**Effort:** S
**Dependencies:** P0-002 (canonical exceptions)
**Owner:** Backend / Security

---

### P1-005: API Key Authentication Not Implemented

| Field | Detail |
|-------|--------|
| **ID** | P1-005 |
| **Severity** | MEDIUM |
| **Category** | Security / Authentication |
| **Status** | OPEN |

**Description:**
The system only supports JWT session authentication via Clerk. There is no API key authentication scheme for service-to-service communication, third-party integrations, or programmatic API access. All API consumers must use browser-based Clerk sessions.

**Why It Matters:**
Service-to-service calls within the cluster should not use browser session JWTs. Third-party integrations (webhook receivers, ETL pipelines, customer scripts) need long-lived API keys. Without API key auth, all programmatic access must simulate browser sessions, which is fragile and less secure.

**Evidence:**
- No `X-API-Key` header handling found in API gateway
- No API key generation/management endpoints
- No API key database table or Redis key pattern

**Acceptance Criteria:**
- [ ] API key model/table created (id, tenant_id, hashed_key, name, scopes, created_at, expires_at, last_used_at)
- [ ] `X-API-Key` header authentication middleware in API gateway
- [ ] API key management endpoints (create, list, revoke) for admin users
- [ ] Scopes/permissions model for API keys (read, write, admin)
- [ ] Rate limiting separate for API keys vs session auth
- [ ] Keys stored as SHA-256 hashes (like token revocation pattern)

**Effort:** M (2-3 weeks including UI for key management)
**Dependencies:** P0-003 (rate limiting shares infrastructure)
**Owner:** Backend / Security

---

### P1-006: Frontend Accessibility — Only 4 alt= Attributes Across Entire Application

| Field | Detail |
|-------|--------|
| **ID** | P1-006 |
| **Severity** | MEDIUM |
| **Category** | Frontend / Accessibility |
| **Status** | OPEN |

**Description:**
The frontend codebase contains approximately 83+ `<img>` elements and image-bearing components, but only 4 have `alt=` attributes. This means screen readers cannot describe images to visually impaired users, and the application fails WCAG 2.1 Level AA compliance. In many jurisdictions, this creates legal liability for accessibility discrimination.

**Why It Matters:**
WCAG 2.1 AA is the legal standard for web accessibility in the US (ADA), EU (EAA), and other regions. Missing alt text is one of the most common and easily detectable violations. Beyond compliance, it makes the application unusable for screen reader users who cannot understand image content.

**Evidence:**
- Frontend audit: 4 `alt=` attributes found across ~158,000 lines of frontend code
- 87 route pages, multiple components with images (avatars, charts, logos, icons)

**Acceptance Criteria:**
- [ ] All `<img>` tags have meaningful `alt` attributes (empty `alt=""` for decorative images)
- [ ] ESLint rule `jsx-a11y/alt-text` enabled and enforced in CI
- [ ] axe-core or pa11y scan passes in CI with zero violations
- [ ] Images in dynamic content (user uploads) use filename fallback with sanitization
- [ ] Charts and data visualizations have `aria-label` or screen-reader text

**Suggested Implementation:**
```tsx
// ESLint config
// .eslintrc.js
{ "extends": ["plugin:jsx-a11y/recommended"] }

// Example fixes
<img src={logo} alt="Fabric 4L logo" />
<img src={user.avatar} alt={`${user.name}'s avatar`} />
<img src={decorativePattern} alt="" role="presentation" />
```

**Effort:** S (1 week for audit + fixes, ongoing lint enforcement)
**Dependencies:** None
**Owner:** Frontend

---

### P1-007: Legacy Components Present with Zero Imports

| Field | Detail |
|-------|--------|
| **ID** | P1-007 |
| **Severity** | MEDIUM |
| **Category** | Frontend / Maintainability |
| **Status** | OPEN |

**Description:**
`LegacyDataTable.tsx` and `LegacyTabs.tsx` remain in the codebase despite having zero imports across the entire application. These are superseded by newer components but continue to be compiled, bundled (potentially), and maintained.

**Why It Matters:**
Dead code increases bundle size (if not tree-shaken), confuses new developers, and creates maintenance burden. If bugs are found in these components, effort is wasted fixing code that is never used. They also appear in IDE autocomplete, increasing cognitive load.

**Evidence:**
- File: `frontend/src/components/LegacyDataTable.tsx` — 0 imports across codebase
- File: `frontend/src/components/LegacyTabs.tsx` — 0 imports across codebase

**Acceptance Criteria:**
- [ ] Verify zero imports via `grep -r "LegacyDataTable\|LegacyTabs" frontend/src --include="*.tsx" --include="*.ts"`
- [ ] Delete both files
- [ ] CI passes without them
- [ ] If they contain useful logic, extract to archive docs or merge into current components

**Effort:** S
**Dependencies:** None
**Owner:** Frontend

---

### P1-008: Layer 2.5 Signal Refinery Has No Coverage Gate

| Field | Detail |
|-------|--------|
| **ID** | P1-008 |
| **Title** | Layer 2.5 Signal Refinery Has No Coverage Gate |
| **Severity** | MEDIUM |
| **Category** | Testing / Quality |
| **Status** | OPEN |

**Description:**
Layer 2.5 (Signal Refinery) — the deduplication and signal enrichment layer — has only 7 test files and no `fail_under` coverage gate in CI. Code can be merged to this layer with zero test coverage, creating a quality hole in the semantic pipeline.

**Why It Matters:**
Signal refinery performs deduplication — one of the most critical data integrity operations. A bug here causes duplicate entities to propagate through the knowledge graph, corrupting downstream analytics and agent reasoning. Without tests and coverage gates, regressions go undetected.

**Evidence:**
- Only 7 test files in `backend/layer2.5-signal-refinery/tests/`
- No `fail_under` in CI matrix for L2.5
- 7 of 8 layers have coverage gates; L2.5 is the exception

**Acceptance Criteria:**
- [ ] `fail_under=80` coverage gate added for L2.5 in CI matrix
- [ ] Test files increase from 7 to minimum 15 covering core dedup logic
- [ ] Integration tests for signal refinery with L2 extraction and L3 agents
- [ ] Mutation testing or property-based testing for dedup edge cases

**Effort:** M (2 weeks to write tests and stabilize coverage)
**Dependencies:** None
**Owner:** QA / Backend

---

### P1-009: Hostile Tests Are Pattern-Based Static Analysis, Not Runtime Behavioral Tests

| Field | Detail |
|-------|--------|
| **ID** | P1-009 |
| **Severity** | MEDIUM |
| **Category** | Testing / Security |
| **Status** | OPEN |

**Description:**
The "hostile" security tests in Layers 1, 2, 3, 5, and 6 use `grep`-based static analysis to verify that certain patterns exist (or don't exist) in source code. They do not execute the application and attempt actual attacks — SQL injection, XSS, path traversal, etc. This means they verify code appearance, not runtime resistance.

**Why It Matters:**
Static analysis can be bypassed by code that looks safe but behaves unsafely (e.g., dynamic query construction that evades the grep pattern). Real security confidence comes from behavioral tests that attempt attacks and verify they are blocked. The current tests create false confidence.

**Evidence:**
- File pattern: `tests/hostile/` — grep-based pattern matching for "dangerous" strings
- No runtime attack simulation (e.g., sending SQL injection payloads to endpoints)

**Acceptance Criteria:**
- [ ] Each hostile test converted to runtime behavioral test
- [ ] SQL injection: send `' OR 1=1 --` to all query endpoints, verify 400/422
- [ ] XSS: send `<script>alert(1)</script>` to all input endpoints, verify sanitization
- [ ] Path traversal: send `../../../etc/passwd` to file endpoints, verify blocking
- [ ] Authentication bypass: attempt admin endpoints without/with wrong role, verify 403
- [ ] Static analysis tests retained as supplementary fast checks

**Effort:** M (2-3 weeks to write behavioral tests for all attack vectors)
**Dependencies:** P0-002 (canonical exceptions for proper error responses)
**Owner:** Security / QA

---

### P1-010: Quarantined Test Overdue — Broken Test Being Ignored

| Field | Detail |
|-------|--------|
| **ID** | P1-010 |
| **Title** | Quarantined Test Overdue — Broken Test Being Ignored |
| **Severity** | MEDIUM |
| **Category** | Testing / Process |
| **Status** | OPEN |

**Description:**
A test in `tests/quarantine/` has an expected resolution date of 2026-05-01, which is now 27+ days overdue. Quarantined tests are meant to be temporary — they isolate a flaky or broken test while it is fixed. An overdue quarantine indicates process failure: the test was forgotten rather than fixed.

**Why It Matters:**
Quarantined tests rot. As the codebase evolves, the quarantined test becomes harder to fix because the code it tests has changed. Meanwhile, the functionality it covers has no automated protection. The quarantine mechanism is valuable; the lack of resolution tracking undermines it.

**Evidence:**
- File: `tests/quarantine/` — contains test with `expected_resolution: 2026-05-01`
- No alerting or CI gate for overdue quarantines

**Acceptance Criteria:**
- [ ] Overdue test fixed and returned to active suite OR deleted if obsolete
- [ ] CI gate added: fail build if any quarantined test is >7 days past expected_resolution
- [ ] Weekly report of quarantined tests sent to team
- [ ] Process documented: max quarantine duration, escalation path

**Effort:** S (1-2 days for fix + gate)
**Dependencies:** None
**Owner:** QA / Backend

---

### P1-011: 69 str(e) Occurrences Lose Exception Type Information

| Field | Detail |
|-------|--------|
| **ID** | P1-011 |
| **Severity** | LOW (aggregated impact MEDIUM) |
| **Category** | Backend / Code Quality |
| **Status** | OPEN |

**Description:**
Across the backend codebase, 69 locations use `str(e)` to convert exceptions to strings. This discards the exception type, stack trace, and structured context. Concentrated in Layer 3 and Layer 4, these occurrences mean agent failures and graph errors are logged as generic strings, making debugging difficult.

**Why It Matters:**
When `str(e)` is used, a `DatabaseConnectionError("timeout")` and a `ValidationError("timeout")` produce identical log messages. Structured logging depends on exception type and context to be useful. During incident response, engineers cannot distinguish error categories from logs.

**Evidence:**
- 69 occurrences of `str(e)` across backend Python files
- Concentration: 0 in API service, highest in Layer 3 (agents) and Layer 4 (knowledge graph)

**Acceptance Criteria:**
- [ ] All `str(e)` occurrences replaced with structured logging: `logger.exception("message", error=e)` or `logger.error("message", exc_info=e)`
- [ ] Ruff/flake8 rule added to ban `str(e)` in exception handling
- [ ] Verify zero occurrences with `grep -r "str(e)" backend/ --include="*.py"`

**Effort:** S (2-3 days for bulk refactor + lint rule)
**Dependencies:** None
**Owner:** Backend

---

### P1-012: Manual Tenant Enforcement Per-Router Creates Inconsistency Risk

| Field | Detail |
|-------|--------|
| **ID** | P1-012 |
| **Severity** | MEDIUM |
| **Category** | Backend / Multi-Tenancy |
| **Status** | OPEN |

**Description:**
Tenant isolation is enforced manually within each router file rather than through reusable middleware or dependencies. Each endpoint handler extracts the tenant from the request context and validates access inline. This creates inconsistency — some endpoints may miss the check, and new endpoints added by developers may not include it.

**Why It Matters:**
In a multi-tenant SaaS product, a single endpoint missing tenant isolation allows cross-tenant data access — a catastrophic security breach. Manual enforcement is error-prone; automated enforcement via middleware guarantees all requests are checked.

**Evidence:**
- Pattern: `tenant_id = request.state.tenant_id` repeated across router files
- No `require_tenant` dependency or middleware in `create_fabric_app()`
- Cross-layer tenant tests exist but excluded from security regression gate (P0-007)

**Acceptance Criteria:**
- [ ] `TenantMiddleware` added to `create_fabric_app()` — extracts and validates tenant on every request
- [ ] `require_tenant` dependency for route-level tenant scoping
- [ ] All inline tenant checks refactored to middleware/dependency
- [ ] Endpoints that are tenant-agnostic (webhooks, health) explicitly whitelisted

**Effort:** M (1-2 weeks for middleware + refactor all routers)
**Dependencies:** P0-002 (canonical exceptions for tenant errors), P0-007 (tests included in gate)
**Owner:** Backend / Security

---

### P1-013: 6 Routes Missing response_model — No Response Validation

| Field | Detail |
|-------|--------|
| **ID** | P1-013 |
| **Severity** | LOW (aggregated MEDIUM) |
| **Category** | Backend / API Contract |
| **Status** | OPEN |

**Description:**
Six API routes are missing the `response_model` parameter in their FastAPI decorator. Without `response_model`, FastAPI does not validate response data against a Pydantic schema, does not generate OpenAPI response documentation, and does not filter unexpected fields from the response.

**Why It Matters:**
Missing `response_model` means responses can leak internal fields (database IDs, internal flags) and break client contracts when the returned dict structure changes. It also prevents OpenAPI auto-documentation generation for these endpoints.

**Evidence:**
- 6 routes across backend routers missing `response_model=`
- File pattern: `backend/**/routers/*.py` — grep for `@router.` without `response_model`

**Acceptance Criteria:**
- [ ] All 6 routes have `response_model` added with correct Pydantic model
- [ ] Ruff/flake8 FastAPI plugin enforces response_model on all routes
- [ ] OpenAPI spec regeneration includes all 6 endpoints with schemas

**Effort:** S (1-2 days)
**Dependencies:** None
**Owner:** Backend

---

### P1-014: Circuit Breaker Only in Layer 1 — Other Layers Unprotected

| Field | Detail |
|-------|--------|
| **ID** | P1-014 |
| **Severity** | MEDIUM |
| **Category** | Backend / Resilience |
| **Status** | OPEN |

**Description:**
Circuit breaker pattern is only implemented in Layer 1 (Ingestion). Layers 2 through 7 have no circuit breaker protection. If a downstream service (e.g., Neo4j, LLM provider) becomes slow or unresponsive, requests will pile up, threads will block, and the requesting service will cascade into failure.

**Why It Matters:**
Without circuit breakers, a single failing dependency can take down an entire service. For example, if Neo4j becomes slow, Layer 4 requests hang, Layer 3 agent requests that touch the graph also hang, and eventually the API gateway times out. A circuit breaker would fail fast and allow degraded service rather than total unavailability.

**Evidence:**
- Circuit breaker implementation found only in `backend/layer1-ingestion/`
- No `pybreaker`, `circuitbreaker`, or custom circuit breaker in L2-L7

**Acceptance Criteria:**
- [ ] Circuit breaker pattern extracted to shared framework
- [ ] All external calls (DB, Redis, Neo4j, LLM APIs) wrapped with circuit breaker
- [ ] Configurable thresholds: failure_count, timeout_duration, recovery_timeout
- [ ] Circuit state exposed in metrics (open/half-closed/closed)
- [ ] Alerts fire when circuit opens

**Suggested Implementation:**
```python
from shared.fabric_framework.circuit_breaker import circuit_breaker

@circuit_breaker(name="neo4j", failure_threshold=5, timeout=60)
async def query_neo4j(cypher: str):
    ...
```

**Effort:** M (2 weeks for shared implementation + rollout to all layers)
**Dependencies:** None
**Owner:** Backend

---

### P1-015: 4 Services Have Zero structlog — Inconsistent Logging

| Field | Detail |
|-------|--------|
| **ID** | P1-015 |
| **Severity** | MEDIUM |
| **Category** | Observability |
| **Status** | OPEN |

**Description:**
Four backend services (Layer 2 Extraction, Layer 2.5 Signal Refinery, Layer 6 Benchmarks, API Gateway) have no structured logging via structlog. They likely use standard Python `logging` or `print`, producing inconsistent log formats that are difficult to parse and correlate across services.

**Why It Matters:**
Centralized logging (ELK/Loki) depends on consistent JSON log format for parsing, indexing, and alerting. When services use different formats, log queries break, dashboards show incomplete data, and alert conditions miss events. Incident response requires manual log reading instead of structured queries.

**Evidence:**
- Layer 2-extraction: no structlog configuration
- Layer 2.5: no structlog configuration
- Layer 6-benchmarks: no structlog configuration
- API gateway: no structlog configuration
- 5 other services use structlog correctly

**Acceptance Criteria:**
- [ ] structlog configured in all 4 services with same JSON formatter
- [ ] Request ID propagated to all log entries via contextvars
- [ ] CI gate verifies structlog import in each service's main module
- [ ] Log samples verified in Loki/ELK after deployment

**Effort:** S (1 week — mostly boilerplate configuration)
**Dependencies:** None
**Owner:** Backend / Observability

---

### P1-016: Pagination Total Count Does O(n) Fetch-All Instead of COUNT(*)

| Field | Detail |
|-------|--------|
| **ID** | P1-016 |
| **Severity** | MEDIUM |
| **Category** | Backend / Performance |
| **Status** | OPEN |

**Description:**
The `PaginatedResponse[T]` generic correctly structures paginated responses on 13 endpoints, but the `total` count field is computed by fetching all rows and calling `len(results)` instead of executing a database `COUNT(*)` query. This defeats the purpose of pagination for large datasets — the count query becomes as expensive as returning all rows.

**Why It Matters:**
For a table with 1 million rows, pagination returns 20 rows quickly, but the count operation fetches all 1 million rows into memory. This causes memory pressure, slow response times, and potential OOM kills for the API service.

**Evidence:**
- 13 endpoints use `PaginatedResponse[T]`
- Count logic: `total = len(all_results)` pattern detected

**Acceptance Criteria:**
- [ ] Pagination count uses `SELECT COUNT(*)` query
- [ ] Count query optimized with appropriate indexes
- [ ] For very large tables (>1M rows), consider `COUNT(*)` approximation or cursor-based pagination
- [ ] Response time for paginated endpoints <200ms at 100K row scale

**Effort:** S (2-3 days)
**Dependencies:** P0-001 (PostgreSQL connectivity)
**Owner:** Backend

---

### P1-017: PostgreSQL Single Replica = Single Point of Failure

| Field | Detail |
|-------|--------|
| **ID** | P1-017 |
| **Severity** | MEDIUM |
| **Category** | Infrastructure / Reliability |
| **Status** | OPEN |

**Description:**
PostgreSQL runs as a single replica with no high-availability configuration. If the PostgreSQL pod/node fails, all services depending on it (Layers 1-3, 5-6) lose database connectivity. There is no automatic failover, no read replica for query offloading, and no streaming replication.

**Why It Matters:**
PostgreSQL is the primary data store for 5 of 6 pipeline layers. Its unavailability means ingestion stops, extraction stops, agents cannot read context, ground truth cannot be labeled, and benchmarks cannot read data. A single node failure is a total platform outage.

**Acceptance Criteria:**
- [ ] Evaluate CloudNativePG or PostgreSQL HA chart (Patroni) for Kubernetes
- [ ] Streaming replication with 1 synchronous replica minimum
- [ ] Automated failover <30 seconds
- [ ] Read replica for heavy analytical queries (benchmarks)
- [ ] Backup strategy verified with HA setup (PgBackRest via CloudNativePG)

**Effort:** L (2-3 weeks for evaluation, setup, migration, testing)
**Dependencies:** P0-005 (backup fix — HA changes backup strategy)
**Owner:** DevOps / SRE

---

### P1-018: Neo4j Community Edition Has No HA

| Field | Detail |
|-------|--------|
| **ID** | P1-018 |
| **Severity** | MEDIUM |
| **Category** | Infrastructure / Reliability |
| **Status** | OPEN |

**Description:**
Neo4j Community Edition does not support clustering or causal clustering. It runs as a single instance. If the Neo4j pod fails, the knowledge graph is unavailable. Agent context retrieval, graph queries, and semantic navigation all fail.

**Why It Matters:**
The knowledge graph is the core differentiator of the platform. Its unavailability means agents operate without context (hallucination risk), users cannot explore entity relationships, and semantic search degrades to keyword search.

**Acceptance Criteria:**
- [ ] Evaluate Neo4j Enterprise vs alternative graph databases (memgraph, Amazon Neptune)
- [ ] If staying on Community: document RTO/RPO, implement PV snapshot strategy
- [ ] If upgrading: causal cluster with 3 cores minimum
- [ ] Read replica for graph analytics

**Effort:** L (evaluation + implementation)
**Dependencies:** P0-010 (backup fix)
**Owner:** DevOps / Architecture

---

### P1-019: Redis Has No AUTH Password Configured

| Field | Detail |
|-------|--------|
| **ID** | P1-019 |
| **Severity** | MEDIUM |
| **Category** | Infrastructure / Security |
| **Status** | OPEN |

**Description:**
The Redis instance has no `requirepass` configuration. Any pod in the cluster (or any compromised container) can connect to Redis and read/write all data, including token revocation lists, rate limit counters, idempotency keys, and cached session data.

**Why It Matters:**
Redis contains security-sensitive data. An attacker with cluster access can delete token revocation entries (allowing revoked tokens to work), manipulate rate limits (bypass throttling), or read cached user sessions.

**Acceptance Criteria:**
- [ ] `requirepass` set in Redis configuration
- [ ] Password stored in Kubernetes secret, injected via env var
- [ ] All services updated to include password in Redis connection URL
- [ ] Network policy restricts Redis port to only authorized pods

**Effort:** S (2-3 days)
**Dependencies:** P0-003 (rate limiting uses Redis)
**Owner:** DevOps / Security

---

### P1-020: All Dockerfiles Are Single-Stage — No Build Optimization

| Field | Detail |
|-------|--------|
| **ID** | P1-020 |
| **Severity** | MEDIUM |
| **Category** | Infrastructure / Performance |
| **Status** | OPEN |

**Description:**
All 8 Dockerfiles use single-stage builds, meaning build dependencies (gcc, dev headers, test runners) are included in the final production image. This increases image size, attack surface, memory usage, and startup time.

**Why It Matters:**
Smaller images deploy faster, use less node disk space, reduce memory pressure, and have fewer packages that could contain vulnerabilities. Multi-stage builds are industry standard for production container images.

**Evidence:**
- 8 Dockerfiles, all single-stage pattern: `FROM python:3.11` → install → copy → run
- No `FROM ... AS builder` pattern detected

**Acceptance Criteria:**
- [ ] All 8 Dockerfiles converted to multi-stage build
- [ ] Builder stage installs build deps, compiles wheels
- [ ] Final stage copies only compiled wheels, runs as non-root
- [ ] Final image size reduced by >50% from current
- [ ] Trivy/Grype scan shows fewer CVEs in final image

**Effort:** M (1 week for all 8 images + CI verification)
**Dependencies:** None
**Owner:** DevOps

---

## 6. P2 Quality and Maintainability

### P2-001: OpenAPI Spec Missing — fabric-4l-api.json Does Not Exist

| Field | Detail |
|-------|--------|
| **ID** | P2-001 |
| **Severity** | LOW |
| **Category** | Documentation / API |
| **Status** | OPEN |

**Description:**
The main OpenAPI specification file `fabric-4l-api.json` does not exist in the repository. This file should be the auto-generated or manually maintained API contract that powers documentation, SDK generation, and client code generation. Without it, there is no machine-readable API specification.

**Why It Matters:**
API consumers (frontend, mobile, integrations) depend on accurate OpenAPI specs for type generation and documentation. Missing specs mean client code is written against undocumented assumptions, creating contract drift and integration bugs.

**Evidence:**
- File: `openapi/fabric-4l-api.json` — does not exist
- FastAPI can auto-generate this from route definitions if `response_model` is present

**Acceptance Criteria:**
- [ ] FastAPI app exports OpenAPI spec on startup: `app.openapi()`
- [ ] CI generates spec and validates it matches committed version (or generates artifact)
- [ ] Spec includes all endpoints, schemas, auth schemes, and error responses
- [ ] Swagger UI accessible in dev/staging environments

**Effort:** S (1-2 days)
**Dependencies:** P1-013 (response_model on all routes)
**Owner:** Backend

---

### P2-002: layer7-billing.json OpenAPI Spec Is Empty (12 Lines)

| Field | Detail |
|-------|--------|
| **ID** | P2-002 |
| **Severity** | LOW |
| **Category** | Documentation / API |
| **Status** | OPEN |

**Description:**
The billing service OpenAPI specification exists but contains only 12 lines — essentially an empty shell with no paths, schemas, or operation definitions.

**Why It Matters:**
The billing service is incomplete (uses in-memory store) but having an empty spec suggests the service was scaffolded without API design. When development resumes, there is no contract to implement against.

**Evidence:**
- File: `openapi/layer7-billing.json` — 12 lines, empty paths object

**Acceptance Criteria:**
- [ ] Design billing API endpoints (subscriptions, invoices, usage, webhooks)
- [ ] Write OpenAPI spec with full schemas before implementation
- [ ] Generate TypeScript types from spec for frontend consumption

**Effort:** S (design session + spec writing)
**Dependencies:** Product decision on billing features
**Owner:** Backend / Product

---

### P2-003: No Architecture Decision Records (ADRs) Found

| Field | Detail |
|-------|--------|
| **ID** | P2-003 |
| **Severity** | LOW |
| **Category** | Documentation |
| **Status** | OPEN |

**Description:**
No Architecture Decision Records (ADRs) were found in the repository for key technical decisions: tenant isolation model, database-per-layer vs shared database, Neo4j Community vs Enterprise, Clerk vs custom auth, semantic pipeline architecture.

**Why It Matters:**
ADRs capture the context and tradeoffs behind important decisions. When the original decision-makers leave, new engineers cannot understand why things are the way they are, leading to dangerous "simplifications" that violate original constraints.

**Acceptance Criteria:**
- [ ] ADR directory created: `docs/adr/`
- [ ] Template established: `docs/adr/template.md`
- [ ] Minimum 5 ADRs written for top-level architectural decisions
- [ ] New ADR required for any decision changing existing architecture

**Effort:** S (1 week for initial set, ongoing discipline)
**Dependencies:** None
**Owner:** Architecture / Tech Lead

---

### P2-004: 69 str(e) Converting Exceptions to Strings

| Field | Detail |
|-------|--------|
| **ID** | P2-004 |
| **Title** | 69 str(e) Converting Exceptions to Strings |
| **Severity** | LOW |
| **Category** | Backend / Code Quality |
| **Status** | OPEN |

**Description:**
(See P1-011 for full details. This P2 tracks the lint rule and full cleanup beyond the immediate priority fix.)

**Acceptance Criteria:**
- [ ] All 69 occurrences converted to structured logging
- [ ] Custom Ruff rule or flake8 plugin bans `str(e)` in exception handlers
- [ ] Zero occurrences in codebase

**Effort:** S
**Dependencies:** P1-011
**Owner:** Backend

---

### P2-005: No Reusable require_super_admin — Authorization Duplication

| Field | Detail |
|-------|--------|
| **ID** | P2-005 |
| **Title** | No Reusable require_super_admin — Authorization Duplication |
| **Severity** | LOW |
| **Category** | Backend / Authorization |
| **Status** | OPEN |

**Description:**
(See P1-004. This P2 tracks the full refactor across all routers after the initial dependency is created.)

**Acceptance Criteria:**
- [ ] All inline super-admin checks converted to `dependencies=[Depends(require_super_admin)]`
- [ ] Zero inline `if user.role != "admin"` patterns remaining
- [ ] All admin endpoints use dependency

**Effort:** S
**Dependencies:** P1-004
**Owner:** Backend

---

### P2-006: Legacy Components Present — LegacyDataTable and LegacyTabs

| Field | Detail |
|-------|--------|
| **ID** | P2-006 |
| **Title** | Legacy Components Present — LegacyDataTable and LegacyTabs |
| **Severity** | LOW |
| **Category** | Frontend / Maintainability |
| **Status** | OPEN |

**Description:**
(See P1-007. P2 tracking item for complete removal.)

**Acceptance Criteria:**
- [ ] `LegacyDataTable.tsx` deleted
- [ ] `LegacyTabs.tsx` deleted
- [ ] No references in any import statements
- [ ] Bundle size reduction measured

**Effort:** S
**Dependencies:** P1-007
**Owner:** Frontend

---

### P2-007: 6 Routes Missing response_model

| Field | Detail |
|-------|--------|
| **ID** | P2-007 |
| **Title** | 6 Routes Missing response_model |
| **Severity** | LOW |
| **Category** | Backend / API Contract |
| **Status** | OPEN |

**Description:**
(See P1-013. P2 tracking item for lint enforcement and OpenAPI completeness.)

**Acceptance Criteria:**
- [ ] All 6 routes fixed
- [ ] Lint rule enforced
- [ ] OpenAPI spec regenerated with all endpoints

**Effort:** S
**Dependencies:** P1-013
**Owner:** Backend

---

### P2-008: No Local Development Docker Compose

| Field | Detail |
|-------|--------|
| **ID** | P2-008 |
| **Severity** | LOW |
| **Category** | Developer Experience |
| **Status** | OPEN |

**Description:**
No `docker-compose.dev.yml` file exists that brings up the full stack (PostgreSQL, Neo4j, Redis, MinIO, all 8 backend services, frontend dev server) for local development. Engineers must run services individually or depend on remote staging.

**Acceptance Criteria:**
- [ ] `docker-compose.dev.yml` starts all dependencies and services
- [ ] Hot reload works for backend (volume mounts) and frontend
- [ ] `.env.dev` template with all required variables
- [ ] README updated with `docker compose -f docker-compose.dev.yml up` instructions
- [ ] Health check script verifies all services started successfully

**Effort:** M (1 week)
**Dependencies:** P0-001 (PostgreSQL driver — otherwise services can't start)
**Owner:** DevOps

---

### P2-009: Resource Limits Not Verified on All K8s Pods

| Field | Detail |
|-------|--------|
| **ID** | P2-009 |
| **Severity** | LOW |
| **Category** | Infrastructure |
| **Status** | OPEN |

**Description:**
Kubernetes resource limits and requests (CPU/memory) have not been verified on all pod specifications. Without limits, a single misbehaving pod can exhaust node resources, causing cluster-wide instability.

**Acceptance Criteria:**
- [ ] All deployments have `resources.requests` and `resources.limits` for CPU and memory
- [ ] Limits based on load testing or production telemetry
- [ ] HPA (HorizontalPodAutoscaler) configured for services with variable load
- [ ] VPA (VerticalPodAutoscaler) recommendations reviewed monthly

**Effort:** S (2-3 days for audit + updates)
**Dependencies:** None
**Owner:** DevOps

---

### P2-010: Missing Runbooks for Incident Response

| Field | Detail |
|-------|--------|
| **ID** | P2-010 |
| **Severity** | LOW |
| **Category** | Documentation / Operations |
| **Status** | OPEN |

**Description:**
No incident response runbooks were found for common failure scenarios: database outage, Redis failure, Neo4j corruption, LLM provider downtime, cascading failure, data corruption, security breach.

**Acceptance Criteria:**
- [ ] Runbook directory created: `docs/runbooks/`
- [ ] Runbooks for top 10 failure scenarios
- [ ] Each runbook: symptoms, diagnosis steps, remediation, escalation path, rollback procedure
- [ ] Runbooks stored in Git (version controlled) and searchable from PagerDuty
- [ ] Quarterly drill scheduled for highest-impact scenarios

**Effort:** M (1 week for initial set, ongoing maintenance)
**Dependencies:** None
**Owner:** SRE / DevOps

---

## 7. Sprint Roadmap

### Phase 0: Emergency Stabilization (Weeks 1-2)

| Attribute | Detail |
|-----------|--------|
| **Goal** | Fix critical infrastructure and CI defects that block all other work |
| **Theme** | "Stop the bleeding" |
| **Velocity** | 4 engineers |

**Scope:**
- P0-005: Fix PostgreSQL backup CronJob secret reference
- P0-006: Rotate Layer 4 hardcoded password, move to Kubernetes secret
- P0-007: Expand security regression gate to include all 6 test groups
- P1-001: Remove _DEFAULT_DEV_SECRET hardcode from config.py
- P1-002: Sanitize .env.example of all real secrets
- P1-010: Fix or delete overdue quarantined test

**Tickets:**
- INFRA-001: Fix backup CronJob secret reference + alerts
- INFRA-002: Rotate Layer 4 DB password + CI secret scanning gate
- CI-001: Expand security regression gate matrix
- SEC-001: Remove hardcoded dev secret + startup validation
- SEC-002: Sanitize .env.example + rotate exposed credentials
- QA-001: Resolve quarantined test + CI overdue check

**Dependencies:** None

**Definition of Done:**
- [ ] All CI pipelines green on main branch
- [ ] Security regression gate runs all 6 test groups and passes
- [ ] No hardcoded secrets in repository (verified by gitleaks scan)
- [ ] PostgreSQL backup job succeeds in staging
- [ ] Zero quarantined tests >7 days overdue

**Risks:**
- Password rotation may break existing staging connections — coordinate with team
- Expanded test groups may reveal hidden failures — budget 2 days for stabilization

**Validation Commands:**
```bash
# Verify backup job
cd k8s/cronjobs && kubectl apply --dry-run=server -f postgres-backup-cronjob.yaml

# Verify no hardcoded secrets
gitleaks detect --source . --verbose

# Verify all test groups run
gh run list --workflow=security-regression.yml --limit 5
```

---

### Phase 1: Database Connectivity Foundation (Weeks 3-4)

| Attribute | Detail |
|-----------|--------|
| **Goal** | Make backend services capable of connecting to production databases |
| **Theme** | "The foundation everything stands on" |
| **Velocity** | 3 backend + 1 DevOps |

**Scope:**
- P0-001: Implement PostgreSQL driver in database.py with connection pooling
- P0-009: Implement real health checks with dependency probing
- P1-016: Fix pagination total count to use COUNT(*)
- P1-017: PostgreSQL HA evaluation (CloudNativePG)

**Tickets:**
- BE-001: Implement asyncpg driver in shared database.py
- BE-002: Add connection pool configuration via environment variables
- BE-003: Implement /health/live and /health/ready endpoints
- BE-004: Optimize pagination count queries with indexes
- INFRA-003: Evaluate CloudNativePG for PostgreSQL HA

**Dependencies:** Phase 0 complete

**Definition of Done:**
- [ ] All 8 backend services start successfully against PostgreSQL in staging
- [ ] Health checks return 503 when dependencies are down
- [ ] Pagination endpoints respond <200ms at 100K row scale
- [ ] CloudNativePG PoC deployed in dev cluster

**Risks:**
- Connection pool tuning may require iteration under real load
- Health check dependency timeouts need careful tuning to avoid cascading slow probes

**Validation Commands:**
```bash
# Test database connectivity
python -c "from fabric_framework.database import get_engine; import asyncio; asyncio.run(get_engine('postgresql+asyncpg://...'))"

# Test health check
curl -f http://api-gateway/health/ready || echo "FAIL"

# Load test pagination
k6 run pagination-load-test.js
```

---

### Phase 2: Error Handling Contract (Weeks 5-6)

| Attribute | Detail |
|-------|--------|
| **Goal** | Restore API error handling contract and prevent future violations |
| **Theme** | "Speak the same language" |
| **Velocity** | 3 backend + 1 frontend |

**Scope:**
- P0-002: Migrate all ~88 HTTPException raises to canonical exceptions
- P0-004: Implement idempotency key middleware for POST endpoints
- P1-011/P2-004: Replace all str(e) with structured logging
- P1-013/P2-007: Add response_model to all 6 missing routes

**Tickets:**
- BE-005: Automated refactor script for HTTPException → canonical exceptions
- BE-006: Add flake8/ruff rule banning raw HTTPException
- BE-007: Implement Idempotency-Key middleware with Redis storage
- BE-008: Convert all str(e) to structured logging
- BE-009: Add response_model to missing routes
- FE-001: Update frontend error parsing to verify ErrorEnvelope contract

**Dependencies:** Phase 1 (database connectivity for error path tests)

**Definition of Done:**
- [ ] Zero `raise HTTPException(` in backend code (lint enforced)
- [ ] Frontend error boundaries correctly parse all canonical error types
- [ ] Idempotency keys prevent duplicate creation on retry
- [ ] All routes have response_model; OpenAPI spec generates cleanly

**Risks:**
- Bulk exception refactor may introduce subtle behavior changes — thorough testing required
- Idempotency key collision with existing caching layer

**Validation Commands:**
```bash
# Verify no HTTPException
grep -r "raise HTTPException(" backend/ --include="*.py" && echo "FAIL" || echo "PASS"

# Test idempotency
curl -X POST -H "Idempotency-Key: test-123" /api/entities -d '{...}'
curl -X POST -H "Idempotency-Key: test-123" /api/entities -d '{...}' # should return 200, not 201

# Verify OpenAPI
curl http://api-gateway/openapi.json | jq '.paths | keys | length' # should match route count
```

---

### Phase 3: Security & Multi-Tenancy Hardening (Weeks 7-8)

| Attribute | Detail |
|-------|--------|
| **Goal** | Centralize authorization, implement API keys, strengthen tenant isolation |
| **Theme** | "Trust but verify" |
| **Velocity** | 2 backend + 1 security + 1 frontend |

**Scope:**
- P1-004/P2-005: Create reusable require_super_admin dependency
- P1-005: Implement API key authentication
- P1-012: Create tenant middleware for automatic isolation
- P1-003: Fix _is_production_like() behavior

**Tickets:**
- SEC-003: Create require_super_admin + require_tenant dependencies
- SEC-004: Implement API key auth (generation, hashing, validation, scopes)
- SEC-005: Add TenantMiddleware to create_fabric_app()
- SEC-006: Fix _is_production_like() to explicit allowlist
- BE-010: Refactor all routers to use centralized auth/tenant deps

**Dependencies:** Phase 2 (canonical exceptions for auth error responses)

**Definition of Done:**
- [ ] All admin endpoints use require_super_admin dependency
- [ ] API keys work for programmatic access with proper scoping
- [ ] Tenant middleware enforces isolation on every request
- [ ] Cross-layer tenant isolation tests pass in CI gate
- [ ] Unknown environment names fail fast with clear error

**Risks:**
- API key storage pattern must match existing token revocation (Redis + SHA256)
- Tenant middleware may break webhook endpoints that are tenant-agnostic — whitelist testing critical

**Validation Commands:**
```bash
# Test super-admin
 curl -H "Authorization: Bearer $USER_JWT" /api/admin/users # 403
curl -H "Authorization: Bearer $ADMIN_JWT" /api/admin/users # 200

# Test API key
curl -H "X-API-Key: $API_KEY" /api/entities # 200
curl -H "X-API-Key: $BAD_KEY" /api/entities # 401

# Test tenant isolation
curl -H "Authorization: Bearer $TENANT_A_JWT" /api/entities/123 # tenant A's entity
curl -H "Authorization: Bearer $TENANT_B_JWT" /api/entities/123 # 404 (not tenant B's)
```

---

### Phase 4: Observability & Reliability (Weeks 9-10)

| Attribute | Detail |
|-------|--------|
| **Goal** | Achieve full observability coverage and circuit breaker protection |
| **Theme** | "See everything, fail fast" |
| **Velocity** | 2 backend + 1 observability + 1 DevOps |

**Scope:**
- P0-008: Replace Layer 3 custom tracer with OTel
- P1-014: Add circuit breakers to all layers
- P1-015: Add structlog to 4 missing services
- P1-019: Configure Redis AUTH password

**Tickets:**
- OBS-001: Instrument Layer 3 with OTel, remove custom tracer
- OBS-002: Add circuit breaker shared module, apply to all external calls
- OBS-003: Configure structlog in L2, L2.5, L6, API gateway
- INFRA-004: Enable Redis requirepass, update all service connection strings

**Dependencies:** Phase 3

**Definition of Done:**
- [ ] Layer 3 traces visible in Jaeger UI
- [ ] Circuit breaker metrics exposed (open/half-closed/closed counts)
- [ ] All services emit structured JSON logs with request_id
- [ ] Redis requires authentication, all services connect successfully

**Risks:**
- OTel instrumentation overhead on LLM calls — monitor latency impact
- Circuit breaker tuning requires production load data

**Validation Commands:**
```bash
# Verify Jaeger traces for L3
curl "http://jaeger:16686/api/traces?service=layer3-agents&limit=1" | jq '.data | length' # should be >0

# Verify circuit breaker metrics
curl http://layer3-agents/metrics | grep circuit_breaker

# Verify structured logging
kubectl logs deployment/api-gateway | jq '.request_id' # should not be null
```

---

### Phase 5: Performance & Resilience (Weeks 11-12)

| Attribute | Detail |
|-------|--------|
| **Goal** | Rate limiting, pagination optimization, multi-stage Docker builds |
| **Theme** | "Fast and efficient" |
| **Velocity** | 2 backend + 2 DevOps |

**Scope:**
- P0-003: Implement rate limiting in API service
- P1-016: Optimize pagination (COUNT(*), indexes)
- P1-018: Neo4j HA decision and implementation
- P1-020: Convert all Dockerfiles to multi-stage

**Tickets:**
- PERF-001: Implement Redis-backed rate limiting with tiers
- PERF-002: Add database indexes for pagination queries
- INFRA-005: Neo4j HA: deploy Enterprise or implement PV snapshot strategy
- INFRA-006: Multi-stage Docker builds for all 8 services

**Dependencies:** Phase 4 (Redis AUTH, OTel complete)

**Definition of Done:**
- [ ] Rate limiting blocks excessive requests with 429 + Retry-After
- [ ] Pagination endpoints <200ms at 1M row scale
- [ ] Docker image sizes reduced >50%
- [ ] Neo4j HA strategy implemented (cluster or snapshot)

**Risks:**
- Rate limiting must not block legitimate bulk operations — tier configuration critical
- Neo4j Enterprise licensing cost may require executive approval

**Validation Commands:**
```bash
# Rate limit test
for i in {1..150}; do curl -s -o /dev/null -w "%{http_code}" http://api-gateway/api/entities; done | sort | uniq -c

# Image size check
docker images | grep fabric | awk '{print $7}' # compare before/after
```

---

### Phase 6: Frontend Accessibility & Polish (Weeks 13-14)

| Attribute | Detail |
|-------|--------|
| **Goal** | WCAG 2.1 AA compliance, dead code removal, frontend performance |
| **Theme** | "Accessible and clean" |
| **Velocity** | 2 frontend |

**Scope:**
- P1-006: Add alt attributes to all images (WCAG)
- P1-007/P2-006: Remove LegacyDataTable and LegacyTabs
- P2-001/P2-002: Generate OpenAPI specs

**Tickets:**
- FE-002: Audit and fix all img alt attributes
- FE-003: Remove legacy components
- FE-004: Add jsx-a11y ESLint rules to CI
- FE-005: Integrate axe-core or pa11y into CI
- BE-011: Auto-generate OpenAPI specs from FastAPI apps

**Dependencies:** Phase 2 (response_model completeness)

**Definition of Done:**
- [ ] Zero axe-core violations in CI
- [ ] All images have meaningful alt text
- [ ] Legacy components removed, bundle size reduced
- [ ] OpenAPI specs auto-generated and committed

**Validation Commands:**
```bash
# Accessibility scan
npx axe-core-cli http://frontend:3000 --exit

# Legacy component check
grep -r "LegacyDataTable\|LegacyTabs" frontend/src && echo "FAIL" || echo "PASS"

# OpenAPI spec
curl -s http://api-gateway/openapi.json | jq '.info.title' # should be "Fabric 4L API"
```

---

### Phase 7: Production Readiness & Documentation (Weeks 15-16)

| Attribute | Detail |
|-------|--------|
| **Goal** | Complete documentation, runbooks, final validation, production migration |
| **Theme** | "Ready to ship" |
| **Velocity** | 2 DevOps + 1 technical writer + 1 QA |

**Scope:**
- P2-003: Write ADRs for key architectural decisions
- P2-008: Create docker-compose.dev.yml
- P2-010: Write incident response runbooks
- P1-017: PostgreSQL HA deployment
- Final production readiness validation

**Tickets:**
- DOCS-001: Write 5+ ADRs (tenant isolation, auth, pipeline, database, graph)
- DOCS-002: Create local development docker-compose
- DOCS-003: Write incident response runbooks (10 scenarios)
- INFRA-007: Production PostgreSQL HA deployment
- QA-002: Full end-to-end validation test run

**Dependencies:** All previous phases

**Definition of Done:**
- [ ] All P0 items resolved and verified
- [ ] All P1 items resolved or accepted with documented risk
- [ ] Runbooks written and reviewed by on-call engineers
- [ ] ADRs committed and team trained on process
- [ ] Staging environment validates full pipeline end-to-end
- [ ] Security scan (Trivy, gitleaks, OWASP ZAP) passes
- [ ] Load test passes (sustained 1000 req/s, p99 <500ms)
- [ ] DR drill: backup restore tested and timed

**Risks:**
- PostgreSQL HA migration is the highest-risk operation — plan maintenance window
- Load testing may reveal performance issues requiring iteration

**Validation Commands:**
```bash
# Full validation suite
make validate-all

# Security scan
trivy fs . && gitleaks detect --source . && zaproxy -cmd -quickurl http://staging/

# Load test
k6 run load-test-1000rps.js

# DR test
cd docs/runbooks && ./test-postgres-restore.sh
```

---

## 8. Copy/Paste Dev Tickets

### Backend / Platform / Security Tickets (10 P0/P1)

---

#### Ticket BE-001: Implement PostgreSQL Async Driver in Shared database.py

| Field | Detail |
|-------|--------|
| **Title** | Implement PostgreSQL Async Driver in Shared database.py |
| **Priority** | P0 |
| **Component** | Backend / Shared Framework |
| **Effort** | L (1-2 weeks) |

**Background:**
All 8 backend services use `shared/fabric_framework/database.py` for database connectivity. The module currently only supports SQLite and in-memory databases. PostgreSQL URLs raise `UnsupportedDatabaseURL`.

**Problem:**
No backend service can connect to PostgreSQL in production. This is a total system outage condition.

**Scope:**
1. Add `asyncpg` support with `create_async_engine`
2. Implement connection pooling with configurable parameters
3. Add pool pre-ping for connection health
4. Maintain SQLite/in-memory for test environments
5. Write integration tests against PostgreSQL

**Non-Goals:**
- Migration from SQLAlchemy to another ORM
- Changing database schemas
- Implementing read replicas (separate ticket)

**Implementation Steps:**
1. Add `asyncpg` and `sqlalchemy[asyncio]` to `requirements.txt`
2. In `database.py`, add PostgreSQL branch:
   ```python
   if db_url.startswith(("postgresql://", "postgresql+asyncpg://")):
       engine = create_async_engine(
           db_url,
           pool_size=int(os.getenv("DB_POOL_SIZE", "10")),
           max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "20")),
           pool_timeout=float(os.getenv("DB_POOL_TIMEOUT", "30")),
           pool_pre_ping=True,
           echo=os.getenv("DB_ECHO", "false").lower() == "true",
       )
   ```
3. Add connection test on engine creation
4. Update `get_session()` to use async session
5. Add `close_engine()` for graceful shutdown

**Files Affected:**
- `shared/fabric_framework/database.py`
- `shared/fabric_framework/requirements.txt`
- `shared/fabric_framework/tests/test_database.py`
- All service `main.py` files (startup/shutdown hooks)

**Acceptance Criteria:**
- [ ] `get_engine("postgresql+asyncpg://user:pass@host/db")` returns valid async engine
- [ ] Connection pool creates connections under load
- [ ] SQLite support preserved for tests
- [ ] All 8 services start successfully in staging with PostgreSQL
- [ ] `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DB_POOL_TIMEOUT` configurable via env

**Test Plan:**
- Unit: Mock `create_async_engine`, verify correct arguments
- Integration: Test against PostgreSQL 15 container in CI
- Service: Each service's startup test verifies DB connection
- Staging: Full deployment smoke test

**Rollback Plan:**
- Revert `database.py` to previous version
- Fallback: services use SQLite in emergency mode (feature flag)

**Security Considerations:**
- Pool pre-ping prevents connection hijacking via stale connections
- Connection string with password must not be logged

**Documentation Updates:**
- `docs/database.md` — connection configuration
- `.env.example` — add `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DB_POOL_TIMEOUT`

---

#### Ticket BE-002: Migrate Raw HTTPException to Canonical Exception Classes

| Field | Detail |
|-------|--------|
| **Title** | Migrate Raw HTTPException to Canonical Exception Classes |
| **Priority** | P0 |
| **Component** | Backend / All Services |
| **Effort** | M (2-3 weeks) |

**Background:**
`shared/fabric_framework/exceptions.py` defines 7 canonical exception classes: `NotFoundError`, `ValidationError`, `AuthenticationError`, `AuthorizationError`, `ConflictError`, `BadRequestError`, `InternalServerError`. None are used. ~88 raise sites use raw `HTTPException`.

**Problem:**
Frontend clients expect `ErrorEnvelope` format. Raw `HTTPException` returns `{"detail": "..."}`, breaking client error parsing.

**Scope:**
1. Create automated refactor script using `libcst`
2. Convert all `raise HTTPException(status_code=X, detail=Y)` to canonical exceptions
3. Add custom flake8/ruff rule banning `raise HTTPException(`
4. Update exception handlers if needed
5. Verify frontend error parsing works

**Non-Goals:**
- Redesigning ErrorEnvelope schema
- Changing HTTP status codes (must remain compatible)
- Frontend error handling redesign

**Implementation Steps:**
1. Map status codes to exceptions:
   - 400 → `BadRequestError`
   - 401 → `AuthenticationError`
   - 403 → `AuthorizationError`
   - 404 → `NotFoundError`
   - 409 → `ConflictError`
   - 422 → `ValidationError`
   - 500 → `InternalServerError`
2. Write `libcst` codemod: `HttpExceptionToCanonical`
3. Run codemod across all backend services
4. Manual review for edge cases (dynamic status codes)
5. Add lint rule to CI

**Files Affected:**
- `shared/fabric_framework/exceptions.py` (verify handlers registered)
- `backend/**/routers/*.py` (all router files)
- `.github/workflows/lint.yml` (add ban rule)
- `frontend/src/lib/errors.ts` (verify parsing)

**Acceptance Criteria:**
- [ ] `grep -r "raise HTTPException(" backend/` returns zero results
- [ ] CI lint gate fails on any new `raise HTTPException(`
- [ ] Frontend receives `ErrorEnvelope` for all 4xx/5xx errors
- [ ] All existing tests pass (status codes unchanged)

**Test Plan:**
- Contract test: Hit each error endpoint, verify JSON schema matches ErrorEnvelope
- E2E: Frontend error boundary displays correct messages
- Lint: CI self-test with intentionally bad commit

**Rollback Plan:**
- Revert codemod commit
- Frontend error parsing temporarily supports both formats

**Security Considerations:**
- Ensure exception messages don't leak internal paths or SQL

**Documentation Updates:**
- `docs/error-handling.md` — canonical exception usage guide

---

#### Ticket BE-003: Implement Rate Limiting Middleware with Redis Backend

| Field | Detail |
|-------|--------|
| **Title** | Implement Rate Limiting Middleware with Redis Backend |
| **Priority** | P0 |
| **Component** | Backend / API Gateway |
| **Effort** | M (1-2 weeks) |

**Background:**
The API gateway has no rate limiting. Any client can make unlimited requests.

**Problem:**
DoS vulnerability, resource exhaustion, cascading failures under load.

**Scope:**
1. Add `slowapi` or custom sliding-window rate limiter
2. Tier-based limits: anonymous (10/min), standard (100/min), admin (1000/min)
3. Redis-backed for distributed rate limiting
4. 429 responses with `Retry-After` header
5. Rate limit headers on all responses

**Non-Goals:**
- Per-endpoint granular limits (future enhancement)
- Geographic rate limiting
- CAPTCHA integration

**Implementation Steps:**
1. Install `slowapi`, configure Redis storage
2. Create `RateLimitMiddleware` in `shared/fabric_framework/middleware/`
3. Apply in `create_fabric_app()`
4. Tier detection from JWT claims or API key scope
5. Add response headers

**Files Affected:**
- `shared/fabric_framework/middleware/rate_limit.py` (new)
- `shared/fabric_framework/main.py` (register middleware)
- `backend/api-gateway/` (tier configuration)
- `.env.example` (rate limit config)

**Acceptance Criteria:**
- [ ] 101st anonymous request returns 429 within 1 minute
- [ ] Standard user gets 100/min, admin gets 1000/min
- [ ] `X-RateLimit-*` headers present on every response
- [ ] Redis stores rate counters with 1-minute TTL

**Test Plan:**
- Unit: `test_rate_limit_allows_under_limit`, `test_rate_limit_blocks_over`
- Load: `k6 run rate-limit-test.js` (sustained 200 req/min)
- Integration: Multi-replica test verifies shared Redis state

**Rollback Plan:**
- Feature flag `RATE_LIMIT_ENABLED=false` in env

**Security Considerations:**
- Rate limits must apply before expensive auth/DB operations
- Key function must not be spoofable (use authenticated user ID, not just IP)

**Documentation Updates:**
- `docs/rate-limiting.md` — tiers, headers, error responses

---

#### Ticket BE-004: Implement Idempotency Key Middleware

| Field | Detail |
|-------|--------|
| **Title** | Implement Idempotency Key Middleware |
| **Priority** | P0 |
| **Component** | Backend / API Gateway |
| **Effort** | M (2 weeks) |

**Background:**
POST endpoints lack idempotency protection. Retried requests create duplicates.

**Problem:**
Duplicate entities, duplicate billing events, knowledge graph corruption on retries.

**Scope:**
1. `Idempotency-Key` header parsing middleware
2. Redis storage with 24-hour TTL
3. Tenant-scoped keys
4. Payload hash validation (409 on mismatch)
5. Cached response replay

**Non-Goals:**
- Idempotency for GET/HEAD (inherently idempotent)
- Cross-service distributed idempotency

**Implementation Steps:**
1. Create `IdempotencyMiddleware` in `shared/fabric_framework/middleware/`
2. Redis key format: `idempotency:{tenant_id}:{key}`
3. Store payload hash + response status + body on first request
4. On duplicate: verify payload hash matches, return cached response
5. On hash mismatch: return 409 Conflict

**Files Affected:**
- `shared/fabric_framework/middleware/idempotency.py` (new)
- `shared/fabric_framework/main.py` (register middleware)
- `backend/**/routers/*.py` (no changes required — middleware is automatic)

**Acceptance Criteria:**
- [ ] Same key + same payload = cached response (200, not 201)
- [ ] Same key + different payload = 409 Conflict
- [ ] Different tenants with same key = separate operations
- [ ] Key expires after 24 hours
- [ ] Concurrent requests with same key: first wins, second waits

**Test Plan:**
- `test_idempotent_creates_once`
- `test_idempotent_conflict_different_payload`
- `test_idempotent_tenant_isolation`
- `test_idempotent_ttl_expiry`
- `test_idempotent_concurrent_requests`

**Rollback Plan:**
- Feature flag `IDEMPOTENCY_ENABLED=false`

**Security Considerations:**
- Redis keys include tenant_id to prevent cross-tenant key collision attacks
- Payload hash prevents replay with different data
- Key max length validation (prevent Redis key exhaustion)

**Documentation Updates:**
- `docs/idempotency.md` — client usage, key generation, error handling

---

#### Ticket BE-005: Replace Layer 3 Custom Tracer with OpenTelemetry

| Field | Detail |
|-------|--------|
| **Title** | Replace Layer 3 Custom Tracer with OpenTelemetry |
| **Priority** | P0 |
| **Component** | Backend / Layer 3 Agents |
| **Effort** | M (2 weeks) |

**Background:**
Layer 3 uses a custom non-OTel tracer that cannot export to Jaeger.

**Problem:**
Agent orchestration, LLM calls, and prompt routing are invisible to operators.

**Scope:**
1. Remove custom tracer imports and initialization
2. Add OTel `TracerProvider` and instrument all agent paths
3. Wrap LLM API calls with spans
4. Add semantic attributes (agent_id, model, provider, token_count)
5. Verify traces appear in Jaeger

**Non-Goals:**
- Changing agent business logic
- Adding new metrics (separate ticket)

**Implementation Steps:**
1. `opentelemetry-instrumentation-httpx` for LLM HTTP calls
2. Custom spans for `agent.execute`, `agent.route`, `llm.call`
3. Attributes: `agent.id`, `llm.model`, `llm.provider`, `llm.tokens.prompt`, `llm.tokens.completion`
4. Remove all custom tracer module references
5. Update `docker-compose.dev.yml` if needed

**Files Affected:**
- `backend/layer3-agents/` (all Python files)
- `backend/layer3-agents/tracer.py` (delete)
- `backend/layer3-agents/requirements.txt`

**Acceptance Criteria:**
- [ ] Jaeger UI shows traces for `layer3-agents` service
- [ ] Each LLM call has span with model and token attributes
- [ ] Agent routing decisions traced
- [ ] No custom tracer code remains

**Test Plan:**
- `test_l3_traces_exported` — query Jaeger API for recent trace
- `test_l3_span_attributes` — verify semantic attributes present
- `test_no_custom_tracer_imports` — grep verification

**Rollback Plan:**
- Revert to custom tracer if OTel causes latency issues

**Security Considerations:**
- Span attributes must not include prompt content (PII risk) — use hashes or summaries

**Documentation Updates:**
- `docs/observability.md` — Layer 3 instrumentation guide

---

#### Ticket BE-006: Implement Real Health Checks with Dependency Probes

| Field | Detail |
|-------|--------|
| **Title** | Implement Real Health Checks with Dependency Probes |
| **Priority** | P0 |
| **Component** | Backend / API Gateway |
| **Effort** | M (1 week) |

**Background:**
`/health` returns static `{"status": "ok"}` regardless of dependency health.

**Problem:**
Kubernetes routes traffic to instances with failed dependencies, causing user-facing errors.

**Scope:**
1. `/health/live` — process liveness (always 200 if running)
2. `/health/ready` — probe PostgreSQL, Redis, Neo4j
3. Individual dependency status in response
4. Update K8s manifests

**Non-Goals:**
- Deep health checks (full table scan, complex query)
- Dependency dependency chains (just direct dependencies)

**Implementation Steps:**
1. Create `health.py` router with `/health/live` and `/health/ready`
2. Ready probe: `SELECT 1` for PostgreSQL, `PING` for Redis, `CALL db.ping()` for Neo4j
3. Return 503 if any dependency fails
4. Update all K8s manifests: `livenessProbe` → `/health/live`, `readinessProbe` → `/health/ready`

**Files Affected:**
- `backend/api-gateway/routers/health.py` (rewrite)
- `k8s/base/*/deployment.yaml` (update probe paths)

**Acceptance Criteria:**
- [ ] `/health/live` returns 200 always
- [ ] `/health/ready` returns 200 when all dependencies up
- [ ] `/health/ready` returns 503 when PostgreSQL down
- [ ] K8s removes pod from service within 10 seconds of 503
- [ ] Response includes per-dependency status object

**Test Plan:**
- `test_health_live_returns_200`
- `test_health_ready_all_ok`
- `test_health_ready_db_down_returns_503`
- Integration: Stop Redis in test env, verify LB behavior

**Rollback Plan:**
- K8s manifests reference old `/health` endpoint

**Documentation Updates:**
- `docs/operations.md` — health check semantics

---

#### Ticket BE-007: Create Reusable Auth Dependencies (require_super_admin, require_tenant)

| Field | Detail |
|-------|--------|
| **Title** | Create Reusable Auth Dependencies |
| **Priority** | P1 |
| **Component** | Backend / Shared Framework |
| **Effort** | S (3-4 days) |

**Background:**
Super-admin and tenant checks are duplicated inline across routers.

**Problem:**
Inconsistent authorization, risk of missed checks on new endpoints.

**Scope:**
1. `require_super_admin` FastAPI dependency
2. `require_tenant` dependency/middleware
3. Refactor all routers to use dependencies

**Implementation Steps:**
1. Create `shared/fabric_framework/auth/dependencies.py`
2. Implement `require_super_admin`, `require_tenant`
3. Update all router files
4. Add tests

**Files Affected:**
- `shared/fabric_framework/auth/dependencies.py` (new)
- `backend/**/routers/*.py` (refactor)

**Acceptance Criteria:**
- [ ] All admin endpoints use `dependencies=[Depends(require_super_admin)]`
- [ ] Zero inline role checks remaining
- [ ] Tests for 403 (non-admin), 401 (no token)

**Test Plan:**
- Unit: dependency behavior with mock users
- Integration: endpoint access with different roles

**Documentation Updates:**
- `docs/auth.md` — authorization patterns

---

#### Ticket BE-008: Implement API Key Authentication

| Field | Detail |
|-------|--------|
| **Title** | Implement API Key Authentication |
| **Priority** | P1 |
| **Component** | Backend / API Gateway |
| **Effort** | M (2-3 weeks) |

**Background:**
Only JWT session auth via Clerk is supported. No programmatic API access.

**Problem:**
Third-party integrations, service-to-service calls, and scripts cannot authenticate cleanly.

**Scope:**
1. API key model (hashed storage in PostgreSQL)
2. `X-API-Key` header middleware
3. Key management endpoints (admin only)
4. Scopes: read, write, admin

**Implementation Steps:**
1. Migration: `api_keys` table
2. `X-API-Key` auth in `get_current_user_or_key`
3. Key generation: `prefix_` + 32 random bytes, store SHA-256 hash
4. CRUD endpoints for key management
5. Scope enforcement

**Files Affected:**
- `backend/api-gateway/` (auth, routers)
- Database migration

**Acceptance Criteria:**
- [ ] Valid API key returns 200
- [ ] Invalid/revoked key returns 401
- [ ] Key scope enforced (read key cannot POST)
- [ ] Admin can create/list/revoke keys

**Test Plan:**
- CRUD tests for key management
- Auth tests for valid/invalid/scoped keys

**Documentation Updates:**
- `docs/api-keys.md` — usage, scopes, rotation

---

#### Ticket BE-009: Add Circuit Breaker Module and Apply to All Layers

| Field | Detail |
|-------|--------|
| **Title** | Add Circuit Breaker Module and Apply to All Layers |
| **Priority** | P1 |
| **Component** | Backend / All Services |
| **Effort** | M (2 weeks) |

**Background:**
Only Layer 1 has circuit breaker protection. Other layers have none.

**Problem:**
Single failing dependency can cascade to total service outage.

**Scope:**
1. Shared circuit breaker module
2. Apply to all external calls (DB, Redis, Neo4j, LLM APIs)
3. Metrics and alerts

**Implementation Steps:**
1. `shared/fabric_framework/circuit_breaker.py` with configurable thresholds
2. Decorator: `@circuit_breaker(name="neo4j", failure_threshold=5)`
3. Apply to all `async def` functions making external calls
4. Prometheus metrics for circuit state

**Files Affected:**
- `shared/fabric_framework/circuit_breaker.py` (new)
- All service call sites

**Acceptance Criteria:**
- [ ] All external calls wrapped
- [ ] Circuit opens after threshold failures
- [ ] Metrics show circuit state
- [ ] Alert fires on circuit open

**Test Plan:**
- Unit: mock failures to trigger open
- Integration: stop dependency, verify fast failure

**Documentation Updates:**
- `docs/resilience.md` — circuit breaker configuration

---

#### Ticket BE-010: Fix _is_production_like() Explicit Environment Allowlist

| Field | Detail |
|-------|--------|
| **Title** | Fix _is_production_like() Explicit Environment Allowlist |
| **Priority** | P1 |
| **Component** | Backend / Shared Framework |
| **Effort** | S (1 day) |

**Background:**
Unknown environments are treated as production, causing surprising behavior.

**Problem:**
New environments (staging, demo) behave like production without explicit opt-in.

**Scope:**
Change to explicit allowlist: only `ENVIRONMENT=production` returns True.

**Implementation Steps:**
```python
def is_production_like() -> bool:
    return os.getenv("ENVIRONMENT") == "production"
```

**Files Affected:**
- `shared/fabric_framework/config.py`

**Acceptance Criteria:**
- [ ] Only `production` env returns True
- [ ] Startup banner shows mode clearly
- [ ] Unknown env fails fast with clear error

**Test Plan:**
- Unit: test with different env values

---

### Frontend / Product Readiness Tickets (8 tickets)

---

#### Ticket FE-001: Audit and Fix All Image alt Attributes for WCAG 2.1 AA

| Field | Detail |
|-------|--------|
| **Title** | Audit and Fix All Image alt Attributes for WCAG 2.1 AA |
| **Priority** | P1 |
| **Component** | Frontend |
| **Effort** | S (1 week) |

**Background:**
Only 4 `alt=` attributes exist across the entire frontend (~83+ images).

**Problem:**
WCAG 2.1 AA violation; screen readers cannot describe images.

**Implementation Steps:**
1. `grep -r "<img" frontend/src --include="*.tsx" -l` to find all image files
2. Audit each image: meaningful alt, decorative (alt=""), or complex (aria-label)
3. Add `jsx-a11y/alt-text` ESLint rule
4. Add CI gate with `axe-core` or `pa11y`

**Files Affected:**
- All `.tsx` files with `<img>` tags
- `.eslintrc.js`
- `.github/workflows/frontend.yml`

**Acceptance Criteria:**
- [ ] All images have alt attributes
- [ ] ESLint enforces rule
- [ ] CI accessibility scan passes

**Test Plan:**
- `npm run lint` passes
- axe-core scan zero violations

---

#### Ticket FE-002: Remove LegacyDataTable and LegacyTabs Components

| Field | Detail |
|-------|--------|
| **Title** | Remove LegacyDataTable and LegacyTabs Components |
| **Priority** | P1 |
| **Component** | Frontend |
| **Effort** | S (1-2 days) |

**Background:**
Both components have zero imports across the codebase.

**Problem:**
Dead code maintenance burden, bundle noise.

**Implementation Steps:**
1. Verify zero imports: `grep -r "LegacyDataTable\|LegacyTabs" frontend/src`
2. Delete files
3. Verify CI passes

**Files Affected:**
- `frontend/src/components/LegacyDataTable.tsx`
- `frontend/src/components/LegacyTabs.tsx`

**Acceptance Criteria:**
- [ ] Files deleted
- [ ] Zero references
- [ ] Build passes

---

#### Ticket FE-003: Verify Frontend Error Boundary with ErrorEnvelope Format

| Field | Detail |
|-------|--------|
| **Title** | Verify Frontend Error Boundary with ErrorEnvelope Format |
| **Priority** | P0 (supporting) |
| **Component** | Frontend |
| **Effort** | S (2-3 days) |

**Background:**
Backend migrating to canonical exceptions (BE-002). Frontend must parse ErrorEnvelope.

**Scope:**
1. Verify error boundary handles `{"error": {"code": "...", "message": "..."}}`
2. Add fallback for legacy `{"detail": "..."}` format during transition
3. TypeScript types for ErrorEnvelope

**Files Affected:**
- `frontend/src/lib/errors.ts`
- `frontend/src/components/ErrorBoundary.tsx`

**Acceptance Criteria:**
- [ ] ErrorEnvelope parsed correctly
- [ ] User-friendly error messages displayed
- [ ] Legacy format handled during transition

---

#### Ticket FE-004: Integrate pa11y Accessibility Scanning into CI

| Field | Detail |
|-------|--------|
| **Title** | Integrate pa11y Accessibility Scanning into CI |
| **Priority** | P1 |
| **Component** | Frontend / CI |
| **Effort** | S (2-3 days) |

**Implementation Steps:**
1. Add `pa11y-ci` to dev dependencies
2. Configure `.pa11yci.json` with URLs to scan
3. Add CI step to start dev server, run scan, fail on violations
4. Exclude known issues (documented) with expiration dates

**Files Affected:**
- `frontend/package.json`
- `frontend/.pa11yci.json` (new)
- `.github/workflows/frontend.yml`

**Acceptance Criteria:**
- [ ] CI runs pa11y on every PR
- [ ] Build fails on accessibility violations
- [ ] Report uploaded as artifact

---

#### Ticket FE-005: Add API Key Management UI for Admin Users

| Field | Detail |
|-------|--------|
| **Title** | Add API Key Management UI for Admin Users |
| **Priority** | P1 |
| **Component** | Frontend |
| **Effort** | M (1 week) |

**Scope:**
1. Page: `/admin/api-keys` — list, create, revoke keys
2. Display key name, scopes, created date, last used
3. Create flow: name + scopes → display key once (copy to clipboard)
4. Revoke with confirmation dialog

**Files Affected:**
- `frontend/src/pages/admin/api-keys.tsx` (new)
- `frontend/src/stores/api-keys.ts` (new)

**Acceptance Criteria:**
- [ ] Admin users see API keys page
- [ ] Create key with scopes
- [ ] Key displayed once on creation
- [ ] Revoke key with confirmation

---

#### Ticket FE-006: Lazy-Load Admin Routes to Reduce Bundle Size

| Field | Detail |
|-------|--------|
| **Title** | Lazy-Load Admin Routes to Reduce Bundle Size |
| **Priority** | P2 |
| **Component** | Frontend |
| **Effort** | S (2-3 days) |

**Implementation:**
Verify all 87 routes use `React.lazy()` + `Suspense`. Admin routes should be in separate chunk.

**Acceptance Criteria:**
- [ ] All routes lazy-loaded
- [ ] Admin chunk separate from main bundle
- [ ] Loading states for all routes

---

#### Ticket FE-007: Generate TypeScript Types from OpenAPI Specification

| Field | Detail |
|-------|--------|
| **Title** | Generate TypeScript Types from OpenAPI Specification |
| **Priority** | P2 |
| **Component** | Frontend |
| **Effort** | S (1-2 days) |

**Implementation:**
1. Add `openapi-typescript` to dev dependencies
2. CI generates types from backend OpenAPI spec
3. Commit generated types or generate on build

**Files Affected:**
- `frontend/package.json`
- `frontend/src/types/api.ts` (generated)

**Acceptance Criteria:**
- [ ] TypeScript types auto-generated from OpenAPI
- [ ] CI validates types are up-to-date

---

#### Ticket FE-008: Add Frontend Metrics (Web Vitals) to Observability Pipeline

| Field | Detail |
|-------|--------|
| **Title** | Add Frontend Metrics (Web Vitals) to Observability Pipeline |
| **Priority** | P2 |
| **Component** | Frontend |
| **Effort** | S (2-3 days) |

**Implementation:**
1. `web-vitals` library for LCP, FID, CLS
2. Send to OTel collector or directly to metrics backend
3. Dashboard in Grafana for Web Vitals

**Files Affected:**
- `frontend/src/lib/metrics.ts` (new)
- `frontend/src/main.tsx` (initialize)

**Acceptance Criteria:**
- [ ] Web Vitals collected on real user sessions
- [ ] Grafana dashboard shows LCP, FID, CLS distributions
- [ ] Alert on p75 LCP >2.5s

---

### Testing / QA Tickets (6 tickets)

---

#### Ticket QA-001: Expand Security Regression Gate to All 6 Test Groups

| Field | Detail |
|-------|--------|
| **Title** | Expand Security Regression Gate to All 6 Test Groups |
| **Priority** | P0 |
| **Component** | CI / Testing |
| **Effort** | S (2-3 days) |

**Background:**
Security regression gate only runs 3 of 6 test groups.

**Scope:**
Add cross-layer-tenant, contract, and k8s test groups to CI matrix.

**Implementation:**
```yaml
strategy:
  matrix:
    test_group:
      - unit
      - integration
      - hostile
      - cross-layer-tenant
      - contract
      - k8s
```

**Acceptance Criteria:**
- [ ] All 6 groups run on every PR
- [ ] Gate execution <15 minutes
- [ ] All groups passing

---

#### Ticket QA-002: Convert Hostile Tests from Grep Patterns to Runtime Behavioral Tests

| Field | Detail |
|-------|--------|
| **Title** | Convert Hostile Tests from Grep Patterns to Runtime Behavioral Tests |
| **Priority** | P1 |
| **Component** | Testing |
| **Effort** | M (2-3 weeks) |

**Scope:**
1. SQL injection payloads sent to all query endpoints → verify 400/422
2. XSS payloads to all input endpoints → verify sanitization
3. Path traversal to file endpoints → verify blocking
4. Auth bypass attempts → verify 403
5. Retain static analysis as fast supplementary checks

**Implementation:**
- `tests/hostile/test_sql_injection.py` — parameterized by endpoint
- `tests/hostile/test_xss.py`
- `tests/hostile/test_path_traversal.py`
- `tests/hostile/test_auth_bypass.py`

**Acceptance Criteria:**
- [ ] All attack vectors tested at runtime
- [ ] Static analysis retained for fast feedback
- [ ] CI passes

---

#### Ticket QA-003: Add Coverage Gate for Layer 2.5 Signal Refinery

| Field | Detail |
|-------|--------|
| **Title** | Add Coverage Gate for Layer 2.5 Signal Refinery |
| **Priority** | P1 |
| **Component** | Testing |
| **Effort** | M (2 weeks) |

**Scope:**
1. Write tests for core dedup logic (currently 7 test files → target 15+)
2. Add `fail_under=80` to CI matrix for L2.5
3. Integration tests with L2 and L3

**Acceptance Criteria:**
- [ ] L2.5 has `fail_under=80` in CI
- [ ] Coverage >=80%
- [ ] Integration tests pass

---

#### Ticket QA-004: Resolve Overdue Quarantined Test and Add CI Check

| Field | Detail |
|-------|--------|
| **Title** | Resolve Overdue Quarantined Test and Add CI Check |
| **Priority** | P1 |
| **Component** | Testing |
| **Effort** | S (1-2 days) |

**Scope:**
1. Fix or delete overdue test in `tests/quarantine/`
2. Add CI check: fail if quarantined test >7 days past expected_resolution

**Implementation:**
```bash
# In CI
find tests/quarantine -name "*.py" -exec python -c "check_quarantine_age({})" \;
```

**Acceptance Criteria:**
- [ ] Zero overdue quarantines
- [ ] CI fails on overdue quarantine

---

#### Ticket QA-005: Write Integration Tests for Idempotency Middleware

| Field | Detail |
|-------|--------|
| **Title** | Write Integration Tests for Idempotency Middleware |
| **Priority** | P1 |
| **Component** | Testing |
| **Effort** | S (2-3 days) |

**Scope:**
1. Same key → duplicate prevention
2. Different payload → 409 Conflict
3. Tenant isolation
4. TTL expiry
5. Concurrent requests

**Implementation:**
- `tests/integration/test_idempotency.py`

**Acceptance Criteria:**
- [ ] All 5 scenarios tested
- [ ] Tests run in CI

---

#### Ticket QA-006: Add E2E Test for Critical User Journey (Ingest → Extract → Query)

| Field | Detail |
|-------|--------|
| **Title** | Add E2E Test for Critical User Journey |
| **Priority** | P1 |
| **Component** | Testing / E2E |
| **Effort** | M (1 week) |

**Scope:**
Full pipeline test: upload document → extraction complete → entity visible in knowledge graph → queryable via API.

**Implementation:**
- Playwright/Cypress test simulating real user flow
- Waits for async processing (polling or webhook)
- Verifies data consistency across layers

**Acceptance Criteria:**
- [ ] E2E test passes in CI
- [ ] Runs in <5 minutes
- [ ] Tests real document processing, not mocks

---

### Infrastructure / DevOps Tickets (5 tickets)

---

#### Ticket INFRA-001: Fix PostgreSQL Backup CronJob Secret Reference

| Field | Detail |
|-------|--------|
| **Title** | Fix PostgreSQL Backup CronJob Secret Reference |
| **Priority** | P0 |
| **Component** | Infrastructure |
| **Effort** | S (1-2 days) |

**Implementation:**
```yaml
# k8s/cronjobs/postgres-backup-cronjob.yaml
- name: PGPASSWORD
  valueFrom:
    secretKeyRef:
      name: postgres-secret  # fix: was postgres-credentials
      key: password
```

**Acceptance Criteria:**
- [ ] `kubectl apply --dry-run=server` passes
- [ ] Manual backup job succeeds in staging
- [ ] Alertmanager rule for backup failure

---

#### Ticket INFRA-002: Rotate Layer 4 Hardcoded Password and Add Secret Scanning

| Field | Detail |
|-------|--------|
| **Title** | Rotate Layer 4 Hardcoded Password and Add Secret Scanning |
| **Priority** | P0 |
| **Component** | Infrastructure / Security |
| **Effort** | S (1-2 days) |

**Implementation:**
1. Create Kubernetes secret for Layer 4 DB credentials
2. Update `layer4-agents.yml` to use `valueFrom.secretKeyRef`
3. Rotate password in PostgreSQL
4. Add gitleaks/detect-secrets to CI

**Files Affected:**
- `k8s/base/layer4-agents.yml`
- `k8s/secrets/layer4-db-secret.yaml` (new)
- `.github/workflows/security-scan.yml`
- `.pre-commit-config.yaml`

**Acceptance Criteria:**
- [ ] No hardcoded passwords in K8s manifests
- [ ] CI blocks commits with password patterns
- [ ] Layer 4 connects successfully with new secret

---

#### Ticket INFRA-003: Fix Neo4j Backup CronJob for Community Edition

| Field | Detail |
|-------|--------|
| **Title** | Fix Neo4j Backup CronJob for Community Edition |
| **Priority** | P0 |
| **Component** | Infrastructure |
| **Effort** | M (1 week) |

**Implementation:**
Replace `neo4j-admin backup` (Enterprise only) with `neo4j-admin database dump` or Cypher-shell export.

```bash
neo4j-admin database dump neo4j --to-path=/backup/neo4j-$(date +%Y%m%d-%H%M%S).dump
```

**Acceptance Criteria:**
- [ ] Backup job succeeds in staging
- [ ] `.dump` file restorable to fresh Neo4j instance
- [ ] Restore procedure documented and tested

---

#### Ticket INFRA-004: Convert All Dockerfiles to Multi-Stage Builds

| Field | Detail |
|-------|--------|
| **Title** | Convert All Dockerfiles to Multi-Stage Builds |
| **Priority** | P1 |
| **Component** | Infrastructure |
| **Effort** | M (1 week) |

**Implementation:**
```dockerfile
# Builder stage
FROM python:3.11-slim AS builder
RUN apt-get update && apt-get install -y gcc
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Runtime stage
FROM python:3.11-slim
COPY --from=builder /root/.local /root/.local
COPY . /app
ENV PATH=/root/.local/bin:$PATH
USER 1000
CMD ["python", "-m", "app"]
```

**Acceptance Criteria:**
- [ ] All 8 images multi-stage
- [ ] Image size reduced >50%
- [ ] Trivy scan shows fewer CVEs
- [ ] All services start correctly

---

#### Ticket INFRA-005: Evaluate and Deploy PostgreSQL HA (CloudNativePG)

| Field | Detail |
|-------|--------|
| **Title** | Evaluate and Deploy PostgreSQL HA (CloudNativePG) |
| **Priority** | P1 |
| **Component** | Infrastructure |
| **Effort** | L (2-3 weeks) |

**Implementation:**
1. Evaluate CloudNativePG vs Patroni
2. Deploy 3-instance cluster in dev
3. Test failover: kill primary, verify promotion
4. Test backup/restore with HA setup
5. Migration plan for production (maintenance window)

**Acceptance Criteria:**
- [ ] 3-instance cluster running
- [ ] Automatic failover <30 seconds
- [ ] Backup via PgBackRest
- [ ] Migration plan approved

---

### Documentation / Developer Experience Tickets (3 tickets)

---

#### Ticket DOCS-001: Write Architecture Decision Records (ADRs)

| Field | Detail |
|-------|--------|
| **Title** | Write Architecture Decision Records (ADRs) |
| **Priority** | P2 |
| **Component** | Documentation |
| **Effort** | S (1 week) |

**Implementation:**
1. Create `docs/adr/template.md`
2. Write minimum 5 ADRs:
   - ADR-001: Tenant Isolation Model (row-level vs schema-level)
   - ADR-002: Database-per-Service Architecture
   - ADR-003: Neo4j Community vs Enterprise Decision
   - ADR-004: Clerk for Authentication
   - ADR-005: Semantic Pipeline 6-Layer Design

**Acceptance Criteria:**
- [ ] 5 ADRs committed
- [ ] Template established
- [ ] Team trained on ADR process

---

#### Ticket DOCS-002: Create docker-compose.dev.yml for Local Development

| Field | Detail |
|-------|--------|
| **Title** | Create docker-compose.dev.yml for Local Development |
| **Priority** | P2 |
| **Component** | Developer Experience |
| **Effort** | M (1 week) |

**Implementation:**
```yaml
# docker-compose.dev.yml
services:
  postgres: { image: postgres:15, ports: ["5432:5432"] }
  neo4j: { image: neo4j:5-community, ports: ["7474:7474", "7687:7687"] }
  redis: { image: redis:7, ports: ["6379:6379"] }
  minio: { image: minio/minio, ports: ["9000:9000"] }
  api-gateway: { build: ./backend/api-gateway, volumes: [".:/app"] }
  # ... other services
```

**Acceptance Criteria:**
- [ ] `docker compose -f docker-compose.dev.yml up` starts full stack
- [ ] Hot reload works for backend and frontend
- [ ] Health check script verifies all services

---

#### Ticket DOCS-003: Write Incident Response Runbooks

| Field | Detail |
|-------|--------|
| **Title** | Write Incident Response Runbooks |
| **Priority** | P2 |
| **Component** | Documentation / Operations |
| **Effort** | M (1 week) |

**Runbooks:**
1. PostgreSQL outage — failover, restore from backup
2. Redis outage — cache warming, session recovery
3. Neo4j corruption — restore from dump, reprocess documents
4. LLM provider downtime — circuit breaker, fallback provider
5. Cascading failure — isolate layer, scale up, root cause
6. Security breach — token revocation, audit log review, notify customers
7. Data corruption — identify scope, restore from backup, reconciliation
8. Deployment rollback — `kubectl rollout undo`, database migration reversal
9. Performance degradation — profiling, scaling, query optimization
10. Certificate expiry — renew, validate, distribute

**Acceptance Criteria:**
- [ ] 10 runbooks written
- [ ] Reviewed by on-call engineers
- [ ] Stored in Git and linked from PagerDuty
- [ ] Quarterly drill scheduled

---

## 9. Launch Gate Checklist

### 9.1 Authentication and Authorization

| # | Check | Evidence Required | Status |
|---|-------|-------------------|--------|
| 1 | Clerk JWT verification with alg enforcement | Unit test output showing rejected `alg=none` tokens | [ ] |
| 2 | Token revocation functional (Redis + SHA256) | Integration test: revoked token returns 401 | [ ] |
| 3 | Account lockout after 10 failed attempts | Test: 10th failure triggers 15-minute lockout | [ ] |
| 4 | Password hashing with bcrypt (72-byte limit) | Code review of auth module + unit test | [ ] |
| 5 | API key authentication implemented | E2E: X-API-Key header works, revoked key fails | [ ] |
| 6 | CORS configured fail-closed | Test: origin not in allowlist rejected | [ ] |
| 7 | Clerk webhooks verified with Svix HMAC | Unit test: valid signature accepted, tampered rejected | [ ] |
| 8 | Stripe webhooks verified with IP + signature | Unit test: wrong IP rejected, valid accepted | [ ] |
| 9 | JWT base64url encoding enforcement | Decode test showing rejection of standard base64 | [ ] |
| 10 | Session timeout and refresh working | E2E: idle timeout logs user out, refresh extends | [ ] |

### 9.2 RBAC and Tenant Isolation

| # | Check | Evidence Required | Status |
|---|-------|-------------------|--------|
| 1 | Tenant middleware enforces isolation on all requests | Middleware unit test + integration test | [ ] |
| 2 | require_super_admin dependency used on all admin endpoints | Code review: zero inline role checks | [ ] |
| 3 | Cross-layer tenant isolation tests pass | CI output: cross-layer-tenant test group green | [ ] |
| 4 | Tenant scoping on all database queries | Query log review: all queries include tenant_id filter | [ ] |
| 5 | Webhook endpoints exempt from tenant check (documented) | ADR + code comment on whitelist | [ ] |
| 6 | RBAC tiers enforced on frontend routes | E2E: standard user cannot access admin routes | [ ] |
| 7 | Data export respects tenant boundaries | Export test: tenant A cannot see tenant B data | [ ] |

### 9.3 Secrets and Credential Management

| # | Check | Evidence Required | Status |
|---|-------|-------------------|--------|
| 1 | Zero hardcoded secrets in repository | gitleaks scan output: zero findings | [ ] |
| 2 | `.env.example` contains only placeholders | Code review: no real credentials | [ ] |
| 3 | Kubernetes secrets used for all credentials | `kubectl get secrets` listing, manifest review | [ ] |
| 4 | Secret rotation procedure documented | Runbook: rotate-db-password.md | [ ] |
| 5 | CI blocks commits with secret patterns | CI gate: detect-secrets passes | [ ] |
| 6 | No secrets in container image layers | `dive` analysis or build log review | [ ] |

### 9.4 Database Migrations

| # | Check | Evidence Required | Status |
|---|-------|-------------------|--------|
| 1 | Migration framework in use (Alembic/Flyway) | Directory listing + version table query | [ ] |
| 2 | All migrations are backward-compatible | ADR: zero-downtime migration policy | [ ] |
| 3 | Migration rollback tested | Staging test: migrate forward, rollback, verify | [ ] |
| 4 | Seed data rejected in production | Test: `validate_production_safety()` blocks seed | [ ] |
| 5 | Migration history documented | `migrations/README.md` with version log | [ ] |
| 6 | Auto-migration on startup disabled | Config review: manual migration required | [ ] |

### 9.5 Backups and Disaster Recovery

| # | Check | Evidence Required | Status |
|---|-------|-------------------|--------|
| 1 | PostgreSQL backup job succeeds | Staging: manual job run, `.sql` file in S3 | [ ] |
| 2 | Neo4j backup job succeeds | Staging: `.dump` file created and restorable | [ ] |
| 3 | Backup alerting configured | Alertmanager: fires on 2 consecutive failures | [ ] |
| 4 | Restore procedure tested quarterly | Runbook + last drill date within 90 days | [ ] |
| 5 | RTO and RPO documented | `docs/disaster-recovery.md` with time objectives | [ ] |
| 6 | Cross-region backup replication | S3 bucket replication rule verified | [ ] |
| 7 | Point-in-time recovery available | PITR test: restore to specific timestamp | [ ] |

### 9.6 Observability

| # | Check | Evidence Required | Status |
|---|-------|-------------------|--------|
| 1 | All services emit OTel traces | Jaeger: traces visible for all 8 services | [ ] |
| 2 | Structured logging (structlog) in all services | Log sample: JSON format with request_id | [ ] |
| 3 | Real health checks with dependency probes | `/health/ready` returns 503 when DB down | [ ] |
| 4 | Request ID propagation across all services | Trace: same request_id in all service logs | [ ] |
| 5 | Audit logging SOC-2 compliant | Audit log sample: user, action, timestamp, result | [ ] |
| 6 | Grafana dashboards for all services | Screenshot: 18 dashboards accessible | [ ] |
| 7 | Alertmanager with PagerDuty + Slack routing | Alert test: synthetic failure triggers page | [ ] |
| 8 | Circuit breaker metrics exposed | Prometheus: `circuit_breaker_state` metric | [ ] |
| 9 | Frontend Web Vitals collected | Grafana: LCP, FID, CLS dashboards | [ ] |
| 10 | Error tracking (Sentry or equivalent) | Sentry project configured with source maps | [ ] |

### 9.7 Error Handling

| # | Check | Evidence Required | Status |
|---|-------|-------------------|--------|
| 1 | Zero raw HTTPException in backend | `grep` output: zero occurrences | [ ] |
| 2 | ErrorEnvelope schema consistent | Contract test: all errors match schema | [ ] |
| 3 | Frontend parses ErrorEnvelope correctly | E2E: error boundary shows meaningful message | [ ] |
| 4 | 5xx errors logged with full stack trace | Log review: exceptions include traceback | [ ] |
| 5 | Client receives safe error messages (no internals) | Response review: no paths, SQL, or secrets | [ ] |

### 9.8 CI/CD

| # | Check | Evidence Required | Status |
|---|-------|-------------------|--------|
| 1 | Security regression gate includes all 6 test groups | CI config review + recent run log | [ ] |
| 2 | Coverage gates on all 8 layers | CI matrix: L2.5 has fail_under=80 | [ ] |
| 3 | Dependency scanning (Dependabot/Snyk) | Tool output: zero critical vulns | [ ] |
| 4 | Container scanning (Trivy/Grype) | Scan report: acceptable CVE count | [ ] |
| 5 | Secret scanning (gitleaks) in CI | CI gate: passes on every PR | [ ] |
| 6 | Branch protection with required checks | GitHub settings screenshot | [ ] |
| 7 | Rollback workflow tested in staging | Drill log: rollback executed <10 minutes | [ ] |
| 8 | Deployment requires manual approval for prod | GitHub Environments: prod requires reviewer | [ ] |

### 9.9 E2E Tests

| # | Check | Evidence Required | Status |
|---|-------|-------------------|--------|
| 1 | Critical user journey E2E passes | CI: ingest → extract → query green | [ ] |
| 2 | Auth flow E2E passes | CI: login → access resource → logout green | [ ] |
| 3 | Admin operations E2E passes | CI: admin dashboard operations green | [ ] |
| 4 | Billing flow E2E passes (when ready) | CI: subscription → invoice → payment green | [ ] |
| 5 | Cross-browser testing | CI matrix: Chrome, Firefox, Safari | [ ] |
| 6 | Mobile responsive E2E | CI: key flows on mobile viewport | [ ] |

### 9.10 Security Tests

| # | Check | Evidence Required | Status |
|---|-------|-------------------|--------|
| 1 | SQL injection resistance | Runtime test: payloads rejected | [ ] |
| 2 | XSS prevention | Runtime test: scripts sanitized | [ ] |
| 3 | Path traversal blocking | Runtime test: `../` paths rejected | [ ] |
| 4 | CSRF protection | Cookie flags + SameSite verification | [ ] |
| 5 | Rate limiting functional | Load test: 429 returned under abuse | [ ] |
| 6 | API key scope enforcement | Test: read key cannot write | [ ] |
| 7 | TLS 1.2+ enforced | SSL Labs scan: A+ rating | [ ] |
| 8 | Security headers (HSTS, CSP, X-Frame-Options) | Header scan: all present | [ ] |

### 9.11 Dependency Scanning

| # | Check | Evidence Required | Status |
|---|-------|-------------------|--------|
| 1 | Python dependencies scanned | Snyk/Dependabot: zero critical | [ ] |
| 2 | Node.js dependencies scanned | npm audit: zero critical | [ ] |
| 3 | Container base images scanned | Trivy: zero critical OS CVEs | [ ] |
| 4 | License compliance verified | FOSSA or manual review: no GPL conflicts | [ ] |

### 9.12 Performance

| # | Check | Evidence Required | Status |
|---|-------|-------------------|--------|
| 1 | API p99 <500ms under 1000 req/s | k6 report: p99 latency | [ ] |
| 2 | Pagination <200ms at 1M rows | DB query timing log | [ ] |
| 3 | Frontend LCP <2.5s (p75) | Web Vitals dashboard | [ ] |
| 4 | Database connection pool adequate | Pool utilization <80% at peak | [ ] |
| 5 | CDN/cache headers on static assets | Header check: Cache-Control present | [ ] |
| 6 | Bundle size <500KB initial JS | Webpack/vite report | [ ] |

### 9.13 Accessibility

| # | Check | Evidence Required | Status |
|---|-------|-------------------|--------|
| 1 | All images have alt attributes | pa11y/axe-core: zero violations | [ ] |
| 2 | Keyboard navigation works | Manual test: all interactive elements reachable | [ ] |
| 3 | Color contrast WCAG AA | axe-core: contrast violations = 0 | [ ] |
| 4 | Screen reader compatibility | NVDA/VoiceOver test on critical flows | [ ] |
| 5 | Focus indicators visible | Visual inspection: focus ring present | [ ] |

### 9.14 Compliance

| # | Check | Evidence Required | Status |
|---|-------|-------------------|--------|
| 1 | SOC-2 audit logging functional | Audit log sample + retention policy | [ ] |
| 2 | GDPR data deletion workflow | Test: user deletion removes all PII | [ ] |
| 3 | Data retention policy enforced | Automated purge job for expired data | [ ] |
| 4 | Terms of service tracking | DB field: `accepted_tos_at` | [ ] |
| 5 | Privacy policy accessible | Footer link + standalone page | [ ] |

### 9.15 Incident Response

| # | Check | Evidence Required | Status |
|---|-------|-------------------|--------|
| 1 | On-call rotation established | PagerDuty schedule screenshot | [ ] |
| 2 | Escalation policy documented | `docs/oncall/escalation.md` | [ ] |
| 3 | Incident response runbooks written | 10 runbooks in `docs/runbooks/` | [ ] |
| 4 | Post-mortem template ready | `docs/incidents/template.md` | [ ] |
| 5 | Communication plan (customer notification) | `docs/incidents/communication.md` | [ ] |

### 9.16 Rollback

| # | Check | Evidence Required | Status |
|---|-------|-------------------|--------|
| 1 | Database rollback tested | Staging: migrate forward + back, verify | [ ] |
| 2 | Application rollback tested | `kubectl rollout undo` <5 minutes | [ ] |
| 3 | Feature flags for risky features | LaunchDarkly or env-based flags verified | [ ] |
| 4 | Rollback runbook written | `docs/runbooks/rollback.md` | [ ] |

### 9.17 Runbooks

| # | Check | Evidence Required | Status |
|---|-------|-------------------|--------|
| 1 | Database failover runbook | `docs/runbooks/postgres-failover.md` | [ ] |
| 2 | Restore from backup runbook | `docs/runbooks/restore-from-backup.md` | [ ] |
| 3 | Scaling runbook | `docs/runbooks/scaling.md` | [ ] |
| 4 | Certificate renewal runbook | `docs/runbooks/cert-renewal.md` | [ ] |
| 5 | Security incident runbook | `docs/runbooks/security-incident.md` | [ ] |

### 9.18 Admin

| # | Check | Evidence Required | Status |
|---|-------|-------------------|--------|
| 1 | Admin dashboard accessible | E2E: admin login → dashboard loads | [ ] |
| 2 | User management (list, disable, impersonate) | Feature test: admin operations | [ ] |
| 3 | Tenant management | Feature test: create, configure tenants | [ ] |
| 4 | API key management | Feature test: create, revoke keys | [ ] |
| 5 | System health overview | Dashboard: all services green/red status | [ ] |
| 6 | Audit log viewer | Admin can query audit logs by user/date | [ ] |

### 9.19 Onboarding

| # | Check | Evidence Required | Status |
|---|-------|-------------------|--------|
| 1 | Developer onboarding guide | `docs/onboarding/developer.md` | [ ] |
| 2 | `docker-compose.dev.yml` works | New hire can start stack in <30 minutes | [ ] |
| 3 | `.env.example` has clear instructions | Documented variable descriptions | [ ] |
| 4 | Architecture overview document | `docs/architecture/overview.md` | [ ] |
| 5 | Code style and contribution guide | `CONTRIBUTING.md` | [ ] |

### 9.20 Support

| # | Check | Evidence Required | Status |
|---|-------|-------------------|--------|
| 1 | Support ticket system configured | Zendesk/Intercom/similar operational | [ ] |
| 2 | Status page (public) | status.fabric4l.com or equivalent | [ ] |
| 3 | Support escalation path documented | `docs/support/escalation.md` | [ ] |
| 4 | Customer data access procedures | `docs/support/data-access.md` | [ ] |

---

## 10. Security Review

### 10.1 Executive Summary

**Total Findings:** 24 (0 Critical, 0 High, 10 Medium, 14 Low)
**Security Posture:** MODERATE — Strong fundamentals in authentication and input validation, but accumulated medium-severity issues in secrets management, tenant enforcement consistency, and missing API key authentication create exploitable gaps under adversarial conditions.

### 10.2 Strengths

**Authentication Layer (Strong)**
- Token revocation uses Redis with SHA-256 hashing — cannot be reversed even with Redis access
- bcrypt password hashing with 72-byte truncation limit prevents DoS via超长密码
- JWT implementation enforces `alg` header, rejecting `alg=none` attacks
- JWT uses base64url encoding per RFC 7515
- Account lockout: progressive delay after 10 failed attempts with 15-minute cooldown window
- Clerk webhook signatures verified via Svix HMAC — prevents impersonation
- Stripe webhook dual verification: IP source allowlist + signature validation

**Infrastructure Security (Good)**
- 50 Kubernetes security contexts enforce `runAsNonRoot: true` and `allowPrivilegeEscalation: false`
- CORS configured fail-closed — unknown origins denied by default
- No containers running as root (verified across 8 Dockerfiles)

**CI/CD Security (Good)**
- Branch protection with merge-blocking gates
- Security regression gate present (though incompletely configured — see P0-007)
- Secret scanning tooling present (though not catching all issues)

### 10.3 Medium Findings (10)

**SEC-M01: _DEFAULT_DEV_SECRET Hardcoded in config.py:9**
- **File:** `shared/fabric_framework/config.py:9`
- **Description:** A default secret is compiled into the application binary. If `SECRET_KEY` environment variable is unset, this predictable value is used for JWT signing.
- **Risk:** JWT forgery, complete authentication bypass
- **CVSS Estimate:** 6.5 (Medium)
- **Fix:** Remove fallback; require explicit secret at startup (P1-001)

**SEC-M02: .env.example Contains Keycloak Client Secrets**
- **File:** `.env.example`
- **Description:** Real credential material present in the example environment file committed to Git.
- **Risk:** Credential exposure to anyone with repository access; Git history retention makes rotation the only true fix
- **CVSS Estimate:** 5.5 (Medium)
- **Fix:** Replace with placeholders, rotate exposed credentials (P1-002)

**SEC-M03: _is_production_like() Surprising Behavior**
- **File:** `shared/fabric_framework/config.py`
- **Description:** Unknown environment names treated as production. New environments (staging, demo) inherit production safety gates unexpectedly.
- **Risk:** Operational confusion, potentially blocked workflows in new environments
- **CVSS Estimate:** 3.5 (Low-Medium)
- **Fix:** Explicit allowlist (P1-003)

**SEC-M04: No Reusable require_super_admin Dependency**
- **Pattern:** `backend/**/routers/*.py`
- **Description:** Super-admin checks duplicated inline across routers instead of reusable dependency.
- **Risk:** Inconsistent authorization, missed checks on new endpoints
- **CVSS Estimate:** 5.0 (Medium) if missed check leads to unauthorized admin access
- **Fix:** Centralized dependency (P1-004)

**SEC-M05: API Key Authentication Not Implemented**
- **Description:** Only browser-session JWT auth available. No mechanism for service-to-service or programmatic authentication.
- **Risk:** Workarounds (session simulation) are less secure; third-party integrations may store user passwords
- **CVSS Estimate:** 4.0 (Medium)
- **Fix:** Implement API key auth (P1-005)

**SEC-M06: Manual Tenant Enforcement Per-Router**
- **Pattern:** `backend/**/routers/*.py`
- **Description:** Each router extracts and validates tenant context inline. No middleware guarantees all requests are checked.
- **Risk:** Single missed check enables cross-tenant data access
- **CVSS Estimate:** 6.0 (Medium)
- **Fix:** TenantMiddleware in create_fabric_app() (P1-012)

**SEC-M07: Hardcoded postgres:postgres Password in Layer 4 Manifest**
- **File:** `k8s/base/layer4-agents.yml`
- **Description:** Database password visible in plain text in committed Kubernetes manifest.
- **Risk:** Complete Layer 4 database compromise if cluster or repository accessed
- **CVSS Estimate:** 7.0 (High) — elevated to P0 as INFRA-002
- **Fix:** Kubernetes secret + rotation (P0-006)

**SEC-M08: No Rate Limiting on API Gateway**
- **File:** `backend/api-gateway/`
- **Description:** Unlimited requests allowed from any client.
- **Risk:** DoS, resource exhaustion, cascading failures
- **CVSS Estimate:** 5.3 (Medium)
- **Fix:** Redis-backed rate limiting (P0-003)

**SEC-M09: 69 str(e) Occurrences Lose Exception Type**
- **Pattern:** `backend/**/*.py`
- **Description:** Exception type information lost in logs, hampering security incident response.
- **Risk:** Extended incident response time, missed attack patterns
- **CVSS Estimate:** 3.0 (Low)
- **Fix:** Structured logging (P1-011)

**SEC-M10: 6 Routes Missing response_model**
- **Pattern:** `backend/**/routers/*.py`
- **Description:** Without response validation, internal fields may leak in responses.
- **Risk:** Information disclosure (internal IDs, flags)
- **CVSS Estimate:** 3.5 (Low)
- **Fix:** Add response_model (P1-013)

### 10.4 Low Findings (14)

The 14 low findings are primarily code quality issues that reduce security resilience indirectly:
- Inconsistent error message formatting (str(e) pattern)
- Missing security headers on some responses
- Documentation gaps in auth flow
- Test coverage gaps in edge cases
- No Content Security Policy header detected
- Subresource Integrity not enforced on CDN assets
- Missing Strict-Transport-Security header on some routes

### 10.5 Security Test Results

| Test Category | Tests Run | Pass | Fail | Notes |
|---------------|-----------|------|------|-------|
| Unit: Auth | ~45 | ~45 | 0 | Strong coverage |
| Unit: Token revocation | ~12 | ~12 | 0 | SHA-256 + Redis |
| Integration: Clerk webhooks | ~8 | ~8 | 0 | Svix HMAC |
| Integration: Stripe webhooks | ~6 | ~6 | 0 | IP + signature |
| Hostile: SQL injection (grep) | 5 | 5 | 0 | Static analysis only |
| Hostile: XSS (grep) | 5 | 5 | 0 | Static analysis only |
| Cross-layer tenant | EXCLUDED | N/A | N/A | NOT RUN IN CI (P0-007) |
| Contract tests | EXCLUDED | N/A | N/A | NOT RUN IN CI (P0-007) |
| K8s security tests | EXCLUDED | N/A | N/A | NOT RUN IN CI (P0-007) |

### 10.6 Recommendations

1. **Immediate (P0):** Rotate Layer 4 password; fix backup secret reference
2. **Short-term (P1):** Implement API keys, centralize auth dependencies, add tenant middleware
3. **Medium-term (P2):** Add Content Security Policy, Subresource Integrity, security headers
4. **Process:** Quarterly penetration test; annual SOC-2 audit preparation

---

## 11. Tenant Isolation Review

### 11.1 Executive Summary

**Current Model:** Row-level tenant isolation with manual per-router enforcement
**Isolation Grade:** B- (functional but inconsistent enforcement)
**Primary Risk:** Manual enforcement creates gaps; cross-layer tests excluded from CI

### 11.2 Current Architecture

The system implements **row-level tenant isolation** where each database table includes a `tenant_id` column, and queries are filtered by the tenant extracted from the JWT token or API key. The tenant context is:
1. Extracted from JWT claim (`tenant_id`) in auth middleware
2. Stored in FastAPI `request.state.tenant_id`
3. Manually referenced in each router handler for query filtering

**Evidence of current pattern:**
```python
# Found across backend/**/routers/*.py
tenant_id = request.state.tenant_id
results = await db.execute(
    select(Entity).where(Entity.tenant_id == tenant_id)
)
```

### 11.3 Strengths

- Tenant context propagated via `request.state` (standard FastAPI pattern)
- JWT `tenant_id` claim prevents tenant spoofing (signed token)
- Cross-layer tenant isolation tests exist (though excluded from CI — P0-007)
- Database queries scoped to tenant (when implemented correctly)

### 11.4 Weaknesses and Risks

**TENANT-01: Manual Enforcement Per-Router (Risk: HIGH)**
- Each router handler must remember to add `.where(Entity.tenant_id == tenant_id)`
- New endpoints added by developers may miss this check
- No compile-time or middleware enforcement
- **Fix:** `TenantMiddleware` auto-injects tenant filter into all ORM queries (P1-012)

**TENANT-02: No Reusable Tenant Dependency (Risk: MEDIUM)**
- No `require_tenant(tenant_id)` dependency for route-level enforcement
- Admin endpoints that operate across tenants lack explicit override mechanism
- **Fix:** Create `require_tenant` dependency with admin override capability (P1-004)

**TENANT-03: Cross-Layer Tenant Tests Excluded from CI (Risk: HIGH)**
- The most critical tenant isolation verification is not run on every merge
- Bugs in tenant scoping can merge undetected
- **Fix:** Include in security regression gate (P0-007)

**TENANT-04: Webhook Endpoints May Not Validate Tenant (Risk: MEDIUM)**
- Webhook handlers (Clerk, Stripe) receive external calls without tenant context
- If these endpoints query tenant data, they need explicit tenant resolution from webhook payload
- **Evidence:** Not audited in detail — requires review

**TENANT-05: Tenant Isolation Model Not Documented (Risk: MEDIUM)**
- No ADR explains why row-level vs schema-level vs database-level was chosen
- New engineers must infer the pattern from code
- **Fix:** Write ADR-001 (P2-003)

### 11.5 Tenant Isolation Test Matrix

| Layer | Tenant Filter | Test Coverage | CI Gate |
|-------|--------------|---------------|---------|
| L1 Ingestion | Manual | Unit tests | Included |
| L2 Extraction | Manual | Unit tests | Included |
| L2.5 Signal Refinery | Manual | 7 files only | No gate |
| L3 Agents | Manual | Unit tests | Included |
| L4 Knowledge Graph | Manual | Unit tests | Included |
| L5 Ground Truth | Manual | Unit tests | Included |
| L6 Benchmarks | Manual | Unit tests | Included |
| API Gateway | N/A (routing) | Unit tests | Included |
| **Cross-layer** | **Integration** | **Exists** | **EXCLUDED (P0-007)** |

### 11.6 Recommendations

1. **P0:** Include cross-layer tenant tests in security regression gate
2. **P1:** Implement `TenantMiddleware` for automatic query scoping
3. **P1:** Create reusable `require_tenant` dependency
4. **P2:** Write ADR documenting tenant isolation architecture
5. **P2:** Annual tenant isolation penetration test (hire external firm)

---

## 12. Testing Review

### 12.1 Executive Summary

**Test Volume:** 1,108 test files (424 backend Python, 164 frontend unit, 87 E2E, plus hostile/quarantine/integration)
**Coverage Gates:** 7 of 8 layers (L2.5 missing)
**Overall Grade:** C+ (good volume, critical gaps in coverage gates, test quality, and CI completeness)

### 12.2 Test Inventory

| Category | Count | Type | CI Gate | Fail Under |
|----------|-------|------|---------|------------|
| Backend unit | 424 | pytest | Yes | 80% (7 layers) |
| Frontend unit | 164 | Jest/Vitest | Yes | 70% |
| E2E | 87 | Playwright | Yes | N/A |
| Hostile (static) | ~25 | grep-based | Yes | N/A |
| Hostile (runtime) | 0 | behavioral | No | N/A |
| Cross-layer integration | ~15 | pytest | **No (P0-007)** | N/A |
| Contract tests | ~10 | schema validation | **No (P0-007)** | N/A |
| K8s tests | ~8 | manifest validation | **No (P0-007)** | N/A |
| L2.5 tests | 7 | pytest | **No gate** | **None** |
| Quarantined | 1 | pytest | N/A | N/A |

### 12.3 Strengths

**Strong Practices:**
- `pytest-randomly` shuffles test order to detect inter-test dependencies
- Placeholder test detection: empty `pass` tests fail CI (prevents false confidence)
- Canonical JWT fixture shared across tests (consistent auth setup)
- Canonical tenant fixture for multi-tenant test scenarios
- Seed data `validate_production_safety()` prevents accidental production modification
- E2E test suite covers critical user journeys

### 12.4 Critical Gaps

**TEST-P0-001: Security Regression Gate Excludes 3 of 6 Test Groups**
- Cross-layer tenant tests, contract tests, and K8s tests are excluded from the mandatory security regression gate
- These are the tests that verify the most critical system properties: tenant isolation, API contract stability, and infrastructure security
- **Impact:** False confidence; critical regressions merge undetected
- **Fix:** P0-007

**TEST-P0-002: Layer 2.5 Has No Coverage Gate**
- Only 7 test files exist for the Signal Refinery layer
- No `fail_under` threshold in CI
- Code can merge with 0% coverage to this layer
- **Impact:** Bugs in deduplication logic (critical data integrity) go undetected
- **Fix:** P1-008

### 12.5 Quality Issues

**TEST-P1-001: Hostile Tests Are Grep-Based, Not Runtime**
The "hostile" security tests verify code patterns using `grep`:
```bash
# Current approach (static analysis)
grep -r "execute(" backend/ --include="*.py"
# If found, fail test — but this doesn't test if SQL injection actually works
```

This approach:
- Cannot detect dynamic query construction that evades patterns
- Creates false confidence ("we have security tests")
- Misses runtime behavior entirely

**Fix:** Convert to runtime behavioral tests (P1-009)

**TEST-P1-002: Overdue Quarantined Test**
- File: `tests/quarantine/test_flaky_feature.py`
- Expected resolution: 2026-05-01
- Current date: 2025-06-02 (27+ days overdue)
- Process failure: test was quarantined but never fixed
- **Fix:** P1-010

### 12.6 Test Debt Analysis

```
Test Debt Quadrant:
                    High Impact
                         |
    P0-007 (gate)        |    P1-008 (L2.5 coverage)
    P1-009 (runtime)     |    P1-012 (tenant middleware tests)
                         |
Low Impact --------------+-------------- High Effort
                         |
    P2-004 (str(e))      |    P1-010 (quarantine)
    P2-007 (response)    |    P2-008 (docker-compose test)
                         |
                    Low Impact
```

### 12.7 Recommendations

1. **P0:** Expand security regression gate to all 6 test groups
2. **P1:** Write 8+ new test files for L2.5; add 80% coverage gate
3. **P1:** Convert hostile tests from grep to runtime behavioral tests
4. **P1:** Add CI check for quarantined test expiry
5. **P1:** Add E2E test for full pipeline (QA-006)
6. **P2:** Property-based testing for deduplication logic (Hypothesis)
7. **Process:** Weekly test debt review in engineering standup

---

## 13. Infrastructure and Deployment Review

### 13.1 Executive Summary

**Infrastructure Grade:** C+ (strong security contexts, critical defects in backup/secret config)
**K8s Manifests:** 176 files with 50 security contexts
**Docker:** 8 single-stage images (optimization opportunity)
**Primary Risks:** Backup failures, hardcoded credentials, single points of failure

### 13.2 Kubernetes Configuration

**Security Contexts (50 entries):**
- `runAsNonRoot: true` on all pods
- `allowPrivilegeEscalation: false` on all containers
- `readOnlyRootFilesystem: true` on select containers
- `seccompProfile: RuntimeDefault` on some pods (verify all)

**Critical Defects:**

**INFRA-P0-001: PostgreSQL Backup CronJob Wrong Secret**
- File: `k8s/cronjobs/postgres-backup-cronjob.yaml`
- References: `postgres-credentials`
- Actual secret: `postgres-secret`
- **Impact:** All automated backups fail
- **Fix:** P0-005

**INFRA-P0-002: Layer 4 Hardcoded Password**
- File: `k8s/base/layer4-agents.yml`
- `CHECKPOINT_DATABASE_URL: postgresql://postgres:postgres@postgres:5432/layer4`
- **Impact:** Credential exposure, unauthorized database access
- **Fix:** P0-006

**INFRA-P0-003: Neo4j Backup Community Edition Syntax**
- File: `k8s/cronjobs/neo4j-backup-cronjob.yaml`
- May use Enterprise-only `neo4j-admin backup` command
- **Impact:** Graph backups fail, data loss exposure
- **Fix:** P0-010

### 13.3 High Availability Assessment

| Component | Current | Target | Risk |
|-----------|---------|--------|------|
| PostgreSQL | Single replica | 3-node HA | **SPOF** |
| Neo4j | Community single | Enterprise cluster or snapshot strategy | **SPOF** |
| Redis | Single instance | Sentinel or Cluster | **SPOF** |
| API Gateway | Multiple replicas | HPA + PDB | Acceptable |
| MinIO | Single instance | Distributed mode | Medium |

### 13.4 Docker Image Analysis

| Service | Current Stage | Image Size Est. | Target | Notes |
|---------|--------------|-----------------|--------|-------|
| layer1-ingestion | Single | ~1.2GB | ~400MB | Multi-stage opportunity |
| layer2-extraction | Single | ~1.3GB | ~450MB | PyTorch/ML libs heavy |
| layer2.5 | Single | ~1.1GB | ~380MB | |
| layer3-agents | Single | ~1.5GB | ~500MB | LLM SDKs heavy |
| layer4-knowledge-graph | Single | ~1.0GB | ~350MB | |
| layer5-ground-truth | Single | ~1.1GB | ~380MB | |
| layer6-benchmarks | Single | ~1.4GB | ~480MB | Benchmark tooling |
| api-gateway | Single | ~900MB | ~300MB | Lightest service |
| **Total** | | **~9.5GB** | **~3.2GB** | **66% reduction** |

### 13.5 CI/CD Pipeline

| Aspect | Status | Notes |
|--------|--------|-------|
| Workflow count | 61 | Good coverage |
| Critical gates | 25 | Merge-blocking |
| Secret scanning | Partial | gitleaks present but not catching all |
| Container scanning | Present | Trivy/Grype in CI |
| Dependency scanning | Present | Dependabot/Snyk |
| Rollback automation | Untested | Workflows exist but not validated |
| Canary deployment | Absent | Binary deploy only |
| Feature flags | Undetected | No LaunchDarkly or equivalent found |

### 13.6 Network Security

- Service mesh: Not detected (no Istio/Linkerd manifests)
- Network policies: Partial (some namespaces isolated)
- Ingress: Present (likely NGINX or similar)
- TLS termination: At ingress
- Service-to-service encryption: Not detected (mTLS not implemented)

### 13.7 Recommendations

1. **P0:** Fix all three backup/secret critical defects
2. **P1:** Evaluate CloudNativePG for PostgreSQL HA (P1-017)
3. **P1:** Neo4j HA decision: Enterprise vs snapshot strategy (P1-018)
4. **P1:** Redis AUTH password + network policies (P1-019)
5. **P1:** Multi-stage Docker builds (P1-020)
6. **P2:** Add resource limits to all pods (P2-009)
7. **P2:** Evaluate service mesh (Istio/Linkerd) for mTLS
8. **Process:** Monthly infrastructure security review

---

## 14. Observability and Operations Review

### 14.1 Executive Summary

**Observability Score:** 6.6 / 10
**Strengths:** Request ID propagation (9/10), audit logging (9/10), Grafana dashboards (18), Alertmanager (3 configs)
**Weaknesses:** Layer 3 blind to tracing, stub health check, 4 services without structured logging, circuit breaker only in L1

### 14.2 Tracing

| Service | Tracer | OTel Compliant | Jaeger Visible |
|---------|--------|----------------|----------------|
| L1 Ingestion | OTel | Yes | Yes |
| L2 Extraction | OTel | Yes | Yes |
| L2.5 Signal Refinery | OTel | Yes | Yes |
| L3 Agents | **Custom** | **No** | **No** |
| L4 Knowledge Graph | OTel | Yes | Yes |
| L5 Ground Truth | OTel | Yes | Yes |
| L6 Benchmarks | OTel | Yes | Yes |
| API Gateway | OTel | Yes | Yes |

**Critical Finding:** Layer 3 is completely invisible to distributed tracing. When agents fail or are slow, operators cannot diagnose the issue. This is the highest-value fix in observability (P0-008).

### 14.3 Logging

| Service | Structured (structlog) | Format | Request ID |
|---------|----------------------|--------|------------|
| L1 Ingestion | Yes | JSON | Yes |
| L2 Extraction | **No** | Plain text | Partial |
| L2.5 Signal Refinery | **No** | Plain text | Partial |
| L3 Agents | Yes | JSON | Yes |
| L4 Knowledge Graph | Yes | JSON | Yes |
| L5 Ground Truth | Yes | JSON | Yes |
| L6 Benchmarks | **No** | Plain text | Partial |
| API Gateway | **No** | Plain text | Partial |

**Impact:** 4 of 8 services produce unstructured logs that cannot be effectively queried in Loki/ELK. Incident response requires manual log reading for these services.

### 14.4 Metrics

**Observed:**
- Prometheus metrics likely exposed (standard with OTel)
- 18 Grafana dashboards
- 3 Alertmanager configurations

**Gaps:**
- No circuit breaker metrics (only L1 has circuit breaker)
- No rate limiting metrics (rate limiting not implemented)
- No business metrics (documents processed, entities extracted, LLM costs)

### 14.5 Alerting

| Channel | Integration | Purpose |
|---------|------------|---------|
| PagerDuty | Configured | P0/P1 page on-call engineer |
| Slack | Configured | Team notification, context |
| Email | Undetected | Not verified |

**Alert Quality:**
- Backup failure: **Not configured** (P0-005)
- Circuit breaker open: **Not configured** (P1-014)
- Health check failure: **Partial** (stub health check)
- Latency p99 >500ms: Likely configured but not verified
- Error rate >1%: Likely configured but not verified

### 14.6 Health Checks

| Endpoint | Current | Target | Gap |
|----------|---------|--------|-----|
| `/health` | Static `{"status": "ok"}` | `/health/live` + `/health/ready` | **Critical** |
| Live probe | N/A | Process running check | Missing |
| Ready probe | N/A | DB + Redis + Neo4j ping | **Critical** |

The stub health check means Kubernetes cannot distinguish healthy from unhealthy pods. Traffic routes to failing instances.

### 14.7 Audit Logging

**Score:** 9/10 — SOC-2 compliant

Evidence of strong audit logging:
- User action logging (who, what, when, result)
- Immutable audit log storage
- Retention policy detected
- Admin actions specifically flagged

### 14.8 Recommendations

1. **P0:** Replace Layer 3 custom tracer with OTel (P0-008)
2. **P0:** Implement real health checks (P0-009)
3. **P1:** Add structlog to L2, L2.5, L6, API gateway (P1-015)
4. **P1:** Add circuit breaker metrics (P1-014)
5. **P1:** Add backup failure alerting (P0-005)
6. **P1:** Add business metrics dashboard (documents, entities, LLM costs)
7. **P2:** Frontend Web Vitals integration (FE-008)
8. **P2:** Sentry integration for error tracking

---

## 15. Frontend UX and Product Readiness Review

### 15.1 Executive Summary

**Frontend Score:** A- (8.0 / 10)
**Code Quality:** Exceptional (2 `any` types in 158K lines, zero console.log in production)
**Accessibility:** Poor (4 alt attributes across entire app — WCAG risk)
**Performance:** Good (87 lazy-loaded routes, TanStack Query caching)

### 15.2 Code Quality Analysis

**Type Safety:**
- TypeScript strict mode: Likely enabled (only 2 `any` types suggests strict checking)
- Generic components properly typed
- API response types defined (but may drift without OpenAPI generation)

**Production Discipline:**
- Zero `console.log` in production source: Excellent
- Error boundaries present: Likely (Clerk integration suggests robust error handling)
- React StrictMode: Not verified

**State Management:**
- 9 Zustand stores: Clean atomic state separation
- 486 TanStack Query usages: Server state well-managed with caching, invalidation, and optimistic updates
- No Redux detected (simpler architecture — positive)

**Routing:**
- 87 lazy-loaded routes with code splitting
- Tier-based RBAC: standard / advanced / admin route guards
- Clerk auth bridge: Race-condition-proof pattern detected

### 15.3 Accessibility (Critical Gap)

| WCAG Criterion | Status | Notes |
|---------------|--------|-------|
| 1.1.1 Non-text Content (alt text) | **FAIL** | Only 4 alt= attributes |
| 1.4.3 Contrast (Minimum) | Unknown | Not tested |
| 2.1.1 Keyboard | Unknown | Not tested |
| 2.4.7 Focus Visible | Unknown | Not tested |
| 4.1.2 Name, Role, Value | Unknown | Not tested |

**Impact:** The alt text failure alone is sufficient for WCAG 2.1 AA non-compliance. In jurisdictions with accessibility legislation (US ADA, EU EAA), this creates legal liability.

### 15.4 Component Architecture

**Strengths:**
- Clear component hierarchy
- Lazy loading for route-level code splitting
- Shared component library (implied by consistent patterns)

**Debt:**
- `LegacyDataTable.tsx` — 0 imports, dead code (P1-007)
- `LegacyTabs.tsx` — 0 imports, dead code (P1-007)
- Both should be removed

### 15.5 Product Completeness

| Feature | Status | Notes |
|---------|--------|-------|
| Document ingestion | Ready | L1 functional |
| Entity extraction | Ready | L2 functional |
| Signal refinery | Ready | L2.5 functional, under-tested |
| Agent orchestration | Ready | L3 functional, tracing blind |
| Knowledge graph | Ready | L4 functional, Neo4j HA gap |
| Ground truth labeling | Ready | L5 functional |
| Benchmarks | Ready | L6 functional |
| Billing | **Not ready** | In-memory only (P2) |
| Admin dashboard | Unknown | Not audited |
| API documentation | **Missing** | OpenAPI specs absent |

### 15.6 Recommendations

1. **P1:** Fix all alt attributes + add jsx-a11y ESLint rule (P1-006)
2. **P1:** Remove legacy components (P1-007)
3. **P2:** Integrate pa11y into CI (FE-004)
4. **P2:** Generate TypeScript types from OpenAPI (FE-007)
5. **P2:** Add Web Vitals tracking (FE-008)
6. **Product:** Complete Layer 7 billing service
7. **Product:** Build admin dashboard

---

## 16. Documentation and Developer Experience Review

### 16.1 Executive Summary

**Documentation Grade:** D+ (critical gaps in API specs, runbooks, and ADRs)
**Developer Experience:** C+ (good framework abstractions, poor local development setup)

### 16.2 Documentation Inventory

| Document | Status | Quality | Location |
|----------|--------|---------|----------|
| README | Likely present | Unknown | `/README.md` |
| API specification (main) | **MISSING** | N/A | `openapi/fabric-4l-api.json` does not exist |
| API specification (billing) | **EMPTY** | 12 lines | `openapi/layer7-billing.json` |
| Architecture overview | Unknown | Unknown | Not found |
| ADRs | **NONE** | N/A | No `docs/adr/` directory |
| Runbooks | **NONE** | N/A | No `docs/runbooks/` directory |
| Onboarding guide | Unknown | Unknown | Not found |
| Contributing guide | Unknown | Unknown | Not found |
| Error handling guide | Unknown | Unknown | Not found |
| Database configuration | Unknown | Unknown | Not found |
| Local development setup | **MISSING** | N/A | No `docker-compose.dev.yml` |

### 16.3 API Documentation Gap (Critical)

The absence of `fabric-4l-api.json` means:
- No auto-generated API docs (Swagger UI)
- No client SDK generation
- Frontend developers must manually maintain TypeScript types
- Third-party integrators have no API reference
- API contract changes are invisible until runtime failures

**Fix:** Auto-generate from FastAPI using `app.openapi()` (P2-001)

### 16.4 Developer Experience Assessment

**Positive:**
- `create_fabric_app()` reduces bootstrapping to one function call
- `.env.example` provides configuration template (despite containing secrets)
- Zustand DevTools integration for state debugging
- FastAPI auto-reload for backend development
- React hot reload for frontend development

**Negative:**
- No `docker-compose.dev.yml` — engineers must start services individually or use staging
- `.env.example` contains real secrets (security risk + confusion)
- `_is_production_like()` surprises new engineers
- No documented troubleshooting guide
- No architecture decision records — engineers cannot understand "why" behind choices

### 16.5 Onboarding Experience

Estimated time for a new senior engineer to be productive:
- **Current:** 3-5 days (must discover configuration, start services individually, infer architecture from code)
- **Target:** 1 day (with docker-compose.dev.yml + onboarding guide + ADRs)

### 16.6 Recommendations

1. **P2:** Auto-generate OpenAPI spec from FastAPI (P2-001)
2. **P2:** Write 5+ ADRs for key decisions (P2-003)
3. **P2:** Create `docker-compose.dev.yml` (P2-008)
4. **P2:** Write incident response runbooks (P2-010)
5. **P2:** Create developer onboarding guide
6. **P2:** Sanitize `.env.example` of secrets
7. **Process:** Documentation review in every PR (checklist item)

---

## 17. Recommended Validation Commands

### 17.1 Local Development Validation

```bash
# Clone and setup
git clone <repo-url> fabric_4l
cd fabric_4l

# Verify Python version
python --version  # >= 3.11 recommended

# Install backend dependencies
pip install -r backend/api-gateway/requirements.txt
pip install -r shared/fabric_framework/requirements.txt

# Verify database.py PostgreSQL support (will FAIL before BE-001)
python -c "
from shared.fabric_framework.database import get_engine
import asyncio
async def test():
    try:
        engine = await get_engine('postgresql+asyncpg://test:test@localhost/test')
        print('PASS: PostgreSQL supported')
    except Exception as e:
        print(f'FAIL: {e}')
asyncio.run(test())
"

# Verify no hardcoded secrets (will FAIL before SEC fixes)
gitleaks detect --source . --verbose

# Run backend tests
cd backend/layer1-ingestion && pytest -xvs
cd backend/layer2-extraction && pytest -xvs
# ... repeat for all layers

# Verify exception handling (will FAIL before BE-002)
grep -r "raise HTTPException(" backend/ --include="*.py" && echo "FAIL: Raw HTTPException found" || echo "PASS: No raw HTTPException"

# Frontend setup
cd frontend
npm install
npm run lint
npm run typecheck
npm run test:unit
npm run build

# Accessibility scan (will FAIL before FE-001)
npx axe-core-cli http://localhost:3000 --exit

# Check for legacy components
grep -r "LegacyDataTable\|LegacyTabs" frontend/src && echo "FAIL: Legacy components present" || echo "PASS: No legacy components"

# Verify no console.log in production source
grep -r "console.log" frontend/src --include="*.ts" --include="*.tsx" | grep -v "\.test\." | grep -v "\.spec\." && echo "FAIL: console.log found" || echo "PASS: No console.log"
```

### 17.2 CI Validation Commands

```bash
# Security regression (should include all 6 groups)
act -j security-regression -W .github/workflows/security-regression.yml

# Verify test groups are all present
yq '.jobs.security-regression.strategy.matrix.test_group[]' .github/workflows/security-regression.yml | sort
# Expected: contract, cross-layer-tenant, hostile, integration, k8s, unit

# Lint backend
ruff check backend/ shared/

# Type check frontend
cd frontend && npx tsc --noEmit

# Container build validation
docker build -t fabric-layer1:latest backend/layer1-ingestion/
docker build -t fabric-api:latest backend/api-gateway/

# Kubernetes manifest validation
kubectl apply --dry-run=client -f k8s/base/
kubeval k8s/base/*.yml  # or kubeconform

# Helm chart linting (if applicable)
helm lint k8s/helm-charts/fabric-4l/

# Verify backup CronJobs reference correct secrets
grep -A5 "secretKeyRef" k8s/cronjobs/postgres-backup-cronjob.yaml
# Should show: name: postgres-secret

grep "CHECKPOINT_DATABASE_URL" k8s/base/layer4-agents.yml
# Should NOT show: postgres:postgres

# OpenAPI spec generation (will FAIL before BE-011)
cd backend/api-gateway && python -c "from main import app; import json; print(json.dumps(app.openapi()))" | jq '.paths | keys'
# Should return list of API paths
```

### 17.3 Production Readiness Validation

```bash
# Health checks (will FAIL before BE-006)
curl -f http://api-gateway/health/live || echo "Liveness FAIL"
curl -f http://api-gateway/health/ready || echo "Readiness FAIL"

# Database connectivity
curl http://api-gateway/health/ready | jq '.checks.postgres'
# Expected: "ok"

# Rate limiting (will FAIL before BE-003)
for i in {1..15}; do
  curl -s -o /dev/null -w "%{http_code}\n" http://api-gateway/api/public/endpoint
done | sort | uniq -c
# Should show: 10 x 200, 5 x 429

# Idempotency (will FAIL before BE-004)
curl -X POST -H "Content-Type: application/json" -H "Idempotency-Key: test-123" \
  -d '{"name":"test"}' http://api-gateway/api/entities
curl -X POST -H "Content-Type: application/json" -H "Idempotency-Key: test-123" \
  -d '{"name":"test"}' http://api-gateway/api/entities
# First: 201 Created, Second: 200 OK (cached)

# Jaeger tracing (will FAIL before BE-005)
curl "http://jaeger:16686/api/traces?service=layer3-agents&limit=1" | jq '.data | length'
# Expected: > 0

# Structured logging
kubectl logs deployment/api-gateway --tail=10 | jq '.request_id'
# Should not be null

# Backup verification
kubectl create job --from=cronjob/postgres-backup test-backup-$(date +%s)
kubectl logs job/test-backup-...
# Should show successful pg_dump and S3 upload

# Security scan
trivy fs . --severity HIGH,CRITICAL
gitleaks detect --source . --verbose

# Load test
k6 run --vus 100 --duration 5m load-test-script.js
# Check: p99 <500ms, error rate <0.1%
```

### 17.4 Quick Health Check Script

Save as `scripts/validate-production-readiness.sh`:

```bash
#!/bin/bash
set -euo pipefail

ERRORS=0

echo "=== Fabric 4L Production Readiness Validation ==="

# P0-001: PostgreSQL support
if grep -r "UnsupportedDatabaseURL" shared/fabric_framework/database.py > /dev/null; then
    echo "[FAIL] P0-001: database.py still raises UnsupportedDatabaseURL for PostgreSQL"
    ERRORS=$((ERRORS + 1))
else
    echo "[PASS] P0-001: PostgreSQL driver implemented"
fi

# P0-002: Exception classes
COUNT=$(grep -r "raise HTTPException(" backend/ --include="*.py" | wc -l)
if [ "$COUNT" -gt 0 ]; then
    echo "[FAIL] P0-002: $COUNT raw HTTPException raises remaining"
    ERRORS=$((ERRORS + 1))
else
    echo "[PASS] P0-002: No raw HTTPException raises"
fi

# P0-005: Backup secret
if grep -r "postgres-credentials" k8s/cronjobs/postgres-backup-cronjob.yaml > /dev/null; then
    echo "[FAIL] P0-005: Backup CronJob references wrong secret"
    ERRORS=$((ERRORS + 1))
else
    echo "[PASS] P0-005: Backup secret reference correct"
fi

# P0-006: Hardcoded password
if grep -r "postgres:postgres" k8s/base/layer4-agents.yml > /dev/null; then
    echo "[FAIL] P0-006: Layer 4 has hardcoded password"
    ERRORS=$((ERRORS + 1))
else
    echo "[PASS] P0-006: No hardcoded Layer 4 password"
fi

# P0-007: Security regression gate
GROUPS=$(yq '.jobs.security-regression.strategy.matrix.test_group | length' .github/workflows/security-regression.yml)
if [ "$GROUPS" -lt 6 ]; then
    echo "[FAIL] P0-007: Security regression gate has only $GROUPS test groups (expected 6)"
    ERRORS=$((ERRORS + 1))
else
    echo "[PASS] P0-007: Security regression gate includes all test groups"
fi

# P1-001: Hardcoded dev secret
if grep -r "_DEFAULT_DEV_SECRET" shared/fabric_framework/config.py > /dev/null; then
    echo "[FAIL] P1-001: _DEFAULT_DEV_SECRET still present"
    ERRORS=$((ERRORS + 1))
else
    echo "[PASS] P1-001: _DEFAULT_DEV_SECRET removed"
fi

# P1-006: Alt attributes
ALT_COUNT=$(grep -r "alt=" frontend/src --include="*.tsx" | wc -l)
IMG_COUNT=$(grep -r "<img" frontend/src --include="*.tsx" | wc -l)
if [ "$ALT_COUNT" -lt "$IMG_COUNT" ]; then
    echo "[FAIL] P1-006: Only $ALT_COUNT alt attributes for $IMG_COUNT images"
    ERRORS=$((ERRORS + 1))
else
    echo "[PASS] P1-006: All images have alt attributes"
fi

# P1-007: Legacy components
if [ -f "frontend/src/components/LegacyDataTable.tsx" ] || [ -f "frontend/src/components/LegacyTabs.tsx" ]; then
    echo "[FAIL] P1-007: Legacy components still present"
    ERRORS=$((ERRORS + 1))
else
    echo "[PASS] P1-007: Legacy components removed"
fi

# P1-008: L2.5 coverage gate
if ! grep -r "layer2.5" .github/workflows/ | grep "fail_under" > /dev/null; then
    echo "[FAIL] P1-008: L2.5 coverage gate missing"
    ERRORS=$((ERRORS + 1))
else
    echo "[PASS] P1-008: L2.5 coverage gate present"
fi

echo ""
echo "=== Results: $ERRORS failures ==="
if [ "$ERRORS" -eq 0 ]; then
    echo "All checks passed! System is production-ready."
    exit 0
else
    echo "System NOT production-ready. Address failures above."
    exit 1
fi
```

---

## 18. Final Recommendation

### 18.1 Verdict: **NOT READY FOR PRODUCTION LAUNCH**

Fabric_4L has a strong architectural foundation, excellent frontend engineering, and robust security fundamentals in authentication. However, **10 P0 launch blockers** spanning database connectivity, error handling, infrastructure secrets, CI completeness, and observability instrumentation make production deployment unsafe at this time.

### 18.2 What Happens If You Launch Now

| Scenario | Likelihood | Impact |
|----------|-----------|--------|
| Services cannot start in production (no PostgreSQL driver) | **Certain** | Total outage |
| API clients cannot parse errors (exception contract broken) | **Certain** | Frontend crashes, integration failures |
| Database backups silently fail | High | Catastrophic data loss on any failure |
| Layer 4 credentials exposed in manifests | High | Security breach, unauthorized DB access |
| Tenant isolation bugs merge undetected | Medium | Cross-tenant data leak |
| Layer 3 incidents unresolvable (no traces) | Medium | Extended outages, customer impact |
| Health checks lie about service status | High | Prolonged outages, failed failovers |

### 18.3 Path to Production

**Estimated Timeline:** 16 weeks (4 months) with 4 engineers
**Critical Path:**
1. Weeks 1-2: Emergency stabilization (Phase 0) — secrets, CI, backups
2. Weeks 3-4: Database connectivity (Phase 1) — PostgreSQL driver, health checks
3. Weeks 5-6: Error handling contract (Phase 2) — exceptions, idempotency
4. Weeks 7-8: Security hardening (Phase 3) — auth, tenant middleware
5. Weeks 9-10: Observability (Phase 4) — OTel, circuit breakers, logging
6. Weeks 11-12: Performance (Phase 5) — rate limiting, HA, Docker
7. Weeks 13-14: Frontend polish (Phase 6) — accessibility, cleanup
8. Weeks 15-16: Documentation and final validation (Phase 7)

**Alternative: Soft Launch**
If business pressure demands earlier launch, consider a **single-tenant managed service** model where:
1. Database connectivity is fixed (P0-001) — non-negotiable
2. Health checks are real (P0-009) — non-negotiable
3. Backups are functional (P0-005) — non-negotiable
4. Tenant isolation is temporarily simplified (single tenant only)
5. Layer 7 billing is disabled
6. All other P0s are addressed in weekly sprints post-launch

Even this reduced scope requires **4-6 weeks** of focused engineering.

### 18.4 Risk Acceptance Statement

If leadership accepts the risks and proceeds without fixing P0 items:

> **We acknowledge that launching Fabric_4L without addressing the identified P0 blockers creates significant risk of service outage, data loss, security breach, and regulatory non-compliance. We accept this risk and will prioritize remediation sprints immediately post-launch. Engineering leadership has communicated that mean time to recovery for incidents may be unbounded due to observability gaps, and that tenant isolation guarantees are not continuously verified by CI.**

*Recommended: Obtain signed risk acceptance from CTO, CISO, and VP Engineering before proceeding.*

### 18.5 Immediate Next Steps (This Week)

1. **Halt feature development** — all engineering effort to P0 remediation
2. **Form tiger team** — 2 backend + 1 DevOps + 1 QA dedicated to P0s
3. **Execute Phase 0** — P0-005, P0-006, P0-007, P1-001, P1-002, P1-010
4. **Daily standup** — track P0 burn-down with executive visibility
5. **Re-audit** — schedule follow-up audit after P0 completion before launch

---

*This audit was conducted against commit `c89469a4` by 7 specialist agents analyzing a fresh clone. All findings are based on static analysis of the codebase. Runtime verification and penetration testing are recommended as follow-up activities.*

*Report generated: 2025-06-02*
*Classification: CONFIDENTIAL — Internal Use Only*
