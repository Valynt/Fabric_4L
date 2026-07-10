# Runbook: PostgreSQL Primary Failover

| Field | Value |
|---|---|
| **Runbook ID** | DR-DB-001 |
| **Service** | PostgreSQL (Primary + Read Replica) |
| **Layers Affected** | L1 (Ingestion), L2 (Extraction), L3 (Knowledge), L5 (Ground Truth) |
| **Severity** | P1 - Critical |
| **RTO** | 5 minutes |
| **RPO** | 1 minute (synchronous replication for critical tables) |
| **Owner** | DBA Team / SRE On-Call |
| **Last Reviewed** | 2025-01-15 |
| **Version** | v1.2.0 |

---

## 1. Detection

### Alert Triggers

| Alert | Query/Condition | Severity |
|---|---|---|
| `PostgresPrimaryDown` | `pg_up{role="primary"} == 0` for 30s | P1 |
| `PostgresReplicationLag` | `pg_replication_lag_seconds > 60` for 2m | P2 |
| `PostgresConnectionExhausted` | `pg_stat_activity_count / pg_settings_max_connections > 0.95` | P2 |
| `PatroniFailoverDetected` | `increase(patroni_failover_count[5m]) > 0` | P1 |
| `PostgresWriteLatencyP99` | `pg_stat_statements_mean_time{quantile="0.99"} > 5000` for 5m | P2 |

### Dashboard Links
- Primary: [Grafana - PostgreSQL Overview](https://grafana.fabric4l.io/d/postgres-overview)
- Replication: [Grafana - PostgreSQL Replication](https://grafana.fabric4l.io/d/postgres-replication)
- Patroni: [Grafana - Patroni Cluster](https://grafana.fabric4l.io/d/patroni-cluster)

### Verification Command
```bash
# Check if primary is actually down (not a false alert)
kubectl exec -n fabric4l deploy/postgres-primary -- pg_isready -h localhost -p 5432
# Expected: localhost:5432 - no response
# If it responds, check for split-brain:
kubectl exec -n fabric4l deploy/postgres-primary -- patronictl list
```

---

## 2. Impact Assessment

### Immediate Impact
- **Write operations** fail until replica is promoted (RTO: 5 min)
- **Read operations** continue via read replica (unaffected)
- **L1 Ingestion** queues incoming documents (backpressure activated)
- **L2 Extraction** reads from replica, writes paused
- **L3 Knowledge** graph writes paused, reads continue
- **L5 Ground Truth** evaluation writes paused

### Data Loss Risk
- **RPO = 1 minute**: synchronous replication ensures < 1 min data loss
- WAL archiving to S3 provides point-in-time recovery if needed
- Check `pg_last_xact_replay_timestamp()` on replica before promotion

### Escalation Matrix
| Time | Action |
|---|---|
| T+0 | Alert fires, on-call SRE acknowledges |
| T+2 min | If not auto-failover, page DBA team lead |
| T+5 min | If still unresolved, escalate to Engineering Manager |
| T+10 min | If data loss suspected, activate DR coordinator |

---

## 3. Prerequisites

Before executing this runbook, ensure:

- [ ] `kubectl` access to `fabric4l` namespace
- [ ] Patroni CLI access (`patronictl`)
- [ ] PostgreSQL superuser credentials in Vault: `vault read secret/fabric4l/postgres/superuser`
- [ ] DBA team contact: `#incidents-db` Slack channel
- [ ] Network access to PostgreSQL pods from bastion host

---

## 4. Step-by-Step Procedure

### Phase 1: Verify Primary Failure (1 minute)

**Step 1.1: Confirm primary is unreachable**
```bash
# From bastion
kubectl -n fabric4l get pods -l app=postgres,role=primary
# If pod is in CrashLoopBackOff or Terminating, proceed

# Check Patroni cluster status
kubectl -n fabric4l exec postgres-0 -- patronictl list
# Expected: Leader = postgres-0, Replica = postgres-1 (lagging or unreachable)
```

**Step 1.2: Check if auto-failover already occurred**
```bash
kubectl -n fabric4l exec postgres-1 -- patronictl list
# If postgres-1 is now Leader, skip to Phase 3 (Verification)
```

**Step 1.3: Assess replication lag on replica**
```bash
kubectl -n fabric4l exec postgres-1 -- psql -U postgres -c \
  "SELECT pg_last_xact_replay_timestamp(), now(), \
   EXTRACT(EPOCH FROM (now() - pg_last_xact_replay_timestamp())) AS lag_seconds;"
# Record lag_seconds for post-incident review
```

### Phase 2: Promote Replica (2 minutes)

**Step 2.1: Trigger manual failover via Patroni**
```bash
# Option A: Graceful failover (preferred if primary is reachable but degraded)
kubectl -n fabric4l exec postgres-0 -- patronictl failover --candidate postgres-1 --force

# Option B: If primary is completely unreachable, Patroni should auto-failover
# If auto-failover did not occur:
kubectl -n fabric4l exec postgres-1 -- patronictl switchover --master postgres-0 --candidate postgres-1 --force
```

**Step 2.2: Verify promotion**
```bash
# Wait for new leader election
sleep 10
kubectl -n fabric4l exec postgres-1 -- patronictl list
# Expected: postgres-1 shows "Leader", postgres-0 shows "running" or "stopped"

# Verify write capability on new primary
kubectl -n fabric4l exec postgres-1 -- psql -U postgres -c \
  "CREATE TABLE IF NOT EXISTS dr_failover_test (id serial, ts timestamp); \
   INSERT INTO dr_failover_test (ts) VALUES (now()); \
   SELECT * FROM dr_failover_test ORDER BY id DESC LIMIT 1;"
# Expected: INSERT 0 1, then a row with current timestamp
```

**Step 2.3: Update application connection strings (if needed)**
```bash
# If using hardcoded DNS instead of Patroni endpoint, update:
kubectl -n fabric4l get endpoints postgres-primary
# Should automatically point to new leader via Patroni

# If applications cache DNS, trigger rolling restart:
kubectl -n fabric4l rollout restart deployment/l1-ingestion
kubectl -n fabric4l rollout restart deployment/l2-extraction
kubectl -n fabric4l rollout restart deployment/l3-knowledge
kubectl -n fabric4l rollout restart deployment/l5-ground-truth
```

**Step 2.4: Update monitoring and alerting**
```bash
# Verify Prometheus targets are healthy
curl -s "http://prometheus:9090/api/v1/targets" | jq '.data.activeTargets[] | select(.labels.job=="postgres")'
# Should show new primary as UP
```

### Phase 3: Verification (2 minutes)

**Step 3.1: Write Test**
```bash
# Execute write test via L1 ingestion
kubectl -n fabric4l exec deploy/l1-ingestion -- python3 -c "
import requests, json, sys
resp = requests.post('http://localhost:8080/ingest', json={
    'tenant_id': 'dr-verification',
    'content': 'Write test after failover at $(date -Iseconds)',
    'source': 'dr-runbook'
}, timeout=10)
print(f'Status: {resp.status_code}')
print(f'Body: {resp.json()}')
sys.exit(0 if resp.status_code == 201 else 1)
"
# Expected: Status 201, body contains document_id
```

**Step 3.2: Read Test**
```bash
# Verify read replica is re-established
kubectl -n fabric4l exec postgres-0 -- psql -U postgres -c \
  "SELECT pg_is_in_recovery();"
# Expected: t (true - it's now a replica)

# Verify replication is flowing
kubectl -n fabric4l exec postgres-1 -- psql -U postgres -c \
  "SELECT client_addr, state, sent_lsn, write_lsn, flush_lsn, replay_lsn \
   FROM pg_stat_replication;"
# Expected: Shows postgres-0 as streaming replica with minimal lag
```

**Step 3.3: Replication Check**
```bash
# Continuous replication lag monitor (run for 30 seconds)
for i in {1..6}; do
  kubectl -n fabric4l exec postgres-1 -- psql -U postgres -tc \
    "SELECT EXTRACT(EPOCH FROM (now() - pg_last_xact_replay_timestamp()))::int FROM pg_stat_replication;"
  sleep 5
done
# Expected: Lag decreasing to < 1 second

# Check replication slots
kubectl -n fabric4l exec postgres-1 -- psql -U postgres -c \
  "SELECT slot_name, active, restart_lsn FROM pg_replication_slots;"
# Expected: All slots active = true
```

**Step 3.4: Application Health Check**
```bash
# Check all affected layers
for layer in l1-ingestion l2-extraction l3-knowledge l5-ground-truth; do
  echo "Checking $layer..."
  kubectl -n fabric4l exec deploy/$layer -- wget -qO- http://localhost:8080/health
done
# Expected: All return {"status": "healthy", "postgres": "connected"}
```

### Phase 4: Failback (Optional - Schedule During Maintenance Window)

**Step 4.1: When original primary is restored**
```bash
# Verify original primary is healthy
kubectl -n fabric4l exec postgres-0 -- pg_isready
# Should return: localhost:5432 - accepting connections

# Rejoin as replica (Patroni should handle this automatically)
kubectl -n fabric4l exec postgres-0 -- patronictl list
# Expected: postgres-0 shows "running" as replica

# If not, manual rejoin:
kubectl -n fabric4l exec postgres-0 -- patronictl reinit postgresql postgres-0
```

**Step 4.2: Graceful switchback to original primary**
```bash
# Schedule during maintenance window
kubectl -n fabric4l exec postgres-1 -- patronictl switchover \
  --master postgres-1 --candidate postgres-0

# Verify
kubectl -n fabric4l exec postgres-0 -- patronictl list
# Expected: postgres-0 = Leader, postgres-1 = Replica
```

---

## 5. Rollback Procedure

If failover causes issues:

```bash
# Emergency: Force original primary back as leader (risk of split-brain!)
# Only use if new primary is also failing

# 1. Stop Patroni on new primary
kubectl -n fabric4l exec postgres-1 -- supervisorctl stop patroni

# 2. Start Patroni on original primary
kubectl -n fabric4l exec postgres-0 -- supervisorctl start patroni

# 3. Verify
kubectl -n fabric4l exec postgres-0 -- patronictl list

# 4. Reinitialize replica
kubectl -n fabric4l exec postgres-1 -- patronictl reinit postgresql postgres-1
```

---

## 6. Communication Template

### Internal Slack (#incidents)
```
:alert-red: **DATABASE FAILOVER IN PROGRESS** — DR-DB-001
- Detection: PostgreSQL primary down (alert: PostgresPrimaryDown)
- Action: Replica promotion in progress
- ETA: 5 minutes
- Impact: Write operations paused, reads unaffected
- Status page: https://status.fabric4l.io
- Incident channel: #incident-YYYY-MM-DD-db-failover
```

### Customer Communication (if needed)
```
We are currently experiencing a database failover event.
- **Impact**: Document ingestion may be delayed by up to 5 minutes
- **Your data**: No data loss expected (synchronous replication)
- **Status**: https://status.fabric4l.io/incidents/INC-XXXX
```

---

## 7. Post-Incident Review Template

Within 24 hours of resolution, complete the following:

### Timeline
| Time (UTC) | Event |
|---|---|
| | Alert fired |
| | SRE acknowledged |
| | Failover initiated |
| | Failover completed |
| | All services verified healthy |
| | Incident closed |

### Metrics
- **Actual RTO**: ___ minutes (target: 5)
- **Actual RPO**: ___ seconds (target: 60)
- **Replication lag at promotion**: ___ seconds
- **Failed write attempts during outage**: ___

### Root Cause
- [ ] Hardware failure
- [ ] Resource exhaustion (CPU/Memory/Disk)
- [ ] Kubernetes issue (node drain, eviction)
- [ ] PostgreSQL bug/crash
- [ ] Network partition
- [ ] Human error
- [ ] Other: ___________

### Action Items
| ID | Action | Owner | Due Date | Status |
|---|---|---|---|---|
| | | | | |

### What Went Well
1.
2.

### What Needs Improvement
1.
2.
