---
id: SHARED-ENV-CONSOLIDATION
type: task
title: "Consolidate value_fabric.shared.environment into canonical shared package"
status: open
parent: (none)
assignee: (unassigned)
---

## Description

The fix to copy `environment.py` into `packages/shared/src/value_fabric/shared/environment.py` was accepted as an unblocker for Layer 6 test hardening, but it creates duplicated source of truth if the root-level `value_fabric/shared/environment.py` still exists.

This ticket tracks consolidation of the shared environment module into a single canonical location.

## Acceptance Criteria

- [ ] One canonical implementation lives under `packages/shared/src/value_fabric/shared/environment.py`
- [ ] Any root-level duplicate (`value_fabric/shared/environment.py`) is removed or converted to a compatibility shim
- [ ] Imports resolve consistently in tests and runtime
- [ ] No shadowing between regular package and namespace package paths
- [ ] Compile/import smoke tests pass

## Dependencies

- Layer 6 test hardening PR (completed)

## Notes

- [2026-05-28] coder: Ticket created post-Layer-6 test hardening acceptance. Root-level `value_fabric/shared/environment.py` and `packages/shared/src/value_fabric/shared/environment.py` may be duplicates. Verify import resolution across services/layer1-ingestion through services/layer6-benchmarks before removing either copy.
