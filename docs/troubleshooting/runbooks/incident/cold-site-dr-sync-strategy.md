# Cold-Site DR Sync Strategy

## Purpose

Use this runbook to rehearse cold-site recovery from a staging failure without claiming production DR readiness. The drill validates that Tier 0 PostgreSQL recovery can meet the policy target of 60-minute RTO and 15-minute RPO when continuous WAL plus daily full backups are available.

## Scope

This drill covers repository-owned procedure and evidence expectations for:

- PostgreSQL backup presence, WAL availability, and restore timing.
- Neo4j backup presence and replay readiness.
- Kubernetes/IaC redeployability into an isolated cold-site namespace or cluster.
- Application health checks after restored stores are attached.

It does not close production DR readiness unless executed in an approved staging or production-like environment with owner sign-off and redacted evidence.

## Preconditions

- Approved drill window and incident commander assigned.
- DR backup bucket access through the approved role only.
- Cold-site namespace or cluster available and isolated from production.
- External secrets resolved without copying raw values into logs or artifacts.
- Release candidate SHA and environment name recorded before execution.

## Procedure

1. Declare the simulated staging failure and record the start timestamp.
2. Freeze unrelated deploys and confirm the rollback/restore owner.
3. Verify latest PostgreSQL full backup and WAL sequence in the backup bucket.
4. Verify latest Neo4j backup and expected replay source.
5. Restore PostgreSQL into the cold-site target and run tenant-scoped integrity checks.
6. Restore or attach Neo4j backup, then run graph smoke queries for at least one tenant-scoped sample.
7. Redeploy required services from immutable release images and IaC.
8. Run `/health` and `/ready` checks for affected layers.
9. Run the critical-path smoke or approved substitute against the cold-site endpoint.
10. Record end timestamp, measured RTO, measured RPO, failures, and owner decision.

## Evidence Contract

Attach only redacted evidence:

- Drill transcript with command identifiers, not secrets.
- Backup object timestamps and checksum status.
- Restore start/end timestamps.
- Measured RTO and RPO versus policy target.
- Data-integrity query summaries.
- Service health output.
- Release candidate SHA.
- Incident commander and SRE owner approval.

Do not attach raw database contents, bearer tokens, cloud credentials, private keys, customer payloads, or unredacted tenant identifiers.

## Acceptance

The drill passes only when measured RTO/RPO meet the policy target, restored data integrity checks pass, application health checks pass, and the SRE owner approves the evidence. If any item is missing, keep the launch gate as `REQUIRES_ENVIRONMENT` and update the launch blocker register with the residual risk.
