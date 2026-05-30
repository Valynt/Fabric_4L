# Investigate Hallucinated Business Case Runbook

> **Scope:** Business-case generation, ROI narratives, evidence citations, Layer 4 agent output, and Layer 5 ground-truth validation.  
> **Related runbooks:** `docs/runbooks/agents/disable-or-contain-misbehaving-agent.md`, `docs/runbooks/reliability/rebuild-neo4j-projection.md`, `docs/runbooks/reliability/rebuild-vector-index.md`.

## Purpose

Use this runbook when a generated business case contains unsupported claims, incorrect customer context, invented metrics, missing/invalid evidence, wrong benchmark peer group, or cross-tenant content.

## Immediate Actions

1. **Contain distribution.** Remove or mark the affected business case as under review in customer-facing surfaces.
2. **Freeze related workflows for the tenant** if the same prompt/version can generate more faulty cases.
3. **Preserve evidence:** business case ID, tenant ID, workflow trace, model route, prompt version, source citations, benchmark dataset IDs, and generated output.
4. **If cross-tenant data is suspected, page Security immediately** and follow tenant-isolation incident handling.

## Triage Questions

- Is the issue a factual hallucination, stale source context, wrong formula/benchmark, or missing citation?
- Did the output pass Layer 5 TruthObject or evidence validation?
- Are source citations valid, tenant-owned, and accessible?
- Did the agent use the expected prompt, tool schema, model, and retrieval configuration?
- Is the problem isolated to one tenant/business case or reproducible across workflows?

## Investigation

```bash
# Fetch workflow state and trace metadata.
kubectl exec -n value-fabric deployment/layer4-agents -- \
  curl -fsS "http://localhost:8000/api/v1/workflows/<workflow-id>/state" | jq

# Search recent business-case generation logs.
kubectl logs -n value-fabric -l app=layer4-agents --since=2h | \
  grep -Ei "business_case|truth|evidence|benchmark|citation|hallucination" || true

# Check Layer 3 retrieval health for the tenant.
kubectl exec -n value-fabric deployment/layer3-knowledge -- \
  curl -fsS "http://localhost:8000/health" | jq
```

Validate every claim class:

| Claim type | Required validation |
|---|---|
| Customer fact | Must map to tenant-owned source record or approved CRM/source document. |
| ROI formula | Must use approved formula version and documented variable bindings. |
| Benchmark | Must use permitted Layer 6 dataset, peer group, and statistical policy. |
| Evidence citation | Must resolve to tenant-owned evidence with provenance and confidence. |
| Narrative conclusion | Must be grounded in the cited evidence and validated metrics. |

## Containment Decision

- **Single bad output:** mark output invalid, regenerate only after validation, and notify account owner.
- **Prompt/tool regression:** disable the agent or workflow using `disable-or-contain-misbehaving-agent.md`.
- **Retrieval/index issue:** rebuild graph/vector derived stores using the reliability runbooks.
- **Formula/benchmark issue:** freeze affected formula or benchmark dataset until governance approval.
- **Tenant leakage:** escalate to Security and treat as SEV1 until disproven.

## Remediation

1. Correct the source-of-truth issue or retrieval configuration.
2. Regenerate with deterministic replay from a clean checkpoint where possible.
3. Run Layer 5 validation and verify every claim has evidence.
4. Have a human reviewer approve customer-visible redistribution.

## Verification

- No unsupported claims remain.
- All citations resolve and are tenant-owned.
- Formula inputs and benchmark peer group match approved source data.
- Replayed workflow passes evals and validation gates.
- Customer-facing copy is updated or withdrawn.

## Customer Handling

Use `docs/runbooks/customer-operations/customer-incident-communication.md` for customer-visible incorrect outputs. Avoid saying “hallucination” externally unless Communications and Legal approve; use factual language such as “incorrect generated business-case content.”

## Evidence to Retain

- Original and corrected business case.
- Workflow trace and model/prompt/tool versions.
- Source records and validation results.
- Customer communication and approvals.
