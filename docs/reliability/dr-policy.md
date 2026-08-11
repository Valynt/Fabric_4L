# Disaster Recovery Policy

> ## Current Implementation Status (2026-08-10, issue #1264)
>
> **This document states TARGET objectives. Several are not yet implemented.**
> Until each item is marked IMPLEMENTED with evidence, no statement below is a
> capability claim (launch contract: no unsupported availability claims).
>
> | Policy statement | Status @ main | Evidence |
> |---|---|---|
> | Continuous WAL archiving (RPO ≤ 15 min) | **NOT IMPLEMENTED** | `k8s/base/postgres-backup-cronjob.yaml`: `ENABLE_WALG_BACKUP: "false"`, gated by `scripts/ci/check_walg_enablement_gate.py` on missing evidence file |
> | Nightly full snapshot | PARTIAL | Daily 02:00 UTC `pg_dump` to in-cluster PVC — **no off-cluster copy** |
> | Weekly immutable copy in secondary region | **NOT IMPLEMENTED** | No producer of S3/immutable artifacts exists |
> | Retention 35d/12w/12mo | **NOT IMPLEMENTED** | Active retention is 7 days (PVC) |
> | PITR restore via wal-g | **UNVERIFIED** | `.github/workflows/dr-drill.yml` verifies artifacts the disabled WAL-G path never produces |
> | Backup of every production database | PARTIAL | Backup CronJob DB list uses k8s names; compose-named DBs are silently SKIPPED |
> | Rollback: previous version recoverable without data loss | **UNMET (as of 2026-06-13)** | `signoff-evidence/p0-rollback-20260613.json`: drill FAILED; re-rehearsal pending |
> | Redis RDB/AOF snapshotting | NOT VERIFIED in this pass | — |
>
> Remediation is tracked in issue #1257 (V1-DR-001): WAL-G enablement with
> restore-drill evidence, dr-drill alignment to the real backup path, backup
> DB-name reconciliation, and rollback rehearsal.

## Purpose

This policy defines disaster recovery objectives, backup standards, restore validation cadence, and accountability for critical Value Fabric services.

## Scope

This policy applies to production environments for:

- Layer 1 ingestion (PostgreSQL + Redis)
- Layer 2 extraction services
- Layer 3 knowledge API (Neo4j + PostgreSQL/pgvector)
- Layer 4 agents API + workflow orchestration
- Layer 5 ground-truth API + storage
- Platform observability and control-plane components required for incident response

## DR Objectives by Critical Service

| Service | Tier | Data Classification | Target RTO | Target RPO | Primary Recovery Method |
|---|---|---|---:|---:|---|
| PostgreSQL (system of record for layer services) | Tier 0 | Critical transactional | 60 minutes | 15 minutes | Point-in-time restore from continuous WAL + daily full backup |
| Neo4j (knowledge graph) | Tier 0 | Critical derived but operationally required | 90 minutes | 30 minutes | Snapshot restore + replay from ingestion/extraction backlog |
| Redis (queues/cache) | Tier 1 | Rebuildable operational state | 120 minutes | 60 minutes | Rehydrate from upstream systems and durable event sources |
| Layer 4 agents API | Tier 1 | Stateless service + workflow state in DB | 60 minutes | 15 minutes | Re-deploy service + restore backing DB |
| Layer 3 knowledge API | Tier 1 | Stateless service + DB-backed | 60 minutes | 15 minutes | Re-deploy service + restore backing stores |
| Layer 2 extraction workers | Tier 2 | Recomputable pipeline state | 4 hours | 4 hours | Rebuild workers and replay extraction jobs |
| Layer 1 ingestion workers | Tier 2 | Re-ingestable from source | 4 hours | 4 hours | Rebuild workers and replay ingestion from source connectors |
| Layer 5 ground-truth API/store | Tier 1 | Evaluation and benchmark evidence | 120 minutes | 60 minutes | Restore DB snapshots and redeploy API |
| Alerting/telemetry minimum stack | Tier 2 | Operational metadata | 8 hours | 24 hours | Recreate from IaC + retained metrics/log backups |

## Backup Policy

### Backup Frequencies

- **PostgreSQL**
  - Continuous WAL archiving (target granularity ≤ 15 minutes).
  - Nightly full snapshot.
  - Weekly immutable copy in secondary region/account.
- **Neo4j**
  - Nightly consistent backup.
  - Weekly immutable copy in secondary region/account.
- **Redis**
  - Hourly RDB snapshot for disaster scenarios.
  - AOF enabled where durability is required by queue semantics.
- **Configuration and Infrastructure Artifacts**
  - Daily export of Kubernetes manifests/Helm values and critical secrets metadata (never raw secret values in git).
- **Runbooks and Incident Evidence**
  - Backed up with docs repository and artifact retention policy.

### Retention

- Daily backups retained for 35 days.
- Weekly backups retained for 12 weeks.
- Monthly backups retained for 12 months.
- Immutable backup retention lock enabled for Tier 0 data.

## Backup Restore Verification Cadence

| Test Type | Scope | Cadence | Exit Criteria |
|---|---|---|---|
| Backup integrity check | All Tier 0/1 backup artifacts | Daily automated | Backup artifact is present, readable, and checksum-verified |
| Database object restore drill | PostgreSQL + Neo4j sampled dataset | Weekly | Successful restore to isolated environment and smoke query pass |
| Service-level DR game day | Tier 0 + Tier 1 services | Monthly | End-to-end recovery within documented RTO/RPO envelope |
| Region/account loss simulation | Platform-wide | Quarterly | Demonstrated rebuild from isolated backups and IaC |
| Executive readiness review | Program-level governance | Semiannual | Risks, exceptions, and remediation plan approved |

## Roles and Responsibilities

- **Incident Commander (IC):** Owns disaster declaration and recovery priorities.
- **Database Recovery Lead:** Executes DB restore procedures and validates data consistency.
- **Service Owner:** Restores service deployments and validates health checks.
- **SRE On-Call:** Coordinates infra recovery, access, and observability.
- **Compliance/Security:** Validates evidence capture and policy adherence.

## Evidence Requirements

Each recovery test (planned or unplanned) must include:

1. Scenario description and blast radius.
2. Start/end timestamps and measured RTO/RPO.
3. Restore commands/automation identifiers.
4. Validation evidence (health checks, sample queries, API checks).
5. Follow-up actions with owner and due date.

Use `docs/runbooks/dr-evidence-log-template.md` for consistent evidence capture.

## Exception Management

Any exception to RTO/RPO targets must:

- Be documented in writing with business impact.
- Include compensating controls.
- Include remediation owner and deadline.
- Be reviewed at least quarterly until closed.

## Policy Review Cadence

- Reviewed quarterly by platform engineering + security.
- Updated after any Severity 1 incident or failed DR exercise.
