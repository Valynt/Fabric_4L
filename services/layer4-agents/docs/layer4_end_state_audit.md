# Layer 4 End-State Audit (May 25, 2026)

## Scope

This audit evaluates `services/layer4-agents` and `value_fabric/layer4` against hardened Layer 4 orchestration end-state requirements, with runtime-enforcement evidence (not just model/policy declarations).

## Status Legend

- **implemented**: runtime enforcement exists and enforcement tests are present.
- **partially_integrated**: meaningful implementation exists, but coverage or lifecycle integration is incomplete.
- **not_enforced_end_to_end**: policy/design intent may exist, but runtime enforcement and/or E2E proof is missing.

## Machine-Readable Audit Matrix

```yaml
audit_date: 2026-05-25
requirements:
  - id: R1
    requirement: Tenant scope for workflows
    status: partially_integrated
    runtime_enforcement:
      - path: services/layer4-agents/src/core/tool_registry.py
        detail: execute() rejects missing tenant context and tenant mismatches.
      - path: services/layer4-agents/src/workflows/roi_calculator.py
        detail: Workflow passes tenant context into tool call inputs.
    enforcement_tests:
      - path: services/layer4-agents/tests/test_tool_execution_contract.py
        detail: Tenant-context validation and mismatch failures.
  - id: R2
    requirement: Stable run ID per workflow run
    status: partially_integrated
    runtime_enforcement:
      - path: services/layer4-agents/src/workflows/state.py
        detail: workflow_id exists in typed workflow state.
      - path: services/layer4-agents/src/workflows/base.py
        detail: Base state initialization populates workflow identifier.
    enforcement_tests:
      - path: services/layer4-agents/tests/unit/test_workflow_state_machine.py
        detail: Workflow state includes identifiers.
  - id: R3
    requirement: Persisted checkpointing + resume support
    status: implemented
    runtime_enforcement:
      - path: services/layer4-agents/src/workflows/base.py
        detail: LangGraph compile path supports checkpointer injection.
      - path: services/layer4-agents/src/workflows/state.py
        detail: Interrupted/paused/resume fields are represented in state.
    enforcement_tests:
      - path: services/layer4-agents/tests/test_checkpoint_boundary.py
        detail: Checkpoint/resume lifecycle coverage.
  - id: R4
    requirement: Idempotency where retries are possible
    status: partially_integrated
    runtime_enforcement:
      - path: services/layer4-agents/src/core/tool_registry.py
        detail: Tenant-scoped idempotency cache and required idempotency_key for irreversible categories.
      - path: services/layer4-agents/src/workflows/base.py
        detail: Node retry policy and retry-aware execution flow.
    enforcement_tests:
      - path: services/layer4-agents/tests/test_usage_idempotency.py
        detail: Idempotency behavior and required-key enforcement.
  - id: R5
    requirement: Human-in-the-loop gates for high-impact actions
    status: partially_integrated
    runtime_enforcement:
      - path: services/layer4-agents/src/core/tool_registry.py
        detail: Approval-required categories block execution until approved.
      - path: services/layer4-agents/src/workflows/state.py
        detail: Pause/resume actor metadata in workflow state.
    enforcement_tests:
      - path: services/layer4-agents/tests/test_action_level_approval.py
        detail: Approval-required failure semantics.
  - id: R6
    requirement: Explicit replay-conflict policy
    status: not_enforced_end_to_end
    runtime_enforcement:
      - path: services/layer4-agents/src/workflows/base.py
        detail: Retry and interruption mechanics exist, but no centralized replay-conflict policy enforcement gate.
    enforcement_tests: []
  - id: R7
    requirement: Permissioned/scoped tool access and no direct DB bypass by agents
    status: implemented
    runtime_enforcement:
      - path: services/layer4-agents/src/core/tool_registry.py
        detail: Tool allowlisting, schema validation, policy authorization, and governed dispatch.
      - path: services/layer4-agents/src/security/policies.py
        detail: Action-level authorization policy checks.
    enforcement_tests:
      - path: services/layer4-agents/tests/test_tools_authorization.py
        detail: Authorization and denied-action enforcement checks.
  - id: R8
    requirement: Structured reasoning trace outputs
    status: partially_integrated
    runtime_enforcement:
      - path: services/layer4-agents/src/observability/lifecycle_events.py
        detail: Structured lifecycle events include trace metadata for tool execution.
      - path: services/layer4-agents/src/core/tool_registry.py
        detail: Tool result envelopes include structured metadata.
    enforcement_tests:
      - path: services/layer4-agents/tests/test_observability_contract_integration.py
        detail: Structured event envelope assertions.
  - id: R9
    requirement: Schema-validated workflow outputs
    status: partially_integrated
    runtime_enforcement:
      - path: services/layer4-agents/src/prompts/registry.py
        detail: Prompt/output schema loading facilities exist.
      - path: services/layer4-agents/src/workflows/state.py
        detail: Typed state models enforce substantial internal structure.
    enforcement_tests:
      - path: services/layer4-agents/tests/test_workflow_canonical_contract.py
        detail: Schema loading behavior coverage.
  - id: R10
    requirement: Safe failure + recoverable error states
    status: implemented
    runtime_enforcement:
      - path: services/layer4-agents/src/core/tool_registry.py
        detail: Structured safe errors with recoverability semantics.
      - path: services/layer4-agents/src/workflows/base.py
        detail: Failure status/error capture and retry path handling.
    enforcement_tests:
      - path: services/layer4-agents/tests/test_error_handling_paths.py
        detail: Error envelope and recoverable/non-recoverable behavior coverage.
  - id: R11
    requirement: Versioned prompts/workflow definitions
    status: implemented
    runtime_enforcement:
      - path: services/layer4-agents/src/prompts/registry.py
        detail: Prompt loading by workflow/version path with frontmatter metadata.
      - path: services/layer4-agents/src/workflows/types.py
        detail: Workflow type/config structures for controlled evolution.
    enforcement_tests:
      - path: services/layer4-agents/tests/test_workflow_canonical_contract.py
        detail: Versioned prompt loading assertions.
  - id: R12
    requirement: Inspect/approve/reject/regenerate output lifecycle
    status: partially_integrated
    runtime_enforcement:
      - path: services/layer4-agents/src/core/tool_registry.py
        detail: Approval gating exists for protected actions.
      - path: services/layer4-agents/src/workflows/state.py
        detail: Pause/resume fields support human-in-loop transitions.
    enforcement_tests:
      - path: services/layer4-agents/tests/test_action_level_approval.py
        detail: Approval gate enforcement behavior.
```

## Dated Delta Notes

- **2026-05-25**: Recast audit into explicit status classes (`implemented`, `partially_integrated`, `not_enforced_end_to_end`) and added requirement-level runtime enforcement pointers and enforcement-test pointers.
- **2026-05-25**: Added CI gate (`scripts/ci/check_layer4_end_state_audit.py`) to fail when any requirement is labeled `implemented` without enforcement test coverage.
- **2026-05-25**: Marked replay-conflict policy as `not_enforced_end_to_end` pending centralized policy artifact and enforcement hook.

## Residual Risk Focus

1. Replay conflict policy remains non-centralized.
2. Full action-level mapping for all high-impact approval classes is incomplete.
3. Uniform final output reasoning-trace schema enforcement is not yet end-to-end.
