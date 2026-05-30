# LLM Provider Outage Runbook

> **Scope:** Layer 2 extraction and Layer 4 agent workflows that call approved LLM or embedding providers.  
> **Reused source:** Consolidates the canonical response from `docs/troubleshooting/runbooks/application/llm-provider-outage.md` with agent containment, cost, and customer-safety guidance.

## Symptoms

- Extraction jobs fail, agent responses time out, or workflow queues back up.
- Logs contain `LLM request failed`, `completion failed`, `rate limit`, `429`, or provider SDK errors.
- `layer2_llm_requests_failed_total` rises, `layer4_llm_latency_seconds` exceeds 30 seconds, or cost drops unexpectedly because calls are failing.
- Provider status page reports outage or degraded performance.

## Severity

| Severity | Condition |
|---|---|
| SEV1 | No approved provider can serve production-critical workflows, or unsafe partial answers are reaching customers. |
| SEV2 | Primary provider degraded but approved fallback is available with limited customer impact. |
| SEV3 | Intermittent failures, isolated tenant impact, or non-critical workflow backlog. |

## Diagnosis

```bash
curl -fsS https://status.openai.com/api/v2/status.json | jq
curl -fsS https://status.anthropic.com/api/v2/status.json | jq

kubectl logs -n value-fabric -l app=layer2-extraction --tail=200 | \
  grep -Ei "llm|openai|anthropic|azure|rate limit|429|timeout" || true

kubectl logs -n value-fabric -l app=layer4-agents --tail=200 | \
  grep -Ei "completion failed|provider|model|timeout|retry|circuit" || true

kubectl exec -n value-fabric deployment/layer4-agents -- \
  curl -fsS http://localhost:8000/health | jq '.dependencies'
```

## Immediate Containment

1. **Declare incident and route decisions through the incident thread.**
2. **Enable provider circuit breakers** so workflows fail fast rather than retrying indefinitely:

   ```bash
   kubectl set env deployment/layer4-agents -n value-fabric \
     LLM_CIRCUIT_BREAKER_ENABLED=true \
     LLM_CIRCUIT_BREAKER_THRESHOLD=5
   kubectl rollout restart deployment/layer4-agents -n value-fabric
   ```

3. **Switch to an approved fallback provider/model.** Keep provider-specific logic in adapters and use runtime configuration only:

   ```bash
   kubectl set env deployment/layer4-agents -n value-fabric \
     LLM_PRIMARY_PROVIDER=anthropic \
     LLM_FALLBACK_ENABLED=true
   kubectl rollout restart deployment/layer4-agents -n value-fabric
   ```

4. **Pause non-critical workflows and batch extraction jobs:**

   ```bash
   kubectl exec -n value-fabric deployment/layer4-agents -- \
     curl -X POST http://localhost:8000/api/v1/workflows/pause \
     -H "Content-Type: application/json" \
     -d '{"reason":"llm_provider_outage","priority":"non_critical"}'
   ```

5. **Disable customer-visible generation if safe answers cannot be guaranteed.** Prefer a clear temporary-unavailable response over hallucinated or partial answers.

## Mitigation Options

| Scenario | Action |
|---|---|
| Primary provider outage | Fail over to approved secondary provider. |
| Rate limiting | Reduce concurrency, enable queue backoff, and pause batch workflows. |
| High latency | Lower max tokens for non-critical workflows and use cached responses where approved. |
| Provider cost spike during failover | Coordinate with FinOps and apply model routing guardrails. |
| Embedding provider outage | Disable semantic rebuilds and use lexical/graph fallback for affected tenants. |

## Verification

```bash
kubectl exec -n value-fabric deployment/layer4-agents -- \
  curl -fsS http://localhost:8000/health/llm | jq

kubectl logs -n value-fabric -l app=layer4-agents --since=10m | \
  grep -Ei "fallback_active|workflow_complete|completion failed|rate limit" || true

kubectl exec -n value-fabric deployment/layer4-agents -- \
  curl -X POST http://localhost:8000/api/v1/workflows/resume \
  -H "Content-Type: application/json" \
  -d '{"reason":"llm_provider_recovered","priority":"non_critical"}'
```

Expected result: LLM health is healthy, fallback state is intentional, error rates decline, and one canary workflow completes before broad resume.

## Customer Communication

- If customer-visible generation is unavailable or degraded, use `docs/runbooks/customer-operations/customer-incident-communication.md`.
- Do not name customer tenants or disclose prompts, provider credentials, stack traces, or raw model responses.

## Escalation

- Page Platform if all providers fail or queues exceed safe backlog.
- Page AI platform owner if fallback model quality is below contract.
- Page FinOps if failover materially increases cost.
- Page Security if provider errors expose data or prompt contents.

## Post-Incident

- Record outage window, affected providers/models, fallback effectiveness, tenant impact, and cost impact.
- Add or update provider evals if fallback quality caused customer-visible regressions.
- Review circuit-breaker thresholds and queue backoff settings.
