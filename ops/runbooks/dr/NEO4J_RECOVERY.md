# Runbook: Neo4j Cluster Recovery

| Field | Value |
|---|---|
| **Runbook ID** | DR-GRAPH-001 |
| **Service** | Neo4j Enterprise Causal Cluster |
| **Layers Affected** | L3 (Knowledge Graph), L4 (Agent reasoning) |
| **Severity** | P1 - Critical |
| **RTO** | 10 minutes |
| **RPO** | 0 (clustered, causal consistency) |
| **Fallback** | pgvector similarity search (degraded mode) |
| **Owner** | Platform Team / SRE On-Call |
| **Last Reviewed** | 2025-01-15 |
| **Version** | v1.2.0 |

---

## 1. Detection

### Alert Triggers

| Alert | Query/Condition | Severity |
|---|---|---|
| `Neo4jClusterNotFullyFormed` | `neo4j_cluster_databases_status != "online"` for 2m | P1 |
| `Neo4jCoreOffline` | `neo4j_up{role="core"} == 0` for 1m | P1 |
| `Neo4jReadReplicaLag` | `neo4j_replication_lag_seconds > 30` for 5m | P2 |
| `Neo4jTransactionFailures` | `increase(neo4j_transaction_failed[5m]) > 100` | P2 |
| `Neo4jHeapPressure` | `neo4j_memory_heap_used / neo4j_memory_heap_max > 0.9` for 5m | P2 |
| `Neo4jNetworkPartition` | `neo4j_cluster_members_available < neo4j_cluster_members_expected` | P1 |

### Dashboard Links
- [Grafana - Neo4j Cluster Health](https://grafana.fabric4l.io/d/neo4j-cluster)
- [Grafana - Neo4j Performance](https://grafana.fabric4l.io/d/neo4j-performance)
- [Neo4j Browser](https://neo4j-browser.fabric4l.io)

### Verification Command
```bash
# Check cluster formation
kubectl -n fabric4l exec neo4j-core-0 -- cypher-shell -u neo4j -p $NEO4J_PASSWORD \
  "CALL dbms.cluster.overview() YIELD id, role, addresses, groups, database, status RETURN *"
# Expected: 3 cores + N read replicas, all "online"
```

---

## 2. Impact Assessment

### Immediate Impact
- **Knowledge graph queries** fail or return stale data
- **L4 Agent reasoning** degrades (no graph traversal available)
- **L3 entity resolution** falls back to pgvector (if configured)
- **No data loss**: Causal cluster maintains consistency

### Fallback Behavior
When Neo4j is unavailable, L3 automatically:
1. Activates circuit breaker (OPEN state after 5 failures)
2. Falls back to pgvector for entity similarity search
3. Returns `X-Fallback: pgvector` header in responses
4. Queues graph mutations for replay after recovery

### Degradation Matrix
| Neo4j State | L3 Behavior | User Impact |
|---|---|---|
| Fully online | Full Cypher queries | No impact |
| 1 core down (2 remain) | Reduced throughput, still consistent | Slight latency increase |
| 2+ cores partitioned | Circuit breaker OPEN, pgvector fallback | Similarity search only |
| All cores down | Full pgvector fallback | No graph insights |

### Escalation Matrix
| Time | Action |
|---|---|
| T+0 | Alert fires, on-call SRE acknowledges |
| T+5 min | If cluster not reforming, page Platform team |
| T+10 min | If still partitioned, activate pgvector fallback (permanent) |
| T+15 min | Escalate to Engineering Director |

---

## 3. Prerequisites

- [ ] `kubectl` access to `fabric4l` namespace
- [ ] Neo4j admin credentials: `vault read secret/fabric4l/neo4j/admin`
- [ ] `cypher-shell` available in Neo4j pods
- [ ] Platform team contact: `#incidents-platform` Slack channel
- [ ] pgvector fallback pre-configured and tested

---

## 4. Step-by-Step Procedure

### Phase 1: Identify Failed Core (2 minutes)

**Step 1.1: Check cluster overview**
```bash
kubectl -n fabric4l exec neo4j-core-0 -- cypher-shell -u neo4j -p $NEO4J_PASSWORD \
  "CALL dbms.cluster.overview() YIELD id, role, addresses, groups, database, status RETURN *"
# Record which cores are offline or in "unknown" status
```

**Step 1.2: Check individual core pod status**
```bash
kubectl -n fabric4l get pods -l app=neo4j-core -o wide
# Look for: CrashLoopBackOff, Error, Pending, or Terminating

# Describe failed pod
kubectl -n fabric4l describe pod neo4j-core-2  # replace with failed pod
# Check Events section for eviction, OOMKilled, etc.
```

**Step 1.3: Check logs for failure reason**
```bash
# Last 100 lines of failed core
kubectl -n fabric4l logs neo4j-core-2 --tail=100

# Check for common issues
# - OutOfMemory errors
# - Disk full
# - Network partition messages
# - Transaction log corruption
```

**Step 1.4: Assess if quorum is maintained**
```bash
# Neo4j requires majority of cores for write quorum (3 cores = 2 needed)
kubectl -n fabric4l exec neo4j-core-0 -- cypher-shell -u neo4j -p $NEO4J_PASSWORD \
  "CALL dbms.cluster.routing.getRoutingTable({}, 'neo4j') YIELD ttl, servers RETURN ttl, servers"
# If < 2 cores available, writes are blocked
```

### Phase 2: Restart/Recover Failed Core (3 minutes)

**Case A: Pod crashed (OOM, panic, etc.)**
```bash
# Delete pod to force recreation (PVC preserves data)
kubectl -n fabric4l delete pod neo4j-core-2 --grace-period=60

# Wait for recreation
kubectl -n fabric4l wait --for=condition=Ready pod/neo4j-core-2 --timeout=120s

# Verify rejoin
kubectl -n fabric4l exec neo4j-core-0 -- cypher-shell -u neo4j -p $NEO4J_PASSWORD \
  "CALL dbms.cluster.overview() YIELD id, role, status RETURN id, role, status"
```

**Case B: Node failure (Kubernetes node down)**
```bash
# Check node status
kubectl get node <node-name>
# If node is NotReady, pod will reschedule automatically

# Force reschedule if stuck
kubectl -n fabric4l delete pod neo4j-core-2 --grace-period=0 --force
# Wait for scheduling to different node
kubectl -n fabric4l get pod neo4j-core-2 -o wide -w
```

**Case C: Data corruption / persistent issue**
```bash
# IMPORTANT: Only use if data corruption is confirmed
# This will reinitialize the core from cluster snapshot

# 1. Scale down
kubectl -n fabric4l scale statefulset neo4j-core --replicas=2

# 2. Delete PVC (data will be re-synced from cluster)
kubectl -n fabric4l delete pvc data-neo4j-core-2

# 3. Scale back up
kubectl -n fabric4l scale statefulset neo4j-core --replicas=3

# 4. Verify rejoin and catch-up
kubectl -n fabric4l exec neo4j-core-2 -- cypher-shell -u neo4j -p $NEO4J_PASSWORD \
  "CALL dbms.cluster.overview() YIELD id, role, status RETURN id, role, status"
```

**Case D: Network partition**
```bash
# Check for CNI issues
kubectl -n kube-system get pods -l k8s-app=calico-node  # or your CNI
kubectl -n kube-system logs <cni-pod>

# Check inter-pod connectivity
kubectl -n fabric4l exec neo4j-core-0 -- nc -zv neo4j-core-2 6362
# Should connect (cluster communication port)

# If network is partitioned, fix CNI or wait for auto-heal
# Consider: kubectl delete pod -n kube-system <cni-pod> to restart CNI
```

### Phase 3: Rejoin Cluster (3 minutes)

**Step 3.1: Monitor rejoin process**
```bash
# Watch cluster reform
watch -n 5 'kubectl -n fabric4l exec neo4j-core-0 -- cypher-shell -u neo4j -p $NEO4J_PASSWORD \
  "CALL dbms.cluster.overview() YIELD id, role, status RETURN id, role, status"'
# Wait until all cores show "online"
```

**Step 3.2: Verify causal consistency catch-up**
```bash
# Check transaction catch-up on recovered core
kubectl -n fabric4l exec neo4j-core-2 -- cypher-shell -u neo4j -p $NEO4J_PASSWORD \
  "CALL dbms.cluster.checkDatabaseConsistency('neo4j')"
# Expected: No inconsistencies reported

# Check store sizes match
for pod in neo4j-core-0 neo4j-core-1 neo4j-core-2; do
  echo "$pod:"
  kubectl -n fabric4l exec $pod -- du -sh /data/databases/neo4j
done
# Sizes should be approximately equal
```

**Step 3.3: Verify read replicas reconnect**
```bash
kubectl -n fabric4l get pods -l app=neo4j-read-replica
# All should be Running

kubectl -n fabric4l exec neo4j-core-0 -- cypher-shell -u neo4j -p $NEO4J_PASSWORD \
  "CALL dbms.cluster.overview() YIELD id, role, groups RETURN id, role, groups"
# Read replicas should show role: "read_replica"
```

### Phase 4: Verify Consistency (2 minutes)

**Step 4.1: Run consistency checks**
```bash
# Count nodes and relationships
kubectl -n fabric4l exec neo4j-core-0 -- cypher-shell -u neo4j -p $NEO4J_PASSWORD \
  "MATCH (n) RETURN count(n) as nodes"
# Record: _____ nodes

kubectl -n fabric4l exec neo4j-core-0 -- cypher-shell -u neo4j -p $NEO4J_PASSWORD \
  "MATCH ()-[r]->() RETURN count(r) as relationships"
# Record: _____ relationships

# Compare across all cores
for pod in neo4j-core-0 neo4j-core-1 neo4j-core-2; do
  echo "$pod:"
  kubectl -n fabric4l exec $pod -- cypher-shell -u neo4j -p $NEO4J_PASSWORD \
    "MATCH (n) RETURN count(n) as nodes"
done
# All should match
```

**Step 4.2: Verify query performance**
```bash
# Test common queries
kubectl -n fabric4l exec neo4j-core-0 -- cypher-shell -u neo4j -p $NEO4J_PASSWORD \
  "PROFILE MATCH (e:Entity)-[:RELATES_TO]->(e2:Entity) WHERE e.tenant_id = 'test' RETURN e, e2 LIMIT 10"
# Should execute without error
```

**Step 4.3: Verify L3 integration**
```bash
# Test L3 health
kubectl -n fabric4l exec deploy/l3-knowledge -- wget -qO- http://localhost:8080/health
# Expected: {"status": "healthy", "neo4j": "connected", "fallback": "inactive"}

# Test L3 graph query
kubectl -n fabric4l exec deploy/l3-knowledge -- wget -qO- \
  --post-data='{"cypher": "MATCH (n) RETURN count(n)"}' \
  http://localhost:8080/graph/query
# Expected: 200 OK with count
```

### Phase 5: Resume Ingestion (Optional - if paused)

**Step 5.1: Deactivate pgvector fallback (if activated)**
```bash
# Only if fallback was manually activated
curl -X POST http://l3-knowledge:8080/admin/fallback \
  -H "Content-Type: application/json" \
  -d '{"neo4j_fallback": false, "reason": "cluster recovered"}'
```

**Step 5.2: Resume queued graph mutations**
```bash
# Check queue depth
kubectl -n fabric4l exec deploy/l3-knowledge -- wget -qO- \
  http://localhost:8080/metrics/graph-mutation-queue
# If mutations queued, trigger replay

# Trigger replay
curl -X POST http://l3-knowledge:8080/admin/replay-queue
```

**Step 5.3: Monitor for 10 minutes**
```bash
# Watch for any recurring issues
kubectl -n fabric4l logs -l app=neo4j-core --tail=50 -f | grep -iE "error|warn|partition"
# Should show no new errors
```

---

## 5. pgvector Fallback Activation (Emergency)

If Neo4j cannot be recovered within 10 minutes:

```bash
# 1. Activate permanent pgvector fallback
curl -X POST http://l3-knowledge:8080/admin/fallback \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{
    "neo4j_fallback": true,
    "fallback_type": "pgvector",
    "reason": "neo4j cluster unrecoverable - DR-GRAPH-001"
  }'

# 2. Verify fallback is active
kubectl -n fabric4l exec deploy/l3-knowledge -- wget -qO- \
  http://localhost:8080/health
# Expected: {"neo4j": "disconnected", "fallback": "pgvector", "pgvector": "connected"}

# 3. Notify stakeholders
echo "Neo4j cluster unrecoverable. pgvector fallback activated. Knowledge graph features degraded."
```

---

## 6. Communication Template

### Internal Slack (#incidents)
```
:alert-red: **NEO4J CLUSTER RECOVERY IN PROGRESS** — DR-GRAPH-001
- Detection: Neo4j cluster partition (alert: Neo4jClusterNotFullyFormed)
- Affected: L3 Knowledge Graph, L4 Agent reasoning
- Action: Recovering failed core server
- ETA: 10 minutes
- Fallback: pgvector similarity search active
- Status page: https://status.fabric4l.io
```

---

## 7. Post-Incident Review Template

### Timeline
| Time (UTC) | Event |
|---|---|
| | Alert fired |
| | SRE acknowledged |
| | Failed core identified |
| | Recovery action initiated |
| | Core rejoined cluster |
| | Consistency verified |
| | Incident closed |

### Metrics
- **Actual RTO**: ___ minutes (target: 10)
- **Actual RPO**: ___ (target: 0)
- **Cores affected**: ___
- **Fallback activated**: Yes / No
- **Data inconsistency detected**: Yes / No

### Root Cause
- [ ] Node failure / eviction
- [ ] OOMKilled
- [ ] Disk full
- [ ] Network partition
- [ ] Data corruption
- [ ] Neo4j bug
- [ ] Human error
- [ ] Other: ___________

### Action Items
| ID | Action | Owner | Due Date | Status |
|---|---|---|---|---|
| | | | | |

### Fallback Effectiveness
- pgvector fallback response time: ___ ms (baseline: ___ ms)
- User complaints during fallback: ___
- Feature degradation noticed: Yes / No
