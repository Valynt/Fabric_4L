# Deprecated Namespace Support Policy: Layer 1 + Layer 3 Compatibility Namespaces

## Scope

This policy governs compatibility shims:

- `value_fabric.layer1_ingestion`
- `value_fabric.layer3_knowledge`

Canonical runtime namespaces are `value_fabric.layer1` and `value_fabric.layer3` respectively.

## Support policy

- Compatibility namespaces remain available for existing callers during migration.
- Every import of deprecated namespaces emits a `DeprecationWarning` with explicit migration guidance.
- New code must not introduce new imports from deprecated namespaces.
- CI enforces zero new internal references by scanning repository Python imports.

## Removal milestones

- **Phase 1 (now, May 12, 2026):** Warnings enabled + CI scanner enabled (report + strict gate).
- **Phase 2 (target: June 30, 2026):** Reduce internal importers to near-zero; keep shims for external/legacy callers only.
- **Phase 3 (target: August 31, 2026):** Remove compatibility namespaces after importer count reaches zero and release notes communicate migration completion.

## Reporting + governance

- CI scanner: `scripts/ci/check_deprecated_namespace_imports.py`
- CI tests: `tests/ci/test_deprecated_namespace_imports.py`
- Progress tracker: `docs/reference/deprecated-namespace-migration-tracker.md`
