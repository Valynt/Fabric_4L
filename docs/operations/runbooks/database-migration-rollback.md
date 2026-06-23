# Database Migration Rollback Runbook

This runbook defines the rollback strategy for Alembic-managed PostgreSQL migrations in Layer 1, Layer 2, Layer 2.5, Layer 4, Layer 5, and the API gateway.

## Mandatory validation

Before production approval, the database production-readiness gate must run against PostgreSQL:

```bash
make gate-database-live DB_MIGRATION_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/postgres
```

The gate runs static migration graph checks, unsupported-downgrade policy checks, an upgrade to `head`, a one-revision downgrade where supported, a second upgrade to `head`, and SQLAlchemy metadata drift comparison against the migrated PostgreSQL schema.

## Standard rollback strategy

For migrations with supported Alembic downgrades:

1. Stop writes for the affected service or put the service in maintenance mode.
2. Snapshot the database and verify the backup can be restored.
3. Run `alembic downgrade -1` from the owning service directory.
4. Run service health checks and tenant-boundary smoke checks.
5. Resume traffic only after the rollback owner signs off.

## Unsupported downgrade policy

A migration may intentionally omit a downgrade only when reversing it is unsafe, lossy, or operationally impossible. Such a migration must document a rollback strategy and require explicit production approval before deployment.

Required controls for every intentionally unsupported downgrade:

- The migration source must explain why the downgrade is unsupported.
- This runbook must list the migration path and owning service.
- The release ticket must include explicit production approval from the database owner and service owner.
- The rollback strategy must be one of:
  - restore from backup into the pre-migration release point;
  - forward-fix with a new migration after preserving affected data;
  - blue/green cutover back to the previous database snapshot.

## Currently approved unsupported downgrades

No Alembic-managed service currently has an intentionally unsupported downgrade. If one is added, append a subsection here using this template:

```markdown
### `services/<service>/migrations/versions/<revision>.py`

- Service: `<service>`
- Reason downgrade is unsupported: `<why reversal is unsafe>`
- Rollback strategy: `restore from backup` or `forward-fix` or `blue/green snapshot cutover`
- Required explicit production approval: database owner + service owner
- Validation evidence: `<artifact or CI run>`
```

## API gateway SQL migrations

The API gateway migration root (`services/api/migrations/versions`) includes SQL-authored migrations bridged through Alembic revision files. Because the SQL files are the authoritative schema for that root, metadata drift comparison is skipped for the API gateway; upgrade/downgrade execution remains mandatory in the PostgreSQL round-trip gate.
