# Value Fabric — Production Launch Readiness Audit

**Audit Date:** 2026-05-27
**Auditor:** Jules, Principal Software Architect
**Target Bar:** Production-ready enterprise SaaS for security-conscious customers

---

# Executive Summary

## Overall Production Readiness Score: 5.8 / 10

**Status: NOT READY for general production. Controlled beta possible after P0 remediation.**

Value Fabric is a sophisticated six-layer agentic SaaS platform with strong architectural foundations, mature tenant-isolation patterns (Postgres RLS), and comprehensive security test coverage. However, **critical security gaps in Layer 7 Billing and Layer 2 Extraction, an unprotected SSRF vector in Layer 1, weak frontend coverage thresholds, and incomplete infrastructure wiring** prevent a production launch today. The platform demonstrates senior-level engineering in core layers but has weak links that break the security perimeter and create cross-tenant data exposure risks.

### Top 10 Risks
1.  **L7 Billing zero authentication** — Accepts tenant identity purely from spoofable headers (`X-Tenant-ID`) without cryptographic validation.
2.  **L2 Extraction auth is conditional/no-op** — `register_fabric_auth_from_env` is a no-op when env vars are unset; no middleware enforces auth.
3.  **L1 callback_url lacks SSRF validation** — Attackers can supply internal metadata endpoints or localhost URLs.
4.  **L3 rate limiter trusts X-Forwarded-For** without proxy validation, allowing infinite client-key rotation/bypass.
5.  **L4 file tools fallback to "default" tenant** — Background jobs without context collide files across tenants in storage.
6.  **Frontend coverage thresholds at 25% branches / 35% lines** — Far below production-grade standards (target ≥70%).
7.  **Hardcoded demo data (Medtronic)** in `ProspectPromptBuilder.tsx` — Risk of leaking internal data or customer IP to production.
8.  **Dev auth bypass (ALLOW_INSECURE_DEV_AUTH_BYPASS)** present in committed compose files — High risk of misconfiguration in production.
9.  **No PostgreSQL backup implementation** — While Neo4j has a backup manager, the primary transactional DB is unprotected.
10. **Dual auth system (Clerk + Keycloak + legacy JWT)** — Increases misconfiguration drift and attack surface during transition.

### Top 10 Recommended Actions
1.  Add JWT validation + `GovernanceMiddleware` + `RateLimitMiddleware` to L7 Billing immediately.
2.  Enforce unconditional `GovernanceMiddleware` in L2 Extraction; block startup without auth keys in production.
3.  Add SSRF validation (`validate_url_safety`) to L1 `callback_url` before storage.
4.  Harden L3 rate limiter to use authenticated identity (`ctx.tenant_id`) instead of `X-Forwarded-For`.
5.  Raise frontend coverage thresholds to ≥60% branches / ≥70% lines and fill gaps in auth/API paths.
6.  Implement PostgreSQL pg_dump/base-backup manager and document the recovery runbook.
7.  Integrate Sentry for exception grouping and production alerting across all layers.
8.  Gate or remove hardcoded demo data from `ProspectPromptBuilder.tsx`.
9.  Add service-to-service JWT signing for L1→L2 Celery calls to prevent internal header spoofing.
10. Complete Clerk auth rollout and deprecate Keycloak/legacy JWT paths with a firm sunset date.

---

# System Map

## Repo Structure
- `apps/web/`: React 19 Frontend (Vite, TanStack Query, Zustand, Clerk).
- `services/`:
  - `api/`: API Gateway (Clerk JWT, tenant context).
  - `layer1-ingestion/`: Playwright crawling, Celery, Redis.
  - `layer2-extraction/`: LLM extraction, Pydantic v2, RDF/OWL.
  - `layer3-knowledge/`: Neo4j, GraphRAG, pgvector.
  - `layer4-agents/`: LangGraph orchestration, ROI calculator.
  - `layer5-ground-truth/`: Validation, evidence-backed claims.
  - `layer6-benchmarks/`: Peer comparison, statistical validation.
  - `layer7-billing/`: Emerging billing service.
- `packages/shared/`: Common identity, database (RLS), and error handling framework.
- `contracts/`: Source-of-truth OpenAPI and JSONSchema definitions.
- `tests/`: Security (130+ files), contract, and integrated E2E test suites.
- `k8s/`: Kubernetes base manifests and environment overlays.

## Services/Apps Matrix
| Layer | Service | Port | Framework | Multi-tenancy |
|-------|---------|------|-----------|---------------|
| Frontend | web | 3001 | React | Clerk Org-based |
| L1 | ingestion | 8001 | FastAPI | Postgres RLS |
| L2 | extraction | 8002 | FastAPI | TenantContext |
| L3 | knowledge | 8003 | FastAPI | Neo4j property filter |
| L4 | agents | 8004 | FastAPI | ContextVar prop |
| L5 | ground-truth | 8005 | FastAPI | Postgres RLS |
| L6 | benchmarks | 8006 | FastAPI | Postgres RLS |
| L7 | billing | - | FastAPI | Spoofable headers (CRITICAL) |

## Key Runtime Dependencies
- **Data Stores**: PostgreSQL (Transactional), Neo4j Community (Graph), Redis (Cache/RateLimit), MinIO (S3 Object Storage).
- **Identity**: Clerk (Primary B2B), Keycloak (Legacy OIDC), Infisical (Secrets Management).
- **AI/Agents**: LangGraph (Orchestration Engine), OpenAI/Anthropic/Together (Model Adapters).

## Deployment Model
- **Target**: Kubernetes (`k8s/base/`) with HPA and SecurityContext (`runAsNonRoot`).
- **Secrets**: Infisical CLI -> GitHub OIDC -> External Secrets Operator.
- **CI/CD**: GitHub Actions (60+ workflows) for contract compliance, security gates, and SLO evaluation.

---

# Scorecard

| Category | Score | Confidence | Evidence | Main Blockers |
|----------|-------|------------|----------|---------------|
| Architecture | 7 | High | 6-layer pipeline, shared packages, contract-first. | Shim drift, L2.5/L7 undocumented boundaries. |
| Frontend | 6 | High | React 19, strict API client, TanStack Query. | 25% branch coverage, demo data leak. |
| Backend | 5 | High | FastAPI, Pydantic v2, structured errors. | L7 zero auth, L2 conditional auth. |
| Data Model | 7 | High | Postgres RLS,Composite indexes, Alembic. | No Postgres backup, no PII encryption. |
| Security | 5 | High | 130+ security tests, JWT hardening. | L1 SSRF, L3 rate-limit bypass, dev bypass. |
| Multi-Tenancy | 6 | High | Postgres RLS, Neo4j filter, ContextVar. | L7/L4 fallback to "default", L2 no auth. |
| Testing | 6 | High | 128 Playwright E2E, 60+ CI workflows. | Low frontend coverage, skipped contract tests. |
| Observability | 7 | Medium | Prometheus per layer, health probes. | No Sentry, L3 tracing isolated. |
| Performance | 6 | Medium | Manual chunking, bundle budget. | L3 metric cardinality risk, no load tests. |
| Infra/Deploy | 6 | Medium | K8s SecurityContext, Infisical. | ArgoCD not wired, hardcoded base manifests. |

---

# P0 Launch Blockers

### PROD-P0-001: L7 Billing Has Zero Authentication
- **Severity**: P0 | **Category**: Security / Tenant Isolation
- **Description**: `services/layer7-billing/src/layer7_billing/api/main.py` accepts tenant identity purely from `X-Tenant-ID` headers without cryptographic validation.
- **Why it matters**: Complete breakdown of tenant isolation. Any caller can spoof any tenant and read/write billing data, usage events, and invoices.
- **Evidence**: `services/layer7-billing/src/layer7_billing/api/main.py` lines 17-22.
- **Acceptance criteria**:
  - All L7 routes must require a valid JWT via `Depends(require_authenticated)`.
  - `GovernanceMiddleware` must be installed and active.
- **Suggested implementation**: Reuse `value_fabric.shared.fastapi_framework.create_fabric_app` and `require_authenticated` from API gateway.
- **Suggested tests**: `tests/security/test_l7_billing_tenant_isolation.py` covering header spoofing and cross-tenant plan write attempts.
- **Estimated effort**: M | **Dependencies**: None | **Owner**: Backend/Security

### PROD-P0-002: L2 Extraction Auth is Conditional
- **Severity**: P0 | **Category**: Security / Tenant Isolation
- **Description**: `register_fabric_auth_from_env` in L2 is a no-op when env vars are unset. No middleware unconditionally enforces auth.
- **Why it matters**: Documents and extractions could be accessed unauthenticated in misconfigured deployments, leading to IP leakage.
- **Evidence**: `services/layer2-extraction/src/layer2_extraction/api/main.py`.
- **Acceptance criteria**:
  - Unconditionally install `GovernanceMiddleware`.
  - Block application startup if auth keys are missing in production environment mode.
- **Suggested implementation**: Add `GovernanceMiddleware` to L2 app bootstrap; enforce `FABRIC_AUTH_PUBLIC_KEYS` presence.
- **Suggested tests**: `tests/security/test_l2_auth_enforcement.py`.
- **Estimated effort**: M | **Dependencies**: None | **Owner**: Backend/Security

### PROD-P0-003: L1 Callback URL Lacks SSRF Validation
- **Severity**: P0 | **Category**: Security / External Integration
- **Description**: `ExecuteTargetRequest` in L1 accepts `callback_url` as a plain string without safety checks.
- **Why it matters**: An attacker can supply internal metadata endpoints (`169.254.169.254`) or localhost URLs to steal credentials or scan internal network.
- **Evidence**: `services/layer1-ingestion/src/api/main.py`.
- **Acceptance criteria**:
  - `callback_url` is validated with `validate_url_safety()` before storage.
  - Only `https` schemes allowed; internal IP ranges blocked.
- **Suggested implementation**: Use `pydantic.HttpUrl` with custom validator blocking private ranges.
- **Suggested tests**: `tests/security/test_l1_callback_url_ssrf.py` with metadata and localhost payloads.
- **Estimated effort**: S | **Dependencies**: None | **Owner**: Backend/Security

### PROD-P0-004: Frontend Coverage Thresholds Too Low
- **Severity**: P0 | **Category**: Frontend / Quality
- **Description**: `vite.config.ts` coverage thresholds are set to 35% lines / 25% branches.
- **Why it matters**: Far below enterprise standards. Critical paths in auth, tenant selection, and data management can remain untested and regression-prone.
- **Evidence**: `apps/web/vite.config.ts`.
- **Acceptance criteria**: Raise thresholds to ≥70% lines and 60% branches. Block PRs that drop coverage.
- **Suggested implementation**: Incremental raise (40% -> 50% -> 70%) while filling unit test gaps in `src/auth/` and `src/api/`.
- **Estimated effort**: L | **Dependencies**: None | **Owner**: Frontend/QA

### PROD-P0-005: No PostgreSQL Backup Implementation
- **Severity**: P0 | **Category**: Data / Operations
- **Description**: No automated `pg_dump` or base-backup manager exists for the primary transactional DB.
- **Why it matters**: Data loss in Postgres would be catastrophic (all tenant, audit, and billing data). Irreversible without backups.
- **Evidence**: Absence of Postgres backup logic in `services/` and `k8s/` (Neo4j has a `backup_manager.py`, Postgres doesn't).
- **Acceptance criteria**:
  - Automated daily encrypted backups stored in S3.
  - Validated and documented restore runbook.
- **Suggested implementation**: Kubernetes CronJob running `pg_dump` with Fernet encryption.
- **Estimated effort**: L | **Dependencies**: None | **Owner**: Platform/Data

---

# P1 Production Hardening

- **PROD-P1-001: L1→L2 Cross-Layer Call Has No Auth Token**: `services/layer1-ingestion/src/shared/tasks.py` calls L2 with only `X-Tenant-ID`. Needs signed JWT.
- **PROD-P1-002: No Centralized Error Aggregator (Sentry)**: MTTR is too high relying on raw logs. Need automated exception grouping.
- **PROD-P1-003: PII Not Encrypted at Rest**: Sensitive fields in PostgreSQL are plain text. Risk of leak via DB snapshots.
- **PROD-P1-004: Audit DB Writes Are Fire-and-Forget**: `emitter.py` uses `BackgroundTask` without retry. DB blips cause audit loss.
- **PROD-P1-005: L3 Rate Limiter IP Spoofing**: Reliance on `X-Forwarded-For` without proxy validation allows bypass.

---

# P2 Quality and Maintainability

- **PROD-P2-001: Legacy Frontend Routes**: `/workflow/*` and `LegacyDataTable` still exist. Needs deprecation.
- **PROD-P2-002: Missing React StrictMode**: Missing from `src/main.tsx`. Harder to catch side-effect bugs.
- **PROD-P2-003: Windows Artifacts in Root**: CRLF issues and root `C:Users...` folders. Needs `.gitattributes` enforcement.

---

# Sprint Roadmap

## Phase 0: Stabilize (Week 1)
- **Goal**: Clean repo hygiene and close dev bypass.
- **Tickets**: PROD-P0-006 (Auth bypass fix), PROD-P2-003 (Cleanup).

## Phase 1: Security & Tenant Isolation (Weeks 2-4)
- **Goal**: Close all P0 security gaps.
- **Tickets**: PROD-P0-001 (L7 Auth), PROD-P0-002 (L2 Auth), PROD-P0-003 (L1 SSRF), PROD-P1-001 (S2S Auth).

## Phase 2: API & Data Correctness (Weeks 4-5)
- **Goal**: Fix contract drift and implementation gaps.
- **Tickets**: PROD-P1-004 (Audit Retry), PROD-P2-006 (Un-skip contract tests).

## Phase 3: Frontend Production UX (Weeks 5-7)
- **Goal**: Raise quality to production grade.
- **Tickets**: PROD-P0-004 (FE Coverage), PROD-P0-010 (Demo data), PROD-FE-003 (Entitlements).

## Phase 4: Observability & Operations (Weeks 7-8)
- **Goal**: Implement backups and Sentry.
- **Tickets**: PROD-P0-005 (Backups), PROD-P1-002 (Sentry).

---

# Copy/Paste Dev Tickets

## Backend / Platform / Security

### [TICKET-SEC-001] Add Authentication and Rate Limiting to L7 Billing
**Priority**: P0 | **Effort**: M
**Problem**: L7 Billing accepts spoofable `X-Tenant-ID` headers without cryptographic validation.
**Scope**:
1. Add JWT validation and `GovernanceMiddleware` to all L7 routes.
2. Replace `get_principal()` with `require_authenticated`.
**Acceptance Criteria**: All L7 routes return 401/403 without valid JWT. Cross-tenant access is denied.
**Files**: `services/layer7-billing/src/layer7_billing/api/main.py`

### [TICKET-SEC-002] Enforce Unconditional Auth in L2 Extraction
**Priority**: P0 | **Effort**: M
**Problem**: L2 auth is conditional, allowing unauthenticated extraction if env vars are unset.
**Scope**: Force `GovernanceMiddleware` installation; block startup in prod mode without auth keys.
**Files**: `services/layer2-extraction/src/layer2_extraction/api/main.py`

### [TICKET-SEC-003] Validate L1 Callback URL for SSRF
**Priority**: P0 | **Effort**: S
**Scope**: Add `validate_url_safety` to L1 callback URL handling. Block private IP ranges.
**Files**: `services/layer1-ingestion/src/api/main.py`

### [TICKET-SEC-004] Harden L3 Rate Limiter Against IP Spoofing
**Priority**: P0 | **Effort**: S
**Scope**: Use authenticated `tenant_id` as the primary rate-limit key. Validate `X-Forwarded-For`.
**Files**: `services/layer3-knowledge/src/api/rate_limiter.py`

### [TICKET-SEC-005] Fix L4 File Tool Tenant Fallback
**Priority**: P0 | **Effort**: S
**Problem**: returns "default" tenant on missing context.
**Scope**: Raise `MissingTenantContextError` instead of fallback.
**Files**: `services/layer4-agents/src/tools/files.py`

### [TICKET-SEC-006] Add Service-to-Service JWT Signing
**Priority**: P1 | **Effort**: M
**Scope**: Sign L1→L2 internal calls with a shared secret JWT.
**Files**: `services/layer1-ingestion/src/shared/tasks.py`

### [TICKET-SEC-007] Implement PII Encryption at Rest
**Priority**: P1 | **Effort**: L
**Scope**: Use L4 encryption service for sensitive PII columns in Postgres.
**Files**: `services/layer1-ingestion/src/shared/models.py`

### [TICKET-SEC-008] Add Audit Event Retry Queue
**Priority**: P1 | **Effort**: M
**Scope**: Implement Redis-backed retry for `emitter.py` writes.
**Files**: `packages/shared/src/value_fabric/shared/audit/emitter.py`

### [TICKET-SEC-009] Audit Dynamic Cypher Builders
**Priority**: P1 | **Effort**: M
**Scope**: Refactor f-string Cypher queries to parameterized patterns.
**Files**: `services/layer3-knowledge/src/services/roi_calculator_service.py`

### [TICKET-SEC-010] Validate LLM API Keys at Startup
**Priority**: P1 | **Effort**: S
**Scope**: Fail fast if `OPENAI_API_KEY` is a placeholder value.
**Files**: `services/layer2-extraction/src/layer2_extraction/api/main.py`

## Frontend / Product Readiness

### [TICKET-FE-001] Raise Frontend Coverage Thresholds
**Priority**: P0 | **Effort**: L
**Scope**: Set thresholds to 70% in `vite.config.ts`. Fill gaps in `src/auth/`.
**Files**: `apps/web/vite.config.ts`

### [TICKET-FE-002] Gate Demo Data in ProspectPromptBuilder
**Priority**: P0 | **Effort**: S
**Scope**: Move "Medtronic" demo data to dev-only conditional import.
**Files**: `apps/web/src/components/workspace/ProspectPromptBuilder.tsx`

### [TICKET-FE-003] Implement Server-side Entitlement Verification
**Priority**: P1 | **Effort**: M
**Scope**: Replace TODO stubs with actual backend calls to L7.
**Files**: `apps/web/src/hooks/useEntitlements.ts`

### [TICKET-FE-004] Add React StrictMode
**Priority**: P2 | **Effort**: XS
**Files**: `apps/web/src/main.tsx`

### [TICKET-FE-005] Deprecate Legacy Routes
**Priority**: P2 | **Effort**: M
**Files**: `apps/web/src/shell/router.tsx`

### [TICKET-FE-006] Sanitize Chart HTML
**Priority**: P1 | **Effort**: S
**Files**: `apps/web/src/components/ui/chart.tsx`

### [TICKET-FE-007] UUID Match in Mocks
**Priority**: P2 | **Effort**: XS
**Files**: `apps/web/src/test/mockAuth.ts`

### [TICKET-FE-008] Frontend Sentry SDK
**Priority**: P1 | **Effort**: S
**Files**: `apps/web/src/main.tsx`

## Testing / QA

1. **[TICKET-QA-001] API Gateway Coverage**: Priority P1. Effort L. Add unit tests for all gateway middleware.
2. **[TICKET-QA-002] Fix Contract Tests**: Priority P1. Effort M. Resolve and un-skip 7 modules in tests/contract/.
3. **[TICKET-QA-003] L7 Security Suite**: Priority P0. Effort M. Hostile header spoofing tests.
4. **[TICKET-QA-004] L2 Security Suite**: Priority P0. Effort M. Dedicated L2 tenant isolation tests.
5. **[TICKET-QA-005] L1 SSRF Integration Tests**: Priority P0. Effort S. Test callbacks with metadata IPs.
6. **[TICKET-QA-006] Clean Assertions**: Priority P2. Effort XS. Remove placeholder expect statements.

## Infrastructure / DevOps

1. **[TICKET-INFRA-001] Postgres Backup CronJob**: Priority P0. Effort M. Automated daily backups to S3.
2. **[TICKET-INFRA-002] Wire ArgoCD Controller**: Priority P1. Effort L. Full GitOps for base manifests.
3. **[TICKET-INFRA-003] K8s Secret Migration**: Priority P1. Effort M. Use ESO for all credentials.
4. **[TICKET-INFRA-004] Backend Sentry Integration**: Priority P1. Effort M. SDK in all FastAPI layers.
5. **[TICKET-INFRA-005] Sunset Keycloak**: Priority P1. Effort L. Remove legacy auth components.

## Documentation / DX

1. **[TICKET-DOC-001] Frontend DESIGN.md**: Priority P2. Effort S. Document patterns for apps/web/.
2. **[TICKET-DOC-002] Service Boundary Docs**: Priority P1. Effort S. ADRs for emerging services.
3. **[TICKET-DOC-003] Recovery Runbook**: Priority P1. Effort S. Postgres restore procedures.

---

# Launch Gate Checklist

- [ ] **Auth**: All non-public routes require valid JWT. Verified in L7, L2, L4.
- [ ] **RBAC**: Role checks enforced on admin endpoints (e.g., `billing:write`).
- [ ] **Tenant Isolation**: Hostile tenant tests pass (`pytest tests/security -m "tenant_boundary"`).
- [ ] **Backups**: Encrypted Postgres and Neo4j backups exist in S3; restore validated.
- [ ] **Secrets**: No secrets in repo history (`gitleaks`); all infra secrets ESO-managed.
- [ ] **Migrations**: `make check-migration-heads` passes; drift detection green.
- [ ] **Observability**: Sentry receiving exceptions; Prometheus targets all UP.
- [ ] **CI/CD**: `make verify` passing; Frontend coverage ≥70% lines.
- [ ] **E2E Tests**: Golden-path Playwright journey tests pass against live stack.
- [ ] **Legal/Compliance**: GDPR/CCPA checklist completed; Privacy policy published.

---

# Security Review

Value Fabric exhibits a strong security-first culture in its core layers (L1, L3, L4, L5), evidenced by 130+ security-specific tests and a robust JWT hardening implementation in `services/api/app/core/security.py`.

### Detailed Findings:
- **Authentication**: Dual existence of Clerk and legacy paths. `GovernanceMiddleware` is missing from L7 and conditional in L2.
- **SSRF Vector**: `services/layer1-ingestion/src/api/main.py` lacks callback URL validation.
- **Rate Limiting**: Bypassable in L3 via header rotation.
- **Secrets Management**: Infisical is used well, but `ALLOW_INSECURE_DEV_AUTH_BYPASS=true` in committed compose files is a risk.

### Recommendations:
- Harmonize on `GovernanceMiddleware` across all services.
- Implement SSRF validation in L1.
- Complete Clerk rollout and sunset Keycloak.

# Tenant Isolation Review

Tenant isolation is primarily enforced via PostgreSQL Row-Level Security (RLS) and property-level filtering in Neo4j.

### Detailed Findings:
- **Postgres RLS**: `services/layer1-ingestion/src/shared/database.py` correctly sets `SET LOCAL app.tenant_id`.
- **Isolation Breakdowns**:
  - **L7 Billing**: Complete breakdown; spoofable headers.
  - **L4 File Tools**: `services/layer4-agents/src/tools/files.py` fallback to "default" causes path collisions.
- **Neo4j**: Robust filtering by `$tenant_id` in `TenantQueryExecutor`.

### Recommendations:
- Secure L7 Billing boundary immediately.
- Remove "default" fallback from L4 file tools.

# Testing Review

The test suite is extensive (128 E2E Playwright specs, 130+ security tests) but lacks depth in gateway and frontend logic.

### Detailed Findings:
- **Unit/Integration**: API Gateway is under-tested (22 tests for 74 files).
- **Contract Testing**: 7 modules in `tests/contract/` are skipped.
- **Frontend Coverage**: Dangerously low at 35% lines.

### Recommendations:
- Raise frontend coverage to 70%.
- Un-skip and fix contract tests to prevent API drift.

# Infrastructure and Deployment Review

Defined using K8s manifests with clear base/overlay separation.

### Detailed Findings:
- **Hardening**: Pods use `runAsNonRoot`. HPA is configured for all layers.
- **Secrets**: Infisical integration is mature.
- **Backups**: Primary PostgreSQL DB lacks automated backup implementation.

### Recommendations:
- Implement `postgres-backup-cronjob.yaml`.
- Fully wire ArgoCD for GitOps delivery.

# Observability and Operations Review

Good foundations with Prometheus and structured logging (`structlog`).

### Detailed Findings:
- **Logging**: JSON rendering enabled, ISO timestamps.
- **Tracing**: L3 tracer is isolated from standard OTel collectors.
- **Alerting**: No Sentry integration for exception grouping.

### Recommendations:
- Integrate Sentry for all services and frontend.
- Standardize L3 tracing with OTel SDK.

# Frontend UX / Product Readiness Review

Modern React 19 stack with disciplined shadcn/ui and TanStack Query usage.

### Detailed Findings:
- **UX Consistency**: 80+ shadcn/ui primitives.
- **Hidden Risks**: Hardcoded demo data in `ProspectPromptBuilder.tsx`. TODO stubs in entitlements.
- **Accessibility**: Accessibility tests exist but coverage for complex keyboard flows is missing.

### Recommendations:
- Gating demo data behind dev-only flags.
- Implement server-side entitlement checks.

# Documentation and Developer Experience Review

Follows Diataxis framework.

### Detailed Findings:
- **Service Boundaries**: L2.5 and L7 lack architecture ADRs.
- **DX Friction**: Windows artifacts and mixed line endings in root.
- **Governance**: Missing `apps/web/DESIGN.md`.

### Recommendations:
- Write DESIGN.md for frontend governance.
- Document emerging service boundaries.

---

# Recommended Validation Commands

## Local Development & Pre-flight
```bash
# 1. Full Structural Pre-flight
make verify

# 2. Frontend Security & Coverage Gate
pnpm --dir apps/web run test:coverage
pnpm --dir apps/web run test:prod-auth-bypass

# 3. Security Boundary Verification
pytest tests/security -m "tenant_boundary"
pytest tests/security -m "security"

# 4. API Contract Consistency
pnpm run check:contract-compliance
pnpm run check:api-types
```

## CI/CD Pipeline Commands (Mandatory Gates)
```bash
# 1. Secret Scanning
make secret-scan

# 2. Dependency Audit
pnpm audit --audit-level moderate
make pip-audit-all

# 3. Kubernetes Manifest Validation
kubectl apply --dry-run=client -f k8s/base/
make k8s-validate

# 4. SLO Evaluation
python scripts/perf/evaluate_slo.py
```

---

# Final Recommendation

**PAUSE FOR REMEDIATION.**

Value Fabric is a high-quality platform but is currently **Not Ready** for production. The authentication gaps in Layer 7 and Layer 2 represent a critical risk to tenant isolation.

**Execute Phase 1 of the roadmap immediately**, focusing on securing the L7/L2 boundaries and implementing PostgreSQL backups. Once P0s are resolved, the platform will be ready for a **Controlled Beta**.
