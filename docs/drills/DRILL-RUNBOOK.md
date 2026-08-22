# Disaster Recovery Drill Runbook (P1-010)

## Scope

This runbook covers DR drills for the Fabric_4L platform:

- Database point-in-time recovery
- Cross-region failover
- Backup integrity verification

## Prerequisites

- Access to AWS console or CLI
- `wal-g` configured with `WALG_S3_PREFIX`
- `pg_restore` or `pg_dump` utilities
- Helm and kubectl access

## Drill 1: Database Point-in-Time Recovery

### Objective

Restore the PostgreSQL database to a specific point in time using WAL archives.

### Steps

1. **Identify recovery target**

   ```bash
   wal-g backup-list | head -n 20
   ```

2. **Stop application writes**

   ```bash
   kubectl scale deployment fabric-layer4 --replicas=0
   ```

3. **Restore from base backup**

   ```bash
   wal-g backup-fetch /var/lib/postgresql/data BASE_BACKUP_NAME
   ```

4. **Configure recovery target**
   Create `recovery.conf`:

   ```ini
   restore_command = 'wal-g wal-fetch %f %p'
   recovery_target_time = '2024-01-01 12:00:00'
   recovery_target_action = 'promote'
   ```

5. **Start PostgreSQL in recovery mode**

   ```bash
   pg_ctl start -D /var/lib/postgresql/data
   ```

6. **Verify data integrity**

   ```bash
   psql -d fabric -c "SELECT COUNT(*) FROM fabric_api_records;"
   ```

7. **Resume application writes**
   ```bash
   kubectl scale deployment fabric-layer4 --replicas=3
   ```

## Drill 2: Cross-Region Failover

### Objective

Fail over the platform to a secondary AWS region.

### Steps

1. **Promote RDS read replica**

   ```bash
   aws rds promote-read-replica \
     --db-instance-identifier fabric-prod-replica \
     --region us-west-2
   ```

2. **Update application database URLs**

   ```bash
   kubectl set env deployment/fabric-layer4 \
     DATABASE_URL="postgresql://...us-west-2..."
   ```

3. **Redirect traffic via Route53**

   ```bash
   aws route53 change-resource-record-sets \
     --hosted-zone-id ZONE_ID \
     --change-batch file://failover.json
   ```

4. **Verify the public gateway health endpoint**

   ```bash
   python scripts/ci/production_edge_smoke.py \
     --base-url "https://www.valuepact.ai"
   ```

   The drill must exercise the public `/api/v1` gateway route. L1–L6 health
   endpoints are internal-only and may be checked with `kubectl` from an
   approved in-cluster diagnostic workload when layer-level evidence is needed.

## Drill 3: Backup Integrity Verification

### Objective

Verify that backups are restorable and contain expected data.

### Steps

1. **List available backups**

   ```bash
   wal-g backup-list
   ```

2. **Restore to a temporary instance**

   ```bash
   docker run -d --name temp-restore \
     -e POSTGRES_PASSWORD=temp \
     -v restore-data:/var/lib/postgresql/data \
     postgres:16-alpine
   ```

3. **Fetch and restore backup**

   ```bash
   wal-g backup-fetch /var/lib/postgresql/data LATEST_BACKUP
   ```

4. **Run integrity checks**

   ```bash
   psql -d fabric -c "SELECT pg_database_datvalid FROM pg_database WHERE datname='fabric';"
   ```

5. **Compare record counts**

   ```bash
   psql -d fabric -c "SELECT table_name, COUNT(*) FROM fabric_api_records GROUP BY table_name;"
   ```

6. **Clean up temporary instance**
   ```bash
   docker stop temp-restore && docker rm temp-restore
   ```

## Acceptance Criteria

- RPO: < 5 minutes of data loss
- RTO: < 30 minutes for full service restoration
- Backup restore: < 1 hour for 100GB dataset
- Cross-region failover: < 15 minutes DNS propagation

## Frequency

- **Backup integrity**: Weekly automated verification
- **Point-in-time recovery**: Monthly drill
- **Cross-region failover**: Quarterly drill

## Escalation

If any drill fails:

1. Document failure in incident tracker
2. Notify platform team via #incidents Slack channel
3. Create JIRA ticket with severity "High"
4. Schedule follow-up within 48 hours
