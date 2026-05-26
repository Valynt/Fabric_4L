# Layer 4 Runtime Durability Policy

This reference documents workflow-start durability behavior for Layer 4 (`services/layer4-agents`).

## Runtime flag

- `REQUIRE_DURABLE_WORKFLOWS` (default: unset / `false`)
- Accepted truthy values: `1`, `true`, `yes`, `on` (case-insensitive)

## Tier behavior

### Enforced durability mode

When `REQUIRE_DURABLE_WORKFLOWS=true`, Layer 4 workflow creation requires an available checkpoint saver.

- If checkpointing is unavailable, workflow creation fails before execution begins.
- The API route returns `503 Service Unavailable` with structured error payload:
  - `error`: `durable_workflow_required`
  - `message`: policy violation detail

### Best-effort durability mode

When `REQUIRE_DURABLE_WORKFLOWS` is not truthy, Layer 4 uses existing best-effort behavior.

- If a checkpoint saver is available, workflows run durably.
- If unavailable, workflows can still start (except existing production-environment guardrails).

## Notes

- This policy is evaluated at workflow start in `engine/executor.py`.
- The API mapping is handled in `src/api/routes/workflows.py`.
