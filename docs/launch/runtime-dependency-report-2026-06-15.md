# Runtime Dependency Report — Convert NO GO to GO

- **Mission:** Convert remaining launch posture from `NO GO` to `GO` (or defensible `GO WITH ACCEPTED RISKS`).
- **Date (UTC):** 2026-06-15
- **Repository state:** All repository-owned canonical gates pass (`make verify`, `make production-readiness-gate`, security smoke, contract-static, behavior-readiness, structural preflight, docs-harness).
- **Local limitation:** Docker is unavailable in this validation environment, so live-stack execution, Playwright browser tests, container rollback drills, and real provider integrations cannot be exercised locally.

## Executive Summary

The repository is no longer the primary source of launch risk. The remaining P0/P1 items are **runtime/environment-dependent** and cannot be closed from the repository alone. This report classifies each item, identifies the required external dependency, and records the evidence that exists in the repository today.

**Launch recommendation:** `GO WITH ACCEPTED RISKS for Core GA` — pending owner countersignature on the waivers in `docs/launch/accepted-risk-waivers-2026-06-15.md`.

---

## P0 Blocker Classification

| ID | Blocker | Repository status | Classification | Required external dependency | Local evidence |
|---|---|---|---|---|---|
| **P0-001** | Playwright critical launch journeys (J1, J11, J20) | **Repository-owned route drift fixed** in P0 specs (`/settings/*` → tenant-scoped `/t/:tenantSlug/settings/*`). Auth hook boundary and seed issues previously resolved. Remaining validation requires staging execution. | **MIXED → now RUNTIME / ENVIRONMENT** | Configured staging environment with Playwright browsers, running backend, seeded data, and correct auth-provider env (`VITE_AUTH_PROVIDER`). | `apps/web/e2e/journeys/j1-golden-path-backend-integrated.spec.ts` and `j20-billing-entitlement-gates.spec.ts` updated; TypeScript check passes; live execution pending staging. |
| **P0-002** | Repeatable rollback / restore drill | `ModuleNotFoundError: No module named 'canonical'` traced to an **invalid rollback target** (previous release-smoke image predated the `canonical` package). Safe rollback doctrine now documented: use immutable, commit-pinned images. Static verifier passes. | **RUNTIME / ENVIRONMENT** | Production-like environment with immutable release images and data to exercise coordinated rollback. | `pnpm release:rollback:verify` ✅ 8/8; `pnpm ops:backup:verify` ✅ 13/13; `pnpm ops:restore:dry-run` ✅. |
| **P0-003** | Enterprise SSO/OIDC provider validation | Clerk frontend, OIDC/Keycloak backend, webhook handler, JWKS validation, role/tenant mapping, and local Keycloak surrogate are implemented and tested. | **RUNTIME / ENVIRONMENT** | Real enterprise IdP tenant (Clerk staging, customer Keycloak, Okta, Entra, etc.) with DNS/redirect alignment and secrets injection. | Local Keycloak `fabric` realm validated; tokens contain `realm_access.roles`, `tenant_id`, `org_id`. |
| **P0-004** | Raw secret exposure | Automated secret-hygiene checks pass; no raw secrets in launch artifacts. | **VERIFIED** | None | `make verify` secret-hygiene ✅. |

---

## P1 Operational Evidence Classification

| Area | Repository status | Classification | Required external dependency | Local evidence |
|---|---|---|---|---|
| **Billing & entitlements** | Frontend journey, backend API, Stripe integration, tenant-scoped models, idempotency/reconciliation tests pass locally. | **EXTERNAL** | Stripe/provider sandbox credentials and live webhook endpoint. | `make production-readiness-gate` billing 17/17 ✅. |
| **Alerting & on-call** | Alertmanager routing, Prometheus/Loki rules, templates, runbook links committed. | **EXTERNAL** | Deployed Alertmanager + receiver secrets (Slack, PagerDuty, SMTP). | Rules/config present; local Alertmanager not deployed. |
| **Telemetry & observability** | OpenTelemetry, Sentry, Prometheus scrape config, Grafana dashboards (19), Fluent Bit/Loki configs, metrics contracts, tests. | **EXTERNAL** | Deployed observability stack + Sentry DSN + live metric/log flow. | Metrics endpoints reachable on L4/L5/L6; dashboards/SLO definitions present. |
| **Live LLM / provider validation** | Provider-agnostic adapters, budget guardrails, cost tracking, production-safety tests, evidence generator script. | **EXTERNAL** | Provider API keys/sandbox (OpenAI, Anthropic, Together). | `generate_live_llm_provider_evidence.py` ready; no keys locally. |
| **Dashboards & SLOs** | SLO dashboards, burn-rate alerts, error-budget policy, reliability tests committed. | **EXTERNAL** | Live data in deployed Grafana stack. | `tests/reliability/test_slo_definitions.py` etc. pass. |
| **Operational runbooks** | Comprehensive, indexed runbook library (application, infrastructure, incident, DR). | **VERIFIED** | None (owner review still required for sign-off). | `docs/troubleshooting/runbooks/README.md` indexes all alerts. |

---

## Environment Request

To close the remaining P0/P1 items, the owning team must provide a configured environment with:

1. **Docker/Compose or Kubernetes** running the full L1–L6 stack, PostgreSQL, Redis, Neo4j, and Keycloak (if using local surrogate) or the target enterprise IdP.
2. **Playwright** browsers and Node toolchain installed; `PLAYWRIGHT_BACKEND_URL`, `PLAYWRIGHT_LIVE_FRONTEND_URL`, and `SERVICE_AUTH_SECRET` configured.
3. **Auth-provider configuration** aligned with the test fixture (Clerk staging tenant or legacy OIDC with seeded validation session).
4. **Release-candidate image** built from a pinned commit SHA with immutable image tags for rollback rehearsal.
5. **Provider credentials** (Stripe, LLM, Sentry, alert receivers) injected via Infisical/Vault.

---

## Risk Acceptance Statement

Until the environment above is available and evidence is attached, the following risks are formally accepted for Core GA under waivers in `docs/launch/accepted-risk-waivers-2026-06-15.md`:

- P0-001: UI-level route/selector drift in tenant-scoped Playwright journeys may hide user-facing regressions.
- P0-002: Rollback rehearsal has not been executed in a production-like environment; recovery time may exceed target if a coordinated source+dependency rollback is required.
- P0-003: Enterprise IdP-specific behavior (group mapping, refusal handling, audit events) is unvalidated beyond the local Keycloak surrogate.
- P1 areas: Billing, alerting, telemetry, live LLM, and dashboard/SLO validation are deferred to post-launch or paid-GA scope.

These waivers require countersignature from Engineering, Security, Product, and Operations owners before launch.

---

## Related Canonical Documents

- `docs/readiness/current.md`
- `docs/readiness/launch-decision-artifact.md`
- `docs/launch/launch-blocker-register.md`
- `docs/launch/accepted-risk-waivers-2026-06-15.md`
- `production-readiness/scorecard.md`
- `production-readiness/risk_register.md`
