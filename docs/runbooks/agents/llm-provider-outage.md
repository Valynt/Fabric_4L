# LLM Provider Outage Runbook

## Purpose

Operate this procedure safely while preserving tenant isolation, evidence, reversibility, and the existing service contract.

## Trigger

Provider health alerts, elevated LLM errors/latency, exhausted quotas, or failed agent/extraction workflows.

## Severity

SEV1 for unsafe or platform-wide failure; SEV2 for major degraded workflows; SEV3 for a provider/model route with a safe fallback.

## Preconditions

- Confirm the incident/request owner, affected environment, authorized tenant scope, and required approvals.
- Verify access to the relevant dashboards, audit records, secrets, backups, and deployment metadata.
- Capture the current version and state before making changes; destructive operations require explicit approval.

## Immediate Actions

1. Stop or freeze the smallest unsafe scope and declare the severity.
2. Preserve logs, traces, audit records, identifiers, configuration, and timestamps before mutation or restart.
3. Notify the owning on-call and Security when authorization, privacy, or tenant isolation may be affected.

## Diagnosis Steps

1. Confirm the trigger, timeline, affected tenants/customers, and last known-good state.
2. Correlate alerts, logs, traces, audit events, recent deployments, configuration changes, and dependency health.
3. Test whether impact is tenant-specific, regional, provider-specific, deployment-specific, or global.

## Resolution Steps

1. Apply the least-risk reversible correction described in the procedure details below.
2. Preserve fail-closed controls, tenant scope, contract compatibility, and auditability.
3. Record commands, approvals, state transitions, and the reason for the selected resolution.

## Validation

- Re-run the related gates and targeted service checks.
- Validate the affected customer path and a known-unaffected control tenant where tenant data is involved.
- Confirm alerts clear, audit evidence is complete, and no new errors or cross-tenant results appear.

## Rollback / Fallback

Return to the captured last known-good deployment, configuration, routing, or data artifact if validation fails. Keep the affected capability contained when no safe fallback preserves security and tenant isolation.

## Customer / Stakeholder Communication

Use the declared severity cadence. Report confirmed scope, customer impact, mitigation, residual risk, and next update time; never include secrets, raw customer data, or another tenant's identifiers.

## Evidence to Preserve

Preserve alert and dashboard snapshots, UTC timestamps, affected tenant/customer IDs, deployment SHAs, sanitized logs/traces, audit events, approvals, commands, gate outputs, and validation results in the incident or request record.

## Related Gates

- `make evals`; AI eval pipeline `run-agent-evals`, `run-skill-evals`, and `deployment-gate`; service readiness probes; `make production-readiness-gate`.

## Related Runbooks

- ../disable-or-contain-misbehaving-agent.md, ../../observability/alert-triage.md, ../../deployment/rollback-production-release.md

## Post-Incident Follow-Up

Assign owners and due dates for the root-cause record, corrective tests/alerts/gates, control improvements, customer follow-up, and any required update to this runbook.

## Procedure Details

> **Scope:** Layer 2 extraction and Layer 4 agent workflows that call approved LLM or embedding providers.  
> **Reused source:** Consolidates the canonical response from `docs/troubleshooting/runbooks/application/llm-provider-outage.md` with agent containment, cost, and customer-safety guidance.

### Symptoms

- Extraction jobs fail, agent responses time out, or workflow queues back up.
- Logs contain `LLM request failed`, `completion failed`, `rate limit`, `429`, or provider SDK errors.
- `layer2_llm_requests_failed_total` rises, `layer4_llm_latency_seconds` exceeds 30 seconds, or cost drops unexpectedly because calls are failing.
- Provider status page reports outage or degraded performance.

### Severity

| Severity | Condition |
|---|---|
| SEV1 | No approved provider can serve production-critical workflows, or unsafe partial answers are reaching customers. |
| SEV2 | Primary provider degraded but approved fallback is available with limited customer impact. |
| SEV3 | Intermittent failures, isolated tenant impact, or non-critical workflow backlog. |

### Diagnosis

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

### Immediate Containment

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

### Mitigation Options

| Scenario | Action |
|---|---|
| Primary provider outage | Fail over to approved secondary provider. |
| Rate limiting | Reduce concurrency, enable queue backoff, and pause batch workflows. |
| High latency | Lower max tokens for non-critical workflows and use cached responses where approved. |
| Provider cost spike during failover | Coordinate with FinOps and apply model routing guardrails. |
| Embedding provider outage | Disable semantic rebuilds and use lexical/graph fallback for affected tenants. |

### Verification

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

### Customer Communication

- If customer-visible generation is unavailable or degraded, use `docs/runbooks/customer-operations/customer-incident-communication.md`.
- Do not name customer tenants or disclose prompts, provider credentials, stack traces, or raw model responses.

### Escalation

- Page Platform if all providers fail or queues exceed safe backlog.
- Page AI platform owner if fallback model quality is below contract.
- Page FinOps if failover materially increases cost.
- Page Security if provider errors expose data or prompt contents.

### Post-Incident

- Record outage window, affected providers/models, fallback effectiveness, tenant impact, and cost impact.
- Add or update provider evals if fallback quality caused customer-visible regressions.
- Review circuit-breaker thresholds and queue backoff settings.
