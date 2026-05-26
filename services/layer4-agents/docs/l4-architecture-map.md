# Layer 4 Architecture Map (Bounded Contexts)

This map defines bounded contexts for Layer 4 and the intended import boundaries for runtime code under:

- `services/layer4-agents/src/`
- `value_fabric/layer4/`

## Contexts

| Context | Primary modules | Public façade |
|---|---|---|
| Orchestration | `agents/`, `workflows/`, `engine/` | `services/layer4-agents/src/contexts/orchestration/public.py` |
| Tools | `tools/`, `skills/` | `services/layer4-agents/src/contexts/tools/public.py` |
| Memory / checkpointing | `messaging/`, `models/run_envelope.py`, `engine/state_manager.py` | `services/layer4-agents/src/contexts/memory/public.py` |
| Provider adapters | `integration/`, `models/account.py`, `models/integration.py`, `models/crm_sync_job.py` | `services/layer4-agents/src/contexts/providers/public.py` |
| Evaluation | `harness/`, `models/workflow_config.py`, `models/tool_schemas.py` | `services/layer4-agents/src/contexts/evaluation/public.py` |
| API surface | `api/`, `contracts/` | `services/layer4-agents/src/contexts/api_surface/public.py` |

## Dependency rules

High-level rules enforced by `scripts/ci/check_layer4_boundaries.py`:

- `orchestration` may depend on `tools`, `memory`, `providers`, `evaluation`, `api_surface`.
- `tools` may depend on `providers`, `memory`.
- `memory` may depend on `api_surface`.
- `providers` may not import other context internals.
- `evaluation` and `api_surface` may compose across contexts.

Cross-context imports should target `contexts/<context>/public.py` façades instead of deep internal paths.

## Commands

- Report and fail on violations: `make check-layer4-boundaries`
- Included in structural verification (`make verify-structure`) and PR checks workflow.

## Report output

The checker prints:

1. Context dependency violations with file:line and source/target context labels.
2. Top transitive dependency hotspots to highlight modules with the largest downstream coupling.
