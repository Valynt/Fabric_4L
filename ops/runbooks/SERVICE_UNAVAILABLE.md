# Runbook: SERVICE_UNAVAILABLE

**Alert:** `ServiceDown`  
**Severity:** Critical  
**Team:** SRE  
**Slack:** #incidents  
**Last Updated:** 2024-06-15

---

## 1. Detection

| Signal | Threshold | Source |
|--------|-----------|--------|
| `up{job=~"l[1-6]-.*"}` | == 0 | Prometheus (blackbox_exporter or kubernetes_sd) |

**Notification:** PagerDuty page after 1 minute of unavailability.

---

## 2. Impact Assessment

### Quick Status Check (within 1 minute)

```bash
# Check service pod status
kubectl get pods -l app=${SERVICE} -n fabric4l -o wide

# Check service endpoints
kubectl get endpoints ${SERVICE} -n fabric4l

# Check recent events
kubectl get events -n fabric4l --field-selector reason!=Scheduled \
  --sort-by='.lastTimestamp' | tail -20
```

### Impact by Layer

| Layer | Port | Critical Path? | Degraded Functionality |
|-------|------|----------------|----------------------|
| L1 Ingestion | 8001 | Yes | No new document ingestion |
| L2 Extraction | 8002 | Yes (downstream of L1) | Entity extraction blocked |
| L3 Knowledge | 8003 | Yes | Graph queries fail, search degraded |
| L4 Agents | 8004 | Partial | No new workflows, existing may continue |
| L5 Ground Truth | 8005 | No | Human validation paused |
| L6 Benchmarks | 8006 | No | Performance testing paused |

---

## 3. Step-by-Step Recovery

### Step 1: Diagnose the cause (0-2 min)

```bash
# Check pod status
kubectl describe pod ${POD_NAME} -n fabric4l

# Common statuses and their meanings:
# CrashLoopBackOff    -> Application crashing, check logs
# ImagePullBackOff    -> Registry issue or bad image tag
# Pending             -> Resource constraints, node issues
# OOMKilled           -> Memory limit too low
# Evicted             -> Node disk/memory pressure
# ContainerCreating   -> Volume mount issue
```

### Step 2: Check logs (2-4 min)

```bash
# Get application logs
kubectl logs ${POD_NAME} -n fabric4l --tail=200 --previous 2>/dev/null || \
kubectl logs ${POD_NAME} -n fabric4l --tail=200

# Get all container logs
kubectl logs ${POD_NAME} -n fabric4l --all-containers --tail=500

# Search for startup errors
grep -iE "error|fatal|panic|traceback|exception" /tmp/service.log
```

### Step 3: Apply fix based on diagnosis

#### Fix A: CrashLoopBackOff (application crash)

```bash
# Check for OOM
kubectl describe pod ${POD_NAME} -n fabric4l | grep -A5 "Last State"

# If OOMKilled, temporarily increase memory
kubectl patch deployment ${SERVICE} -n fabric4l --patch '
{
  "spec": {
    "template": {
      "spec": {
        "containers": [{
          "name": "'${SERVICE}'",
          "resources": {
            "limits": {"memory": "2Gi"},
            "requests": {"memory": "1Gi"}
          }
        }]
      }
    }
  }
}'

# Check for config error causing crash
kubectl get configmap ${SERVICE}-config -n fabric4l -o yaml | head -50
```

#### Fix B: ImagePullBackOff (container image issue)

```bash
# Check which image is being pulled
kubectl describe pod ${POD_NAME} -n fabric4l | grep "Failed to pull"

# Option 1: Roll back to previous image
kubectl rollout undo deployment/${SERVICE} -n fabric4l

# Option 2: Use explicit working image tag
kubectl set image deployment/${SERVICE} \
  ${SERVICE}=${ECR_REGISTRY}/${SERVICE}:${LAST_KNOWN_GOOD_TAG} \
  -n fabric4l
```

#### Fix C: Pending (scheduling issue)

```bash
# Check why pod is pending
kubectl describe pod ${POD_NAME} -n fabric4l | grep -A10 "Events"

# Common fixes:
# Insufficient CPU/memory -> Reduce resource requests or add nodes
kubectl patch deployment ${SERVICE} -n fabric4l --patch '
{
  "spec": {
    "template": {
      "spec": {
        "containers": [{
          "name": "'${SERVICE}'",
          "resources": {
            "requests": {"cpu": "100m", "memory": "256Mi"}
          }
        }]
      }
    }
  }
}'

# Taint/toleration issue -> Add toleration or use different node pool
# PV not available -> Check storage class and PV status
```

#### Fix D: Force restart (last resort)

```bash
# Delete the pod (it will be recreated by the deployment)
kubectl delete pod ${POD_NAME} -n fabric4l --grace-period=30

# Or restart the entire deployment
kubectl rollout restart deployment/${SERVICE} -n fabric4l

# Watch for recovery
kubectl rollout status deployment/${SERVICE} -n fabric4l --timeout=120s
```

### Step 4: Verify recovery

```bash
# Check pod is running
kubectl get pods -l app=${SERVICE} -n fabric4l

# Check health endpoint
kubectl exec -it deploy/${SERVICE} -n fabric4l -- \
  wget -qO- http://localhost:800${LAYER}/health

# Check Prometheus metric
up{job="${SERVICE}"} == 1
```

---

## 4. Verification

- [ ] `up{job="${SERVICE}"}` == 1 for 2 consecutive minutes
- [ ] Health endpoint returns 200 OK
- [ ] `/metrics` endpoint is scrapeable
- [ ] Key API endpoint responds correctly (smoke test)
- [ ] No CrashLoopBackOff or Error statuses in pod description
- [ ] Log volume has returned to normal levels

---

## 5. Post-Incident Review

**Within 24 hours:**

1. **Timeline:**
   - Last successful health check
   - Alert fired
   - Investigation started
   - Root cause identified
   - Fix applied
   - Service recovered

2. **Root cause categories:**
   - Deployment issue?
   - Resource exhaustion?
   - Dependency failure?
   - Configuration error?
   - Infrastructure issue?

3. **Preventive actions:**
   - Add readiness/liveness probe improvements
   - Resource request/limit tuning
   - Deployment automation improvements
   - Circuit breaker configuration

**Required metrics:**
- Total downtime (minutes)
- MTTR (target: < 10 minutes)
- User-facing impact (failed requests)
