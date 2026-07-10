# Runbook: LLM_RATE_LIMITING

**Alert:** `LLMAPIRateLimit`, `LLMCostSpike`  
**Severity:** Warning  
**Team:** Agents + Cost  
**Slack:** #agents-team  
**Last Updated:** 2024-06-15

---

## 1. Detection

| Signal | Threshold | Source |
|--------|-----------|--------|
| `increase(llm_rate_limit_hits_total[5m])` | > 0 | Prometheus |
| `increase(llm_api_cost_total[1h])` | > $100 | Prometheus |

---

## 2. Impact Assessment

### Check current provider status

```bash
# Check rate limit headers from recent LLM calls
kubectl logs -l app=l4-agents -n fabric4l --tail=100 | \
  grep -i "rate_limit\|x-ratelimit\|429"

# Check rate limit status by provider
sum by (provider) (rate(llm_rate_limit_hits_total[5m]))
```

### Rate limit tiers by provider

| Provider | Tier | RPM | TPM | Daily $ |
|----------|------|-----|-----|---------|
| OpenAI | GPT-4 | 200 | 40k | Varies |
| OpenAI | GPT-4-turbo | 500 | 80k | Varies |
| Anthropic | Claude 3 Opus | 400 | 40k | Varies |
| Anthropic | Claude 3 Sonnet | 1,000 | 100k | Varies |
| Azure OpenAI | Depends on deployment | Configurable | Configurable | Varies |

---

## 3. Step-by-Step Recovery

### Step 1: Identify which provider is rate-limited (0-2 min)

```promql
# Rate limit hits by provider
sum by (provider) (increase(llm_rate_limit_hits_total[1h]))

# Current request rate by provider
sum by (provider) (rate(llm_api_requests_total[5m]))
```

### Step 2: Enable provider fallback (2-5 min)

```bash
# Update config to use fallback provider
kubectl patch configmap l4-agents-config -n fabric4l --patch '
{
  "data": {
    "LLM_PRIMARY_PROVIDER": "anthropic",
    "LLM_FALLBACK_PROVIDER": "openai",
    "LLM_FALLBACK_ON_RATE_LIMIT": "true",
    "LLM_FALLBACK_ON_TIMEOUT": "true"
  }
}'

# Restart agents service
kubectl rollout restart deployment/l4-agents -n fabric4l
```

### Step 3: Reduce request concurrency (5-8 min)

```bash
# Lower max concurrent LLM calls
kubectl patch configmap l4-agents-config -n fabric4l --patch '
{
  "data": {
    "LLM_MAX_CONCURRENT": "5",
    "LLM_REQUEST_QUEUE_SIZE": "100",
    "LLM_TIMEOUT_SECONDS": "60"
  }
}'

kubectl rollout restart deployment/l4-agents -n fabric4l
```

### Step 4: Enable request batching (8-12 min)

```python
# If the workload supports it, enable prompt batching
# Update the batching config via API:
import httpx
httpx.post("http://l4-agents:8004/admin/llm/batching", json={
    "enabled": True,
    "max_batch_size": 10,
    "max_wait_ms": 1000
})
```

### Step 5: If cost spike is the issue

```bash
# Identify which tenant is driving high cost
kubectl exec -it deploy/l4-agents -n fabric4l -- \
  python -c "
from app.cost import get_cost_by_tenant
for tenant, cost in get_cost_by_tenant(hours=1).items():
    print(f'{tenant}: \${cost:.2f}')
"

# Apply emergency rate limit to high-spend tenant
kubectl exec -it deploy/l4-agents -n fabric4l -- \
  python -c "
from app.rate_limit import set_tenant_limit
set_tenant_limit(tenant_id='HIGH_SPEND_TENANT', max_requests_per_hour=100)
"
```

---

## 4. Verification

- [ ] Rate limit hits == 0 for 10 minutes
- [ ] LLM requests succeeding with fallback provider
- [ ] Cost per hour returning to baseline
- [ ] No workflow failures due to LLM issues
- [ ] Queue depth stable

---

## 5. Post-Incident Review

**Within 24 hours:**

1. Document rate limit trigger point
2. Evaluate upgrading provider tier or adding capacity
3. Review request batching effectiveness
4. Update cost monitoring thresholds
5. Consider implementing token bucket rate limiter client-side
