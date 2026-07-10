# Runbook: Corrupted Tenant Data Recovery

| Field | Value |
|---|---|
| **Runbook ID** | DR-TENANT-001 |
| **Service** | Tenant-scoped data (PostgreSQL + Neo4j + S3) |
| **Severity** | P1 - Critical (single tenant) |
| **Impact** | Single tenant affected — no blast radius to other tenants |
| **RTO** | 30 minutes (depends on data size) |
| **RPO** | Point-in-time recovery available |
| **Owner** | SRE On-Call + DBA Team |
| **Last Reviewed** | 2025-01-15 |
| **Version** | v1.2.0 |

---

## 1. Detection

### Alert Triggers

| Alert | Query/Condition | Severity |
|---|---|---|
| `TenantDataIntegrityCheckFailed` | `tenant_integrity_check_status == 0` | P1 |
| `TenantOrphanedRecords` | `tenant_orphaned_record_count > 0` | P2 |
| `TenantIngestionAnomaly` | `tenant_ingestion_rate < baseline * 0.1` for 30m | P2 |
| `TenantQueryFailures` | `tenant_query_error_rate > 0.1` for 5m | P2 |
| `CustomerReportedDataIssue` | Support ticket / customer report | P1 |

### Data Integrity Checks (Automated)

These checks run every 6 hours per tenant:

```sql
-- Check 1: Referential integrity
SELECT COUNT(*) FROM documents d
LEFT JOIN tenants t ON d.tenant_id = t.id
WHERE t.id IS NULL;
-- Expected: 0

-- Check 2: Neo4j entity consistency
MATCH (e:Entity)
WHERE NOT EXISTS { MATCH (t:Tenant {id: e.tenant_id}) }
RETURN count(e);
-- Expected: 0

-- Check 3: S3 object existence
-- Verify all document.content_url references resolve to existing S3 objects
```

### Dashboard Links
- [Grafana - Tenant Health](https://grafana.fabric4l.io/d/tenant-health)
- [Grafana - Data Integrity](https://grafana.fabric4l.io/d/data-integrity)
- [Admin - Tenant Details](https://admin.fabric4l.io/tenants)

---

## 2. Impact Assessment

### Corruption Types

| Type | Scope | Recovery Method |
|---|---|---|
| **Referential integrity violation** | PostgreSQL | FK repair or restore |
| **Orphaned Neo4j entities** | Knowledge graph | Cleanup script or subgraph restore |
| **Missing S3 objects** | Blob storage | Restore from S3 versioning / Glacier |
| **Index corruption** | PostgreSQL/Neo4j | REINDEX or rebuild |
| **Tenant config corruption** | Metadata | Restore from backup |
| **Cross-system inconsistency** | PostgreSQL + Neo4j + S3 | Coordinated point-in-time restore |

### Tenant Isolation
Fabric_4L uses strict tenant isolation:
- **PostgreSQL**: `tenant_id` column in every table (row-level security)
- **Neo4j**: `tenant_id` property on every node
- **S3**: `s3://fabric4l-documents/{tenant_id}/` prefix
- **Redis**: `tenant:{tenant_id}:` key prefix

This ensures corruption is **scoped to a single tenant** with zero blast radius.

---

## 3. Prerequisites

- [ ] Identify affected `tenant_id`
- [ ] Tenant backup location: `s3://fabric4l-backups/tenants/{tenant_id}/`
- [ ] Point-in-time recovery WAL archives: `s3://fabric4l-wal/{date}/`
- [ ] DBA team contact: `#incidents-db` Slack
- [ ] Customer success team (for customer communication)
- [ ] Audit log access for corruption timeline

---

## 4. Step-by-Step Procedure

### Phase 1: Isolate Tenant (3 minutes)

**Step 1.1: Identify affected tenant**
```bash
# From alert, get tenant_id
TENANT_ID="<tenant_id_from_alert>"

# Verify tenant exists and is active
kubectl -n fabric4l exec deploy/l3-knowledge -- psql -U postgres -c \
  "SELECT id, name, status, created_at FROM tenants WHERE id = '$TENANT_ID';"
```

**Step 1.2: Disable tenant access (read-only mode)**
```bash
# Set tenant to maintenance mode
curl -X POST http://l1-ingestion:8080/admin/tenant-maintenance \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"tenant_id\": \"$TENANT_ID\",
    \"mode\": \"read_only\",
    \"reason\": \"Data integrity issue under investigation - DR-TENANT-001\"
  }"

# Verify
kubectl -n fabric4l exec deploy/l1-ingestion -- psql -U postgres -c \
  "SELECT id, maintenance_mode FROM tenants WHERE id = '$TENANT_ID';"
# Expected: maintenance_mode = 'read_only'
```

**Step 1.3: Document pre-recovery state**
```bash
# Record counts for comparison post-recovery
mkdir -p /tmp/dr-tenant-$TENANT_ID

# PostgreSQL counts
kubectl -n fabric4l exec deploy/l3-knowledge -- psql -U postgres -tc \
  "SELECT 'documents', COUNT(*) FROM documents WHERE tenant_id = '$TENANT_ID' \
   UNION ALL \
   SELECT 'entities', COUNT(*) FROM entities WHERE tenant_id = '$TENANT_ID' \
   UNION ALL \
   SELECT 'relationships', COUNT(*) FROM relationships WHERE tenant_id = '$TENANT_ID';" \
  > /tmp/dr-tenant-$TENANT_ID/pg-counts-before.txt

# Neo4j counts
kubectl -n fabric4l exec neo4j-core-0 -- cypher-shell -u neo4j -p $NEO4J_PASSWORD \
  "MATCH (n {tenant_id: '$TENANT_ID'}) RETURN count(n) as nodes" \
  > /tmp/dr-tenant-$TENANT_ID/neo4j-counts-before.txt

# S3 object count
aws s3 ls s3://fabric4l-documents/$TENANT_ID/ --recursive | wc -l \
  > /tmp/dr-tenant-$TENANT_ID/s3-counts-before.txt
```

### Phase 2: Identify Corruption Scope (5 minutes)

**Step 2.1: Run integrity checks**
```bash
# Run comprehensive integrity check
kubectl -n fabric4l exec deploy/l3-knowledge -- python3 /app/scripts/check_tenant_integrity.py \
  --tenant-id $TENANT_ID \
  --output /tmp/dr-tenant-$TENANT_ID/integrity-report.json

# Review report
cat /tmp/dr-tenant-$TENANT_ID/integrity-report.json | jq .
```

**Step 2.2: Determine corruption window**
```bash
# Check audit log for the tenant
curl -s "http://l5-ground-truth:8080/audit?tenant_id=$TENANT_ID&limit=100" | jq '.'

# Check PostgreSQL write timeline
kubectl -n fabric4l exec deploy/l3-knowledge -- psql -U postgres -c \
  "SELECT date_trunc('hour', created_at) as hour, COUNT(*) \
   FROM documents WHERE tenant_id = '$TENANT_ID' \
   GROUP BY hour ORDER BY hour DESC LIMIT 24;"
# Look for anomalous patterns
```

**Step 2.3: Identify root cause**
Common causes:
- [ ] Bug in ingestion pipeline (specific tenant data trigger)
- [ ] Failed migration script
- [ ] Race condition in concurrent ingestion
- [ ] Manual data manipulation error
- [ ] Neo4j transaction timeout (partial write)
- [ ] Storage corruption (extremely rare)

### Phase 3: Restore from Backup (15 minutes)

**Decision matrix:**

| Scenario | Action |
|---|---|
| Small corruption (< 100 rows) | Manual SQL repair |
| Medium corruption (100-10K rows) | Targeted restore from backup |
| Large corruption (> 10K rows) | Full tenant PITR |
| Unknown scope | Full tenant PITR (safest) |

**Option A: Point-in-Time Recovery (PITR) — Full Tenant**
```bash
# 1. Determine recovery timestamp (before corruption)
RECOVERY_TIME="2025-01-15T08:30:00Z"  # Adjust based on investigation

# 2. Create restore job
kubectl -n fabric4l apply -f - <<EOF
apiVersion: batch/v1
kind: Job
metadata:
  name: tenant-restore-$TENANT_ID
spec:
  template:
    spec:
      containers:
      - name: restore
        image: fabric4l/tenant-restore:latest
        env:
        - name: TENANT_ID
          value: "$TENANT_ID"
        - name: RECOVERY_TIME
          value: "$RECOVERY_TIME"
        - name: S3_BACKUP_BUCKET
          value: "fabric4l-backups"
        - name: S3_WAL_BUCKET
          value: "fabric4l-wal"
        command: ["/app/restore-tenant.sh"]
      restartPolicy: Never
  backoffLimit: 1
EOF

# 3. Monitor restore progress
kubectl -n fabric4l logs -f job/tenant-restore-$TENANT_ID

# 4. Verify completion
kubectl -n fabric4l get job tenant-restore-$TENANT_ID -o jsonpath='{.status.conditions[?(@.type=="Complete")].status}'
# Expected: True
```

**Option B: Targeted Neo4j Subgraph Restore**
```bash
# If only Neo4j is corrupted
# 1. Export tenant subgraph from backup
kubectl -n fabric4l exec neo4j-core-0 -- cypher-shell -u neo4j -p $NEO4J_PASSWORD \
  "CALL apoc.export.cypher.query( \
    'MATCH (n {tenant_id: \"$TENANT_ID\"})-[r]-(m) RETURN n, r, m', \
    '/backups/neo4j-$TENANT_ID-backup.cypher', {} \
  )"

# 2. Delete corrupted subgraph
kubectl -n fabric4l exec neo4j-core-0 -- cypher-shell -u neo4j -p $NEO4J_PASSWORD \
  "MATCH (n {tenant_id: \"$TENANT_ID\"}) DETACH DELETE n"

# 3. Restore from backup
kubectl -n fabric4l exec neo4j-core-0 -- cypher-shell -u neo4j -p $NEO4J_PASSWORD \
  < /backups/neo4j-$TENANT_ID-backup.cypher
```

**Option C: Manual SQL Repair**
```bash
# For small, well-understood corruption
# Example: Fix orphaned records
kubectl -n fabric4l exec deploy/l3-knowledge -- psql -U postgres -c \
  "DELETE FROM documents WHERE tenant_id = '$TENANT_ID' AND id IN (
    SELECT d.id FROM documents d
    LEFT JOIN tenants t ON d.tenant_id = t.id
    WHERE t.id IS NULL
  );"

# Always verify before committing
# Use BEGIN; ...; ROLLBACK; first to preview changes
```

### Phase 4: Verify Data (5 minutes)

**Step 4.1: Re-run integrity checks**
```bash
kubectl -n fabric4l exec deploy/l3-knowledge -- python3 /app/scripts/check_tenant_integrity.py \
  --tenant-id $TENANT_ID \
  --output /tmp/dr-tenant-$TENANT_ID/integrity-report-after.json

# Compare before/after
diff <(jq -S . /tmp/dr-tenant-$TENANT_ID/integrity-report-before.json) \
     <(jq -S . /tmp/dr-tenant-$TENANT_ID/integrity-report-after.json)
# Expected: No differences (all checks pass)
```

**Step 4.2: Verify record counts**
```bash
# PostgreSQL
kubectl -n fabric4l exec deploy/l3-knowledge -- psql -U postgres -tc \
  "SELECT 'documents', COUNT(*) FROM documents WHERE tenant_id = '$TENANT_ID' \
   UNION ALL \
   SELECT 'entities', COUNT(*) FROM entities WHERE tenant_id = '$TENANT_ID';" \
  > /tmp/dr-tenant-$TENANT_ID/pg-counts-after.txt

# Compare with before (should be close, not exact due to PITR)
diff /tmp/dr-tenant-$TENANT_ID/pg-counts-before.txt /tmp/dr-tenant-$TENANT_ID/pg-counts-after.txt
# Small differences expected; large differences = investigation needed
```

**Step 4.3: Verify Neo4j consistency**
```bash
kubectl -n fabric4l exec neo4j-core-0 -- cypher-shell -u neo4j -p $NEO4J_PASSWORD \
  "MATCH (n {tenant_id: '$TENANT_ID'}) RETURN count(n) as nodes, \
   count{(n)-[:RELATES_TO]-()} as relationships"

# Run consistency check
kubectl -n fabric4l exec neo4j-core-0 -- cypher-shell -u neo4j -p $NEO4J_PASSWORD \
  "CALL dbms.cluster.checkDatabaseConsistency('neo4j')"
```

**Step 4.4: End-to-end test**
```bash
# Test ingestion for tenant
curl -X POST http://l1-ingestion:8080/v1/ingest \
  -H "Authorization: Bearer $TEST_TOKEN" \
  -H "X-Tenant-ID: $TENANT_ID" \
  -d '{
    "content": "Post-recovery test document",
    "source": "dr-verification"
  }'
# Expected: 201 Created

# Test query
curl -X POST http://l3-knowledge:8080/v1/search \
  -H "Authorization: Bearer $TEST_TOKEN" \
  -H "X-Tenant-ID: $TENANT_ID" \
  -d '{"query": "test"}'
# Expected: 200 OK with results
```

### Phase 5: Re-enable Access (2 minutes)

**Step 5.1: Remove maintenance mode**
```bash
curl -X POST http://l1-ingestion:8080/admin/tenant-maintenance \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"tenant_id\": \"$TENANT_ID\",
    \"mode\": \"active\",
    \"reason\": \"Data integrity restored - DR-TENANT-001 resolved\"
  }"

# Verify
kubectl -n fabric4l exec deploy/l1-ingestion -- psql -U postgres -c \
  "SELECT id, maintenance_mode FROM tenants WHERE id = '$TENANT_ID';"
# Expected: maintenance_mode = 'active'
```

**Step 5.2: Notify customer**
```bash
# Trigger customer notification
curl -X POST http://l5-ground-truth:8080/admin/notify-tenant \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d "{
    \"tenant_id\": \"$TENANT_ID\",
    \"message\": \"Your data has been restored. All services are now active.\"
  }"
```

---

## 5. Audit Trail Requirements

All actions must be logged for compliance:

```bash
# Generate audit report
cat > /tmp/dr-tenant-$TENANT_ID/audit-trail.json <<EOF
{
  "runbook_id": "DR-TENANT-001",
  "tenant_id": "$TENANT_ID",
  "started_at": "$(date -Iseconds)",
  "executed_by": "$(whoami)",
  "corruption_detected_by": "integrity_check / alert / customer_report",
  "recovery_method": "PITR / subgraph_restore / manual_repair",
  "recovery_timestamp": "$RECOVERY_TIME",
  "records_affected": $(cat /tmp/dr-tenant-$TENANT_ID/pg-counts-after.txt | head -1),
  "integrity_check_before": "/tmp/dr-tenant-$TENANT_ID/integrity-report-before.json",
  "integrity_check_after": "/tmp/dr-tenant-$TENANT_ID/integrity-report-after.json",
  "maintenance_windows": ["$(date -d '-1 hour' -Iseconds)", "$(date -Iseconds)"],
  "customer_notified": true
}
EOF

# Upload to audit log S3 bucket
aws s3 cp /tmp/dr-tenant-$TENANT_ID/audit-trail.json \
  s3://fabric4l-audit/tenant-recovery/$(date +%Y/%m/%d)/$TENANT_ID-$(date +%s).json
```

---

## 6. Communication Template

### Internal Slack (#incidents)
```
:orange_circle: **TENANT DATA RECOVERY** — DR-TENANT-001
- Tenant: `<tenant_id>` (<tenant_name>)
- Detection: Data integrity check failed
- Impact: Single tenant — no blast radius to other tenants
- Action: Tenant isolated, investigating corruption scope
- ETA: 30 minutes for full recovery
- Customer: <customer_success_contact> notified
- Audit trail: DR-TENANT-001 compliance logging active
```

---

## 7. Post-Incident Review Template

### Timeline
| Time (UTC) | Event |
|---|---|
| | Integrity check failed |
| | Tenant isolated |
| | Corruption scope identified |
| | Recovery method selected |
| | Recovery executed |
| | Verification completed |
| | Tenant re-enabled |
| | Incident closed |

### Metrics
- **Actual RTO**: ___ minutes (target: 30)
- **Records affected**: ___
- **Recovery method used**: PITR / Subgraph / Manual
- **Data loss**: ___ records (should be 0 with PITR)

### Corruption Analysis
| Field | Value |
|---|---|
| Corruption type | |
| First corrupted record timestamp | |
| Last known good state | |
| Root cause | |
| Detection latency | |

### Prevention Action Items
| ID | Action | Owner | Due Date | Status |
|---|---|---|---|---|
| | Add pre-write validation for tenant data | | | |
| | Improve integrity check frequency | | | |
| | Add tenant-level circuit breaker | | | |
| | Review ingestion pipeline for tenant $TENANT_ID | | | |

### Audit Compliance
- [ ] Audit trail uploaded to S3
- [ ] Customer notified of resolution
- [ ] Data retention policies verified
- [ ] GDPR/compliance review completed (if applicable)
