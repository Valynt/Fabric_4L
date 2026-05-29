# L3 Facade Wrapper Migration Strategy

**Status:** Open - wrapper retention documented
**Created:** 2026-05-29
**Target removal date:** 2026-09-30

## Current Facade-Removal State

Layer 3 is now in the post-neutralization state for repository-level facade removal:

- **Layer shims are neutralized.** `value_fabric/layer3/__init__.py` no longer appends the Layer 3 service source path or acts as a runtime path redirect. It is retained only as an empty namespace placeholder with guidance to use the canonical Layer 3 service modules.
- **L3 service wrappers are intentionally retained.** The remaining Layer 3 service-local wrappers and compatibility surfaces are not accidental facade drift; they are retained to preserve service startup behavior, historical bare-module imports inside `services/layer3-knowledge/src/`, and wrapper compatibility while the service continues its own migration.
- **Target removal date remains 2026-09-30.** No change to the documented wrapper-removal target is made by the facade-neutralization work.

## Scope

This ticket now tracks the intentionally retained Layer 3 wrapper surface, not the already-neutralized `value_fabric.layer3` path shim.

### In Scope

- Maintain documentation for retained Layer 3 service wrappers.
- Track wrapper drift against the 2026-09-30 removal target.
- Migrate or remove service wrappers only when Layer 3 startup, tests, and contract behavior no longer depend on them.
- Preserve explicit compatibility notes for service-local bare imports until those imports are normalized.

### Out of Scope

- Reintroducing `value_fabric.layer3` path bootstrapping.
- Treating neutralized layer shim placeholders as canonical runtime imports.
- Moving Layer 3 runtime logic out of `services/layer3-knowledge/src/`.

## Current Decisions

1. `value_fabric/layer3/__init__.py` remains neutralized and must not append service paths.
2. Canonical Layer 3 runtime code remains under `services/layer3-knowledge/src/`.
3. Layer 3 service wrappers remain intentional until the 2026-09-30 target unless a separate migration proves they can be removed safely earlier.
4. Wrapper cleanup must be validated through Layer 3 startup/import tests and the relevant contract/security suites.

## Acceptance Criteria

- [x] `value_fabric.layer3` shim is neutralized and no longer performs path redirection.
- [x] Retained L3 service wrappers are documented as intentional compatibility surfaces.
- [x] Target removal date remains documented as 2026-09-30.
- [ ] Service wrappers have an owner-approved removal or replacement plan.
- [ ] Layer 3 startup/import tests pass without relying on wrapper behavior before final wrapper removal.
- [ ] Contract/security tests pass after wrapper removal or replacement.

## Validation / Monitoring

Use targeted validation before changing retained wrappers:

```bash
pytest services/layer3-knowledge/tests -q
pytest tests/contract -q
pytest tests/security -q
```

Also keep CI/import-topology checks aligned so no new `value_fabric.layer3` runtime imports are introduced.

## Notes

- [2026-05-29] coder: Updated to reflect current facade-removal state. Layer shims are neutralized; L3 service wrappers are intentionally retained; removal target remains 2026-09-30.
