# Database Degradation Runbook

## Purpose

Restore PostgreSQL, Neo4j, pgvector, or related database-backed workflows while
preserving tenant-scoped access, data integrity, migrations, and audit evidence.

## Trigger

- Elevated query latency, connection pool exhaustion, failed health checks, slow
  graph retrieval, failed migrations, or customer-visible database errors.
- Alerts for Postgres, Neo4j, Redis-backed state, pgvector retrieval, or layer
  data-store dependencies.

## Severity

- SEV-1 when a primary database is unavailable, data loss or corruption is
  suspected, cross-tenant data risk exists, or core workflows cannot proceed.
- SEV-2 when latency or partial outage affects major workflows with mitigation.
- SEV-3 when degradation is isolated, bounded, and no data-integrity risk exists.

## Preconditions

- Access to database dashboards, connection pool metrics, query logs, migration
  state, backup status, service logs, and tenant-scoped audit records.
- Database reliability owner approval before restore, failover, migration
  repair, destructive query, or broad index rebuild.

## Immediate Actions

1. Declare incident severity and assign database technical lead.
2. Capture first-bad timestamp, affected database, affected layers, impacted
   tenants, recent migrations, and active alerts.
3. Freeze migrations and non-essential deploys touching affected persistence.
4. Preserve logs, query samples, migration output, backup IDs, and dashboard
   snapshots before remediation.

## Diagnosis Steps

1. Determine whether degradation is availability, latency, lock contention,
   connection pool exhaustion, storage pressure, failed migration, or dependency
   failure.
2. Identify top queries, blocked sessions, error rates, replication or backup
   status, and resource saturation.
3. Confirm queries remain tenant-scoped and do not rely on request-body tenant
   IDs.
4. Check recent schema, index, config, credential, and deploy changes.
5. Validate whether impact is global or tenant-specific.

## Resolution Steps

1. Apply reversible mitigation first: scale capacity, restart unhealthy clients,
   reduce traffic, disable non-critical jobs, or roll back the correlated deploy.
2. Add or rebuild indexes only through approved migration or documented
   operational procedure.
3. Escalate before restore, failover, migration surgery, data repair, queue
   purge, or destructive SQL/Cypher.
4. Keep audit evidence and tenant filters intact during all remediation.

## Validation

- Confirm database health, latency, and connection pools return to expected
  ranges.
- Confirm affected customer workflows recover.
- Confirm tenant-isolation regression or targeted tenant-boundary checks where
  data access paths changed.
- Confirm backup/restore posture remains valid after mitigation.

## Rollback / Fallback

- Roll back recent schema, config, or application changes when correlation is
  clear and rollback is safer than forward fix.
- Use read-only mode, queue pause, or traffic shedding when writes risk data
  integrity.

## Customer / Stakeholder Communication

- Communicate customer symptoms such as delayed workflows or degraded retrieval,
  not internal table names or raw query details.
- Security and Legal review is required before discussing data integrity,
  exposure, or regulated data impact externally.

## Evidence to Preserve

- Query plans, slow query samples, lock graphs, connection metrics, migration
  IDs, backup IDs, sanitized logs, audit events, deployment SHA, and validation
  results.

## Escalation

- Escalate to database reliability, affected layer owner, SRE, Security for
  tenant/data risk, and Legal/Privacy for potential data impact.

## Related Runbooks

- [Incident response workflow](../README.md)
- [API outage](api_outage.md)
- [Production Postgres HA](../../../docs/runbooks/postgres-ha.md)
- [Production Neo4j HA](../../../docs/runbooks/neo4j-ha.md)

## Post-Incident Follow-Up

- Add missing query, pool, migration, backup, or tenant-boundary detection.
- File remediation with owners and due dates in the postmortem.
