# Elevate-to-9 Migration Report

**Date:** 2026-05-27
**Plan:** elevate-to-9-a79d0e
**PRs:** 5 sequential surgical PRs

## Executive Summary

Delivered framework-level fixes once so all eight services inherit them automatically.
All new controls default to `AUDIT` (log-only) for backward compatibility; per-service
`ENFORCE` flip is a follow-up after each service's tests pass.

## PR 1 — Shared Framework Compatibility Controls

### Files Added
- `packages/shared/src/value_fabric/shared/fastapi_framework/health.py`
- `packages/shared/src/value_fabric/shared/fastapi_framework/logging.py`
- `packages/shared/src/value_fabric/shared/fastapi_framework/tests/test_pr1_controls.py`

### Files Modified
- `packages/shared/src/value_fabric/shared/fastapi_framework/app.py`
- `packages/shared/src/value_fabric/shared/fastapi_framework/middleware.py`
- `packages/shared/src/value_fabric/shared/fastapi_framework/__init__.py`

### What Changed
- Added `HealthCheckProbe` protocol + `aggregate_probes()` with per-probe timeout and caching.
- Added `register_readiness_endpoint()` with 503 response when probes fail.
- Added `StructuredLoggingConfig` + `configure_structlog()` (graceful no-op when structlog absent).
- Added `FrameworkRateLimitConfig` and `FrameworkIdempotencyConfig` dataclasses.
- Extended `create_fabric_app()` with 5 new keyword args (all default to None/inert).
- Wired conditional middleware installation for tenant enforcement, rate limiting, idempotency.
- All controls default to `EnforcementMode.AUDIT`.

### Test Coverage
- 13 new unit tests covering OFF/AUDIT/ENFORCE modes, readiness endpoint, probe timeout/failure, signature stability.

## PR 2 — Async PostgreSQL Session Layer

### Files Added
- `packages/shared/src/value_fabric/shared/database/lifespan.py`
- `packages/shared/src/value_fabric/shared/database/tests/test_pr2_lifespan.py`
- `tests/arch/test_async_session_only.py`
- `config/ci/async_session_legacy_baseline.txt`

### Files Modified
- `packages/shared/src/value_fabric/shared/database/__init__.py`

### What Changed
- Added `pg_lifespan()` context manager for engine + session_maker lifecycle.
- Added `PostgresHealthProbe` implementing the `HealthCheckProbe` protocol.
- Added architecture gate `test_async_session_only.py` that blocks new sync `create_engine` use.
- Documented baseline exception for `services/layer1-ingestion/src/shared/database.py` (intentional RLS sync bypass).

### Test Coverage
- 5 tests (probe healthy/unhealthy/timeout, exception safety, architecture gate).

## PR 3 — HTTPException Router Codemod + CI Gate

### Files Added
- `scripts/ci/check_no_raw_httpexception_in_routers.py`
- `scripts/ci/tests/test_no_raw_httpexception_gate.py`
- `config/ci/httpexception_router_allowlist.txt`

### What Changed
- Created AST-based CI gate that scans router/API boundary files for raw `raise HTTPException(...)`.
- Frozen 724-entry baseline of pre-existing router usages.
- Gate fails the build when new offenders appear outside the baseline.
- Provides canonical exception mapping guidance in error output.

### Test Coverage
- 5 gate-teeth tests (pass on clean baseline, detect new offender, skip allowlisted, attribute form detection, skip unrelated raises).

## PR 4 — Infrastructure Secret Sweep

### Files Added
- `scripts/ci/audit_infra_secrets.py`
- `scripts/ci/tests/test_audit_infra_secrets.py`
- `config/ci/infra_secret_baseline.txt`
- `infra_secret_mapping.md`

### What Changed
- Created regex-based CI gate scanning docker-compose, K8s, workflows, and .env.example files.
- Detects literal values for password/secret/token/api_key fields.
- Treats `${VAR}`, `{{ secrets.X }}`, `secretKeyRef`, empty placeholders, and `<CHANGE_ME>` as safe.
- Frozen 93-entry baseline.
- Auto-generated Markdown remediation mapping table.

### Test Coverage
- 4 tests (clean baseline, blocks new offender, allows env references, allows placeholders).

## PR 5 — Observability Modernization + CI Gate

### Files Added
- `scripts/ci/check_otel_tracer_provider_centralization.py`
- `scripts/ci/tests/test_otel_tracer_provider_gate.py`
- `config/ci/otel_tracer_provider_baseline.txt`

### What Changed
- Created AST-based CI gate detecting `TracerProvider(...)` and `set_tracer_provider(...)` outside the shared framework.
- Frozen 6-entry baseline (layer1-ingestion, layer3-knowledge, layer4-agents pre-existing sites).
- Added `--repo-root` CLI override for testability.
- No legacy Python tracer module found in `packages/shared/src/value_fabric/shared/tracing/` (only config + docs).

### Test Coverage
- 4 tests (clean baseline, detects name form, detects attribute form, skips unrelated raises).

## Metrics

| Metric | Count |
|---|---|
| New framework modules | 3 |
| New CI gate scripts | 3 |
| New test files | 7 |
| New config baselines | 4 |
| Total new tests added | 31 |
| Pre-existing router HTTPException sites (frozen) | 724 |
| Pre-existing infra secret findings (frozen) | 93 |
| Pre-existing TracerProvider sites (frozen) | 6 |
| Services with sync `create_engine` exception (documented) | 1 |

## Next Steps (Post-PR5)

1. **Per-service ENFORCE flip**: Bump each service's `EnforcementRolloutConfig` from AUDIT to ENFORCE for rate_limit, idempotency, tenant_enforcement after that service's CI is green for one week. One tiny PR per service (eight total).

2. **Migrate 6 TracerProvider baselines**: Refactor layer1-ingestion, layer3-knowledge, and layer4-agents to use the shared `init_telemetry()` rather than instantiating their own `TracerProvider`.

3. **Remediate 93 infra secret findings**: Replace literal values with ExternalSecret / Vault / Infisical references, then remove from baseline.

4. **Migrate 724 router HTTPException sites**: Apply codemod (or manual migration) to canonical exceptions, then remove from baseline.

5. **Wiring L2.5 + L7 billing**: Out of scope for these five PRs; tracked separately on ROADMAP.md.
