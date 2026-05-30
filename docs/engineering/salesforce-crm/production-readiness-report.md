# Salesforce CRM Integration — Production Readiness Report

**Date:** 2026-05-01
**Scope:** Salesforce CRM integration (backend, frontend, security, observability)
**Assessor:** Kimi Code CLI
**Status:** PILOT-READY — NOT SUITABLE FOR GENERAL AVAILABILITY (GA)

---

## 1. Executive Status

**Pilot-ready with explicit caveats.**

The integration is **structurally sound for a controlled pilot** with a small number of trusted tenants who accept manual onboarding steps. It is **NOT ready for broad production/GA deployment** until the blockers listed in Section 4 are resolved.

Critical security gaps (tenant isolation bypass, environment fallback, missing RLS) have been closed. The remaining issues are a mix of product-level gaps (OAuth UI), data integrity risks (SOQL pagination), and operational scalability concerns (in-memory scheduler).

| Area | Before | After | Status |
|------|--------|-------|--------|
| Tenant isolation | Broken (empty tenant_id) | Fixed (RLS + proper context) | ✅ Pilot-ready |
| Credential security | Env fallback allowed | Fallback removed; per-tenant only | ✅ Pilot-ready |
| Token refresh | Missing | Implemented with degraded state | ✅ Pilot-ready |
| Data model | Missing OAuth fields | Added refresh_token, org_id | ✅ Pilot-ready |
| Observability | Basic logging | Structured logs + metrics | ⚠️ In-memory only |
| OAuth flow | Not implemented | Backend ready; UI missing | ❌ Blocker for GA |
| Scheduler | Singleton, no tenant sweep | Tenant-aware sweep | ⚠️ In-memory singleton |
| Frontend | Manual API key only | OAuth-aware status display | ⚠️ Manual entry only |
| SOQL pagination | Missing | Still missing | ❌ Blocker for GA |
| E2E smoke tests | None | None | ❌ Blocker for GA |

---

## 2. What Was Changed

### Backend

| File | Change |
|------|--------|
| `services/layer4-agents/src/layer4_agents/services/crm_sync_scheduler.py` | **Rewritten.** Removed `app.tenant_id = ''`. Added per-tenant sweep with `db_session_for_context()`. |
| `services/layer4-agents/src/layer4_agents/services/crm_sync_service.py` | Removed `ALLOW_ENV_CRM_FALLBACK`. Added token refresh call. Added structured logging and metrics. |
| `services/layer4-agents/src/layer4_agents/services/integration_service.py` | Added `refresh_salesforce_token()`. **SECURITY:** Removed `refresh_token` from `create_or_update_integration()` API. Tokens only obtained via OAuth callback. |
| `services/layer4-agents/src/layer4_agents/models/integration.py` | Added `DEGRADED` to `IntegrationStatus`. Added `refresh_token_encrypted` and `salesforce_org_id` columns. `to_dict()` now returns `has_refresh_token: bool` instead of token. |
| `services/layer4-agents/src/layer4_agents/api/routes/integrations.py` | **SECURITY:** Removed `refresh_token` from `IntegrationCreateRequest`. Response schema now includes `has_refresh_token: bool`. |
| `services/layer4-agents/migrations/versions/021_add_salesforce_oauth_fields.py` | **New migration.** Adds columns and partial index for active Salesforce integrations. |
| `.env.example` | Documented `SALESFORCE_CLIENT_ID`, `SALESFORCE_CLIENT_SECRET`, `SALESFORCE_REDIRECT_URI`. Added warning about `ALLOW_ENV_CRM_FALLBACK`. |

### Frontend

| File | Change |
|------|--------|
| `frontend/client/src/hooks/useIntegrations.ts` | **SECURITY:** Removed `refresh_token` from `IntegrationCreateRequest`. `Integration` interface now uses `has_refresh_token: boolean`. Added `degraded` to status union. |
| `frontend/client/src/components/integrations/utils.ts` | Added `degraded` status badge styling and text. |
| `frontend/client/src/components/integrations/IntegrationConfigPanel.tsx` | Added degraded state rendering in status badge. |
| `frontend/client/src/pages/intelligence/EvidenceTab.tsx` | Fixed pre-existing TypeScript error (unrelated but blocking typecheck). |

### Tests

| File | Change |
|------|--------|
| `services/layer4-agents/tests/test_salesforce_oauth.py` | **Updated.** Tests token refresh success, 401 degradation, missing refresh token, **runtime tenant isolation verification**, env fallback removal. |
| `services/layer4-agents/tests/test_crm_sync_service.py` | **Updated.** Replaced env-fallback tests with integration-table-driven config tests. |

### Documentation

| File | Change |
|------|--------|
| `docs/operations/salesforce-crm/runbook.md` | **New.** Operator runbook for Connected App config, secret rotation, reconnect, sync inspection, rollback. |
| `docs/engineering/salesforce-crm/architecture.md` | **New.** Architecture overview, data flow diagrams, security model, known limitations. |
| `docs/engineering/salesforce-crm/production-readiness-report.md` | **New.** This report. |

---

## 3. Validation Results

### TypeScript / Frontend

```
pnpm check
# Result: PASS for all modified files.
# Pre-existing errors in CompetitiveTab.tsx and EnrichmentTab.tsx are
# unrelated to CRM integration and existed before this sprint.
```

### Python Syntax

```
python -m py_compile src/services/crm_sync_scheduler.py
python -m py_compile src/services/crm_sync_service.py
python -m py_compile src/services/integration_service.py
python -m py_compile src/models/integration.py
python -m py_compile src/api/routes/integrations.py
python -m py_compile tests/test_salesforce_oauth.py
# Result: All pass.
```

### Backend Tests

```
pytest tests/test_salesforce_oauth.py tests/test_integration_service.py
# Result: 21 passed (token refresh, validation, encryption, tenant isolation)
#
# Note: Full pytest execution for test_crm_sync_service.py blocked by
# missing psycopg binary in local env. Must run in CI Docker container.
```

### Migrations

| Migration | Status |
|-----------|--------|
| `021_add_salesforce_oauth_fields.py` | Written; awaiting `alembic upgrade head` in staging |

### RLS / Security

| Check | Status |
|-------|--------|
| `integrations` table has RLS enabled | ✅ (migration 013) |
| `account_sync_status` table has RLS enabled | ✅ (migration 013 + 020) |
| Scheduler uses `db_session_for_context()` | ✅ |
| No unsafe `app.tenant_id = ''` in sync execution | ✅ |
| No env fallback in sync service | ✅ |
| `refresh_token` excluded from API request/response | ✅ |
| `has_refresh_token` boolean exposed instead of token | ✅ |

### Contract Drift

| Check | Status |
|-------|--------|
| OpenAPI auto-generated | Needs regeneration from FastAPI app in CI |
| Frontend types match backend | ✅ (manual verification) |

---

## 4. Remaining Risks

### GA Blockers (Must resolve before general availability)

| # | Risk | Impact | Mitigation | Owner |
|---|------|--------|------------|-------|
| 1 | **OAuth Connect UI not implemented** — Frontend still requires manual API key paste. No Salesforce OAuth redirect flow. Admin burden; tokens may be exposed during copy-paste. | High | Documented as known limitation. Acceptable for pilot with trusted admins only. | Frontend team |
| 2 | **No SOQL pagination** — `GetProspectDataTool._get_salesforce_data()` queries without `nextRecordsUrl` handling. Large tenants will silently truncate data. | High | Add cursor-based pagination. Hard ceiling of 2,000 records without pagination. | Backend team |
| 3 | **No E2E smoke tests** — No Playwright tests covering connect → sync → verify flow. Regressions in critical path will not be caught. | High | Add mocked E2E test using MSW handlers. | QA / Frontend |
| 4 | **Distributed scheduler missing** — Background sync uses in-memory `asyncio.create_task`; lost on pod restart. No horizontal scaling. | High | Migrate to Celery + Redis for durable job queue. | Backend team |

### High (Acceptable for pilot, must resolve for GA)

| # | Risk | Impact | Mitigation | Owner |
|---|------|--------|------------|-------|
| 5 | **No KMS integration** — Fernet key from env var. Key rotation requires re-encrypting all tokens. | Medium | Use Infisical/Vault for key management. Document rotation runbook. | Platform / SRE |
| 6 | **Metrics are in-memory** — Prometheus counters reset on restart. No durable metrics history. | Medium | Add Prometheus/OpenTelemetry export. | Backend team |

### Medium

| # | Risk | Impact | Mitigation | Owner |
|---|------|--------|------------|-------|
| 7 | **No deleted record sync** — Salesforce soft-deletes not propagated to Value Fabric. | Low | Add `IsDeleted = false` filter and periodic cleanup job. | Backend team |
| 8 | **Webhook secret not auto-configured** — `salesforce_webhook_secret` must be set manually on app state. | Low | Documented in runbook. Add startup check that logs warning if missing. | Backend team |
| 9 | **OpenAPI not regenerated** — Contract may drift if backend routes change without spec update. | Low | Add `make generate-openapi` to CI pipeline. | DevOps |

---

## 5. Launch Decision

### Recommendation: **PILOT ONLY**

The integration is **safe to deploy for pilot tenants** who:
1. Are willing to manually paste Salesforce access tokens (OAuth UI missing).
2. Have fewer than 2,000 records per query (SOQL pagination missing).
3. Accept that background sync jobs are ephemeral (no Celery/Redis).
4. Are notified that this is a pilot feature with known limitations.

### Required Pre-Pilot Fixes

1. Run migration `021` in staging and production.
2. Configure `SALESFORCE_CLIENT_ID`, `SALESFORCE_CLIENT_SECRET`, `SALESFORCE_REDIRECT_URI` in Infisical.
3. Verify RLS policies are active on `integrations` table.
4. Confirm `CREDENTIALS_MASTER_KEY` is set and ≥ 43 characters.
5. Add pilot tenant flag to gate access (do not expose to all tenants).

### Post-Pilot Roadmap to GA

| Sprint | Deliverable |
|--------|-------------|
| **Sprint 1** | OAuth connect UI — authorization URL, callback handler, success/failure states |
| **Sprint 2** | SOQL pagination + `nextRecordsUrl` handling in `GetProspectDataTool` |
| **Sprint 3** | Celery-based distributed scheduler + durable `sync_jobs` table |
| **Sprint 4** | E2E smoke test (Playwright) for full connect → sync flow |
| **Sprint 5** | KMS integration (AWS KMS / Vault) + automatic key rotation |
| **Sprint 6** | Prometheus metrics export + Grafana dashboards + alert thresholds |

---

## Appendix A: Pilot Checklist

- [x] Env vars documented in `.env.example`
- [x] Salesforce Connected App configuration documented
- [x] Redirect URI documented
- [x] Token encryption key documented
- [x] Migration `021` written
- [ ] Migration `021` applied in staging
- [ ] Migration `021` applied in production
- [x] RLS policies verified (existing from migration 013)
- [ ] Contract drift script passes (pending CI run)
- [x] Typecheck passes for modified frontend files
- [x] Backend syntax checks pass
- [ ] Full backend test suite passes (pending CI with Docker)
- [x] Observability metrics defined
- [x] Operator runbook written
- [x] Rollback plan documented
- [ ] Alert thresholds configured in Prometheus/Grafana
- [ ] Pilot tenant flag implemented (gating)
