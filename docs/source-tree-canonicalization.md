# Source Tree Canonicalization (Layers 5-6)

> **Updated for [ADR-027](architecture/ADR-021-layer-3-canonical-runtime-path.md).** The earlier revision of this document
> named `value_fabric/layer6/` as the canonical Layer 6 runtime tree. Under ADR-027 the canonical runtime tree
> for every layer is `services/layer{N}-*/src/`. See
> [`reference/layer-runtime-path-governance.md`](reference/layer-runtime-path-governance.md) for the full matrix.

## Ownership

- **Layer 5 canonical runtime modules:** `services/layer5-ground-truth/src/layer5_ground_truth/**`
- **Layer 6 canonical runtime modules:** `services/layer6-benchmarks/src/**`
- **Shim packages:** `value_fabric/layer5/` remains a compatibility shim; `value_fabric/layer6/` is a neutralized namespace placeholder. New code must import canonical service packages directly.
- **Service tree ownership:** `services/layer5-ground-truth/` and `services/layer6-benchmarks/` own implementation, deployment wiring (Dockerfiles, service config, tests, manifests), and any remaining mirrored compatibility wrappers.

## Compatibility policy

- Legacy imports via `value_fabric.layer5.*` and `value_fabric.layer6.*` remain supported via the shim packages.
- New Layer 5 and Layer 6 code must live under `services/layer{5,6}-*/src/` and import canonical modules from `layer5_ground_truth.*` / `layer6_benchmarks.*` (or the `value_fabric.layer{5,6}.*` shim — both resolve to the canonical tree).

## CI drift guards

- `scripts/ci/check_layer56_shims.py` — shim-only compatibility enforcement for mirror paths.
- `scripts/ci/check_stale_namespace_dirs.py` — rejects reintroduction of removed legacy namespaces and verifies shim directories contain only `__init__.py`.
- `scripts/ci/check_layer6_wrapper_drift.py` + `scripts/check_mirrored_files.py` — byte-alignment of registered mirrored wrappers.

These guards fail if local logic is reintroduced into shim files or stale namespace directories return.
