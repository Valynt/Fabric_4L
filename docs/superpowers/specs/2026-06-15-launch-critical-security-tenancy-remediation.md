# Launch-Critical Security & Tenancy Remediation Design

**Date:** 2026-06-15  
**Status:** Active — audit note added 2026-07-18.
**Goal:** Fix the High and Critical code-level security and tenancy findings that are most likely to block launch or cause incidents, without destabilizing the rest of the platform.  
**Scope:** Code-level security/tenancy defects only. CI/CD, K8s, frontend hygiene, and large architecture refactorings are out of scope for this pass and will be tracked separately.

> **Audit note (2026-07-18):** The Layer 4 executable sub-plan is `docs/superpowers/plans/2026-06-15-layer4-security-tenancy-plan.md`. Some tasks (e.g., API-key hardening, auth-bypass consolidation) have already landed in `services/api` and `packages/shared`; verify current code before re-implementing. The older `docs/superpowers/plans/2026-06-14-remediation-sprint-plan.md` has been archived as superseded by `2026-06-15-remediation-sprint-p0.md`.

---

## 1. Problem Summary

The 2026-06-15 audit produced the following launch-critical findings. The table below maps each finding to the confirmed file(s), current state, and the proposed fix.

| ID | Severity / Domain | Problem | File(s) | Current State | Proposed Fix |
|---|---|---|---|---|---|
| SEC-001 | Critical Security | SQL injection via f-string DDL in tenant provisioning. | `services/layer4-agents/src/layer4_agents/services/tenant_provisioning.py` | REAL | Derive schema name safely; use SQLAlchemy `CreateSchema` / identifier quoting; never interpolate identifiers into raw SQL. |
| SEC-002 | Critical Security | Hardcoded Neo4j password `"password"` in Layer 4 tools. | `services/layer4-agents/src/layer4_agents/tools/knowledge.py`, `competitive_tools.py`, `knowledge_tools.py` | REAL | Remove all default fallbacks to `"password"`; consume `get_settings().neo4j_password` or fail closed if missing. |
| SEC-003 | Critical Security | Hardcoded MinIO credentials in Layer 1 config and compose. | `services/layer1-ingestion/src/layer1_ingestion/shared/config.py`, `src/shared/config.py`, `docker-compose*.yml` | REAL | Remove hardcoded defaults from code and all compose files; require env vars; update `.env.example` and Infisical templates with safe local-only values. |
| SEC-004 | Critical Security | Cypher injection via f-string `WHERE`/relationship/predicate clauses in Layer 4 services and tools. | `services/layer4-agents/src/layer4_agents/services/value_hypothesis_engine.py`, `narrative_builder_service.py`, `variable_registry_service.py`, `tools/knowledge_tools.py`, plus other direct `session.run` callers | MITIGATED (values parameterized) | Keep parameterization; migrate direct `session.run` calls to `tenant_cypher.py` seam; add contract tests covering relationship-type/predicate/depth injection, not just value f-strings. |
| SEC-005 | Critical Security | Cypher injection in Layer 3 knowledge services. | `services/layer3-knowledge/src/services/roi_calculator_service.py`, `case_study_service.py`, `competitive_intel_service.py` | MITIGATED (validated) | Ensure `validate_tenant_scoped_cypher` / `run_validated_query` are always called; add regression tests for failure modes. |
| TEN-001 | Critical Tenancy | S3 object keys are not tenant-scoped at the storage layer. | `services/layer4-agents/src/layer4_agents/services/export_storage.py` | REAL | Centralize key construction in `export_storage.py`; require `tenant_id` and prefix every key with `f"{tenant_id}/"`. Update callers to pass a relative object name. |
| TEN-002 | Critical Tenancy | `CrawlDecisionRepository` queries rely on RLS only. | `services/layer1-ingestion/src/layer1_ingestion/crawler/decision_store.py` | REAL | Add explicit `tenant_id = :tenant_id` predicates to all repository queries. |
| SEC-006 | High Security | Four auth-bypass env flags create persistent attack surface. | `packages/shared/src/value_fabric/shared/security/config.py`, `startup/validator.py`, `identity/auth_mode.py`, `services/layer5-ground-truth/src/layer5_ground_truth/config.py` | PARTIALLY MITIGATED | Consolidate all flag checks into a single canonical helper; tolerate flags **only** when `ENVIRONMENT=local`; make any set flag fatal in every other environment. |
| SEC-009 | High Security | SQL injection via f-string table name in Layer 4 tenant API. | `services/layer4-agents/src/layer4_agents/api/tenants.py`, `tenants/api/routes/admin_dashboard.py` | MITIGATED (input allow-listed) | Replace f-string table/SET interpolation with pre-built statements or identifier quoting; add contract test proving unknown table names are rejected. |
| SEC-010 | High Security | Clerk webhook endpoint lacks rate limiting. | `services/api/app/routers/clerk_webhooks.py`, `services/api/app/main.py`, `packages/shared/src/value_fabric/shared/fastapi_framework/app.py`, `packages/shared/src/value_fabric/shared/fastapi_framework/middleware.py` | REAL | Add endpoint-specific IP-based rate limiting to `/clerk` that handles `X-Forwarded-For`; do not rely on `TenantRateLimitMiddleware` (it skips unauthenticated paths). |
| TEN-003 | High Tenancy | Layer 2.5 `db_session` permits `None` tenant, disabling RLS. | `services/layer2-5-signal-refinery/src/layer2_5_signal_refinery/database.py` | REAL | Make `tenant_id` required; audit all callers and fix any that pass `None`. |
| TEN-007 | High Tenancy | Tenant mismatch enforcement is opt-in, not automatic. | `services/layer4-agents/src/layer4_agents/services/tenant_query_helper.py`, `tenant_cypher.py`, and all Layer 4 Neo4j callers | REAL | Migrate all Layer 4 graph calls to the `tenant_cypher.py` seam (`fetch_tenant_validated_records` / `fetch_tenant_validated_single`), which structurally enforces a tenant predicate and validates the parameter. |

---

## 2. Detailed Design

### 2.1 SEC-001 — Safe tenant schema provisioning

**File:** `services/layer4-agents/src/layer4_agents/services/tenant_provisioning.py`

**Change:**
- Keep deriving `schema_name = f"tenant_{tenant_id.hex[:8]}"` because `tenant_id` is a UUID.
- Build the `CREATE SCHEMA` and `GRANT` statements with SQLAlchemy `CreateSchema` or `quoted_name`, or validate the schema name against `^[a-z_][a-z0-9_]*$` and use `psycopg2.sql.Identifier`.
- For `GRANT USAGE ON SCHEMA ... TO app_user`, parameterize only the literal `app_user` via config; do not interpolate user input.

**Validation:**
- Existing tenant provisioning tests pass.
- Add a contract test that proves a malformed schema identifier cannot be injected (UUID only today, so test asserts no f-string identifiers).

### 2.2 SEC-002 — Remove hardcoded Neo4j passwords

**Files:**
- `services/layer4-agents/src/layer4_agents/tools/knowledge.py`
- `services/layer4-agents/src/layer4_agents/tools/competitive_tools.py`
- `services/layer4-agents/src/layer4_agents/tools/knowledge_tools.py`

**Change:**
- Replace `os.getenv("NEO4J_PASSWORD", "password")` and `config.get("neo4j_password", "password")` with `get_settings().neo4j_password` (Layer 4 settings already default to `None`).
- Raise a clear `ConfigurationError` at import/init time if the password is missing.
- Do **not** add a local-dev fallback in source code; local defaults live only in `.env.example`/Infisical.

**Validation:**
- Unit tests for these tools fail until `NEO4J_PASSWORD` is present in test env; update `pytest.ini` / test fixtures.
- No literal `"password"` remains in the Layer 4 tools directory (grep check).

### 2.3 SEC-003 — Remove hardcoded MinIO credentials

**Files:**
- `services/layer1-ingestion/src/layer1_ingestion/shared/config.py`
- `services/layer1-ingestion/src/shared/config.py`
- `services/layer1-ingestion/docker-compose.yml`
- `docker-compose.dev.yml`, `docker-compose.backend-integrated.yml`, `docker-compose.contract.yml`, `docker-compose.release-smoke.yml`
- `.env.example` and Infisical templates

**Change:**
- Remove `Field(default="minioadmin")` for `s3_access_key` and `s3_secret_key`.
- In compose files, replace literal `minioadmin` with `${MINIO_ROOT_USER:?MISSING}` / `${MINIO_ROOT_PASSWORD:?MISSING}` and similarly for `LAYER1_S3_*`.
- Add `MINIO_ROOT_USER=minioadmin`, `MINIO_ROOT_PASSWORD=minioadmin`, `LAYER1_S3_ACCESS_KEY=minioadmin`, `LAYER1_S3_SECRET_KEY=minioadmin` to `.env.example` with a `LOCAL DEV ONLY` comment.
- Update `mc config host add` command to use env vars.

**Validation:**
- `make test-layer1` passes with env vars set.
- `docker compose -f docker-compose.dev.yml config` parses successfully after adding vars.
- A startup check fails fast if credentials are missing.

### 2.4 SEC-004 / SEC-005 — Harden dynamic Cypher builders

**Files:** Layer 4 and Layer 3 services/tools listed above.

**Change:**
- Keep existing value parameterization/validation.
- For Layer 4, migrate every direct `session.run(...)` / `execute_query(...)` call to `tenant_cypher.py` (`fetch_tenant_validated_records`, `fetch_tenant_validated_single`).
- For Layer 3, keep using `validate_tenant_scoped_cypher` + `run_validated_query`; add a regression test that fails if a query lacks an explicit `tenant_id` predicate.
- Add a contract test that inspects Cypher strings and rejects user-controlled value interpolation while permitting identifier allow-list interpolation (e.g., relationship types from a hardcoded set).

**Validation:**
- New contract test passes.
- Existing service tests still pass.
- Tenant-boundary test proves a query without `tenant_id` predicate is rejected.

### 2.5 TEN-001 — Tenant-scoped S3 keys

**File:** `services/layer4-agents/src/layer4_agents/services/export_storage.py`

**Change:**
- Add `tenant_id: str` as a required parameter to `upload_bytes`, `download_bytes`, and `delete_object`.
- Change the internal key to `f"{tenant_id}/{object_key}"`, stripping any leading tenant prefix the caller may have already added.
- Update current callers (`analysis.py`, `tools.py`) to pass only a relative object name and the `tenant_id`.
- Reject object keys containing `..` or leading `/` to prevent path traversal.

**Validation:**
- Unit test proves keys are always prefixed with the tenant segment.
- Unit test proves a traversal attempt is rejected.
- Existing export tests pass after caller migration.

### 2.6 TEN-002 — Explicit tenant filters in crawl decisions

**File:** `services/layer1-ingestion/src/layer1_ingestion/crawler/decision_store.py`

**Change:**
- Add `tenant_id: str` to method signatures (`get_by_id`, `get_by_job`, `get_by_url`, `get_by_domain`, list methods).
- Append `.where(table.c.tenant_id == tenant_id)` to every query.
- If the repository is sometimes used with an RLS-applied session, still add the predicate (defense in depth).

**Validation:**
- Update repository tests to assert queries include `tenant_id`.
- Add a tenant-boundary test proving Tenant B decisions are not returned for Tenant A.

### 2.7 SEC-006 — Reduce auth-bypass attack surface

**Files:**
- `packages/shared/src/value_fabric/shared/security/config.py`
- `packages/shared/src/value_fabric/shared/startup/validator.py`
- `packages/shared/src/value_fabric/shared/identity/auth_mode.py`
- `services/layer5-ground-truth/src/layer5_ground_truth/config.py`

**Change:**
- Create one canonical helper `_bypass_flags_are_set()` and one canonical helper `_raise_if_bypass_in_nonlocal_env()`.
- Treat any value other than unset/`false`/`0` as "set".
- In non-`local` environments, raise `RuntimeError` / add fatal validation error if any flag is set.
- In `local`, log a single prominent warning.
- Keep flags documented in `.env.example` but add a comment: `LOCAL DEV ONLY — will fail startup in production`.

**Validation:**
- Test that setting any bypass flag with `ENVIRONMENT=production` causes startup failure.
- Test that `ENVIRONMENT=local` with flags set logs warning but starts.

### 2.8 SEC-009 — Safe table/SET interpolation

**Files:**
- `services/layer4-agents/src/layer4_agents/api/tenants.py`
- `services/layer4-agents/src/layer4_agents/tenants/api/routes/admin_dashboard.py`

**Change:**
- For `tenants.py`: map each allowed table in `_TENANT_ENTITY_TABLES` to a pre-built `text('SELECT COUNT(*) FROM "{table}" WHERE tenant_id = :tenant_id')` or use SQLAlchemy `quoted_name`/identifier quoting.
- For `admin_dashboard.py`: build the `SET` clause from a fixed field map with bound parameters; do not concatenate user-controlled keys or values.

**Validation:**
- Add a contract test that an unknown table/column is rejected.
- Existing tenant admin tests pass.

### 2.9 SEC-010 — Rate-limit Clerk webhooks

**Files:**
- `services/api/app/routers/clerk_webhooks.py`
- `services/api/app/main.py`
- `packages/shared/src/value_fabric/shared/fastapi_framework/app.py`
- `packages/shared/src/value_fabric/shared/fastapi_framework/middleware.py`

**Change:**
- Add a per-endpoint rate-limit dependency to the `/clerk` route keyed on source IP.
- Use a small in-memory limiter (e.g., `slowapi`/`limits`) rather than `TenantRateLimitMiddleware`, because webhooks are unauthenticated and have no tenant context.
- Derive the client IP from `X-Forwarded-For` last? No, **first** safe non-private IP, with a configurable number of trusted proxy hops. Default to `request.client.host` when no proxy headers are present.
- Configure a generous limit (e.g., 30 requests/minute) documented in `.env.example`.

**Validation:**
- Add a test proving >N requests/min from the same IP returns 429.
- Add a test proving `X-Forwarded-For` is honored correctly.
- Existing webhook tests still pass.

### 2.10 TEN-003 — Require tenant_id in Layer 2.5 sessions

**File:** `services/layer2-5-signal-refinery/src/layer2_5_signal_refinery/database.py`

**Change:**
- Change `db_session(tenant_id: str | None = None)` to require `tenant_id: str`.
- Audit all callers with grep for `db_session(` / `db_session()` and update any that pass `None`.
- Keep `SET LOCAL app.tenant_id = :tenant_id` execution.

**Validation:**
- Update unit tests to pass a tenant_id.
- Add a test proving `None` raises.

### 2.11 TEN-007 — Automatic tenant validation for Layer 4 Cypher

**Files:**
- `services/layer4-agents/src/layer4_agents/services/tenant_cypher.py`
- All Layer 4 Neo4j callers, including but not limited to:
  - `value_hypothesis_engine.py`
  - `narrative_builder_service.py`
  - `variable_registry_service.py`
  - `value_pack_service.py`
  - `formula_governance_service.py`
  - `intelligence_orchestrator.py`
  - `api/routes/analysis.py`
  - `services/tenant_provisioning.py` (Neo4j constraint check)

**Change:**
- Use `tenant_cypher.py` (`fetch_tenant_validated_records` / `fetch_tenant_validated_single`) as the single seam for all graph reads/writes.
- These helpers already structurally require a `tenant_id` predicate and validate the supplied parameter.
- Remove or deprecate `tenant_query_helper.py::run_tenant_validated_query()` because it only checks parameter mismatch, not structural tenant filtering.

**Validation:**
- Add a tenant-boundary test that a mismatched `tenant_id` parameter is rejected.
- Add a contract test that a Cypher string lacking a tenant predicate is rejected.
- Existing Layer 4 graph tests pass.

---

## 3. Out of Scope

The following audit categories are **not** part of this remediation pass and will be tracked in a follow-up issue/spec:

- Frontend lint/hygiene findings (e.g., `any` types, dead code, a11y).
- Large architecture refactorings (Layer 4 accessing Neo4j, Layer 3 ROI calculator, L4 billing duplicating L7, multiple Alembic bases).
- CI/CD workflow and K8s manifest hardening beyond env-var hygiene touched by SEC-003/SEC-006.
- Test-coverage gaps unrelated to the specific behaviors above.

---

## 4. Testing Strategy

1. **Targeted unit/contract tests:** For each finding, add or update tests that prove:
   - Intended allowed behavior passes.
   - Intended denied behavior fails (e.g., missing tenant, bad key prefix, injection attempt, bypass flag in production).
2. **Integration tests:**
   - Missing `NEO4J_PASSWORD` / MinIO credentials cause startup failure.
   - Cross-tenant graph reads are rejected by the validating runner.
   - S3 export key prefix enforcement works against the configured store.
   - Clerk webhook 429 behavior under burst and behind `X-Forwarded-For`.
3. **Layer tests:** Run the affected layer tests individually:
   - `make test-layer1`
   - `make test-layer2`
   - `make test-layer3`
   - `make test-layer4`
   - `make test-layer5` (for SEC-006 config impact)
4. **Security/contract marker tests:**
   - `pytest tests/security -m tenant_boundary`
   - `pytest -m security`
   - `make contract-tests`
5. **Compose smoke:** Validate `docker compose -f docker-compose.dev.yml config` after env-var changes.
6. **Full verify:** `make verify` after all targeted changes pass.

---

## 5. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Removing hardcoded defaults breaks local/dev startup | Update `.env.example`, `docker-compose.dev.yml`, and CI env files before changing code; run `pnpm env:dev` path. |
| Adding tenant filters changes query semantics | Add defense-in-depth predicates only; RLS remains in place. Tests cover both paths. |
| S3 key-prefix enforcement breaks existing callers | Centralize prefix construction in `export_storage.py` and update callers to pass relative names. |
| Tenant mismatch enforcement may break existing callers | Migrate callers incrementally to `tenant_cypher.py`; keep direct-driver calls behind the helper. |
| Rate limiting on webhooks may drop legitimate bursts | Use a generous limit (30/min) and document tuning in `.env.example`; honor `X-Forwarded-For`. |
| Auth-bypass hardening may block legitimate test harnesses | Keep `ENVIRONMENT=local` path working; update test fixtures with explicit local env. |
| AST/token lint test false-positives on legitimate templates | Distinguish user-controlled value interpolation from identifier allow-list interpolation in the test. |

---

## 6. Definition of Done

- [ ] SEC-001: Tenant provisioning uses safe identifier handling; no f-string DDL.
- [ ] SEC-002: No hardcoded `"password"` in Layer 4 Neo4j tool code; tools consume settings.
- [ ] SEC-003: No hardcoded MinIO credentials in Layer 1 code or any compose file; `.env.example` updated.
- [ ] SEC-004/005: Dynamic Cypher builders are regression-tested against value, relationship-type, and predicate injection.
- [ ] TEN-001: S3 storage layer centralizes key construction with tenant prefix.
- [ ] TEN-002: Crawl decision repository always filters by `tenant_id`.
- [ ] SEC-006: Auth-bypass flags fatal in non-local environments; local path still works.
- [ ] SEC-009: Tenant API table/SET interpolation uses allow-list or identifier quoting.
- [ ] SEC-010: Clerk webhook endpoint has IP-based rate limiting that handles proxy headers.
- [ ] TEN-003: Layer 2.5 `db_session` requires `tenant_id`; callers audited and fixed.
- [ ] TEN-007: Layer 4 graph queries use the `tenant_cypher.py` validating seam.
- [ ] All new/changed unit, integration, and security-marker tests pass.
- [ ] `make verify` passes.
- [ ] This spec and `docs/launch/launch-blocker-register.md` are updated with residual risks.
