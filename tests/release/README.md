# Release Safety Tests

## What This Suite Validates

This suite verifies static release controls for Value Fabric production readiness. It does not deploy, migrate, roll out Kubernetes resources, or call live services.

## Production Risks Covered

- Release candidates without immutable identity metadata.
- Missing or untested rollback procedures.
- Canary promotion without health, error-rate, and latency gates.
- Feature flags defaulting open for unknown tenants or environments.
- Release artifacts using mutable image references or placeholder build metadata.

## Existing Coverage Aggregated

- `tests/release/test_release_metadata.py`
- `tests/release/test_database_migration_rollback.py`
- `tests/release/test_feature_flag_defaults.py`
- `tests/release/test_canary_health_gates.py`
- `tests/release/test_rollback_procedure.py`
- `tests/release/test_release_artifact_integrity.py`
- `.github/workflows/release-evidence-bundle.yml`
- `.github/workflows/environment-promotion.yml`

## Known Gaps

- LIVE_CANARY_PROMOTION: live promotion remains workflow/environment-specific.
- LIVE_DATABASE_ROLLBACK: this suite validates rollback policy and dry-run evidence, not a production database rollback.

## How To Run

```bash
pytest tests/release/
pnpm test:release
pnpm release:dry-run
pnpm release:rollback:verify
```

## CI Artifact

CI should publish `artifacts/production-readiness/release/junit.xml` and `artifacts/production-readiness/release/summary.md`. Related release evidence remains:

- `artifacts/release/release-safety.json`
- `artifacts/release/gate-result.json`
- `artifacts/release/summary.md`

