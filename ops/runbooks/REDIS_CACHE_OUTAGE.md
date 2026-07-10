# Runbook: REDIS_CACHE_OUTAGE

**Alert:** `RedisUnavailable`, `RedisMemoryHigh`  
**Severity:** Critical  
**Team:** SRE  
**Slack:** #incidents  
**Last Updated:** 2024-06-15

---

## 1. Detection

| Signal | Threshold | Source |
|--------|-----------|--------|
| `redis_up` | == 0 | Prometheus redis_exporter |
| `redis_memory_used_bytes / redis_memory_max_bytes` | > 85% | Prometheus |

---

## 2. Impact Assessment

### Impact scope

| Component | Impact if Redis Down |
|-----------|---------------------|
| Session management | Users logged out, auth failures |
| Rate limiting | No rate limiting (open floodgates) |
| Caching | All requests hit database |
| Distributed locks | Concurrent operations may conflict |
| Pub/sub | Real-time features degraded |

### Quick status check

```bash
# Check Redis pod status
kubectl get pods -l app=redis -n fabric4l -o wide

# Try direct connection
kubectl exec -it deploy/redis -n fabric4l -- redis-cli ping
# Expected: PONG

# Check Redis info
kubectl exec -it deploy/redis -n fabric4l -- redis-cli INFO | head -30
```

---

## 3. Step-by-Step Recovery

### Scenario A: Redis Pod Crash/Restart

```bash
# Check pod events
kubectl describe pod ${REDIS_POD} -n fabric4l | grep -A20 "Events"

# Check if persistent volume is attached
kubectl get pvc redis-data -n fabric4l

# If pod is stuck, delete and let StatefulSet recreate it
kubectl delete pod ${REDIS_POD} -n fabric4l --grace-period=60

# Monitor recovery
kubectl rollout status statefulset/redis -n fabric4l --timeout=120s
```

### Scenario B: Redis Memory Exhaustion

```bash
# Check memory breakdown
kubectl exec -it deploy/redis -n fabric4l -- redis-cli INFO memory

# Check key count and sizes
kubectl exec -it deploy/redis -n fabric4l -- redis-cli DBSIZE

# Find largest keys
kubectl exec -it deploy/redis -n fabric4l -- redis-cli --bigkeys

# Find keys with TTL about to expire
kubectl exec -it deploy/redis -n fabric4l -- redis-cli EVAL '
  local keys = redis.call("keys", "*")
  local soon = {}
  for _, key in ipairs(keys) do
    local ttl = redis.call("ttl", key)
    if ttl > 0 and ttl < 300 then
      table.insert(soon, key .. "=" .. ttl)
    end
  end
  return soon
' 0

# Emergency: Clear non-critical keys
# WARNING: Only clear keys with known prefixes
kubectl exec -it deploy/redis -n fabric4l -- redis-cli EVAL '
  local keys = redis.call("keys", "cache:*")
  for _, key in ipairs(keys) do
    redis.call("del", key)
  end
  return #keys
' 0

# Increase memory limit (if cluster has capacity)
kubectl patch statefulset redis -n fabric4l --patch '
{
  "spec": {
    "template": {
      "spec": {
        "containers": [{
          "name": "redis",
          "resources": {
            "limits": {"memory": "4Gi"},
            "requests": {"memory": "2Gi"}
          }
        }]
      }
    }
  }
}'
```

### Scenario C: Redis Sentinel Failover (HA mode)

```bash
# Check Sentinel status
kubectl exec -it deploy/redis-sentinel -n fabric4l -- \
  redis-cli -p 26379 SENTINEL master mymaster

# Check current master
kubectl exec -it deploy/redis-sentinel -n fabric4l -- \
  redis-cli -p 26379 SENTINEL get-master-addr-by-name mymaster

# If failover didn't happen automatically, force it
kubectl exec -it deploy/redis-sentinel -n fabric4l -- \
  redis-cli -p 26379 SENTINEL failover mymaster

# Verify new master
kubectl exec -it deploy/redis-sentinel -n fabric4l -- \
  redis-cli -p 26379 SENTINEL master mymaster | grep flags
```

### Scenario D: Connection Issues

```bash
# Check if apps can connect to Redis
for pod in $(kubectl get pods -n fabric4l -l layer -o name); do
  echo "=== $pod ==="
  kubectl exec -it $pod -n fabric4l -- \
    python -c "import redis; r = redis.Redis(host='redis'); print(r.ping())"
done

# Check network policies
kubectl get networkpolicies -n fabric4l

# Check service endpoints
kubectl get endpoints redis -n fabric4l
```

### Application-level fallback

When Redis is unavailable, applications should fall back to database-only mode:

```python
# This is handled automatically by the redis-py library
# with retry and fallback configuration:
import redis
from redis.retry import Retry
from redis.backoff import ExponentialBackoff

redis_client = redis.Redis(
    host='redis',
    retry=Retry(ExponentialBackoff(cap=2, base=0.1), 3),
    retry_on_timeout=True,
    health_check_interval=30,
)

# Cache decorator with fallback:
from functools import wraps

def cache_with_fallback(redis_client, ttl=300):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            cache_key = f"{fn.__name__}:{hash(args)}"
            try:
                cached = redis_client.get(cache_key)
                if cached:
                    return json.loads(cached)
            except redis.ConnectionError:
                pass  # Fall through to database
            result = fn(*args, **kwargs)
            try:
                redis_client.setex(cache_key, ttl, json.dumps(result))
            except redis.ConnectionError:
                pass  # Cache update failed, but result is still valid
            return result
        return wrapper
    return decorator
```

---

## 4. Verification

- [ ] `redis_up` == 1
- [ ] `redis_memory_used_bytes / redis_memory_max_bytes` < 80%
- [ ] All application health checks pass
- [ ] Session operations working (test login)
- [ ] Rate limiting functional
- [ ] Cache hit rate returning to normal

---

## 5. Post-Incident Review

**Within 24 hours:**

1. Determine root cause: crash, OOM, network, configuration?
2. Review memory usage trends — was growth expected?
3. Evaluate key expiration policies
4. Consider Redis Cluster vs. standalone architecture
5. Review application fallback behavior effectiveness

**Key metrics:**
- Cache hit rate before/during/after incident
- Database load increase during outage
- User-facing impact (session timeouts, etc.)
