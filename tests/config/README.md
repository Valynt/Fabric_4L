# Configuration Readiness Suite

## What This Suite Validates

This suite verifies production configuration guardrails: required environment variables, safe production defaults, feature flag defaults, secret references, config schema validation, and environment parity.

## Production Risks Covered

- Production startup with missing persistence, auth, cache, or tenant settings.
- Dev-only auth bypass or mock persistence enabled in production-like environments.
- Feature flags or rollout policies defaulting open without tenant or environment guardrails.
- Inline secrets replacing ExternalSecret, Infisical, or Vault references.
- Python and TypeScript config validation drifting apart.

## Existing Coverage Aggregated

- `tests/config/test_startup_validation.py`
- `tests/config/test_startup_tenant_validation.py`
- `tests/config/test_environment_matrix.py`
- `tests/config/test_database_tls_validation.py`
- `tests/config/test_neo4j_aura_validation.py`
- `packages/config/src/env/backend.test.ts`
- `tests/release/test_feature_flag_defaults.py`

## Known Gaps

- LIVE_SECRET_MANAGER_PARITY: CI-safe tests validate references and policy files only; live Infisical/Vault parity remains environment-specific.
- LIVE_ENVIRONMENT_DIFF: the suite does not compare deployed staging and production runtime values.

## How To Run

```bash
pytest tests/config/
pnpm test:config
```

## CI Artifact

CI should publish `artifacts/production-readiness/config/junit.xml`.

