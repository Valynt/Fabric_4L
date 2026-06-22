# DEPRECATED: `value_fabric/` Runtime Compatibility Facades

**REMEDIATION COMPLETE 2026-06-22**

The `value_fabric/layer*` namespace shims have been successfully removed as part of
the strategic remediation plan. All canonical runtime code now lives under:

- `services/layer1-ingestion/`
- `services/layer2-extraction/`
- `services/layer3-knowledge/`
- `services/layer4-agents/`
- `services/layer5-ground-truth/`
- `services/layer6-benchmarks/`
- `packages/shared/src/value_fabric/shared/`

## Remediation Summary

**Phase 1 (Completed):**
- Added runtime deprecation warnings to all shim `__init__.py` files
- Configured CI to capture and archive deprecation warnings
- Generated baseline usage report: 0 shim consumers found

**Phase 2 (Completed):**
- Removed sys.path manipulations from conftest files and test bootstraps
- Refactored build system for PEP 420 implicit namespace packaging
- Updated `value_fabric/__init__.py` for simplified namespace resolution

**Phase 4 (Completed):**
- Extended Ruff config with banned-api rules for deprecated namespace imports across all layers
- Added CI workflow step for Ruff linting enforcement

**Phase 5 (Completed):**
- Verified all non-shim content in layer4/billing and layer5 were neutralized
- Deleted `value_fabric/layer1` through `value_fabric/layer6` directories
- Canonical code already exists in service directories

## Enforcement

PRs attempting to import from `value_fabric.layer*` will now fail:
- At edit-time via Ruff banned-api rules
- At CI-time via runtime canonical import checks
- At lint-time via dedicated CI workflow step

## Migration Guidance

All code must use canonical imports:
- Layer 1: `layer1_ingestion.*`
- Layer 2: `layer2_extraction.*`
- Layer 3: `services/layer3-knowledge/src/ modules`
- Layer 4: `layer4_agents.*`
- Layer 5: `layer5_ground_truth.*`
- Layer 6: `layer6_benchmarks.*`
- Shared: `value_fabric.shared.*` (from `packages/shared/src/value_fabric/shared/`)

Last updated: 2026-06-22
