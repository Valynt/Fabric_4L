# Disable or Contain Misbehaving Agent Runbook

> **Scope:** Layer 4 agents, LangGraph workflows, tools, skills, and customer-visible agent outputs.  
> **Related runbooks:** `docs/troubleshooting/runbooks/application/agent-workflow-stall.md`, `docs/troubleshooting/runbooks/application/high-llm-cost.md`, `docs/runbooks/agents/respond-to-prompt-injection.md`.

## Purpose

Use this runbook when an agent loops, emits unsafe output, calls tools outside policy, burns excessive tokens, stalls workflows, or produces customer-visible results that should not be trusted.

## Symptoms

- Repeated workflow retries, `GraphRecursionError`, `NodeInterrupt`, checkpoint errors, or stalled executions.
- Tool calls exceed rate limits, mutate unexpected resources, or target the wrong tenant.
- LLM/token spend spikes for one tenant, model, workflow, or agent.
- Guardrails, prompt-injection detectors, or support reports flag unsafe behavior.

## Severity

| Severity | Condition |
|---|---|
| SEV1 | Misbehavior risks data exposure, tenant-boundary violation, destructive action, or broad customer-visible hallucination. |
| SEV2 | A specific workflow/tenant is impacted but containment is available. |
| SEV3 | Non-critical agent quality issue with no security/data impact. |

## Immediate Containment

1. **Freeze the smallest safe scope:** agent ID, workflow type, tenant, tool, or model route.

   ```bash
   <approved-agent-containment-command> \
     --agent-id "<agent-id>" \
     --mode disable-new-runs \
     --reason misbehaving_agent
   ```

2. **Pause running workflows if output or tool calls are unsafe:**

   ```bash
   kubectl exec -n value-fabric deployment/layer4-agents -- \
     curl -X POST http://localhost:8000/api/v1/workflows/pause \
     -H "Content-Type: application/json" \
     -d '{"workflow_type":"<workflow-type>","tenant_ids":["<tenant-id>"],"reason":"agent_containment"}'
   ```

3. **Disable high-risk tools before restarting executors:**

   ```bash
   kubectl set env deployment/layer4-agents -n value-fabric \
     DISABLED_AGENT_TOOLS="<tool-name-1>,<tool-name-2>"
   kubectl rollout restart deployment/layer4-agents -n value-fabric
   ```

4. **Preserve evidence.** Export traces, checkpoints, prompts, tool calls, tenant IDs, and output IDs to the incident evidence store. Do not paste raw customer content into Slack.

## Diagnosis

```bash
kubectl logs -n value-fabric -l app=layer4-agents --since=2h | \
  grep -Ei "agent|workflow|tool|retry|guardrail|checkpoint|hallucination|prompt" || true

kubectl exec -n value-fabric deployment/layer4-agents -- \
  curl -fsS "http://localhost:8000/api/v1/workflows?status=running" | jq

kubectl exec -n value-fabric deployment/layer4-agents -- \
  curl -fsS "http://localhost:8000/api/v1/workflows/<workflow-id>/state" | jq
```

Check:

- Agent version, prompt version, skill/tool manifest version, and model route.
- Whether checkpoint/resume is repeatedly replaying the same unsafe state.
- Whether the tool calls were tenant-scoped and authorized.
- Whether a recent deploy or configuration change altered agent behavior.
- Whether source context from Layer 3/5/6 is stale, missing, or cross-tenant.

## Safe Recovery

1. Patch configuration or roll back to the last approved agent/prompt/model/tool version.
2. Re-run a deterministic replay/eval for the affected trace before unpausing.
3. Resume a single canary tenant/workflow first.
4. Monitor workflow completion, guardrail events, tool calls, token cost, and support tickets for at least 30 minutes.

```bash
kubectl exec -n value-fabric deployment/layer4-agents -- \
  curl -X POST http://localhost:8000/api/v1/workflows/<workflow-id>/restart \
  -H "Content-Type: application/json" \
  -d '{"from_checkpoint":false,"reason":"agent_recovered_canary"}'
```

## Escalation

- Security: suspected prompt injection, data exposure, tenant leakage, or unsafe tool action.
- Layer 4 owner: prompt/tool/workflow logic regression.
- FinOps: runaway token spend.
- Customer Operations: customer-visible answer or workflow impact.

## Post-Incident

- Add regression evals for the failed behavior.
- Update tool permissions or tenant-scoping checks if containment relied on manual disablement.
- Update affected runbooks if new containment knobs were needed.
