# Respond to Prompt Injection Runbook

> **Scope:** Prompt-injection attempts against Layer 2 extraction, Layer 3 retrieval context, Layer 4 agents, tools, and customer-supplied documents.  
> **Related runbooks:** `disable-or-contain-misbehaving-agent.md`, `investigate-hallucinated-business-case.md`, `docs/troubleshooting/runbooks/incident/data-breach-response.md`.

## Purpose

Use this runbook when customer content, web-ingested content, user prompts, or retrieved evidence attempts to override system instructions, exfiltrate data, bypass tenant boundaries, or manipulate tool calls.

## Indicators

- Guardrail or detector alerts for prompt injection, jailbreak, data exfiltration, or tool misuse.
- Retrieved content includes instructions like “ignore previous instructions,” secret requests, or tool-routing commands.
- Agent attempts unauthorized tool calls or asks for data outside the authenticated tenant.
- Business-case or extraction output cites suspicious instructions rather than factual content.

## Severity

| Severity | Condition |
|---|---|
| SEV1 | Confirmed data exposure, cross-tenant access, or successful unauthorized tool execution. |
| SEV2 | Injection influenced output or workflow behavior but no exposure is confirmed. |
| SEV3 | Attempt blocked by guardrails with no customer impact. |

## Immediate Containment

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

## Investigation

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

## Remediation

- Quarantine or sanitize the source content.
- Re-index/rebuild affected retrieval stores only after malicious content is excluded.
- Tighten tool allowlists, system prompt boundaries, and retrieved-content delimiters.
- Add detector regression cases and agent evals for the injection pattern.
- Regenerate affected outputs from clean context and invalidate unsafe outputs.

## Verification

- Replaying the malicious input triggers guardrail block or safe refusal.
- Tool calls remain denied unless explicitly authorized and tenant-scoped.
- Retrieval no longer returns quarantined chunks.
- No customer-visible outputs contain injected instructions or leaked data.

## Customer / Legal Handling

Security and Legal must approve customer notifications for any suspected data exposure. Use `docs/runbooks/customer-operations/customer-incident-communication.md` for approved updates and do not disclose exploit details.

## Post-Incident

- File a security postmortem for SEV1/SEV2.
- Update prompt-injection detectors and eval coverage.
- Review ingestion allowlists and retrieval sanitization for the source class.
