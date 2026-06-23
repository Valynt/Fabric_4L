# Layer 4 Legacy Shims

This directory documents legacy shim trees that were removed from the Layer 4 agents service.

## Removed shims

- `services/layer4-agents/src/tenant/` — Legacy flat tenant shim. Superseded by the canonical package at `services/layer4-agents/src/layer4_agents/tenant/` and `services/layer4-agents/src/layer4_agents/tenants/`.
- `services/layer4-agents/workflows/` — Top-level doc-only/legacy workflow tree. Superseded by the canonical package at `services/layer4-agents/src/layer4_agents/workflows/`.

## Removal verification

- Import/search checks confirmed zero live imports from either tree.
- Both directories were deleted via `git rm`.

## See also

- `services/layer4-agents/src/layer4_agents/` — Canonical Layer 4 package.
