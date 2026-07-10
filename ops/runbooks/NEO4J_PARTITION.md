# Runbook: NEO4J_PARTITION

**Alert:** `Neo4jClusterPartition`  
**Severity:** Critical  
**Team:** DBA  
**Slack:** #database-oncall  
**Last Updated:** 2024-06-15

---

## 1. Detection

| Signal | Threshold | Source |
|--------|-----------|--------|
| `neo4j_cluster_core_databases_status{status!="online"}` | > 0 | Neo4j metrics endpoint |
| `neo4j_cluster_databases_status` != 1 | any value | Neo4j metrics |

---

## 2. Impact Assessment

### Neo4j Cluster Architecture

```
         Core Servers (3-7)                    Read Replicas
        ┌─────┐  ┌─────┐  ┌─────┐            ┌─────┐  ┌─────┐
        │ C-1 │──│ C-2 │──│ C-3 │            │ R-1 │  │ R-2 │
        │ LEADER     FOLLOWER  FOLLOWER       └─────┘  └─────┘
        └─────┘  └─────┘  └─────┘
            \       |       /
             Raft Consensus
```

### Check cluster health

```bash
# Check cluster overview via Neo4j Browser or cypher-shell
cypher-shell -u neo4j -p $NEO4J_PASSWORD -a bolt://neo4j-core-1:7687 "
  SHOW DATABASE fabric4l YIELD name, address, currentStatus, role, error
"

# Expected: All cores should show 'online', one LEADER, rest FOLLOWER
```

### Impact by partition type

| Partition Type | Writes | Reads | Action |
|----------------|--------|-------|--------|
| Minority partition | BLOCKED | DEGRADED | Wait for auto-recovery or manual intervention |
| Leader isolated | BLOCKED | DEGRADED | Force leader election |
| Full split brain | BLOCKED | BLOCKED | Emergency cluster repair |

---

## 3. Step-by-Step Recovery

### Step 1: Assess cluster state (0-3 min)

```bash
# Get full cluster status from each core
for core in neo4j-core-1 neo4j-core-2 neo4j-core-3; do
  echo "=== $core ==="
  cypher-shell -u neo4j -p $NEO4J_PASSWORD -a bolt://${core}:7687 "
    CALL dbms.cluster.overview() YIELD id, role, addresses, groups
    RETURN id, role, addresses
  "
done

# Check Raft log state
cypher-shell -u neo4j -p $NEO4J_PASSWORD -a bolt://neo4j-core-1:7687 "
  CALL dbms.cluster.raftLog() YIELD logIndex, term, content
  RETURN logIndex, term ORDER BY logIndex DESC LIMIT 10
"
```

### Step 2: Identify the leader (if any)

```bash
# Find current leader
cypher-shell -u neo4j -p $NEO4J_PASSWORD -a bolt://neo4j-core-1:7687 "
  CALL dbms.cluster.routing.getRoutingTable({'database':'fabric4l'})
  YIELD ttl, servers
  RETURN servers
"

# If no leader exists, cores may be in a partition
```

### Step 3: Recovery based on partition type

#### Case A: One core down (expected with 3-core cluster)

```bash
# With 3 cores, the cluster tolerates 1 failure.
# If 1 core is down, the remaining 2 can continue (if they can communicate).

# Check if the 2 remaining cores see each other
cypher-shell -u neo4j -p $NEO4J_PASSWORD -a bolt://neo4j-core-1:7687 "
  CALL dbms.cluster.overview() YIELD id, role
  RETURN count(*) AS visible_cores
"
# Expected: 2 (the down core won't be visible)

# Recovery: Restart the failed core
kubectl delete pod neo4j-core-3 -n fabric4l

# Wait for it to rejoin
cypher-shell -u neo4j -p $NEO4J_PASSWORD -a bolt://neo4j-core-1:7687 "
  CALL dbms.cluster.overview() YIELD id, role, groups
  RETURN id, role, groups
"
```

#### Case B: Network partition (split brain)

```bash
# If cores are split into two groups that can't communicate:
# - The majority partition continues
# - The minority partition goes into READ-ONLY mode

# Identify which partition has the majority
for core in neo4j-core-1 neo4j-core-2 neo4j-core-3; do
  echo "=== $core ==="
  cypher-shell -u neo4j -p $NEO4J_PASSWORD -a bolt://${core}:7687 "
    CALL dbms.cluster.overview() YIELD id
    RETURN count(*) AS visible_cores
  "
done

# The core that sees the most other cores is in the majority partition.
# Cores in the minority partition need to be restarted to rejoin.

# On minority partition cores, restart and let them rejoin:
kubectl delete pod neo4j-core-minority -n fabric4l --grace-period=60

# If they can't rejoin automatically, may need to seed from majority:
# (This requires careful coordination — consult DBA team lead)
```

#### Case C: Full cluster failure (all cores down)

```bash
# If all cores are down, the cluster must be recovered from backup.

# Check latest backup
ls -la /backups/neo4j/*.backup | tail -5

# Recovery procedure:
# 1. Restore the most recent backup to the first core
kubectl exec -it neo4j-core-1 -n fabric4l -- \
  neo4j-admin database restore --from-path=/backups/neo4j/latest.backup --database=fabric4l

# 2. Start the first core as a seed
kubectl exec -it neo4j-core-1 -n fabric4l -- \
  cypher-shell -u neo4j -p $NEO4J_PASSWORD "
    CREATE DATABASE fabric4l IF NOT EXISTS
  "

# 3. Start other cores and let them join
kubectl rollout restart statefulset/neo4j-core -n fabric4l

# 4. Verify cluster reformation
cypher-shell -u neo4j -p $NEO4J_PASSWORD -a bolt://neo4j-core-1:7687 "
  CALL dbms.cluster.overview() YIELD id, role, groups, databases
  RETURN id, role, databases
"
```

### Step 4: Verify data consistency

```bash
# Run consistency check
cypher-shell -u neo4j -p $NEO4J_PASSWORD -a bolt://neo4j-core-1:7687 "
  CALL dbms.checkDatabaseConsistency('fabric4l')
  YIELD nodeCount, relationshipCount, propertyCount
  RETURN nodeCount, relationshipCount, propertyCount
"

# Compare counts across cores
for core in neo4j-core-1 neo4j-core-2 neo4j-core-3; do
  echo "=== $core ==="
  cypher-shell -u neo4j -p $NEO4J_PASSWORD -a bolt://${core}:7687 "
    MATCH (n) RETURN count(n) AS nodes
  "
  cypher-shell -u neo4j -p $NEO4J_PASSWORD -a bolt://${core}:7687 "
    MATCH ()-[r]->() RETURN count(r) AS relationships
  "
done
# All cores should show the same counts
```

### Step 5: Re-enable read replicas

```bash
# Restart read replicas to reconnect to the new leader
kubectl rollout restart deployment/neo4j-read-replica -n fabric4l

# Verify read replicas are catching up
cypher-shell -u neo4j -p $NEO4J_PASSWORD -a bolt://neo4j-read-replica:7687 "
  CALL dbms.cluster.routing.getServers() YIELD role, addresses
  RETURN role, addresses
"
```

---

## 4. Verification

- [ ] All core servers show `online` status
- [ ] Exactly one LEADER, rest FOLLOWERs
- [ ] Read replicas connected and catching up
- [ ] Write operations succeed
- [ ] Read operations return consistent results
- [ ] Knowledge graph queries (L3) working end-to-end
- [ ] Node/relationship counts match across all cores

---

## 5. Post-Incident Review

**Within 24 hours:**

1. **Timeline:** Document exact sequence of events
2. **Root cause:** Network issue? Resource exhaustion? Configuration change?
3. **Data integrity:** Any data loss? Inconsistencies resolved?
4. **Preventive actions:**
   - Network redundancy review
   - Cluster size adequacy (3 cores minimum, 5 recommended for production)
   - Backup frequency review
   - Monitoring improvements for early detection

**Key metrics:**
- Time to detect partition
- Time to restore full write availability
- Any data loss (should be 0 with Raft)
- Transactions aborted during partition
