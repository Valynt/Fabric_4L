# Rollback and Recovery Policy

## Scope

This policy applies to rollback and disaster recovery for the Fabric_4L production environment.

## Rollback readiness gate

Before every production release, the following must be proven:

- Previous production artifact digest is recorded and available in the registry.
- Data written by the new version is readable by the rollback version, or a safe roll-forward path exists.
- Database migration compatibility is documented.
- Event consumers tolerate replay and version skew.
- Rollback does not duplicate side effects (idempotent connectors, idempotent workers).
- Long-running workflows can resume or be safely superseded.

## Recovery objectives

| Objective | Target | Validation |
|---|---|---|
| Recovery Point Objective (RPO) | ≤ 5 minutes | Backup frequency and WAL shipping |
| Recovery Time Objective (RTO) | ≤ 1 hour | Quarterly DR drill |
| Restore verification | Quarterly | `pnpm ops:restore:dry-run` |

## Rollback decision authority

- Automatic rollback: triggered by canary or post-deployment gates.
- Manual rollback: executed by release manager or incident commander.
- Emergency rollback: any on-call engineer may invoke after paging the release manager.

## Idempotency

All external connector operations and worker side effects must be idempotent. Releases that introduce non-idempotent side effects are blocked until a compensating mechanism is proven.

## Rollback prohibition

Rollback is prohibited when:

- The previous artifact is unavailable or untrusted.
- The migration compatibility matrix shows the previous version cannot read new data and no roll-forward path exists.
- Rollback would corrupt data or duplicate financial side effects.

## Evidence

Rollback evidence is recorded in `artifacts/release/rollback/` and retained for one year.
