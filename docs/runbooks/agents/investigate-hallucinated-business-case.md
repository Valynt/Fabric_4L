# Investigate Hallucinated Business Case Runbook

## Purpose

Use this runbook when a generated business case contains unsupported claims, incorrect customer context, invented metrics, missing/invalid evidence, wrong benchmark peer group, or cross-tenant content.

## Trigger

A customer, evaluator, or evidence validator identifies an unsupported or materially incorrect business-case claim.

## Severity

SEV1 for cross-tenant or regulated-data exposure; SEV2 for published material customer impact; SEV3 for unpublished or isolated quality defects.

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

- `make evals`; AI eval pipeline `run-agent-evals` and `run-golden-traces`; `tenant-isolation-gate`; Layer 3/5 contract and behavior-readiness gates.

## Related Runbooks

- ../disable-or-contain-misbehaving-agent.md, ../respond-to-prompt-injection.md, ../../data-governance/investigate-data-corruption.md

## Post-Incident Follow-Up

Assign owners and due dates for the root-cause record, corrective tests/alerts/gates, control improvements, customer follow-up, and any required update to this runbook.

## Procedure Details

> **Scope:** Business-case generation, ROI narratives, evidence citations, Layer 4 agent output, and Layer 5 ground-truth validation.  
> **Related runbooks:** `docs/runbooks/agents/disable-or-contain-misbehaving-agent.md`, `docs/runbooks/reliability/rebuild-neo4j-projection.md`, `docs/runbooks/reliability/rebuild-vector-index.md`.

### Purpose

Use this runbook when a generated business case contains unsupported claims, incorrect customer context, invented metrics, missing/invalid evidence, wrong benchmark peer group, or cross-tenant content.

### Immediate Actions

1. **Contain distribution.** Remove or mark the affected business case as under review in customer-facing surfaces.
2. **Freeze related workflows for the tenant** if the same prompt/version can generate more faulty cases.
3. **Preserve evidence:** business case ID, tenant ID, workflow trace, model route, prompt version, source citations, benchmark dataset IDs, and generated output.
4. **If cross-tenant data is suspected, page Security immediately** and follow tenant-isolation incident handling.

### Triage Questions

- Is the issue a factual hallucination, stale source context, wrong formula/benchmark, or missing citation?
- Did the output pass Layer 5 TruthObject or evidence validation?
- Are source citations valid, tenant-owned, and accessible?
- Did the agent use the expected prompt, tool schema, model, and retrieval configuration?
- Is the problem isolated to one tenant/business case or reproducible across workflows?

### Investigation

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

### Containment Decision

- **Single bad output:** mark output invalid, regenerate only after validation, and notify account owner.
- **Prompt/tool regression:** disable the agent or workflow using `disable-or-contain-misbehaving-agent.md`.
- **Retrieval/index issue:** rebuild graph/vector derived stores using the reliability runbooks.
- **Formula/benchmark issue:** freeze affected formula or benchmark dataset until governance approval.
- **Tenant leakage:** escalate to Security and treat as SEV1 until disproven.

### Remediation

1. Correct the source-of-truth issue or retrieval configuration.
2. Regenerate with deterministic replay from a clean checkpoint where possible.
3. Run Layer 5 validation and verify every claim has evidence.
4. Have a human reviewer approve customer-visible redistribution.

### Verification

- No unsupported claims remain.
- All citations resolve and are tenant-owned.
- Formula inputs and benchmark peer group match approved source data.
- Replayed workflow passes evals and validation gates.
- Customer-facing copy is updated or withdrawn.

### Customer Handling

Use `docs/runbooks/customer-operations/customer-incident-communication.md` for customer-visible incorrect outputs. Avoid saying “hallucination” externally unless Communications and Legal approve; use factual language such as “incorrect generated business-case content.”

### Evidence to Retain

- Original and corrected business case.
- Workflow trace and model/prompt/tool versions.
- Source records and validation results.
- Customer communication and approvals.
