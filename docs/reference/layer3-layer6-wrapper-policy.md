# Layer 3 / Layer 6 canonical-vs-wrapper policy

> **SUPERSEDED by [ADR-027](../architecture/adr-027-layer3-canonical-path.md).** This document described the
> pre-ADR-027 policy where `value_fabric/layer{3,6}/` was canonical and `services/layer{3,6}-*/src/` held
> wrappers. Under ADR-027 that direction is **inverted**: canonical runtime is
> `services/layer{N}-*/src/` and `value_fabric/layer{N}/` are path-appender shims. Refer to
> [`layer-runtime-path-governance.md`](layer-runtime-path-governance.md) for the authoritative matrix.
> The mirrored-wrapper / byte-alignment rules below still apply to **legacy** wrapper files that remain registered in
> `scripts/mirrored_files.json`; do not register new wrappers.

## Purpose (historical)

`value_fabric/` was the canonical runtime source for Layer 3 and Layer 6 API modules under the pre-ADR-027 policy.

For Layer 6 specifically, the historical canonical runtime implementation location was:

- `value_fabric/layer6/`

The service-local Layer 6 tree under `services/layer6-benchmarks/src/` was treated as a compatibility-only wrapper tree that preserved deployable import paths while forwarding all implementation to `value_fabric.layer6.*`.

Service-local API modules under:

- `services/layer3-knowledge/src/api/`
- `services/layer6-benchmarks/src/api/`

are compatibility wrappers only, so deployable service import paths remain stable.

## Rules

1. Put implementation changes in canonical modules under:
   - `value_fabric/layer3/api/`
   - `value_fabric/layer6/api/`
2. Keep service-local modules as thin re-exports (`from value_fabric... import *`).
3. Preserve public import surfaces (entrypoints like `api.main`, route modules, and exported symbols).
4. Register every Layer 6 wrapper file in `scripts/mirrored_files.json`. `python scripts/check_mirrored_files.py` enforces byte-alignment against the approved wrapper template generated from the manifest.
5. Non-canonical Layer 6 wrappers must never contain implementation logic; CI enforces this with `python scripts/ci/check_layer6_wrapper_drift.py`.
6. `services/layer6-benchmarks/src/` is a required compatibility tree because Docker and service-local tests still import `src.api.main`. CI must fail if that tree or `src/api/main.py` is missing.

## CI / drift guard

Run:

```bash
python scripts/check_mirrored_files.py
```

The check fails when configured mirrored file pairs diverge.


## Allowed wrapper-only deviations

Wrapper-only edits are allowed **only** for deploy-time bootstrap concerns that cannot live in canonical runtime modules. Current allowed categories are:

1. Service process entry wiring (for example package/module invocation glue specific to `services/layer6-benchmarks`).
2. Deployment metadata outside mirrored runtime files (container manifests, service-local launch scripts, Helm/K8s wiring).

For the mirrored Layer 6 runtime files under:

- `value_fabric/layer6/`
- `services/layer6-benchmarks/src/`

there are currently **no approved content deviations** from the wrapper policy:

- canonical implementation code lives only under `value_fabric/layer6/`
- `services/layer6-benchmarks/src/` files must be manifest-backed thin re-exports
- wrapper bytes must match the generated template enforced by `scripts/check_mirrored_files.py`

If a future exception is required, document it in this file with:

- exact file path(s)
- rationale
- expected removal date or follow-up issue

## Contributor workflow

When adding a new Layer 6 runtime module:

1. Create or update the implementation in `value_fabric/layer6/`.
2. Add the matching service wrapper path to `scripts/mirrored_files.json`.
3. Keep the service wrapper content to the generated two-line template only.
4. Run `python scripts/ci/check_layer6_wrapper_drift.py`, `python scripts/check_mirrored_files.py`, and the targeted `tests/ci/test_layer6_service_src_presence.py` guard.
## Audit artifacts

Layer 6 wrapper drift-audit evidence lives in:

- `docs/contracts/layer6-audit-artifacts/`

Start with:

- `docs/contracts/layer6-audit-artifacts/README.md`
- `docs/contracts/layer6-audit-artifacts/active-milestones.md`

For every active milestone, keep both `report.md` and `checklist.md` under `milestones/<milestone-id>/`.



See also: `docs/reference/layer6-drift-audit-artifact-index.md` for current audit evidence and milestone artifact requirements.


See also: `docs/reference/layer6-drift-audit-artifact-index.md` for current audit evidence and milestone artifact requirements.
