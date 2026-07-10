# Runbook: SLO_BURN_RATE

**Alert:** `SLOBurnRateFast` / `SLOBurnRateSlow`  
**Severity:** Critical (Fast) / Warning (Slow)  
**Team:** SRE  
**Slack:** #sre-alerts  
**Last Updated:** 2024-06-15

---

## 1. Detection

| Alert | Burn Rate | Budget Exhaustion |
|-------|-----------|-------------------|
| `SLOBurnRateFast` | > 14.4x | ~50 hours at current rate |
| `SLOBurnRateSlow` | > 2x | Before window end |

**Burn rate formula:**
```
Burn Rate = (Error Rate over Short Window) / (Acceptable Error Rate)

14.4x = consumes 2% of budget in 1 hour
2x    = consumes 100% of budget over full window
```

---

## 2. Impact Assessment

### Determine which SLO is burning

```promql
# Check all burn rates
slo_error_budget_burn_rate

# Check budget remaining per SLO
slo:api_availability:error_budget_remaining
slo:agent_workflow_success:error_budget_remaining
```

### Classify the burn

| Burn Type | Pattern | Likely Cause |
|-----------|---------|--------------|
| Fast burn | Sudden spike | Deployment, dependency failure, traffic spike |
| Slow burn | Gradual climb | Memory leak, gradual degradation, capacity limit |
| Periodic | Repeating pattern | Batch jobs, cron schedules, user behavior |

---

## 3. Step-by-Step Recovery

### Step 1: Identify the burning SLO (0-2 min)

```bash
# Check which SLO is burning
open "https://grafana.fabric4l.io/d/fabric4l-platform-overview?viewPanel=5"

# Check the specific error budget panel
```

### Step 2: Identify the cause (2-10 min)

#### For API Availability burn:

```promql
# Which service is failing?
sum by (service) (rate(http_requests_total{status=~"5.."}[1h]))
/
sum by (service) (rate(http_requests_total[1h]))

# Which status codes?
sum by (status) (rate(http_requests_total[1h]))
```

#### For Latency burn:

```promql
# Which endpoints are slow?
topk(10,
  histogram_quantile(0.95,
    sum by (le, path) (rate(http_request_duration_seconds_bucket[1h]))
  )
)
```

#### For Workflow burn:

```promql
# Which workflow types are failing?
sum by (workflow_type) (rate(agent_workflow_failed_total[1h]))
/
sum by (workflow_type) (rate(agent_workflow_total[1h]))
```

### Step 3: Mitigate based on cause

| Cause | Fast Burn Action | Slow Burn Action |
|-------|-----------------|------------------|
| Bad deployment | Rollback immediately | Schedule rollback in maintenance window |
| Traffic spike | Enable rate limiting | Scale up capacity |
| Dependency down | Enable circuit breaker | Escalate to dependency owner |
| Resource exhaustion | Vertical/horizontal scale | Plan capacity increase |
| Code bug | Deploy hotfix | Schedule fix for next sprint |
| Database slow | Query kill + cache warm | Index optimization |

### Step 4: Implement temporary mitigation

```bash
# Enable circuit breaker if downstream is failing
kubectl patch configmap fabric4l-config -n fabric4l --patch '
{
  "data": {
    "CIRCUIT_BREAKER_ENABLED": "true",
    "CIRCUIT_BREAKER_THRESHOLD": "50"
  }
}'

# Scale up if resource-constrained
kubectl scale deployment/${SERVICE} --replicas=6 -n fabric4l

# Enable emergency rate limiting
kubectl patch configmap fabric4l-config -n fabric4l --patch '
{
  "data": {
    "RATE_LIMIT_REQUESTS_PER_MIN": "1000"
  }
}'
```

### Step 5: Monitor recovery

```promql
# Watch burn rate decrease
slo_error_budget_burn_rate

# Confirm error rate returning to normal
slo:api_availability:ratio_5m
```

---

## 4. Verification

- [ ] Burn rate < 1x for 30 consecutive minutes
- [ ] Error budget consumption has stabilized
- [ ] Alert is resolved in Alertmanager
- [ ] No new burn rate alerts firing
- [ ] If release freeze was triggered, document when it can be lifted

---

## 5. Post-Incident Review

### Within 24 hours:

1. **Calculate budget consumed:**
   ```
   Budget consumed = (1 - remaining_budget_at_end) * 100%
   ```

2. **Determine if release freeze is needed:**
   - >50% budget consumed → Consider freeze
   - >75% budget consumed → Recommend freeze
   - 100% budget consumed → Mandatory freeze

3. **Preventive actions:**
   - Add canary deployment gates
   - Improve load testing
   - Add pre-deploy SLO validation
   - Tune alert sensitivity

### Release Freeze Lifting Criteria:

- [ ] Burn rate < 1x for 6+ hours
- [ ] Error budget has stabilized (not decreasing)
- [ ] Root cause fix deployed and verified
- [ ] Engineering lead approval
