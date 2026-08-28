# Disable or Contain Misbehaving Agent Runbook

## Purpose

Use this runbook when an agent loops, emits unsafe output, calls tools outside policy, burns excessive tokens, stalls workflows, or produces customer-visible results that should not be trusted.

## Trigger

Agent loops, unsafe output, unauthorized tool use, anomalous cost, or guardrail alerts.

## Severity

SEV1 for security, destructive-action, or cross-tenant risk; SEV2 for contained customer impact; SEV3 for quality degradation.

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

- `make evals`; AI eval pipeline `run-agent-evals`, `run-golden-traces`, and `deployment-gate`; `tenant-isolation-gate`; `make production-readiness-gate`.

## Related Runbooks

- ../respond-to-prompt-injection.md, ../investigate-hallucinated-business-case.md, ../../observability/alert-triage.md

## Post-Incident Follow-Up

Assign owners and due dates for the root-cause record, corrective tests/alerts/gates, control improvements, customer follow-up, and any required update to this runbook.

## Procedure Details

> **Scope:** Layer 4 agents, LangGraph workflows, tools, skills, and customer-visible agent outputs.  
> **Related runbooks:** `docs/troubleshooting/runbooks/application/agent-workflow-stall.md`, `docs/troubleshooting/runbooks/application/high-llm-cost.md`, `docs/runbooks/agents/respond-to-prompt-injection.md`.

### Purpose

Use this runbook when an agent loops, emits unsafe output, calls tools outside policy, burns excessive tokens, stalls workflows, or produces customer-visible results that should not be trusted.

### Symptoms

- Repeated workflow retries, `GraphRecursionError`, `NodeInterrupt`, checkpoint errors, or stalled executions.
- Tool calls exceed rate limits, mutate unexpected resources, or target the wrong tenant.
- LLM/token spend spikes for one tenant, model, workflow, or agent.
- Guardrails, prompt-injection detectors, or support reports flag unsafe behavior.

### Severity

| Severity | Condition |
|---|---|
| SEV1 | Misbehavior risks data exposure, tenant-boundary violation, destructive action, or broad customer-visible hallucination. |
| SEV2 | A specific workflow/tenant is impacted but containment is available. |
| SEV3 | Non-critical agent quality issue with no security/data impact. |

### Immediate Containment

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

### Diagnosis

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

### Safe Recovery

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

### Escalation

- Security: suspected prompt injection, data exposure, tenant leakage, or unsafe tool action.
- Layer 4 owner: prompt/tool/workflow logic regression.
- FinOps: runaway token spend.
- Customer Operations: customer-visible answer or workflow impact.

### Post-Incident

- Add regression evals for the failed behavior.
- Update tool permissions or tenant-scoping checks if containment relied on manual disablement.
- Update affected runbooks if new containment knobs were needed.
