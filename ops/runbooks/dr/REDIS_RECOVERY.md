# Runbook: Redis Recovery

| Field | Value |
|---|---|
| **Runbook ID** | DR-CACHE-001 |
| **Service** | Redis (Master-Replica + Sentinel) |
| **Layers Affected** | All layers (L1-L6) — caching and pub/sub |
| **Severity** | P2 - High (cache only, not data loss) |
| **RTO** | 3 minutes |
| **RPO** | N/A (cache — reconstructible from database) |
| **Owner** | SRE On-Call |
| **Last Reviewed** | 2025-01-15 |
| **Version** | v1.2.0 |

---

## 1. Detection

### Alert Triggers

| Alert | Query/Condition | Severity |
|---|---|---|
| `RedisMasterDown` | `redis_up{role="master"} == 0` for 30s | P2 |
| `RedisConnectionTimeout` | `redis_connected_clients` absent for 1m | P2 |
| `RedisMemoryHigh` | `redis_memory_used_bytes / redis_memory_max_bytes > 0.95` for 5m | P2 |
| `RedisReplicationBroken` | `redis_master_link_status == 0` for 2m | P2 |
| `RedisHitRateLow` | `redis_keyspace_hits / (redis_keyspace_hits + redis_keyspace_misses) < 0.5` for 10m | P3 |
| `RedisSlowCommands` | `redis_commands_duration_seconds{quantile="0.99"} > 0.1` for 5m | P3 |

### Dashboard Links
- [Grafana - Redis Overview](https://grafana.fabric4l.io/d/redis-overview)
- [Grafana - Redis Sentinel](https://grafana.fabric4l.io/d/redis-sentinel)

### Verification Command
```bash
# Check Redis master
kubectl -n fabric4l exec redis-master-0 -- redis-cli ping
# Expected: PONG
# If timeout or connection refused, Redis is down

# Check Sentinel
kubectl -n fabric4l exec redis-sentinel-0 -- redis-cli -p 26379 sentinel master fabric4l-redis
# Shows master status and failover state
```

---

## 2. Impact Assessment

### Immediate Impact
- **Cache miss rate jumps to 100%** (all requests hit database)
- **Latency increases 2-5x** for cached endpoints
- **Pub/sub events delayed** (affects real-time features)
- **Rate limiting disabled** (Redis-backed)
- **Session cache unavailable**

### What Still Works
- All database operations continue normally
- No data loss (cache is reconstructible)
- Circuit breakers activate to prevent cascading latency
- Services degrade gracefully (cache-aside pattern)

### Escalation Matrix
| Time | Action |
|---|---|
| T+0 | Alert fires, on-call SRE acknowledges |
| T+3 min | If not auto-recovered, page SRE team lead |
| T+10 min | If Sentinel also failing, manual intervention required |

---

## 3. Prerequisites

- [ ] `kubectl` access to `fabric4l` namespace
- [ ] Redis CLI available in pods
- [ ] Sentinel CLI access
- [ ] SRE contact: `#incidents-sre` Slack channel

---

## 4. Step-by-Step Procedure

### Phase 1: Verify Pod Status (30 seconds)

**Step 1.1: Check Redis pods**
```bash
kubectl -n fabric4l get pods -l app=redis -o wide
# Expected:
# redis-master-0     Running   1/1
# redis-replica-0    Running   1/1
# redis-sentinel-0   Running   1/1
# redis-sentinel-1   Running   1/1
# redis-sentinel-2   Running   1/1
```

**Step 1.2: Check pod events**
```bash
kubectl -n fabric4l describe pod redis-master-0 | grep -A 20 Events
# Look for: OOMKilled, Evicted, NodeNotReady
```

**Step 1.3: Check node resources**
```bash
kubectl top node $(kubectl -n fabric4l get pod redis-master-0 -o jsonpath='{.spec.nodeName}')
# Check if node is under memory pressure
```

### Phase 2: Restart if Needed (1 minute)

**Case A: Pod crashed**
```bash
# Delete pod — StatefulSet recreates with same PVC (data preserved)
kubectl -n fabric4l delete pod redis-master-0 --grace-period=30

# Wait for recreation
kubectl -n fabric4l wait --for=condition=Ready pod/redis-master-0 --timeout=60s

# Verify
kubectl -n fabric4l exec redis-master-0 -- redis-cli ping
# Expected: PONG
```

**Case B: OOMKilled**
```bash
# Check memory limit
kubectl -n fabric4l get pod redis-master-0 -o jsonpath='{.spec.containers[0].resources.limits.memory}'

# Temporarily increase memory limit
kubectl -n fabric4l patch statefulset redis-master -p \
  '{"spec":{"template":{"spec":{"containers":[{"name":"redis","resources":{"limits":{"memory":"2Gi"}}}]}}}}'

# Wait for rollout
kubectl -n fabric4l rollout status statefulset/redis-master --timeout=120s

# Plan: Evaluate if memory limit increase should be permanent
```

**Case C: Sentinel-initiated failover already occurred**
```bash
# Check if Sentinel already promoted replica
kubectl -n fabric4l exec redis-sentinel-0 -- redis-cli -p 26379 sentinel master fabric4l-redis
# Look for: flags = master (not down or s_down)
# If replica was promoted, skip to Phase 3
```

**Case D: Network partition (Redis master isolated)**
```bash
# Check connectivity from replica to master
kubectl -n fabric4l exec redis-replica-0 -- redis-cli -h redis-master-0.redis-master.fabric4l.svc.cluster.local ping
# If timeout, check network

# Force failover via Sentinel
kubectl -n fabric4l exec redis-sentinel-0 -- redis-cli -p 26379 \
  sentinel failover fabric4l-redis

# Verify new master
kubectl -n fabric4l exec redis-sentinel-0 -- redis-cli -p 26379 sentinel master fabric4l-redis
```

### Phase 3: Check Memory (30 seconds)

**Step 3.1: Check memory usage**
```bash
kubectl -n fabric4l exec redis-master-0 -- redis-cli info memory
# Key metrics:
#   used_memory
#   used_memory_rss
#   maxmemory
#   maxmemory_policy

# Check memory fragmentation
kubectl -n fabric4l exec redis-master-0 -- redis-cli info stats | grep fragmentation
# fragmentation_ratio > 1.5 indicates memory fragmentation
```

**Step 3.2: If memory is full**
```bash
# Check eviction policy
kubectl -n fabric4l exec redis-master-0 -- redis-cli config get maxmemory-policy
# Should be: allkeys-lru or allkeys-lfu

# Check key count by pattern
kubectl -n fabric4l exec redis-master-0 -- redis-cli dbsize

# If keys are growing unboundedly, check for cache key leak
kubectl -n fabric4l exec redis-master-0 -- redis-cli --bigkeys

# Emergency: Clear non-critical caches
cat <<'EOF' | kubectl -n fabric4l exec -i redis-master-0 -- redis-cli
EVAL "local keys = redis.call('keys', 'non-critical:*'); for i=1,#keys,5000 do redis.call('del', unpack(keys, i, math.min(i+4999, #keys))); end; return #keys" 0
EOF
```

### Phase 4: Warm Critical Caches (1 minute)

**Step 4.1: Trigger cache warming via L3**
```bash
# Warm knowledge graph cache
curl -X POST http://l3-knowledge:8080/admin/warm-cache \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "cache_types": ["entity_index", "relationship_cache", "tenant_metadata"],
    "concurrency": 10
  }'
```

**Step 4.2: Warm rate limiter state**
```bash
# Rate limiter state is not critical (will rebuild on demand)
# But warm if needed:
curl -X POST http://l1-ingestion:8080/admin/warm-rate-limits \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

**Step 4.3: Monitor cache warming progress**
```bash
watch -n 5 'kubectl -n fabric4l exec redis-master-0 -- redis-cli info stats | grep -E "keyspace_hits|keyspace_misses"'
# Hit rate should climb from 0% toward > 70%
```

### Phase 5: Verify Hit Rate (30 seconds)

**Step 5.1: Check cache metrics**
```bash
# Hit rate
kubectl -n fabric4l exec redis-master-0 -- redis-cli info stats | grep -E "keyspace_hits|keyspace_misses"
# Calculate: hits / (hits + misses) > 0.70

# Connected clients (should be > 0)
kubectl -n fabric4l exec redis-master-0 -- redis-cli info clients | grep connected_clients

# No blocked clients
kubectl -n fabric4l exec redis-master-0 -- redis-cli info clients | grep blocked_clients
# Should be 0
```

**Step 5.2: Verify application health**
```bash
# Check all layers
for layer in l1-ingestion l2-extraction l3-knowledge l4-agent l5-ground-truth l6-benchmark; do
  echo "=== $layer ==="
  kubectl -n fabric4l exec deploy/$layer -- wget -qO- http://localhost:8080/health | jq '.redis'
done
# Expected: All show "connected"
```

**Step 5.3: Verify latency recovery**
```bash
# Test L3 query latency
curl -w "@curl-format.txt" -o /dev/null -s \
  -X POST http://l3-knowledge:8080/search \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "tenant_id": "perf-test"}'
# p99 should be < 500ms
```

---

## 5. Sentinel Recovery (If Sentinel Also Down)

If both Redis and Sentinel are unavailable:

```bash
# 1. Recover Sentinel first
kubectl -n fabric4l delete pod -l app=redis-sentinel --grace-period=30
kubectl -n fabric4l wait --for=condition=Ready pod -l app=redis-sentinel --timeout=60s

# 2. Check if Sentinel remembers the master
kubectl -n fabric4l exec redis-sentinel-0 -- redis-cli -p 26379 sentinel master fabric4l-redis

# 3. If not, manually configure
kubectl -n fabric4l exec redis-sentinel-0 -- redis-cli -p 26379 \
  sentinel monitor fabric4l-redis redis-master-0.redis-master.fabric4l.svc.cluster.local 6379 2
kubectl -n fabric4l exec redis-sentinel-0 -- redis-cli -p 26379 \
  sentinel set fabric4l-redis down-after-milliseconds 5000
kubectl -n fabric4l exec redis-sentinel-0 -- redis-cli -p 26379 \
  sentinel set fabric4l-redis failover-timeout 60000
```

---

## 6. Communication Template

### Internal Slack (#incidents)
```
:yellow_circle: **REDIS RECOVERY IN PROGRESS** — DR-CACHE-001
- Detection: Redis connection timeout (alert: RedisConnectionTimeout)
- Impact: Increased latency, cache misses only (no data loss)
- Action: Redis pod restart / Sentinel failover
- ETA: 3 minutes
- All services operating in degraded mode (no cache)
- Status page: https://status.fabric4l.io
```

---

## 7. Post-Incident Review Template

### Timeline
| Time (UTC) | Event |
|---|---|
| | Alert fired |
| | SRE acknowledged |
| | Recovery action taken |
| | Redis restored |
| | Cache warmed |
| | Incident closed |

### Metrics
- **Actual RTO**: ___ minutes (target: 3)
- **Peak cache miss rate**: ___%
- **Latency increase during outage**: ___x baseline
- **Cache warming time**: ___ minutes
- **Hit rate after recovery**: ___%

### Root Cause
- [ ] Pod crash / panic
- [ ] OOMKilled
- [ ] Node eviction
- [ ] Network partition
- [ ] Memory exhaustion
- [ ] Configuration error
- [ ] Redis bug
- [ ] Other: ___________

### Action Items
| ID | Action | Owner | Due Date | Status |
|---|---|---|---|---|
| | | | | |

### Prevention
- Should memory limits be increased? ___
- Should eviction policy change? ___
- Should cache TTLs be reduced? ___
