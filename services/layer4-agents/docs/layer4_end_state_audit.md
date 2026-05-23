# Layer 4 End-State Audit (May 23, 2026)

## Scope

This audit evaluates `services/layer4-agents` and `value_fabric/layer4` against the requested hardened end-state for Layer 4 agent orchestration.

## Executive Summary

- **Overall status: PARTIAL**.
- Core foundations exist (tenant-aware tool dispatch, checkpoint-capable LangGraph workflows, typed state, structured tool errors, and prompt version loading).
- The largest gaps are around **explicit replay-conflict policy**, **comprehensive human approval gates for the listed high-impact actions**, **uniform structured reasoning traces at agent-output level**, and **observability completeness (approval wait/stuck-workflow/checkpoint corruption alerting coverage)**.

## Findings Matrix

### 1) Tenant scope for workflows — **PARTIAL**

**What is present**
- Tool execution enforces tenant presence and tenant context consistency with request context. It returns explicit failures on missing/mismatched tenant context.  
- ROI workflow passes tenant context from workflow state into tool calls.

**Evidence**
- `ToolRegistry.execute()` tenant checks and mismatch handling.  
- ROI workflow tenant propagation into tool inputs.

**Gap**
- The base workflow runner accepts arbitrary `initial_state` and does not itself hard-fail if workflow state lacks tenant metadata, so tenant scope is currently strongest at tool boundary rather than guaranteed as a workflow invariant.

### 2) Stable run ID for each workflow run — **PARTIAL**

**What is present**
- `workflow_id` is generated via UUID in base agent state.
- Harness run helper ties LLM attribution to run-like identifiers and tenant context.

**Gap**
- No single, explicit run-ID contract is visibly enforced across *all* workflow types, logs, checkpoints, and output envelopes as a distinct canonical field separate from `workflow_id`.

### 3) Persisted state/checkpointing and resume support — **PARTIAL to STRONG**

**What is present**
- Base workflow supports LangGraph checkpointer injection during compile.
- Workflow state model includes paused/interrupted statuses and resume-related fields.
- Interruption persistence marks interrupted workflows and stores interruption metadata.

**Gap**
- Resume/replay semantics are present in pieces but not fully consolidated into a clearly documented, single policy artifact for operator and engineering governance.

### 4) Idempotency where retries are possible — **PARTIAL**

**What is present**
- Tool registry has idempotency cache keyed by `(tenant_id, tool_name, idempotency_key)`.
- CRM/integration tool categories require `idempotency_key` for irreversible operations.
- Workflow retry behavior exists at node-level (`retry_policy`) and scheduler-level backoff.

**Gap**
- Idempotency guarantees are strongest for tool calls, but end-to-end workflow-level idempotency (including side effects across all high-impact flows) is not uniformly evidenced.

### 5) Human-in-the-loop gates for listed high-impact actions — **PARTIAL**

**What is present**
- Approval-required categories and explicit `APPROVAL_REQUIRED` failures exist in tool registry.
- State model includes pause/resume/human metadata (`paused_by`, `resumed_by`, etc.).

**Gap**
- The required list is action-specific (approve hypotheses, publish business cases, apply benchmark assumptions, generate customer-facing deliverables, change account value models). Current gating is mostly category-based and not yet clearly mapped to all listed actions with explicit policy coverage evidence.

### 6) Replay conflict policy explicitly defined — **GAP**

**What is present**
- Retry and interruption handling exist.

**Gap**
- No explicit, centralized replay-conflict policy definition was identified in the reviewed workflow/runtime code artifacts.

### 7) Tool access permissioned/scoped; no direct DB bypass by agents — **PARTIAL to STRONG**

**What is present**
- Policy-based authorization checks are run per tool action.
- Tool name registry + schema validation limits arbitrary invocation paths.
- Tool execution path is orchestration dispatch, not free-form command execution.

**Gap**
- Strong for the registry path; still requires periodic verification that all agents use governed tool paths and no shadow direct DB access is introduced outside established service/repository contracts.

### 8) Structured reasoning trace outputs — **PARTIAL**

**What is present**
- Tool result envelope includes structured metadata and trace IDs.
- Lifecycle emits tool-call/tool-result events.

**Gap**
- Required trace fields (inputs used, tools called, evidence considered, assumptions, confidence, output object IDs) are not clearly enforced as a uniform agent-output schema across all workflows.

### 9) Schema-validated workflow outputs — **PARTIAL**

**What is present**
- Pydantic models strongly type workflow state and many tool I/O structures.
- Prompt registry supports output schema loading.

**Gap**
- No clear end-to-end enforcement point was identified ensuring final workflow outputs are universally validated against versioned output schemas before release/consumption.

### 10) Safe failure + recoverable error states — **PARTIAL to STRONG**

**What is present**
- Node failures update workflow status/errors and can trigger retries.
- Tool failures use structured safe error results with recoverability flags.
- Interruption persistence supports recoverable states.

**Gap**
- Consistent recoverability playbooks and operator-facing error taxonomy across all workflow types should be made explicit.

### 11) Versioned prompts/workflow definitions — **PARTIAL to STRONG**

**What is present**
- Prompt registry loads prompts from workflow/version paths and frontmatter metadata versioning.
- Workflow types/config classes are structured and extensible.

**Gap**
- Workflow-definition version governance could be made more explicit (e.g., immutable published workflow spec versions + migration policy).

### 12) Inspect/approve/reject/regenerate outputs — **PARTIAL**

**What is present**
- Approval enforcement and pause/resume primitives exist.

**Gap**
- Explicit full lifecycle coverage for inspect/approve/reject/regenerate at output-object granularity is not uniformly evidenced in the reviewed runtime layer.

## Security Requirements Check

- **Tenant-scoped tool calls:** Present in registry checks (strong).  
- **Least privilege:** Policy registry authorization is present, but completeness depends on policy mappings per tool/action (partial).  
- **Prompt injection defenses on retrieved content:** Not clearly evidenced in reviewed files (gap/needs explicit controls).  
- **No arbitrary system commands:** Registry-governed tools reduce risk; no direct arbitrary executor observed in reviewed layer (strong in observed path).  
- **Secrets not exposed to model context:** Sensitive-key redaction helpers and safe metadata behavior are present, but full prompt-context sanitization proof needs broader tracing tests (partial).  
- **Safe user-facing error envelopes:** Structured safe tool errors are present (strong for tool boundary).  
- **No cross-tenant workflow leakage:** tenant mismatch checks are present at tool boundary; workflow-level invariant enforcement still partial.

## Observability Requirements Check

- **Workflow duration/failure/retry metrics:** present in Prometheus workflow + scheduler/retry instrumentation (partial-strong).
- **Approval wait time metric:** not explicitly found (gap).
- **Tool-call count:** present (agent/tool counters, lifecycle events).
- **Model usage metrics:** present (LLM cost/tokens/requests).
- **Log dimensions (workflow ID, run ID, tenant ID, account ID, agent name, tool name, checkpoint ID):** partial; several dimensions exist, but complete required dimension set is not uniformly evidenced.
- **Alerts (stuck workflows, repeated failures, tool auth failures, checkpoint corruption):** alert-specific rules were not confirmed in reviewed source artifacts (gap).

## Prioritized Remediation Plan

1. **Define and publish a canonical replay/conflict policy** (source-of-truth doc + runtime enforcement hooks).
2. **Promote tenant scope from tool boundary to workflow invariant** (reject workflow start without authenticated tenant context).
3. **Standardize a Layer 4 run envelope** with canonical `run_id`, workflow IDs, checkpoint IDs, and trace IDs across logs/outputs/checkpoints.
4. **Implement explicit approval policies for the five required high-impact action classes** (not only category-level).
5. **Enforce a structured “reasoning trace” output schema** with required fields and validation gates.
6. **Add observability gaps**: approval wait time metric, stuck-workflow detection, checkpoint corruption detection, and alerting rules.
7. **Add regression tests** for replay collisions, approval-gate bypass attempts, tenant mismatch, and output schema rejection paths.

## Conclusion

Layer 4 has a meaningful governance and reliability baseline, but it is not yet fully at the hardened end state requested. The most critical improvements are policy explicitness (replay + approvals), end-to-end trace/schema enforcement, and observability/alerting completion.
