# ADR-027: Namespace Shim Removal

## Status

Accepted — 2026-06-04

Implemented — 2026-06-22: root `value_fabric/` and `value_fabric/layer{N}/`
compatibility shims were removed. Shared imports continue to resolve through
the PEP 420 namespace at `packages/shared/src/value_fabric/shared/`.

Supersedes: ADR-021 (canonical path direction)

---

## Context

Per ADR-021, all implementation logic was moved to `services/` trees and `value_fabric/layer{N}/` directories were converted to thin namespace shims for backward compatibility. These shim packages existed at:

- `value_fabric/layer1/` — Layer 1 ingestion compatibility
- `value_fabric/layer2/` — Layer 2 extraction compatibility
- `value_fabric/layer3/` — Layer 3 knowledge graph compatibility
- `value_fabric/layer4/` — Layer 4 agents compatibility
- `value_fabric/layer5/` — Layer 5 ground truth compatibility
- `value_fabric/layer6/` — Layer 6 benchmarks compatibility

Each shim contains only `__init__.py` files that append the corresponding service `src/` path via `__path__` manipulation. No implementation logic resides in these directories.

The CI gates added in ADR-021 (`adr027-duplicate-source-trees`, `adr027-deprecated-namespaces`, `stale-namespace-dirs`) enforce that:

1. No new implementation code is added to shim directories
2. Deleted namespace directories are not reintroduced
3. Non-canonical imports are blocked on PR

---

## Decision

**All `value_fabric/layer{N}/` namespace shims are removed as of 2026-06-22.**

### Removal Schedule

| Phase | Date | Action |
|-------|------|--------|
| 1 | 2026-06-15 | Audit all internal imports; open tracking issues per layer |
| 2 | 2026-07-15 | Migrate all cross-layer imports to service packages |
| 3 | 2026-08-15 | Update CI gates to emit warnings for shim imports |
| 4 | 2026-09-15 | Final notification period for external consumers |
| 5 | 2026-06-22 | Remove all shim directories; archive migration guide |

### Migration Rule

During the migration window, all imports must move off the removed shims and
use service packages or canonical service source roots directly:

| Old (shim, deprecated) | New (canonical) |
|------------------------|-----------------|
| `from value_fabric.layer1 import ...` | `from layer1_ingestion import ...` |
| `from value_fabric.layer2 import ...` | `from layer2_extraction import ...` |
| `from value_fabric.layer3 import ...` | Import from the canonical Layer 3 service source under `services/layer3-knowledge/src/` |
| `from value_fabric.layer4 import ...` | `from layer4_agents import ...` |
| `from value_fabric.layer5 import ...` | `from layer5_ground_truth import ...` |
| `from value_fabric.layer6 import ...` | `from layer6_benchmarks import ...` |

### Why 2026-09-30?

This date aligns with:
- The existing deferred-item schedule in ADR-021
- Quarterly dependency review cycle
- GA release milestone allowing a full deprecation period

---

## Consequences

### Positive

- Eliminates the last source of dual-path ambiguity in the monorepo
- Reduces import-time `__path__` manipulation overhead
- Simplifies onboarding: "implementation lives in `services/`, period"
- Removes a class of accidental-deletion risks
- Enables cleaner IDE resolution (no duplicate module paths)

### Negative

- Any external consumers using `value_fabric.layer{N}` imports will break
- Internal test fixtures and notebooks may need updates
- The root `value_fabric/` compatibility package was deleted; `value_fabric.shared.*` remains available through `packages/shared/src`

### Neutral

- `packages/shared/src/value_fabric/shared/` remains unchanged (shared models, schemas, utilities)
- `value_fabric/__init__.py` path appending logic was removed with the root compatibility package
- Archive documentation will retain the historical context

---

## Alternatives Considered

### Keep shims indefinitely (rejected)

- **Why rejected:** Perpetuates technical debt; ADR-021 explicitly chose service-first as the end state

### Extend deadline to 2026-12-31 (rejected)

- **Why rejected:** ADR-021 already committed to 2026-09-30; deferring creates ambiguity

### Remove shims immediately (rejected)

- **Why rejected:** Need migration period for external consumers and internal audit

---

## Related

- [ADR-021: Layer 3 Canonical Runtime Path](./ADR-021-layer-3-canonical-runtime-path.md) — Original canonical path decision
- `docs/reference/layer-runtime-path-governance.md` — Detailed governance rules
- `tests/arch/test_canonical_module_sentinels.py` — CI enforcement
- `canonical-paths.yaml` — Repository path manifest

---

*Last updated: 2026-06-04 | Status: Accepted*

---

## Addendum — Phase 0 Completion Status (2026-08-29, Sprint 1)

The root `value_fabric/` namespace shims remain removed; no reintroduction was
detected during the Phase 0 ground-truth sweep. Remaining shim-guard machinery:

- `services/layer1-ingestion/src/api/main.py` (Layer 1 api.main shim) is
  removed; `scripts/ci/check_layer1_api_main_shim_drift.py` now passes as a
  tripwire that fails only if the legacy entrypoint is reintroduced.
- `services/layer3-knowledge/src/config.py` (Layer 3 settings shim) still
  exists and remains actively guarded by
  `scripts/ci/check_layer3_settings_shim_drift.py`; removal is pending caller
  migration to the canonical `config/settings.py`.
- The deprecated tracer module (`value_fabric.layer3.tracing.tracer`) is gone;
  GATE-COMPAT-005 (`scripts/ci/check_deprecated_tracer_imports.py`) is retained
  as a tripwire and its registry entry is annotated
  `status: retired — module removed per ADR-027`.
- Duplicate-source-tree and deprecated-namespace guards (GATE-COMPAT-001/003)
  remain fully active.

See `docs/governance/compatibility-debt-registry.md` for the machine-readable
gate inventory and the dated Phase 0 note.
