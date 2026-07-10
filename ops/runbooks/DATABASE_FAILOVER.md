# Runbook: DATABASE_FAILOVER

**Alert:** `PostgreSQLPrimaryDown`, `DatabaseConnectionsHigh`, `PostgreSQLReplicationLag`  
**Severity:** Critical  
**Team:** DBA + SRE  
**Slack:** #database-oncall  
**Last Updated:** 2024-06-15

---

## 1. Detection

| Signal | Threshold | Source |
|--------|-----------|--------|
| `pg_up{role="primary"}` | == 0 | Prometheus postgres_exporter |
| `pg_stat_activity_count` | > 80 | Prometheus |
| `pg_replication_lag_seconds` | > 30s | Prometheus |

---

## 2. Impact Assessment

### Immediate Checks (within 1 minute)

```bash
# Check primary health
psql $PRIMARY_DSN -c "SELECT pg_is_in_recovery(), now(), inet_server_addr();"

# Check replica status
psql $REPLICA_DSN -c "SELECT pg_is_in_recovery(), pg_last_xact_replay_timestamp(), now();"

# Check replication lag on replica
psql $REPLICA_DSN -c "SELECT
  now() - pg_last_xact_replay_timestamp() AS lag,
  pg_is_wal_replay_paused();
"
```

### Impact Classification

| Scenario | Lag | RTO | RPO | Action |
|----------|-----|-----|-----|--------|
| Primary restart | N/A | 1-2 min | 0 | Wait for restart |
| Primary crash | N/A | 5 min | ~0 | Promote replica |
| Network partition | >30s | 5 min | ~lag | Promote replica, fix partition |
| Connection exhaustion | N/A | 2 min | 0 | Kill idle connections |

---

## 3. Step-by-Step Recovery

### Scenario A: Connection Exhaustion (most common)

```bash
# Step 1: Identify idle connections
psql $PRIMARY_DSN -c "
SELECT pid, usename, state, query_start, now() - query_start AS duration, left(query, 80)
FROM pg_stat_activity
WHERE state = 'idle in transaction'
  AND now() - query_start > interval '5 minutes'
ORDER BY duration DESC;
"

# Step 2: Kill idle connections (carefully!)
psql $PRIMARY_DSN -c "
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE state = 'idle in transaction'
  AND now() - query_start > interval '10 minutes'
  AND usename NOT IN ('postgres', 'replicator');
"

# Step 3: Check connection pool status
psql $PRIMARY_DSN -c "
SELECT count(*) FILTER (WHERE state = 'active') AS active,
       count(*) FILTER (WHERE state = 'idle') AS idle,
       count(*) FILTER (WHERE state = 'idle in transaction') AS idle_in_tx,
       count(*) AS total
FROM pg_stat_activity;
"
```

### Scenario B: Primary Failover

```bash
# ===== AUTOMATED FAILOVER (patroni recommended) =====
# If using Patroni, failover is typically automatic.
# Verify patroni status:
patronictl -c /etc/patroni.yml list

# ===== MANUAL FAILOVER (if automation fails) =====

# Step 1: Verify primary is truly down
# Try connecting 3 times with 10s intervals
for i in 1 2 3; do
  psql $PRIMARY_DSN -c "SELECT 1" && echo "Primary is up" && exit 0
  sleep 10
done
echo "Primary confirmed down"

# Step 2: Choose best replica (lowest lag)
# Compare lag across all replicas
for replica in $REPLICA1_DSN $REPLICA2_DSN; do
  echo "=== $replica ==="
  psql $replica -c "SELECT
    pg_is_in_recovery(),
    now() - pg_last_xact_replay_timestamp() AS lag,
    pg_last_xlog_receive_location(),
    pg_last_xlog_replay_location()
  ;"
done

# Step 3: Stop replication on chosen replica and promote
psql $BEST_REPLICA_DSN -c "SELECT pg_promote();"

# Step 4: Verify promotion
psql $BEST_REPLICA_DSN -c "SELECT pg_is_in_recovery();"  # Should return 'f'

# Step 5: Update application connection strings
# If using PgBouncer or service mesh, update the writer endpoint:
kubectl patch service postgres-primary -n fabric4l -p \
  '{"spec":{"selector":{"role":"postgres-primary"}}}'

# Step 6: Reconfigure old primary as replica (when it comes back)
# On old primary:
sudo systemctl stop postgresql
rm -rf /var/lib/postgresql/data/*
pg_basebackup -h $NEW_PRIMARY -D /var/lib/postgresql/data -U replicator -v -P -W
# Create recovery.conf or use patroni to rejoin
sudo systemctl start postgresql
```

### Scenario C: Replication Lag (non-critical but concerning)

```bash
# Check what's causing lag
psql $REPLICA_DSN -c "
SELECT
  pid,
  phase,
  client_addr,
  backend_start,
  state
FROM pg_stat_replication;
"

# Common causes and fixes:
# 1. Large transaction holding back replay
# 2. WAL archive delivery issues
# 3. Network congestion between primary and replica

# Force replay resume (if paused)
psql $REPLICA_DSN -c "SELECT pg_wal_replay_resume();"
```

---

## 4. Verification

- [ ] New primary accepts writes: `CREATE TABLE _failover_test (id int); DROP TABLE _failover_test;`
- [ ] Application health checks pass
- [ ] Connection count < 80
- [ ] Replication lag < 5s (if replica exists)
- [ ] All RLS policies verified: `\d+` on key tables
- [ ] Tenant isolation test suite passes

---

## 5. Post-Incident Review

**Within 24 hours:**

1. **Timeline reconstruction:**
   - When did primary become unresponsive?
   - When was failover initiated?
   - When did services recover?

2. **Root cause analysis:**
   - Hardware failure? OS issue? PostgreSQL crash?
   - Query of death? Connection leak?

3. **Preventive actions:**
   - Connection pool sizing review
   - Query timeout enforcement
   - Patroni/watchdog configuration review
   - Backup validation

**Key metrics to capture:**
- RTO (Recovery Time Objective): Target < 5 minutes
- RPO (Recovery Point Objective): Target < 1 minute
- Total downtime
- Data loss (should be 0 with synchronous replication)
