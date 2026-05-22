# DEPRECATED: `value_fabric/` Runtime Compatibility Facades

The top-level `value_fabric/` tree is now a compatibility namespace and is **not** a canonical runtime source of truth.

## Canonical Runtime Paths

All runtime code has been migrated to:

- `services/layer1-ingestion/`
- `services/layer2-extraction/`
- `services/layer3-knowledge/`
- `services/layer4-agents/`
- `services/layer5-ground-truth/`
- `services/layer6-benchmarks/`
- `packages/shared/src/value_fabric/shared/`

`value_fabric/shared/` has already been removed. Shared code now lives exclusively in `packages/shared/src/value_fabric/shared/`.

## Deprecation Timeline

- **2026-05-13:** `value_fabric/shared/` removed.
- **2026-05-18:** runtime import guard added at `scripts/ci/check_runtime_canonical_imports.py` to report new non-canonical imports.
- **2026-06-30 (target):** enforce `--strict` mode in CI for runtime package imports once active import count is below threshold.
- **2026-07-31 (target):** remove remaining `value_fabric.layer{1,2,3,4,6}` facade entry points after release-note callout and migration completion.

## Facade Removal Conditions

Facade entry points under `value_fabric/` can be removed when all of the following are true:

1. **Adoption threshold met:** non-canonical runtime imports reported by `scripts/ci/check_runtime_canonical_imports.py` are zero for two consecutive release branches.
2. **Contract safety:** contract tests and service integration tests pass without any import fallback to `value_fabric.layer*` facades.
3. **Migration hygiene:** migration PRs are completed in layer-scoped batches with no API shape changes.
4. **Release communication:** release notes include a compatibility-removal callout with migration guidance.

## Migration Guidance

- Prefer direct imports from service/runtime packages (for example `layer2_extraction...`) instead of `value_fabric.layer*`.
- Migrate by layer-scoped batches and validate targeted test suites before broadening validation.
- If a shim import is intentionally temporary (tests, docs, or compatibility checks), annotate and keep it in explicit allowlists only.

Last updated: 2026-05-18
