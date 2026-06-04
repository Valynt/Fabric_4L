# Value Fabric — Production Launch Readiness Audit

**Audit Date:** 2026-05-27  
**Auditor:** Principal Software Architect / Enterprise SaaS Production-Readiness Review  
**Repository:** `C:\Users\BBB\Fabric_4L`  
**Target Bar:** Production-ready enterprise SaaS for security-conscious customers  

---

# Executive Summary

## Overall Production Readiness Score: **5.8 / 10**

**Status: NOT READY for general production. Controlled beta possible after P0 remediation.**

Value Fabric is a sophisticated six-layer agentic SaaS platform with strong architectural foundations, mature tenant-isolation patterns, comprehensive security test coverage, and well-governed CI/CD. However, **critical security gaps in Layer 7 Billing and Layer 2 Extraction, an unprotected SSRF vector in Layer 1, weak frontend coverage thresholds, and incomplete infrastructure wiring** prevent a production launch today. The platform demonstrates senior-level engineering in L1/L3/L4/L5/L6 but has **two weak links (L2, L7) that break the security perimeter** and create cross-tenant data exposure risks.

## Top 10 Risks

1. **L7 Billing has zero authentication** — any caller can spoof `X-Tenant-ID` and read/write billing data, usage events, and invoices for any tenant.
2. **L2 Extraction auth is conditional/no-op** — `register_fabric_auth_from_env` is a no-op when env vars are unset; no `GovernanceMiddleware` enforces auth.
3. **L1 `callback_url` lacks SSRF validation** — attackers can supply internal metadata endpoints or localhost URLs.
4. **L3 rate limiter trusts `X-Forwarded-For`** without proxy validation, allowing infinite client-key rotation.
4. **L4 file tools fall back to `"default"` tenant** — background jobs without context collide files across tenants.
5. **Frontend coverage thresholds at 25% branches / 35% lines** — far below production-grade standards.
6. **Hardcoded demo data (`Medtronic`) in `ProspectPromptBuilder`** — could leak to production UI.
7. **Dev auth bypass (`ALLOW_INSECURE_DEV_AUTH_BYPASS`) present in committed compose files** — production-gate risk if env detection fails.
8. **No PostgreSQL backup implementation** — only Neo4j (L3) has a backup manager; primary transactional DB is unprotected.
9. **No centralized error aggregator (Sentry)** — errors rely on logs and metrics only; no automated grouping or alerting.
10. **Dual auth system (Clerk + Keycloak + legacy JWT) in transition** — increases misconfiguration drift and attack surface.

## Top 10 Recommended Actions

1. Add JWT validation + `GovernanceMiddleware` + `RateLimitMiddleware` to L7 Billing immediately.
2. Enforce unconditional `GovernanceMiddleware` in L2 Extraction; block startup without auth keys in production.
3. Add SSRF validation to L1 `callback_url` before storing or dispatching.
4. Harden L3 rate limiter to use authenticated identity instead of `X-Forwarded-For`.
5. Raise frontend coverage thresholds to ≥60% branches / ≥70% lines and fill gaps.
6. Implement PostgreSQL pg_dump/base-backup manager and document runbook.
7. Integrate Sentry (or equivalent) for exception grouping and production alerting.
8. Gate or remove hardcoded demo data from `ProspectPromptBuilder.tsx`.
9. Add service-to-service JWT signing for L1→L2 Celery calls.
10. Complete Clerk auth rollout and deprecate Keycloak/legacy JWT paths with a sunset date.

## Estimated Launch Readiness Status

**Not ready** for general production launch. After P0 remediation (estimated 2–3 sprints), the platform could enter a **controlled beta** with security-conscious early adopters. Full production readiness requires P0 + P1 hardening (estimated 4–6 sprints total).

---

# System Map

## Repo Structure

```
Fabric_4L/
├── apps/web/                    # Frontend (React 19, Vite, TanStack Query, Zustand, Clerk)
├── services/
│   ├── api/                     # API Gateway (Clerk JWT, tenant context, RBAC)
│   ├── layer1-ingestion/        # L1: Playwright crawling, Celery, Redis (port 8001)
│   ├── layer2-extraction/       # L2: LLM extraction, Pydantic v2, RDF/OWL (port 8002)
│   ├── layer2-5-signal-refinery/# L2.5: Signal refinement (port 8007) — NOT in canonical 6-layer
│   ├── layer3-knowledge/        # L3: Neo4j, GraphRAG, pgvector (port 8003)
│   ├── layer4-agents/           # L4: LangGraph workflows, ROI calculator (port 8004)
│   ├── layer5-ground-truth/     # L5: TruthObject validation, maturity ladder (port 8005)
│   ├── layer6-benchmarks/       # L6: Peer comparison, statistical validation (port 8006)
│   └── layer7-billing/          # L7: Billing domain — emerging, minimal implementation
├── value_fabric/                # Namespace shim packages (ADR-027; removal by 2026-09-30)
├── packages/
│   ├── shared/                  # Shared Python library (tenant context, base models, error handling)
│   └── platform-contract/       # Cross-layer contract definitions and test harness
├── contracts/
│   ├── openapi/                 # Per-layer OpenAPI specs (source of truth)
│   └── jsonschema/              # JSON Schemas for agent responses, signals, entities
├── tests/
│   ├── contract/                # Cross-layer contract and architecture tests
│   ├── security/                # OWASP / tenant-boundary security tests (130+ files)
│   └── backend_integrated/      # Full-stack integration tests (requires live services)
├── k8s/                         # Kubernetes manifests (base + overlays)
├── monitoring/                  # Prometheus, Alertmanager, Grafana configs
├── docs/                        # Diataxis docs (tutorials, how-to, reference, explanations)
└── scripts/ci/                  # CI gate scripts
```

## Services/Apps

| Layer | Service | Port | Framework | Auth Middleware |
|-------|---------|------|-----------|-----------------|
| Frontend | `apps/web/` | 3001 | React 19 + Vite | Clerk React |
| L1 | `services/layer1-ingestion/` | 8001 | FastAPI + Celery | `GovernanceMiddleware` + `SecurityMiddleware` |
| L2 | `services/layer2-extraction/` | 8002 | FastAPI | `register_fabric_auth_from_env` (no-op if unset) |
| L2.5 | `services/layer2-5-signal-refinery/` | 8007 | FastAPI | Unknown |
| L3 | `services/layer3-knowledge/` | 8003 | FastAPI | `GovernanceMiddleware` + `SecurityMiddleware` + `RateLimitMiddleware` |
| L4 | `services/layer4-agents/` | 8004 | FastAPI + LangGraph | `GovernanceMiddleware` + `SecurityMiddleware` + `tenant_settings_resolver` |
| L5 | `services/layer5-ground-truth/` | 8005 | FastAPI | `GovernanceMiddleware` + `SecurityMiddleware` |
| L6 | `services/layer6-benchmarks/` | 8006 | FastAPI | `GovernanceMiddleware` + `SecurityMiddleware` |
| L7 | `services/layer7-billing/` | — | FastAPI | **None** — header-based only |
| API Gateway | `services/api/` | — | FastAPI | `AuditMiddleware` + JWT `require_authenticated` |

## Key Runtime Dependencies

- **Node.js ≥22.12.0**, pnpm 10.18.1
- **Python 3.11+**, FastAPI, SQLAlchemy, Alembic, Pydantic v2, Celery
- **LangGraph** (L4 agent orchestration)
- **LLM Providers:** OpenAI, Anthropic, Together (adapter pattern)
- **PostgreSQL** (primary transactional DB, multi-tenant via RLS)
- **Redis** (Celery broker, cache, pub/sub, rate limiting)
- **Neo4j Community v5 + APOC** (knowledge graph)
- **MinIO** (S3-compatible object storage for crawled content)
- **Keycloak** (legacy OIDC/SAML broker, port 8080)
- **Clerk** (primary B2B auth, org-based multi-tenancy)

## Key Data Stores

| Store | Purpose | Tenant Isolation |
|-------|---------|------------------|
| PostgreSQL (multiple DBs) | Primary transactional data | Shared schema + RLS (`SET LOCAL app.tenant_id`) |
| Redis | Cache, queues, sessions, checkpoints | Key prefixing |
| Neo4j | Knowledge graph, entity relationships | Property-level `$tenant_id` filtering |
| MinIO | Raw crawled HTML, screenshots | Bucket/path prefixing |
| PostgreSQL (Audit) | Append-only audit events | Tenant-scoped |

## Main User Flows

1. **Authentication & Onboarding:** Sign In → Select Organization (`/workspaces`) → Onboarding
2. **Account Workspaces (`/t/:tenantSlug/accounts/:accountId/*`):**
   - Intelligence: Signals, drivers, enrichment, evidence, ROI
   - Value Studio: Action plans, narratives, competitive analysis
   - Deliverables: Business cases, CFO/Executive/Technical views
3. **Context Engine (`/t/:tenantSlug/context/*`):** Data sources, ontology editor, graph explorer, agent workflows
4. **Governance (`/t/:tenantSlug/governance/*`):** Decision traces, provenance, compliance, audit log
5. **Settings:** Personal profile, tenant billing, team members/roles, API keys

## Main API Flows

```
Frontend (3001)
  ↓ REST / WebSocket / SSE (Bearer token via Clerk)
API Gateway / L4 (8004)  ← orchestration hub
  ↓ REST (service-to-service JWT or internal envelope)
L1 (8001) — L2 (8002) — L3 (8003) — L5 (8005) — L6 (8006)
  ↓
L2.5 Signal Refinery (8007)
```

## Deployment Model

- **Local Dev:** Docker Compose (`docker-compose.dev.yml`) with hot-reload, auth bypass, Vite frontend
- **Production-like Local:** Docker Compose (`docker-compose.yml`) with all L1–L6 services
- **Production Target:** Kubernetes (`k8s/base/`) with HPA, SecurityContext, External Secrets Operator
- **Secret Management:** Infisical CLI (local) → GitHub OIDC → Infisical machine identity (CI) → Infisical K8s Operator (prod)

---

# Scorecard

| Category | Score | Confidence | Evidence | Main Blockers | Recommended Next Action |
|----------|-------|------------|----------|---------------|------------------------|
| **Architecture** | 7 | High | 6-layer pipeline, contract-first OpenAPI, canonical paths, shared packages | L2.5 undocumented, L7 emerging without ADR, shim drift risk | Document L2.5 boundary or merge into L2/L3; sunset shim packages by 2026-09-30 |
| **Frontend** | 6 | High | Strong auth security, disciplined API client, shadcn/ui, 128 E2E + 162 unit tests | 25% branch coverage, hardcoded demo data, missing StrictMode, TODO stubs | Raise coverage to 60% branches; gate demo data; implement account/entitlement verification |
| **Backend** | 5 | High | FastAPI + Pydantic v2, structured errors, JWT hardening, webhook HMAC | L7 has zero auth; L2 auth is conditional; L1 SSRF vector; L3 IP spoofing risk | Add auth to L7; enforce GovernanceMiddleware in L2; validate callback_url |
| **Data Model & Migrations** | 7 | High | RLS policies, Alembic per-service, composite tenant indexes, append-only audit triggers | No PII column encryption; no automated retention purging; no PostgreSQL backup | Wire L4 encryption service to PII columns; implement retention jobs; build pg_backup manager |
| **Security** | 5 | High | 130+ security tests, Cypher injection guard, JWT revocation denylist, bcrypt policies | L7 header spoofing, L2 no-op auth, L1 SSRF, L3 rate-limit bypass, dev bypass in compose | Fix L7/L2 auth; SSRF validation; harden rate limiter; remove bypass from committed compose |
| **Multi-Tenancy** | 6 | High | Postgres RLS, Neo4j `$tenant_id` filtering, tenant-scoped repositories, ContextVar propagation | L7 no tenant verification; L2 no auth means no tenant context; L4 "default" fallback | Add tenant verification to L7; enforce auth in L2; raise on missing L4 context |
| **Testing** | 6 | High | 130+ security tests, contract tests, Playwright E2E, chaos tests, OWASP coverage | API Gateway under-tested (22 tests for 74 src files); 7 skipped contract tests; low frontend coverage | Add API Gateway tests; un-skip contract tests; raise frontend thresholds |
| **Observability** | 7 | Medium | Prometheus per layer, structured logging, health/ready probes, alert rules, SLO docs | No Sentry; L3 tracing isolated; audit DB best-effort; no log retention policy | Integrate Sentry; unify L3 OTel; retry queue for audit events |
| **Performance** | 6 | Medium | Manual chunking, bundle budget, cardinality-safe metrics, request deduplication | L3 metrics lack path normalization; no load-test evidence; no DB query-plan review | Strip UUIDs from metric paths; run load tests; review expensive queries |
| **Infrastructure/Deployment** | 6 | Medium | K8s SecurityContext, HPA, Infisical secret mgmt, 40+ runbooks | ArgoCD not wired; placeholder kubeconfig; hardcoded creds in base K8s manifests | Wire ArgoCD; replace placeholder secrets with External Secrets Operator |
| **CI/CD** | 7 | High | 60+ workflows, contract compliance, security gates, SLO evaluation script, build-deploy | Some workflows may not enforce all gates; burn-rate CI gating unverified | Verify all P0 gates run in `pr-checks.yml`; enforce SLO evaluation in CI |
| **Developer Experience** | 7 | High | pnpm-only, Makefile targets, Infisical CLI, pre-commit hooks, comprehensive docs | Windows artifacts in root, CRLF warnings, missing DESIGN.md at apps/web/ | Run `make clean-root-debris`; add `.gitattributes` enforcement; write DESIGN.md |
| **Documentation** | 7 | High | Diataxis structure, ADRs, runbooks, SLOs, contract docs, security model | Some runbooks are internal placeholders; L2.5 undocumented; L7 undocumented | Replace placeholder runbook links; document L2.5 and L7 boundaries |
| **Product Completeness** | 6 | Medium | Full 6-layer pipeline, ROI calculator, business case generation, GraphRAG, benchmarking | L7 billing minimal; TODO stubs in frontend entitlements; legacy routes unmaintained | Implement L7 to contract spec; remove or deprecate legacy frontend routes |
| **Production Readiness Overall** | **5.8** | **Medium** | Strong foundations with critical security gaps | L7 auth, L2 auth, L1 SSRF, frontend coverage, PostgreSQL backup | Execute Phase 1 (security) + Phase 2 (API/data) + Phase 3 (frontend) of roadmap |

---

# P0 Launch Blockers

## PROD-P0-001: L7 Billing Has Zero Authentication
- **Severity:** P0
- **Category:** Security / Tenant Isolation
- **Description:** `services/layer7-billing/src/layer7_billing/api/main.py` accepts tenant identity purely from `X-Tenant-ID`, `X-Actor`, and `X-Roles` headers with zero cryptographic validation. Any HTTP client can spoof any tenant and escalate to `billing:write`.
- **Why it matters:** Complete breakdown of tenant isolation for billing data, usage events, invoices, and payment state. A malicious tenant can read/write another tenant's financial data.
- **Evidence:** `services/layer7-billing/src/layer7_billing/api/main.py` lines 17–22; `services/layer7-billing/src/layer7_billing/storage/store.py` returns store for any `tenant_id` without verification.
- **Acceptance criteria:**
  1. Add `GovernanceMiddleware` to L7 FastAPI app.
  2. Validate JWT or HMAC-signed headers before accepting tenant identity.
  3. Add `RateLimitMiddleware`.
  4. All L7 routes require authenticated principal.
  5. Security tests cover cross-tenant billing access denial.
- **Suggested implementation:** Reuse `value_fabric.shared.fastapi_framework.create_fabric_app` and `require_authenticated` from API gateway.
- **Suggested tests:** `tests/security/test_l7_billing_tenant_isolation.py` — hostile header spoofing, missing JWT, cross-tenant plan read/write.
- **Estimated effort:** M
- **Dependencies:** None
- **Owner:** Backend / Security

## PROD-P0-002: L2 Extraction Auth Is Conditional / No-Op
- **Severity:** P0
- **Category:** Security / Tenant Isolation
- **Description:** `services/layer2-extraction/src/layer2_extraction/api/main.py` uses `register_fabric_auth_from_env` which is a no-op when `FABRIC_AUTH_PUBLIC_KEYS` is unset. No `GovernanceMiddleware` is installed. Routes may run unauthenticated in misconfigured deployments.
- **Why it matters:** L2 processes sensitive documents and runs LLM extraction. Unauthenticated access allows arbitrary document ingestion and extraction for any tenant.
- **Evidence:** `services/layer2-extraction/src/layer2_extraction/api/main.py` lines 45–60; no `GovernanceMiddleware` in route handlers.
- **Acceptance criteria:**
  1. L2 unconditionally installs `GovernanceMiddleware`.
  2. Startup fails in production-like environments without auth configuration.
  3. All routes require authenticated principal.
- **Suggested implementation:** Add `GovernanceMiddleware` to L2 app bootstrap; enforce `FABRIC_AUTH_PUBLIC_KEYS` or `CLERK_JWT_PUBLIC_KEY` presence in production.
- **Suggested tests:** `tests/security/test_l2_auth_enforcement.py` — missing auth header, invalid JWT, expired token, cross-tenant extraction.
- **Estimated effort:** M
- **Dependencies:** None
- **Owner:** Backend / Security

## PROD-P0-003: L1 Callback URL Lacks SSRF Validation
- **Severity:** P0
- **Category:** Security / External Integration
- **Description:** `ExecuteTargetRequest` in L1 accepts `callback_url: str | None` with no SSRF validation. An attacker can supply `http://169.254.169.254/latest/meta-data/` or `http://localhost:8001/internal/…`.
- **Why it matters:** SSRF allows attackers to access internal cloud metadata APIs, internal services, or localhost endpoints, potentially leading to credential theft or lateral movement.
- **Evidence:** `services/layer1-ingestion/src/api/main.py` lines 654–655; schema defines `callback_url` as plain `str`.
- **Acceptance criteria:**
  1. `callback_url` is validated with `validate_url_safety()` before storing or dispatching.
  2. Block internal IP ranges, metadata endpoints, and localhost.
  3. Only allow `http`/`https` schemes.
- **Suggested implementation:** Add `pydantic.HttpUrl` with custom validator; block private IP ranges; enforce allowlist if needed.
- **Suggested tests:** `tests/security/test_l1_callback_url_ssrf.py` — metadata endpoint, localhost, file://, internal DNS.
- **Estimated effort:** S
- **Dependencies:** None
- **Owner:** Backend / Security

## PROD-P0-004: L7 Billing Has No Rate Limiting
- **Severity:** P0
- **Category:** Security / Reliability
- **Description:** L7 Billing has no `RateLimitMiddleware`, no `GovernanceMiddleware`, and no Redis rate limiter. Unauthenticated requests can hit all endpoints without throttling.
- **Why it matters:** Billing endpoints (usage event ingestion, plan updates) are high-value targets for abuse. Without rate limiting, an attacker can flood usage events, distort billing calculations, or cause denial of service.
- **Evidence:** `services/layer7-billing/src/layer7_billing/api/main.py` — no middleware stack beyond FastAPI defaults.
- **Acceptance criteria:**
  1. `RateLimitMiddleware` installed on all L7 routes.
  2. Per-tenant rate limits for usage event ingestion.
  3. Global rate limit for plan/entitlement reads.
- **Suggested implementation:** Reuse `value_fabric.shared.identity.rate_limiter` or Redis-based sliding window.
- **Suggested tests:** `tests/security/test_l7_rate_limiting.py` — burst abuse, per-tenant isolation, header rotation bypass.
- **Estimated effort:** S
- **Dependencies:** PROD-P0-001
- **Owner:** Backend / Platform

## PROD-P0-005: L3 Rate Limiter Trusts X-Forwarded-For Without Proxy Validation
- **Severity:** P0
- **Category:** Security / Rate Limiting
- **Description:** `services/layer3-knowledge/src/api/rate_limiter.py:56-65` uses `X-Forwarded-For` first, then `X-Real-IP`. If not behind a trusted load balancer that strips these headers, attackers can rotate client keys infinitely.
- **Why it matters:** Complete bypass of rate limiting for all L3 endpoints, enabling brute-force, scraping, and resource exhaustion.
- **Evidence:** `services/layer3-knowledge/src/api/rate_limiter.py` lines 56–65.
- **Acceptance criteria:**
  1. Prefer authenticated identity (`ctx.tenant_id` or `ctx.user_id`) for rate-limit keys.
  2. If IP-based limiting is required, validate `X-Forwarded-For` against a trusted proxy list.
  3. Fallback to connection IP when behind unknown proxies.
- **Suggested implementation:** Use `TenantContext` or JWT `sub` claim as primary rate-limit key; add `TRUSTED_PROXIES` env var.
- **Suggested tests:** `tests/security/test_l3_rate_limit_ip_spoofing.py` — header rotation, bypass attempt, trusted proxy validation.
- **Estimated effort:** S
- **Dependencies:** None
- **Owner:** Backend / Security

## PROD-P0-006: Dev Auth Bypass in Committed Compose Files
- **Severity:** P0
- **Category:** Security / Configuration
- **Description:** `ALLOW_INSECURE_DEV_AUTH_BYPASS=true` is set in committed `docker-compose.dev.yml` and `docker-compose.yml`. While `reject_insecure_bypass_in_production()` is called at startup, environment-detection bugs or mis-set `ENVIRONMENT` vars could open bypass in prod.
- **Why it matters:** A single misconfigured environment variable allows complete auth bypass in production.
- **Evidence:** `docker-compose.dev.yml` line 242; `docker-compose.yml` (live stack); `services/layer4-agents/src/api/main.py` line 9.
- **Acceptance criteria:**
  1. Remove `ALLOW_INSECURE_DEV_AUTH_BYPASS` from all committed compose files.
  2. Require explicit local-only override file (e.g., `docker-compose.override.yml` gitignored) for bypass.
  3. Add CI check that fails if bypass env var is present in any committed config.
- **Suggested implementation:** Move bypass to `.env.dev` (already gitignored) and reference from override compose; add `grep -r ALLOW_INSECURE_DEV_AUTH_BYPASS` to CI preflight.
- **Suggested tests:** `tests/security/test_dev_bypass_production_block.py` — verify startup fails in prod mode with bypass enabled.
- **Estimated effort:** S
- **Dependencies:** None
- **Owner:** Platform / Security

## PROD-P0-007: Frontend Coverage Thresholds Too Low for Production
- **Severity:** P0
- **Category:** Frontend / Quality
- **Description:** `vite.config.ts` coverage thresholds are 35% lines/functions/statements and 25% branches. This is far below industry production-grade standards and permits significant untested critical paths.
- **Why it matters:** Low coverage allows bugs in auth flows, tenant scoping, data mutations, and error handling to reach production undetected.
- **Evidence:** `apps/web/vite.config.ts` coverage configuration.
- **Acceptance criteria:**
  1. Raise thresholds to ≥70% lines, ≥60% branches.
  2. Achieve thresholds across all critical paths (auth, API client, routing, state management).
  3. Add coverage gate to CI that blocks PRs below threshold.
- **Suggested implementation:** Incremental raises per sprint (40% → 50% → 60% → 70%); focus on `src/auth/`, `src/api/`, `src/hooks/`, `src/stores/`.
- **Suggested tests:** Fill unit test gaps in `useFabricQuery`, `useFabricMutation`, `accountContextStore`, `ClerkAuthBridge`.
- **Estimated effort:** L
- **Dependencies:** None
- **Owner:** Frontend / QA

## PROD-P0-008: PostgreSQL Backup/Restore Foundation Added; Operational PITR Drill Still Required
- **Severity:** P0 until a production/staging PITR drill is executed and retained as launch evidence
- **Category:** Data / Operations
- **Description:** PostgreSQL now has repository-level logical backup/restore support and a Docker-backed drill gate. Production still requires provider-native physical/PITR configuration evidence and a dated staging or production-like restore drill before this item can be closed.
- **Why it matters:** PostgreSQL contains all tenant data, audit events, billing records, and agent state. Data loss would be catastrophic and irreversible.
- **Implementation evidence:** `scripts/ops/postgres_backup.py` supports `pg_dump` logical backup, Fernet encryption, local/S3/GCS storage, retention, and `psql` restore; `scripts/ops/test_postgres_backup_restore.sh` seeds tenant data, backs it up, restores to an isolated PostgreSQL instance, and compares SHA-256 plus per-tenant checksums; `docs/troubleshooting/runbooks/infrastructure/postgres-backup-restore.md` documents logical restore and managed PostgreSQL PITR/physical-backup strategy; `make gate-database-live` wires the drill into the Makefile.
- **Remaining launch evidence:** Run `make gate-database-live` in a Docker-enabled CI/staging environment and retain `artifacts/postgres-backup-restore/evidence.json`, `backup-artifact.sha256`, `source-checksums.txt`, and `restored-checksums.txt`; separately attach managed PostgreSQL continuous-backup/PITR configuration and quarterly restore-drill evidence.
- **Acceptance criteria:**
  1. [x] Implement pg_dump logical backup manager with encryption and local/S3/GCS storage backends.
  2. [x] Create PostgreSQL-specific runbook with RTO/RPO targets, restore procedures, validation steps, and managed physical/PITR strategy.
  3. [x] Add scheduled backup job or external scheduler evidence (`k8s/base/postgres-backup-cronjob.yaml`).
  4. [x] Add executable logical backup/restore drill gate (`make gate-database-live`).
  5. [ ] Execute and archive quarterly managed PostgreSQL PITR restore evidence.
- **Estimated effort remaining:** M
- **Dependencies:** Docker-enabled CI/staging runner; managed PostgreSQL provider configuration
- **Owner:** Platform / Data

## PROD-P0-009: L4 File Tools Fall Back to "default" Tenant
- **Severity:** P0
- **Category:** Security / Tenant Isolation
- **Description:** `services/layer4-agents/src/tools/files.py:18-26` returns `"default"` when `RequestContext` is missing (background tasks / tests). Files from different tenants could collide under `/var/lib/services/tenant-files/default`.
- **Why it matters:** Cross-tenant file collision leads to data leakage and corruption in agent file operations.
- **Evidence:** `services/layer4-agents/src/tools/files.py` lines 18–26.
- **Acceptance criteria:**
  1. Raise an exception instead of returning `"default"` when tenant context is missing.
  2. Background jobs must explicitly pass tenant_id; no silent fallback.
  3. File paths must always include validated tenant_id.
- **Suggested implementation:** Change `_get_tenant_id()` to raise `TenantContextMissingError`; update all background job callers to propagate tenant_id.
- **Suggested tests:** `tests/security/test_l4_file_tool_tenant_fallback.py` — missing context raises error, correct tenant isolation.
- **Estimated effort:** S
- **Dependencies:** None
- **Owner:** Backend / Security

## PROD-P0-010: Hardcoded Demo Data in Production Component
- **Severity:** P0
- **Category:** Frontend / Product
- **Description:** `src/components/workspace/ProspectPromptBuilder.tsx` contains hardcoded "Medtronic" prospect prompt with full stakeholder mapping. This demo data could leak to production UI.
- **Why it matters:** Exposes internal demo content to production users, creating confusion and potential IP leakage.
- **Evidence:** `apps/web/src/components/workspace/ProspectPromptBuilder.tsx`.
- **Acceptance criteria:**
  1. Gate demo data behind `import.meta.env.DEV` or remove entirely.
  2. Add CI check that blocks hardcoded customer names in production components.
  3. Use fixture/mock data for demos, never inline in components.
- **Suggested implementation:** Move demo content to `src/test/fixtures/demo-prospects.ts`; conditionally import in dev only.
- **Suggested tests:** `scripts/security/assert-no-demo-data-in-production.mjs` — scan for known customer names in `src/components/`.
- **Estimated effort:** S
- **Dependencies:** None
- **Owner:** Frontend / Product

---

# P1 Production Hardening

## PROD-P1-001: L1→L2 Cross-Layer Call Has No Auth Token
- **Severity:** P1
- **Category:** Security / Service-to-Service
- **Description:** `services/layer1-ingestion/src/shared/tasks.py:788-799` calls L2 via `httpx.AsyncClient` with only `X-Tenant-ID` header. If L2 is reachable directly, this header can be spoofed.
- **Evidence:** `services/layer1-ingestion/src/shared/tasks.py` lines 788–799.
- **Acceptance criteria:** Sign outbound request with internal JWT or mTLS; L2 validates signature.
- **Estimated effort:** M
- **Owner:** Backend / Security

## PROD-P1-002: L3 Metrics Middleware Lacks Path Normalization
- **Severity:** P1
- **Category:** Performance / Observability
- **Description:** L3 metrics middleware does not strip UUIDs/numeric IDs from endpoint labels, risking cardinality explosion.
- **Evidence:** `services/layer3-knowledge/src/metrics/prometheus_metrics.py` lines 670–741.
- **Acceptance criteria:** Normalize paths before creating metric labels; cap label cardinality.
- **Estimated effort:** S
- **Owner:** Backend / Platform

## PROD-P1-003: No Centralized Error Aggregator (Sentry)
- **Severity:** P1
- **Category:** Observability / Operations
- **Description:** No Sentry or equivalent found. Errors rely on Prometheus counters and structured logs only.
- **Evidence:** No Sentry references in codebase; `docs/ERROR_MONITORING.md` references Prometheus only.
- **Acceptance criteria:** Integrate Sentry for exception grouping, deduplication, and alerting; configure per-layer DSNs.
- **Estimated effort:** M
- **Owner:** Platform / Observability

## PROD-P1-004: PII Not Encrypted at Rest
- **Severity:** P1
- **Category:** Security / Data
- **Description:** No column-level encryption for PII fields (email, name in billing_customers or tenants). L4 encryption service exists but is not wired into models.
- **Evidence:** `services/layer4-agents/src/services/encryption_service.py` exists but unused in models; `services/layer1-ingestion/src/compliance/pii_scanner.py` detects but does not encrypt.
- **Acceptance criteria:** Encrypt PII columns at rest using pgcrypto or L4 encryption service; key rotation mechanism documented.
- **Estimated effort:** L
- **Owner:** Backend / Security / Data

## PROD-P1-005: Audit DB Writes Are Fire-and-Forget
- **Severity:** P1
- **Category:** Security / Observability
- **Description:** Audit events use FastAPI `BackgroundTask` for DB persistence. Failures are logged but not retried, creating audit loss windows.
- **Evidence:** `packages/shared/src/value_fabric/shared/audit/emitter.py` lines 152–224.
- **Acceptance criteria:** Add Redis-backed retry queue for audit events; alert on persistent audit sink failures.
- **Estimated effort:** M
- **Owner:** Backend / Platform

## PROD-P1-006: Dynamic Cypher WHERE Clause Builders Are Fragile
- **Severity:** P1
- **Category:** Security / Data
- **Description:** `roi_calculator_service.py`, `competitive_intel_service.py`, and `case_study_service.py` build `where_clauses` via f-string interpolation. Current code uses parameterized placeholders, but the pattern is fragile.
- **Evidence:** `services/layer3-knowledge/src/services/roi_calculator_service.py:498-504`, `competitive_intel_service.py:291`, `case_study_service.py:424`.
- **Acceptance criteria:** Add runtime `validate_tenant_scoped_cypher` calls before executing; refactor to query builder pattern.
- **Estimated effort:** M
- **Owner:** Backend / Security

## PROD-P1-007: No Automated Data Retention Purging
- **Severity:** P1
- **Category:** Data / Compliance
- **Description:** Retention fields exist (`retention_raw_content_expiry_days`, `retention_screenshot_expiry_days`) but no scheduled job purges expired data.
- **Evidence:** `services/layer1-ingestion/src/shared/models.py` lines 572–573.
- **Acceptance criteria:** Implement Celery job to purge expired raw content, screenshots, and soft-deleted tenants.
- **Estimated effort:** M
- **Owner:** Backend / Data

## PROD-P1-008: Frontend TODO Stubs for Account Access and Entitlements
- **Severity:** P1
- **Category:** Frontend / Security
- **Description:** `useAccountAccess.ts` and `useEntitlements.ts` are stubs with TODO comments. Route guards rely on client-side tier store only.
- **Evidence:** `apps/web/src/hooks/useAccountAccess.ts:8`, `useEntitlements.ts:7`.
- **Acceptance criteria:** Implement backend verification for account access and entitlements; fail closed on network errors.
- **Estimated effort:** M
- **Owner:** Frontend / Backend

## PROD-P1-009: L2 Extractor Loads OpenAI Key from Env Without Validation
- **Severity:** P1
- **Category:** Security / Secrets
- **Description:** `os.getenv("OPENAI_API_KEY")` is read at runtime with no check for placeholder values. All tenants share the same provider key.
- **Evidence:** `services/layer2-extraction/src/layer2_extraction/api/main.py:172-184`.
- **Acceptance criteria:** Validate key format and reject placeholders; support per-tenant key vault paths.
- **Estimated effort:** S
- **Owner:** Backend / Security

## PROD-P1-010: L5 `jwt_fallback_to_query_param` Flag Exists
- **Severity:** P1
- **Category:** Security / Auth
- **Description:** If enabled, JWTs can be passed in query strings (logged by proxies/CDNs). Flag exists in codebase.
- **Evidence:** Inherited pattern in L5/L6 settings.
- **Acceptance criteria:** Remove the flag entirely; block JWT in query strings at middleware level.
- **Estimated effort:** S
- **Owner:** Backend / Security

---

# P2 Quality and Maintainability

## PROD-P2-001: Legacy Frontend Routes and Components
- **Description:** `/workflow/*` and `/value-pilot/*` routes still mounted; `LegacyDataTable` and `LegacyTabs` exist.
- **Evidence:** `src/shell/router.tsx:242-327`, `src/components/ui/fabric/LegacyDataTable.tsx`, `LegacyTabs.tsx`.
- **Suggested action:** Deprecate with feature flags or redirects; remove after migration confirmed.

## PROD-P2-002: Missing React StrictMode
- **Description:** `src/main.tsx` does not wrap app in `StrictMode`.
- **Evidence:** `src/main.tsx`.
- **Suggested action:** Add `StrictMode` wrapper.

## PROD-P2-003: Console.warn in Non-Dev Paths
- **Description:** `HorizontalTabWrapper` and `sessionService` emit console warnings that bypass telemetry dev-guard.
- **Evidence:** `src/components/blocks/HorizontalTabWrapper.tsx`, `src/services/sessionService.ts`.
- **Suggested action:** Route warnings through telemetry system or remove.

## PROD-P2-004: Missing DESIGN.md at apps/web/
- **Description:** AGENTS.md requires reading DESIGN.md before modifying apps/web/, but the file does not exist.
- **Evidence:** `apps/web/DESIGN.md` (missing).
- **Suggested action:** Write DESIGN.md or update AGENTS.md reference.

## PROD-P2-005: API Gateway Under-Tested
- **Description:** 22 tests for 74 source files in API Gateway.
- **Evidence:** `services/api/app/tests/`.
- **Suggested action:** Add unit tests for auth, tenant context, RBAC, webhook handlers.

## PROD-P2-006: Seven Skipped Contract Test Modules
- **Description:** `test_entity_contract.py`, `test_l3_route_alias_parity.py`, `test_system_route_contract.py`, and 4 others are entirely skipped.
- **Evidence:** `tests/contract/`.
- **Suggested action:** Un-skip or fix; add CI gate that blocks new skipped contract tests.

## PROD-P2-007: value_fabric Runtime Package Tests Minimal
- **Description:** Only 2 smoke tests for 15 source files in canonical runtime packages.
- **Evidence:** `value_fabric/` test files.
- **Suggested action:** Add unit tests for shared error handling, audit, logging, trace context.

## PROD-P2-008: L3 Tracing Interoperability Gap
- **Description:** L3 uses custom tracer that does not interoperate with standard OTel collectors.
- **Evidence:** `services/layer3-knowledge/src/tracing/middleware.py`.
- **Suggested action:** Migrate to `opentelemetry-instrumentation-fastapi`.

## PROD-P2-009: No Log Retention Policy
- **Description:** No documented log retention or rotation configuration.
- **Evidence:** None found.
- **Suggested action:** Document 30 days hot / 1 year cold retention; enforce in K8s/config.

## PROD-P2-010: Mixed Line Endings / Windows Artifacts
- **Description:** CRLF warnings on Makefile; Windows temp directories in root.
- **Evidence:** Git warnings; root `C:Users*` artifacts.
- **Suggested action:** Add `.gitattributes` with `* text=auto eol=lf`; run `make clean-root-debris`.

---

# Sprint Roadmap

## Phase 0: Stabilize and Inventory (Week 1)
**Goal:** Lock the repository state, inventory all P0/P1 items, and establish baseline metrics.

**Scope:**
- Run full test suite and document current pass/fail/skip counts.
- Inventory all TODO/FIXME/HACK comments in critical paths.
- Verify CI workflow completeness (do all P0 gates actually run?).
- Establish security bug bounty / pen-test schedule.

**Tickets:**
- PROD-P0-006 (Dev auth bypass in compose)
- PROD-P2-010 (Windows artifacts / line endings)

**Validation:**
```bash
make verify
pnpm --dir apps/web run test
pytest tests/security -m "unit"
```

## Phase 1: Security and Tenant Isolation (Weeks 2–4)
**Goal:** Close all P0 security gaps. No production launch without this phase complete.

**Scope:**
- L7 Billing auth + rate limiting
- L2 Extraction unconditional auth
- L1 SSRF validation
- L3 rate limiter hardening
- L4 file tool tenant fallback fix
- Service-to-service auth for L1→L2

**Tickets:**
- PROD-P0-001 through PROD-P0-006, PROD-P0-009
- PROD-P1-001, PROD-P1-006, PROD-P1-010

**Validation:**
```bash
pytest tests/security -m "tenant_boundary"
pytest tests/security -m "security"
make contract-tests
```

**Risks:** L7 Billing may require API contract changes that affect frontend consumers.

## Phase 2: API/Data Correctness (Weeks 4–5)
**Goal:** Fix API contract drift, schema consistency, and data integrity issues.

**Scope:**
- L7 OpenAPI response models
- L2/L3 type drift fixes
- Dynamic Cypher builder audit
- PII encryption at rest planning
- Audit retry queue

**Tickets:**
- PROD-P1-004, PROD-P1-005, PROD-P1-006
- PROD-P2-006 (un-skip contract tests)

**Validation:**
```bash
pnpm run check:contract-compliance
pnpm run check:api-types
make check-migration-heads
```

## Phase 3: Frontend Production UX (Weeks 5–7)
**Goal:** Raise frontend quality to production grade.

**Scope:**
- Raise coverage thresholds and fill gaps
- Implement account access / entitlement verification
- Gate/remove demo data
- Add StrictMode
- Deprecate legacy routes/components

**Tickets:**
- PROD-P0-007, PROD-P0-010
- PROD-P1-008
- PROD-P2-001 through PROD-P2-004

**Validation:**
```bash
pnpm --dir apps/web run test
pnpm --dir apps/web run test:e2e
pnpm --dir apps/web run build
pnpm --dir apps/web run test:prod-auth-bypass
```

## Phase 4: Observability and Operations (Weeks 7–8)
**Goal:** Close observability gaps and establish operational runbooks.

**Scope:**
- Integrate Sentry
- Unify L3 OTel tracing
- Implement PostgreSQL backup manager
- Add log retention policy
- Wire SLO evaluation to CI

**Tickets:**
- PROD-P0-008
- PROD-P1-002, PROD-P1-003, PROD-P1-007
- PROD-P2-008, PROD-P2-009

**Validation:**
```bash
scripts/perf/evaluate_slo.py
# Verify Sentry receives test exception
# Verify pg_backup produces encrypted artifact
```

## Phase 5: Performance and Scalability (Weeks 8–9)
**Goal:** Validate performance under load and fix bottlenecks.

**Scope:**
- Load tests for L3 and L4
- Review expensive queries
- Path normalization for L3 metrics
- Bundle size audit
- Database query-plan review

**Tickets:**
- PROD-P1-002
- PROD-P2-007

**Validation:**
```bash
# Run load tests (add to CI if missing)
make perf-test
pnpm --dir apps/web run build:analyze
```

## Phase 6: Deployment and Release Readiness (Weeks 9–10)
**Goal:** Make infrastructure production-deployable.

**Scope:**
- Wire ArgoCD / GitOps controller
- Replace placeholder K8s secrets with External Secrets Operator
- Complete Clerk auth rollout and deprecate Keycloak
- Blue-green deployment validation
- Rollback runbook testing

**Tickets:**
- Infrastructure wiring (not ticketed above)
- Dual auth sunset

**Validation:**
```bash
make k8s-validate
kubectl apply --dry-run=client -f k8s/base/
# ArgoCD sync test
```

## Phase 7: Final Launch Gate (Week 11)
**Goal:** Execute launch gate checklist and sign off.

**Scope:**
- Full penetration test
- Security audit re-run
- Load test at 2x expected traffic
- DR drill (PostgreSQL restore)
- Accessibility audit
- Legal/compliance review

**Validation:**
```bash
make verify
make test-backend-integrated-validation
make test-backend-integrated-release-smoke
```

---

# Copy/Paste Dev Tickets

## Backend / Platform / Security Tickets

### TICKET-SEC-001: Add Authentication and Rate Limiting to L7 Billing
**Priority:** P0  
**Background:** L7 Billing currently accepts tenant identity from unvalidated headers.  
**Problem:** Complete auth bypass and rate-limit bypass.  
**Scope:** Add JWT validation, GovernanceMiddleware, RateLimitMiddleware to all L7 routes.  
**Non-goals:** Billing business logic changes; payment provider integration.  
**Implementation steps:**
1. Import `create_fabric_app` from `value_fabric.shared.fastapi_framework`.
2. Add `GovernanceMiddleware` and `RateLimitMiddleware` to app bootstrap.
3. Replace `get_principal()` with `require_authenticated` + tenant context builder.
4. Add Pydantic response models for all routes.
5. Update `contracts/openapi/layer7-billing.json` if shape changes.
**Files affected:**
- `services/layer7-billing/src/layer7_billing/api/main.py`
- `services/layer7-billing/src/layer7_billing/storage/store.py`
- `contracts/openapi/layer7-billing.json`
**Acceptance criteria:**
- [ ] All L7 routes require valid JWT.
- [ ] Cross-tenant access returns 403.
- [ ] Rate limiting blocks burst abuse.
- [ ] Security tests pass.
**Test plan:**
- Unit tests for auth middleware.
- Security tests for header spoofing, missing JWT, cross-tenant read/write.
**Rollback plan:** Revert to previous commit; L7 is not yet in production.
**Security considerations:** This is a security fix; no new attack surface introduced.
**Documentation updates:** Update `docs/core-concepts/security-model.md` with L7 auth pattern.
**Estimated effort:** M

### TICKET-SEC-002: Enforce Unconditional Auth in L2 Extraction
**Priority:** P0  
**Background:** L2 auth is conditional on env vars.  
**Problem:** Unauthenticated access to document extraction.  
**Scope:** Add GovernanceMiddleware; block startup without auth in production.  
**Files affected:**
- `services/layer2-extraction/src/layer2_extraction/api/main.py`
- `services/layer2-extraction/src/layer2_extraction/api/routes/*.py`
**Acceptance criteria:**
- [ ] L2 starts only when auth keys are present in production.
- [ ] All routes require authenticated principal.
- [ ] Security tests cover missing auth, invalid JWT, cross-tenant extraction.
**Estimated effort:** M

### TICKET-SEC-003: Validate L1 Callback URL for SSRF
**Priority:** P0  
**Background:** L1 accepts arbitrary callback URLs.  
**Problem:** SSRF vector to internal metadata and localhost.  
**Scope:** Add URL safety validation to `ExecuteTargetRequest`.  
**Files affected:**
- `services/layer1-ingestion/src/api/main.py`
- `services/layer1-ingestion/src/api/schemas.py`
**Acceptance criteria:**
- [ ] Block private IP ranges, metadata endpoints, localhost.
- [ ] Only allow http/https schemes.
- [ ] SSRF security tests pass.
**Estimated effort:** S

### TICKET-SEC-004: Harden L3 Rate Limiter Against IP Spoofing
**Priority:** P0  
**Background:** L3 rate limiter trusts X-Forwarded-For.  
**Problem:** Complete rate-limit bypass.  
**Scope:** Use authenticated identity for rate-limit keys; validate proxies.  
**Files affected:**
- `services/layer3-knowledge/src/api/rate_limiter.py`
**Acceptance criteria:**
- [ ] Rate-limit keys use tenant_id or user_id.
- [ ] IP-based fallback validates trusted proxy list.
- [ ] Security tests cover header rotation bypass.
**Estimated effort:** S

### TICKET-SEC-005: Fix L4 File Tool Tenant Fallback
**Priority:** P0  
**Background:** L4 file tools return "default" tenant when context missing.  
**Problem:** Cross-tenant file collision.  
**Scope:** Raise exception on missing context; propagate tenant_id in background jobs.  
**Files affected:**
- `services/layer4-agents/src/tools/files.py`
- `services/layer4-agents/src/engine/executor.py`
**Acceptance criteria:**
- [ ] Missing tenant context raises error.
- [ ] Background jobs pass tenant_id explicitly.
- [ ] Security tests verify tenant isolation.
**Estimated effort:** S

### TICKET-SEC-006: Add Service-to-Service Auth for L1→L2 Calls
**Priority:** P1  
**Background:** L1 Celery calls L2 with only X-Tenant-ID header.  
**Problem:** Header spoofing between layers.  
**Scope:** Sign outbound requests with internal JWT; L2 validates signature.  
**Files affected:**
- `services/layer1-ingestion/src/shared/tasks.py`
- `services/layer2-extraction/src/layer2_extraction/api/main.py`
**Acceptance criteria:**
- [ ] L1→L2 requests carry signed JWT.
- [ ] L2 rejects unsigned or invalid cross-layer requests.
- [ ] Security tests cover signature validation.
**Estimated effort:** M

### TICKET-SEC-007: Remove Dev Auth Bypass from Committed Compose Files
**Priority:** P0  
**Background:** ALLOW_INSECURE_DEV_AUTH_BYPASS is in committed compose files.  
**Problem:** Production auth bypass risk.  
**Scope:** Move to gitignored override; add CI check.  
**Files affected:**
- `docker-compose.dev.yml`
- `docker-compose.yml`
- `.github/workflows/preflight.yml`
**Acceptance criteria:**
- [ ] No bypass env var in committed compose files.
- [ ] CI fails if bypass found in committed configs.
- [ ] Local dev still works via override file.
**Estimated effort:** S

### TICKET-SEC-008: Add PostgreSQL Backup Manager
**Priority:** P0  
**Status:** Repository foundation implemented; operational PITR evidence pending.
**Background:** Only Neo4j previously had backup implementation.
**Problem:** Primary DB restore readiness must be continuously proven.
**Scope:** Implement pg_dump logical backup/restore with encryption and storage backends, plus document managed physical/PITR strategy.
**Files affected:**
- `scripts/ops/postgres_backup.py`
- `scripts/ops/test_postgres_backup_restore.sh`
- `docs/troubleshooting/runbooks/infrastructure/postgres-backup-restore.md`
- `Makefile` (`gate-database-live`)
**Acceptance criteria:**
- [x] Automated logical backups with optional encryption.
- [x] Multi-storage support (local/S3/GCS).
- [x] Restore runbook with RTO/RPO targets.
- [x] Logical backup/restore drill documented and wired to Make.
- [ ] Managed PostgreSQL PITR drill documented from staging/production-like infrastructure.
**Estimated effort remaining:** M

### TICKET-SEC-009: Implement PII Encryption at Rest
**Priority:** P1  
**Background:** PII detected but not encrypted in DB.  
**Problem:** Compliance risk for sensitive customer data.  
**Scope:** Wire L4 encryption service to PII columns; add migration.  
**Files affected:**
- `services/layer4-agents/src/services/encryption_service.py`
- `services/layer4-agents/src/models/billing.py`
- `services/layer1-ingestion/src/shared/models.py`
**Acceptance criteria:**
- [ ] PII columns encrypted at rest.
- [ ] Key rotation mechanism documented.
- [ ] Performance impact acceptable (<5% query latency).
**Estimated effort:** L

### TICKET-SEC-010: Add Audit Event Retry Queue
**Priority:** P1  
**Background:** Audit DB writes are best-effort BackgroundTask.  
**Problem:** Audit loss on transient DB failures.  
**Scope:** Redis-backed retry queue with dead-letter handling.  
**Files affected:**
- `packages/shared/src/value_fabric/shared/audit/emitter.py`
**Acceptance criteria:**
- [ ] Failed audit events retried with exponential backoff.
- [ ] Dead-letter queue for persistent failures.
- [ ] Alert on DLQ growth.
**Estimated effort:** M

---

## Frontend / Product-Readiness Tickets

### TICKET-FE-001: Raise Frontend Coverage Thresholds to Production Grade
**Priority:** P0  
**Background:** Current thresholds are 25% branches / 35% lines.  
**Problem:** Untested critical paths can reach production.  
**Scope:** Raise thresholds; fill gaps in auth, API client, routing, state management.  
**Files affected:**
- `apps/web/vite.config.ts`
- `apps/web/src/auth/*`
- `apps/web/src/api/*`
- `apps/web/src/hooks/*`
- `apps/web/src/stores/*`
**Acceptance criteria:**
- [ ] Thresholds ≥70% lines, ≥60% branches.
- [ ] All critical paths have tests.
- [ ] CI blocks PRs below threshold.
**Estimated effort:** L

### TICKET-FE-002: Gate Hardcoded Demo Data in ProspectPromptBuilder
**Priority:** P0  
**Background:** "Medtronic" demo data inlined in production component.  
**Problem:** Demo content leaks to production UI.  
**Scope:** Move to dev-only fixtures; add CI scanner.  
**Files affected:**
- `apps/web/src/components/workspace/ProspectPromptBuilder.tsx`
- New: `apps/web/src/test/fixtures/demo-prospects.ts`
**Acceptance criteria:**
- [ ] No hardcoded customer names in production components.
- [ ] CI blocks known customer names in `src/components/`.
**Estimated effort:** S

### TICKET-FE-003: Implement Backend Verification for Account Access and Entitlements
**Priority:** P1  
**Background:** `useAccountAccess` and `useEntitlements` are TODO stubs.  
**Problem:** Route guards rely on client-side tier store only; easy to bypass.  
**Scope:** Add API endpoints for account access check and entitlement resolution; wire hooks.  
**Files affected:**
- `apps/web/src/hooks/useAccountAccess.ts`
- `apps/web/src/hooks/useEntitlements.ts`
- `services/api/app/routers/accounts.py` (or new router)
**Acceptance criteria:**
- [ ] Backend verifies account membership before returning data.
- [ ] Entitlements fetched from server, not inferred client-side.
- [ ] Fail closed on network/auth errors.
**Estimated effort:** M

### TICKET-FE-004: Add React StrictMode to Main Entry Point
**Priority:** P2  
**Background:** StrictMode absent from `src/main.tsx`.  
**Problem:** Double-render edge cases not caught in dev.  
**Files affected:**
- `apps/web/src/main.tsx`
**Acceptance criteria:**
- [ ] App wrapped in `React.StrictMode`.
- [ ] No console errors from StrictMode in dev.
**Estimated effort:** XS

### TICKET-FE-005: Deprecate Legacy Frontend Routes and Components
**Priority:** P2  
**Background:** `/workflow/*`, `/value-pilot/*`, `LegacyDataTable`, `LegacyTabs` still exist.  
**Problem:** Maintenance burden; potential drift from backend reality.  
**Scope:** Add deprecation redirects; schedule removal.  
**Files affected:**
- `apps/web/src/shell/router.tsx`
- `apps/web/src/components/ui/fabric/LegacyDataTable.tsx`
- `apps/web/src/components/ui/fabric/LegacyTabs.tsx`
**Acceptance criteria:**
- [ ] Legacy routes redirect to canonical equivalents.
- [ ] Legacy components flagged for removal in next major version.
**Estimated effort:** M

### TICKET-FE-006: Write DESIGN.md for Frontend Governance
**Priority:** P2  
**Background:** AGENTS.md references DESIGN.md but it does not exist.  
**Files affected:**
- New: `apps/web/DESIGN.md`
**Acceptance criteria:**
- [ ] DESIGN.md covers component patterns, state management, API client conventions, testing strategy.
**Estimated effort:** S

### TICKET-FE-007: Audit dangerouslySetInnerHTML in Chart Component
**Priority:** P1  
**Background:** `src/components/ui/chart.tsx` uses `dangerouslySetInnerHTML`.  
**Problem:** XSS if chart data is user-controlled.  
**Scope:** Sanitize or replace with safe rendering.  
**Files affected:**
- `apps/web/src/components/ui/chart.tsx`
**Acceptance criteria:**
- [ ] No raw HTML injection without sanitization.
- [ ] Security test covers chart XSS vector.
**Estimated effort:** S

### TICKET-FE-008: Align Mock Auth IDs Between Runtime and Tests
**Priority:** P2  
**Background:** `AuthContext.tsx` uses UUIDs; `test/mockAuth.ts` uses string IDs.  
**Problem:** Test contracts drift from runtime behavior.  
**Files affected:**
- `apps/web/src/contexts/AuthContext.tsx`
- `apps/web/src/test/mockAuth.ts`
**Acceptance criteria:**
- [ ] Mock auth IDs match runtime format and structure.
**Estimated effort:** XS

---

## Testing / QA Tickets

### TICKET-QA-001: Add API Gateway Unit Tests
**Priority:** P1  
**Background:** 22 tests for 74 source files.  
**Scope:** Add tests for auth, tenant context, RBAC, webhook handlers.  
**Files affected:**
- `services/api/app/tests/`
**Acceptance criteria:**
- [ ] ≥60% line coverage for API Gateway.
- [ ] All auth paths tested.
**Estimated effort:** L

### TICKET-QA-002: Un-Skip or Fix Seven Skipped Contract Test Modules
**Priority:** P1  
**Background:** `test_entity_contract.py`, `test_l3_route_alias_parity.py`, etc. are skipped.  
**Files affected:**
- `tests/contract/`
**Acceptance criteria:**
- [ ] All contract tests pass.
- [ ] CI gate blocks new skipped contract tests.
**Estimated effort:** M

### TICKET-QA-003: Add L7 Billing Security Tests
**Priority:** P0  
**Background:** No security tests for L7.  
**Scope:** Tenant isolation, auth bypass, rate limiting tests.  
**Files affected:**
- New: `tests/security/test_l7_billing_tenant_isolation.py`
- New: `tests/security/test_l7_rate_limiting.py`
**Acceptance criteria:**
- [ ] Cross-tenant access denied.
- [ ] Unauthenticated access denied.
- [ ] Rate limiting enforced.
**Estimated effort:** M

### TICKET-QA-004: Add L2 Extraction Security Tests
**Priority:** P0  
**Background:** No dedicated L2 tenant-isolation security tests.  
**Files affected:**
- New: `tests/security/test_l2_auth_enforcement.py`
- New: `tests/security/test_l2_tenant_isolation.py`
**Acceptance criteria:**
- [ ] Missing auth returns 401.
- [ ] Cross-tenant extraction denied.
**Estimated effort:** M

### TICKET-QA-005: Add SSRF Tests for L1 Callback URL
**Priority:** P0  
**Files affected:**
- New: `tests/security/test_l1_callback_url_ssrf.py`
**Acceptance criteria:**
- [ ] Metadata endpoints blocked.
- [ ] Localhost blocked.
- [ ] file:// scheme blocked.
**Estimated effort:** S

### TICKET-QA-006: Remove Placeholder Assertions in Frontend Tests
**Priority:** P2  
**Background:** `expect(true).toBe(true)` found in 3 instances.  
**Files affected:**
- Frontend test files with placeholder assertions.
**Acceptance criteria:**
- [ ] No placeholder assertions in test suite.
- [ ] CI gate catches `expect(true).toBe(true)`.
**Estimated effort:** XS

---

## Infrastructure / DevOps Tickets

### TICKET-INFRA-001: Wire ArgoCD / GitOps Controller
**Priority:** P1  
**Background:** ArgoCD Application manifests exist but controller is not installed.  
**Scope:** Install ArgoCD; configure Application auto-sync; validate blue-green progressive delivery.  
**Files affected:**
- `k8s/argocd/`
- `.github/workflows/deploy.yml`
**Acceptance criteria:**
- [ ] ArgoCD auto-syncs base manifests.
- [ ] Blue-green deployment validated in staging.
**Estimated effort:** L

### TICKET-INFRA-002: Replace Placeholder K8s Secrets with External Secrets Operator
**Priority:** P1  
**Background:** Base K8s manifests contain placeholder credentials relying on overlays.  
**Scope:** Migrate all secrets to External Secrets Operator; remove placeholders from base.  
**Files affected:**
- `k8s/base/*`
- `k8s/overlays/*/`
**Acceptance criteria:**
- [ ] No hardcoded credentials in base manifests.
- [ ] ESO pulls from Infisical vault.
**Estimated effort:** M

### TICKET-INFRA-003: Add PostgreSQL Backup CronJob
**Priority:** P0  
**Status:** Logical backup CronJob manifest present; managed physical/PITR evidence pending.
**Background:** PostgreSQL requires both logical backup smoke coverage and provider/self-managed PITR.
**Scope:** Kubernetes CronJob running pg_dump plus documented managed physical/PITR strategy.
**Files affected:**
- `k8s/base/postgres-backup-cronjob.yaml`
- `docs/troubleshooting/runbooks/infrastructure/postgres-backup-restore.md`
**Acceptance criteria:**
- [x] Scheduled logical backup manifest exists.
- [x] Logical backup/restore drill gate exists.
- [ ] Managed physical/PITR backup configuration evidence attached.
- [ ] Encrypted object-storage destination verified in production configuration.
**Estimated effort remaining:** M

### TICKET-INFRA-004: Integrate Sentry for Error Aggregation
**Priority:** P1  
**Background:** No centralized error aggregator.  
**Scope:** Add Sentry SDK to frontend and all backend layers; configure DSNs per environment.  
**Files affected:**
- `apps/web/src/main.tsx`
- `services/*/src/main.py`
**Acceptance criteria:**
- [ ] Sentry receives exceptions from all layers.
- [ ] PII scrubbing configured.
- [ ] Alert rules for error rate spikes.
**Estimated effort:** M

### TICKET-INFRA-005: Complete Clerk Auth Rollout and Deprecate Keycloak
**Priority:** P1  
**Background:** Dual auth system increases attack surface.  
**Scope:** Remove Keycloak from docker-compose; deprecate legacy JWT paths; document sunset date.  
**Files affected:**
- `docker-compose.dev.yml`
- `services/api/app/core/security.py`
- `infra/keycloak/`
**Acceptance criteria:**
- [ ] Keycloak removed from dev stack.
- [ ] Legacy JWT paths return deprecation headers.
- [ ] Sunset date documented.
**Estimated effort:** L

---

## Documentation / Developer-Experience Tickets

### TICKET-DOC-001: Write DESIGN.md for Frontend
**Priority:** P2  
**Files affected:**
- New: `apps/web/DESIGN.md`
**Acceptance criteria:**
- [ ] Covers architecture, patterns, component conventions, testing strategy.
**Estimated effort:** S

### TICKET-DOC-002: Document L2.5 and L7 Boundaries
**Priority:** P1  
**Background:** L2.5 and L7 are not in canonical 6-layer architecture.  
**Files affected:**
- `ARCHITECTURE.md`
- `AGENTS.md`
- New: `docs/explanations/adr/ADR-00X-layer2-5-boundary.md`
**Acceptance criteria:**
- [ ] L2.5 responsibility documented.
- [ ] L7 responsibility documented.
- [ ] ADR approved.
**Estimated effort:** S

### TICKET-DOC-003: Add PostgreSQL Backup-Restore Runbook
**Priority:** P1  
**Status:** Implemented; keep quarterly evidence current.
**Files affected:**
- `docs/troubleshooting/runbooks/infrastructure/postgres-backup-restore.md`
**Acceptance criteria:**
- [x] Step-by-step logical restore procedure.
- [x] RTO/RPO targets defined.
- [x] Quarterly logical drill schedule and Make gate documented.
- [x] Managed PostgreSQL physical/PITR strategy documented.
**Estimated effort:** S

---

# Launch Gate Checklist

## Auth
- [ ] All production routes require valid JWT (except public health endpoints).
- [ ] L7 Billing routes require authenticated principal.
- [ ] L2 Extraction routes require authenticated principal.
- [ ] Dev auth bypass is impossible in production builds.
- [ ] Clerk auth rollout is complete; Keycloak sunset date published.
- [ ] Service-to-service calls carry signed JWT or mTLS.
- **Evidence:** `pytest tests/security -m "tenant_boundary"` passes; `pnpm --dir apps/web run test:prod-auth-bypass` passes.

## RBAC
- [ ] Role checks enforced on all admin/mutating endpoints.
- [ ] `billing:write` requires elevated role.
- [ ] `tenant:admin` cannot escalate to platform admin.
- **Evidence:** Security tests for RBAC expanded pass.

## Tenant Isolation
- [ ] Cross-tenant read/write returns 403 on all layers.
- [ ] RLS policies active on all PostgreSQL tenant tables.
- [ ] Neo4j queries filter by `$tenant_id`.
- [ ] File storage paths include validated tenant_id.
- [ ] Background jobs propagate tenant_id explicitly.
- **Evidence:** `pytest tests/security -m "tenant_boundary"` passes; hostile tenant tests pass.

## Secrets
- [ ] No secrets in committed code (scan with gitleaks).
- [ ] No placeholder credentials in K8s base manifests.
- [ ] External Secrets Operator pulls from Infisical.
- [ ] LLM API keys validated at startup (reject placeholders).
- **Evidence:** `make secret-scan` passes; `kubectl get secrets` shows ESO-managed secrets.

## Migrations
- [ ] Exactly one Alembic head per service.
- [ ] Destructive migrations require explicit ack in production.
- [ ] Migration rollback tested in staging.
- [ ] Schema-drift detection passes in CI.
- **Evidence:** `make check-migration-heads` passes.

## Backups
- [x] PostgreSQL logical backup/restore tooling with optional encryption.
- [ ] PostgreSQL managed physical/PITR configuration and dated restore drill evidence.
- [ ] Neo4j automated backups with encryption.
- [ ] Redis persistence configured (AOF or RDB).
- [ ] Restore runbooks tested quarterly.
- [ ] RTO ≤ 30 min, RPO ≤ 15 min validated.
- **Evidence:** PostgreSQL repository evidence now includes `scripts/ops/postgres_backup.py`, `scripts/ops/test_postgres_backup_restore.sh`, `docs/troubleshooting/runbooks/infrastructure/postgres-backup-restore.md`, `k8s/base/postgres-backup-cronjob.yaml`, and `make gate-database-live`. Production closure still requires archived `artifacts/postgres-backup-restore/` drill output and managed PITR evidence.

## Observability
- [ ] Sentry integrated and receiving exceptions.
- [ ] Prometheus metrics scrapeable from all layers.
- [ ] Alertmanager routes alerts to on-call.
- [ ] Structured logs include request_id and tenant_id.
- [ ] Health/ready probes respond correctly.
- [ ] Distributed tracing covers cross-service requests.
- **Evidence:** Sentry dashboard shows events; Prometheus targets all UP; alert test fires.

## Error Handling
- [ ] Production responses do not include stack traces.
- [ ] Error envelope format consistent across all layers.
- [ ] Sensitive keys scrubbed from logs and errors.
- [ ] Client-side errors reported to telemetry.
- **Evidence:** `tests/contract/test_error_envelope_consistency.py` passes.

## CI/CD
- [ ] All PRs pass `structural-preflight`, lint, typecheck, and tests.
- [ ] Contract checks pass (OpenAPI drift, API types).
- [ ] Security gates pass (tenant boundary, OWASP).
- [ ] Build artifacts signed and scanned.
- [ ] Deployment requires approval for production.
- **Evidence:** `.github/workflows/pr-checks.yml` all green.

## E2E Tests
- [ ] Playwright contract tests pass.
- [ ] Playwright journey tests pass.
- [ ] Backend-integrated E2E tests pass against live stack.
- [ ] Accessibility tests pass (keyboard flow, landmarks).
- [ ] Golden-path journeys verified.
- **Evidence:** `pnpm --dir apps/web run test:e2e` passes.

## Security Tests
- [ ] Tenant isolation tests pass (all layers).
- [ ] OWASP Top 10 tests pass.
- [ ] Rate limiting tests pass.
- [ ] SSRF tests pass.
- [ ] Auth bypass tests pass.
- [ ] Penetration test completed by third party.
- **Evidence:** `pytest tests/security` passes; pen-test report signed off.

## Dependency Scanning
- [ ] No critical vulnerabilities in dependencies.
- [ ] pnpm audit clean.
- [ ] pip-audit clean for all Python services.
- [ ] Supply-chain attestation verified.
- **Evidence:** `pnpm audit --audit-level moderate` passes; `pip-audit` passes.

## Performance Smoke Tests
- [ ] Frontend bundle ≤ 3.5 MiB.
- [ ] API p95 latency ≤ 500 ms for read endpoints.
- [ ] Agent workflow p95 latency ≤ 30 s.
- [ ] Load test at 2x expected traffic passes.
- **Evidence:** `scripts/perf/evaluate_slo.py` artifacts published.

## Accessibility
- [ ] WCAG 2.1 AA compliance verified.
- [ ] Keyboard navigation works for all primary flows.
- [ ] Screen reader labels present on interactive elements.
- **Evidence:** `pnpm --dir apps/web run test:a11y:pages` passes.

## Legal / Compliance Basics
- [ ] Privacy policy published.
- [ ] Terms of service published.
- [ ] DSAR workflow tested end-to-end.
- [ ] Data retention policy documented.
- [ ] GDPR/CCPA compliance checklist completed.
- **Evidence:** Legal review sign-off.

## Incident Response
- [ ] On-call rotation defined.
- [ ] PagerDuty/Opsgenie integration active.
- [ ] Runbooks cover all P1 alert scenarios.
- [ ] Incident commander training completed.
- **Evidence:** On-call schedule published; alert test triggers PagerDuty.

## Rollback
- [ ] Database rollback procedure tested.
- [ ] K8s rollout rollback tested (blue-green).
- [ ] Feature flags allow quick disable.
- [ ] Previous Docker image retained for 30 days.
- **Evidence:** Rollback drill completed in staging.

## Runbooks
- [ ] 40+ runbooks exist and are accurate.
- [ ] No internal placeholder links (wiki.internal).
- [ ] Runbooks cover security incidents, data loss, tenant isolation breaches.
- **Evidence:** Runbook validation passes.

## Admin Operations
- [ ] Admin CLI tools documented.
- [ ] Admin operations require MFA.
- [ ] Admin actions are audited.
- [ ] No admin backdoors in production.
- **Evidence:** Admin ops audit log review.

## Customer Onboarding
- [ ] Self-service signup works end-to-end.
- [ ] Tenant provisioning is automated.
- [ ] Welcome email and docs sent.
- [ ] First-value delivery ≤ 24 hours.
- **Evidence:** Onboarding journey E2E test passes.

## Support Process
- [ ] Support ticket system configured.
- [ ] SLA definitions published.
- [ ] Escalation path to engineering defined.
- [ ] Customer-facing status page active.
- **Evidence:** Support workflow tested.

---

# Security Review

## Strengths
- **JWT Hardening:** Canonical base64url encoding, algorithm match, required claims, issuer/audience verification, Redis-backed revocation denylist (`services/api/app/core/security.py`).
- **Tenant Isolation:** Postgres RLS with `SET LOCAL app.tenant_id`; Neo4j `$tenant_id` filtering; ContextVar propagation.
- **Cypher Injection Guard:** `TENANT_OWNED_LABELS` registry, `validate_cypher_identifier` allowlist, static regex validator (`services/layer3-knowledge/src/utils/cypher_security.py`).
- **Webhook Security:** Clerk Svix HMAC-SHA256 + timestamp tolerance + idempotency; CRM per-tenant token + HMAC signature.
- **Password Policy:** bcrypt 72-byte limit, common-password blocklist, account lockout after 10 failures.
- **Production Gates:** Vault health checks, weak JWT secret denylist, schema-migration alignment probes.
- **Error Sanitization:** `sanitize_log_error` in Celery tasks; canonical `ErrorEnvelope`; explicit `exc_info` control.

## Critical Gaps
1. **L7 Billing zero auth** — any caller can spoof tenant identity.
2. **L2 conditional auth** — no-op when env vars unset.
3. **L1 SSRF** — unvalidated callback_url.
4. **L3 rate-limit bypass** — X-Forwarded-For trust without proxy validation.
5. **L4 file tool fallback** — "default" tenant collision.
6. **Dev bypass in committed configs** — production misconfiguration risk.
7. **L1→L2 no service-to-service auth** — header spoofing between layers.
8. **Dynamic Cypher builders** — fragile f-string pattern.
9. **Raw str(exc) in L3 logs** — potential secret leakage.
10. **OpenAI keys from env without validation** — placeholder keys accepted.

## Recommended Actions
- See P0 and P1 tickets TICKET-SEC-001 through TICKET-SEC-010.

---

# Tenant Isolation Review

## Strengths
- **PostgreSQL RLS:** Shared schema with `tenant_id` column + session variable. Migration history shows active hardening (null-tenant fixes, admin bypass policies).
- **Neo4j Filtering:** `$tenant_id` parameterization in Cypher queries; `TenantQueryExecutor` centralizes query building.
- **Repository Pattern:** All repository methods require `tenant_id` parameter; SQLAlchemy filters enforce scoping.
- **ContextVar Propagation:** `TenantContext` ContextVar ensures thread-safe tenant tracking across async boundaries.
- **Audit Append-Only:** DB triggers block UPDATE/DELETE on `validation_events` for non-privileged roles.

## Critical Gaps
1. **L7 Billing** — no tenant verification; header spoofing allows cross-tenant billing data access.
2. **L2 Extraction** — no auth means no tenant context extraction; extraction runs unauthenticated.
3. **L4 File Tools** — "default" fallback allows cross-tenant file collision.
4. **L1→L2 Calls** — `X-Tenant-ID` header only; spoofable if L2 exposed directly.
5. **L6 Seed Data** — `tenant_id="system"` used during startup; must ensure read-only for non-admins.

## Recommended Actions
- See P0 tickets PROD-P0-001, PROD-P0-002, PROD-P0-004, PROD-P0-009, and P1 ticket PROD-P1-001.

---

# Testing Review

## Strengths
- **Security Testing Culture:** 130+ security test files, OWASP Top 10 coverage, cross-tenant JWT manipulation tests, tenant boundary fails-closed tests, RBAC expanded tests.
- **Contract Testing:** OpenAPI drift detection, schema consistency checks, error envelope consistency.
- **E2E Infrastructure:** 128 Playwright specs across contracts, journeys, backend-integrated, mobile, cross-browser, accessibility.
- **CI Governance:** Strict pytest markers, timeout enforcement, randomization, skip governance checks.
- **Frontend Testing:** Vitest + React Testing Library + MSW + jest-axe + keyboard-flow E2E.

## Critical Gaps
1. **API Gateway Under-Tested:** 22 tests for 74 source files.
2. **L2.5 Signal Refinery Under-Tested:** 5 tests for entire service.
3. **Seven Skipped Contract Tests:** `test_entity_contract.py`, `test_l3_route_alias_parity.py`, etc.
4. **value_fabric Runtime Packages Minimal:** 2 smoke tests for 15 source files.
5. **L7 Billing Missing:** No security tests at all.
6. **L2 Tenant Isolation Weak:** Only API-level hostile test; no dedicated security suite.
7. **Frontend Coverage Too Low:** 25% branches / 35% lines.
8. **Placeholder Assertions:** `expect(true).toBe(true)` found in 3 frontend tests.
9. **Timing-Dependent Sleeps:** Integration/chaos tests use sleeps; latent flakiness.
10. **Backend-Integrated Tests Thin:** 9 files for full 6-layer pipeline.

## Recommended Actions
- See tickets TICKET-QA-001 through TICKET-QA-006 and PROD-P0-007.

---

# Infrastructure and Deployment Review

## Strengths
- **K8s Hardening:** `runAsNonRoot`, `seccompProfile: RuntimeDefault`, `allowPrivilegeEscalation: false`, `capabilities.drop: [ALL]`.
- **HPA:** Horizontal Pod Autoscalers for frontend and all L1-L6 services.
- **Secret Management:** Infisical CLI (local) → GitHub OIDC (CI) → Infisical K8s Operator (prod).
- **CI/CD Maturity:** 60+ workflows, contract compliance, security gates, SLO evaluation script.
- **Runbooks:** 40+ runbooks covering application, infrastructure, and incident response.

## Critical Gaps
1. **ArgoCD Not Wired:** Application manifests exist but controller not installed; GitOps non-functional.
2. **Placeholder K8s Secrets:** Base manifests contain hardcoded credentials relying on overlays.
3. **PostgreSQL PITR Evidence Pending:** Logical backup/restore tooling and drill gate exist; managed physical/PITR configuration and executed restore evidence are still required.
4. **Deploy Pipeline Lacks Live Cluster Credentials:** Placeholder kubeconfig.
5. **Blue-Green / Canary Non-Functional:** Without ArgoCD, progressive delivery is manual.
6. **Mixed Line Endings:** CRLF warnings; Windows artifacts in root.

## Recommended Actions
- See tickets TICKET-INFRA-001 through TICKET-INFRA-005 and PROD-P0-006, PROD-P0-008.

---

# Observability and Operations Review

## Strengths
- **Prometheus Metrics:** Per-layer metrics with cardinality safety (tenant tier bucketing instead of tenant_id).
- **Structured Logging:** `structlog` with JSON rendering, ISO timestamps, context propagation.
- **Health/Ready Probes:** Auto-registered `/health`, `/ready`, `/metrics`.
- **Alert Rules:** Layer-specific Prometheus rules with severity labels and runbook URLs.
- **SLOs:** Platform-wide and per-layer SLOs with burn-rate policies.
- **Error Envelope:** Standardized `ErrorEnvelope` with code, message, request_id, sanitized details.

## Critical Gaps
1. **No Sentry:** No centralized error aggregator; errors rely on logs and metrics only.
2. **L3 Tracing Isolated:** Custom tracer does not interoperate with standard OTel collectors.
3. **Audit DB Best-Effort:** BackgroundTask-only persistence; no retry on failure.
4. **No Log Retention Policy:** Undefined hot/cold retention.
5. **L3 Metrics Cardinality Risk:** No path normalization for UUIDs in endpoint labels.
6. **Some Runbook Placeholders:** Links to `wiki.internal` may be unreachable.

## Recommended Actions
- See tickets TICKET-INFRA-004, TICKET-SEC-010, and P1 items PROD-P1-002, PROD-P1-003.

---

# Frontend UX / Product Readiness Review

## Strengths
- **Architecture:** Clean layer separation, contract-first API, canonical hook wrappers, route-level policy system.
- **Auth Security:** Clerk integration, Bearer sanitization, CSRF, production mock-auth kill-switch, post-build bypass scanner.
- **API Client:** Axios with Zod validation, deduplication, exponential retry, structured errors.
- **State Management:** Zustand for local, TanStack Query for server, centralized cache policies.
- **Design System:** 80+ shadcn/ui primitives, shared states, Fabric domain components.
- **Accessibility:** jest-axe, keyboard E2E, landmarks, skip links.
- **Build:** Vite manual chunking, bundle budget gate, auth bypass scanner.

## Critical Gaps
1. **Coverage Too Low:** 25% branches / 35% lines.
2. **Hardcoded Demo Data:** "Medtronic" in `ProspectPromptBuilder.tsx`.
3. **TODO Stubs:** `useAccountAccess.ts` and `useEntitlements.ts` unimplemented.
4. **No StrictMode:** Missing from `src/main.tsx`.
5. **Legacy Debt:** `/workflow/*`, `/value-pilot/*`, `LegacyDataTable`, `LegacyTabs`.
6. **dangerouslySetInnerHTML:** XSS risk in `chart.tsx`.
7. **Mock Auth ID Mismatch:** Runtime UUIDs vs test string IDs.
8. **Missing DESIGN.md:** AGENTS.md references non-existent file.

## Recommended Actions
- See tickets TICKET-FE-001 through TICKET-FE-008.

---

# Documentation and Developer Experience Review

## Strengths
- **Diataxis Structure:** Tutorials, how-to guides, reference, explanations.
- **Governance Docs:** ADRs, contract docs, security model, SLOs, runbooks.
- **Agent Onboarding:** AGENTS.md provides clear setup, testing, lint, and PR guidance.
- **Scripts:** Makefile targets for common operations; pnpm scripts for frontend.
- **Pre-Commit Hooks:** gitleaks, black, ruff, prettier.
- **Env Examples:** `.env.example` and `.env.dev.example` with safe defaults.

## Critical Gaps
1. **Missing DESIGN.md:** At `apps/web/DESIGN.md`.
2. **L2.5 Undocumented:** Not in canonical 6-layer architecture.
3. **L7 Undocumented:** No ADR or architecture doc.
4. **Placeholder Runbook Links:** `wiki.internal` URLs.
5. **Windows Artifacts:** CRLF warnings, temp directories in root.
6. **Cypress Listed but Unused:** Adds install weight.

## Recommended Actions
- See tickets TICKET-DOC-001 through TICKET-DOC-003 and PROD-P2-010.

---

# Recommended Validation Commands

## Local Development
```bash
# Install
corepack enable && corepack prepare pnpm@10.18.1 --activate
pnpm install --frozen-lockfile
make setup

# Lint & Format
make lint
pnpm --dir apps/web run lint
pnpm --dir apps/web run format

# Typecheck
make typecheck
pnpm --dir apps/web run typecheck

# Unit Tests
make test
pnpm --dir apps/web run test

# Contract Tests
make contract-tests
pnpm --dir apps/web run test:contracts

# Security Tests
pytest tests/security -m "tenant_boundary"
pytest tests/security -m "security"

# Build
pnpm --dir apps/web run build
make build  # if defined

# Docker Build
docker compose -f docker-compose.dev.yml build

# Migration Checks
make check-migration-heads

# OpenAPI Validation
pnpm run check:contract-compliance
pnpm run check:api-types
```

## CI/CD (should be in `.github/workflows/`)
```bash
# Full verification gate
make verify

# Frontend verification
pnpm run verify:frontend

# Security scan
make secret-scan  # add if missing
pnpm audit --audit-level moderate

# Dependency audit (Python)
# Add: pip-audit for each service

# Kubernetes validation
kubectl apply --dry-run=client -f k8s/base/
make k8s-validate  # add if missing

# SLO evaluation
scripts/perf/evaluate_slo.py

# Bundle analysis
pnpm --dir apps/web run build:analyze

# E2E
pnpm --dir apps/web run test:e2e
make test-backend-integrated-validation
make test-backend-integrated-release-smoke
```

## Missing Commands (Recommended to Add)
- `make secret-scan` — wrapper for gitleaks + trufflehog
- `make pip-audit-all` — run pip-audit across all Python services
- `make k8s-validate` — kubeval / kubeconform for all manifests
- `make load-test` — k6 or locust against staging
- `make accessibility-audit` — axe-ci or pa11y against built frontend

---

# Final Recommendation

**Do not launch to general production.**

Value Fabric has strong architectural foundations and mature security testing, but **two critical service boundaries (L2 and L7) are unauthenticated, creating complete tenant isolation breakdown**. Additionally, an unprotected SSRF vector in L1, a rate-limit bypass in L3, and weak frontend coverage thresholds create unacceptable risk for a security-conscious enterprise SaaS.

**Recommended path:**
1. Execute **Phase 0–1 (Security and Tenant Isolation)** over the next 2–3 sprints.
2. Re-run penetration tests and security audits after P0 fixes.
3. Enter **controlled beta** with a small cohort of trusted customers after P0 remediation.
4. Execute **Phase 2–6** during beta to reach full production readiness.
5. Target **general production launch** after all P0 and P1 items are resolved and validated.

The engineering team has demonstrated they can build a high-quality platform. The gaps are specific, measurable, and fixable. Focus the next sprint exclusively on closing P0 security gaps before any customer data enters the system.
