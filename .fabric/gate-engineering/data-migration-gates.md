# Data and Migration Gates

## Migration gate checklist

For every migration, verify:

- [ ] Forward migration tested on production-like volume
- [ ] Old application version can still read data (backward compatibility)
- [ ] New application version can read data (forward compatibility)
- [ ] Mixed-version rollout behavior is safe
- [ ] Lock duration is within SLO
- [ ] Index-build impact is acceptable
- [ ] Backfill duration and correctness are verified
- [ ] Retry behavior is idempotent
- [ ] Rollback or roll-forward plan is documented
- [ ] Data-integrity checks exist
- [ ] Tenant-key preservation is verified
- [ ] Default-value semantics are documented
- [ ] Nullability transition is safe

## Expand-and-contract

Use expand-and-contract for incompatible schema evolution:

1. **Expand** — add new column/table while old code still reads old column.
2. **Migrate** — backfill new representation.
3. **Contract** — remove old column only after all consumers use the new representation.

## Destructive cleanup rules

Do not permit destructive cleanup until:

- All production instances use the new representation.
- Supported rollback versions no longer require the old representation.
- Backfill is complete and verified.
- Reads no longer depend on the old representation.
- Observability confirms zero use during the required window.

## Static gates

- `make check-migration-heads`
- `make check-migration-entrypoints`
- `make check-migration-rollback-policy`
- `make check-migration-runtime-consistency`
- `make gate-database-live` (requires isolated PostgreSQL)

## Live gates

- `scripts/ci/run_db_production_readiness_gate.sh`
- `scripts/ops/test_postgres_backup_restore.sh`

## Evidence

Migration evidence is retained in `artifacts/database/` and `artifacts/release/migrations/` for one year.
