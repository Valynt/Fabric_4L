---
id: SHARED-ENV-CONSOLIDATION
type: task
title: "Consolidate value_fabric.shared.environment into canonical shared package"
status: open
parent: (none)
assignee: (unassigned)
---

## Description

During Layer 6 test hardening, `environment.py` was copied into `packages/shared/src/value_fabric/shared/environment.py` to unblock an import failure. This was accepted as a temporary fix.

The root-level `value_fabric/shared/environment.py` likely still exists, creating a duplicated source of truth. This ticket tracks consolidation into a single canonical implementation.

## Desired Final State

- One canonical implementation lives under `packages/shared/src/value_fabric/shared/environment.py`
- The root-level duplicate (`value_fabric/shared/environment.py`) is either removed or converted to a compatibility shim that re-exports from the canonical location
- No shadowing between regular package and namespace package paths

## Acceptance Criteria

- [ ] Canonical implementation confirmed at `packages/shared/src/value_fabric/shared/environment.py`
- [ ] Root-level duplicate removed or converted to a compatibility shim
- [ ] Imports resolve consistently in tests and runtime
- [ ] No shadowing between regular package and namespace package paths
- [ ] Compile/import smoke tests pass across L1–L6

## Dependencies

- Layer 6 test hardening PR (completed)

## Recommended Next Steps

1. Verify whether `value_fabric/shared/environment.py` still exists and whether any runtime or test code imports from the root path.
2. Decide: remove the root-level file (if no consumers) or convert it to a thin compatibility shim that imports from `packages/shared/src/value_fabric/shared/environment.py`.
3. Update any remaining root-level imports to point to the canonical shared package.
4. Run compile/import smoke tests across all layers to confirm no breakage.

## Notes

- [2026-05-28] coder: Ticket created post-Layer-6 test hardening acceptance. Verify import resolution across services/layer1-ingestion through services/layer6-benchmarks before removing either copy.
