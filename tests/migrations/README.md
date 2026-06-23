# Database Migration Safety Suite

This suite verifies production-readiness invariants for Value Fabric database
migrations. It intentionally combines fast static policy tests with a live
PostgreSQL round-trip hook.

Run the static suite:

```bash
pytest tests/migrations/
```

Run live migration validation against an isolated PostgreSQL maintenance
database:

```bash
MIGRATION_DRIFT_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/postgres pnpm db:migrate:test
```

Generate the read-only schema and migration drift report:

```bash
make db-migrate-check
```

## Policy Coverage

- Alembic-managed services must have a single ordered revision head.
- File-managed Layer 3 and Layer 6 migrations must have deterministic numeric
  ordering for schema-changing files.
- Live validation must migrate disposable databases from empty schema to head,
  exercise a one-step downgrade/upgrade round trip where supported, and compare
  SQLAlchemy metadata to the migrated schema.
- Destructive migrations must be documented in the rollback runbook and require
  explicit production approval or a phased rollout guard.
- Expand/contract changes must avoid adding non-null columns to existing tables
  without a default, backfill, or explicit precondition.
- Raw SQL index creation must be idempotent or non-blocking. Large table index
  migrations must use `CONCURRENTLY` or document an equivalent phased strategy.

