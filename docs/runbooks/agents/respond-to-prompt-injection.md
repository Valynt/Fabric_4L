# Respond to Prompt Injection Runbook

## Purpose

Use this runbook when customer content, web-ingested content, user prompts, or retrieved evidence attempts to override system instructions, exfiltrate data, bypass tenant boundaries, or manipulate tool calls.

## Trigger

Guardrail alerts, suspicious retrieved instructions, unauthorized tool attempts, or reports of manipulated agent output.

## Severity

SEV1 for successful data/tool compromise or cross-tenant risk; SEV2 for contained attempts affecting production; SEV3 for blocked attempts requiring tuning.

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

- `make evals`; AI eval pipeline `run-agent-evals` and `run-golden-traces`; `tenant-isolation-gate`; mandatory security regression gate; `make production-readiness-gate`.

## Related Runbooks

- ../disable-or-contain-misbehaving-agent.md, ../investigate-hallucinated-business-case.md, ../../security/respond-to-tenant-data-exposure.md

## Post-Incident Follow-Up

Assign owners and due dates for the root-cause record, corrective tests/alerts/gates, control improvements, customer follow-up, and any required update to this runbook.

## Procedure Details

> **Scope:** Prompt-injection attempts against Layer 2 extraction, Layer 3 retrieval context, Layer 4 agents, tools, and customer-supplied documents.  
> **Related runbooks:** `disable-or-contain-misbehaving-agent.md`, `investigate-hallucinated-business-case.md`, `docs/troubleshooting/runbooks/incident/data-breach-response.md`.

### Purpose

Use this runbook when customer content, web-ingested content, user prompts, or retrieved evidence attempts to override system instructions, exfiltrate data, bypass tenant boundaries, or manipulate tool calls.

### Indicators

- Guardrail or detector alerts for prompt injection, jailbreak, data exfiltration, or tool misuse.
- Retrieved content includes instructions like “ignore previous instructions,” secret requests, or tool-routing commands.
- Agent attempts unauthorized tool calls or asks for data outside the authenticated tenant.
- Business-case or extraction output cites suspicious instructions rather than factual content.

### Severity

| Severity | Condition |
|---|---|
| SEV1 | Confirmed data exposure, cross-tenant access, or successful unauthorized tool execution. |
| SEV2 | Injection influenced output or workflow behavior but no exposure is confirmed. |
| SEV3 | Attempt blocked by guardrails with no customer impact. |

### Immediate Containment

1. **Disable affected workflow/tool/tenant scope** using `disable-or-contain-misbehaving-agent.md`.
2. **Quarantine the malicious source content** so it is not used for retrieval or generation:

   ```bash
   <approved-evidence-quarantine-command> \
     --evidence-id "<evidence-id>" \
     --tenant-id "<tenant-id>" \
     --reason prompt_injection
   ```

3. **Preserve evidence** in the incident evidence store, including prompt, retrieved chunks, tool calls, output, and detector result. Redact customer-sensitive content in chat.
4. **Page Security** for SEV1/SEV2 or any suspected data exposure.

### Investigation

```bash
kubectl logs -n value-fabric -l app=layer4-agents --since=2h | \
  grep -Ei "prompt_injection|jailbreak|guardrail|tool_denied|exfiltration" || true

kubectl exec -n value-fabric deployment/layer4-agents -- \
  curl -fsS "http://localhost:8000/api/v1/workflows/<workflow-id>/state" | jq

kubectl exec -n value-fabric deployment/layer3-knowledge -- \
  curl -fsS "http://localhost:8000/api/v1/evidence/<evidence-id>" \
  -H "Authorization: Bearer $TENANT_TOKEN" | jq
```

Determine:

- Injection source: direct prompt, uploaded document, crawled page, retrieved evidence, tool output, or benchmark/formula metadata.
- Whether guardrails blocked, transformed, or allowed the content.
- Whether tool calls were attempted or executed.
- Whether any response included secrets, raw customer data, cross-tenant data, or policy text.
- Which tenants, workflows, and output IDs are affected.

### Remediation

- Quarantine or sanitize the source content.
- Re-index/rebuild affected retrieval stores only after malicious content is excluded.
- Tighten tool allowlists, system prompt boundaries, and retrieved-content delimiters.
- Add detector regression cases and agent evals for the injection pattern.
- Regenerate affected outputs from clean context and invalidate unsafe outputs.

### Verification

- Replaying the malicious input triggers guardrail block or safe refusal.
- Tool calls remain denied unless explicitly authorized and tenant-scoped.
- Retrieval no longer returns quarantined chunks.
- No customer-visible outputs contain injected instructions or leaked data.

### Customer / Legal Handling

Security and Legal must approve customer notifications for any suspected data exposure. Use `docs/runbooks/customer-operations/customer-incident-communication.md` for approved updates and do not disclose exploit details.

### Post-Incident

- File a security postmortem for SEV1/SEV2.
- Update prompt-injection detectors and eval coverage.
- Review ingestion allowlists and retrieval sanitization for the source class.
