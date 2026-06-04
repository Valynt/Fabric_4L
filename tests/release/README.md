# Release Safety Tests

This suite verifies static release controls for Value Fabric production readiness.
It does not deploy, migrate, roll out Kubernetes resources, or call live services.

## Invariants

- Release evidence includes version, commit SHA, build timestamp, environment, and profile metadata.
- Rollback procedures are documented for failed deployments, production release rollback, and database migrations.
- Canary promotion is blocked by health, error-rate, and latency gates.
- Feature flag defaults fail closed for unknown flags and missing tenant or environment context.
- Release artifacts use immutable image references and validated build metadata.

## Evidence Locations

- `artifacts/release/release-safety.json`
- `artifacts/release/gate-result.json`
- `artifacts/release/summary.md`
- `.github/workflows/release-evidence-bundle.yml`
- `.github/workflows/build-deploy.yml`
- `.github/workflows/environment-promotion.yml`

## Validation

```bash
pytest tests/release/
pnpm release:dry-run
pnpm release:rollback:verify
```
