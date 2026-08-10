# AGENTS — services/layer6-benchmarks (L6, port 8006)

Scoped instructions; universal rules live in the root `AGENTS.md`.

## Responsibility

Peer comparison, statistical validation, datasets, benchmark policies.

## Canonical runtime path

`services/layer6-benchmarks/src/` — all net-new logic lands here (see
`docs/reference/layer-runtime-path-governance.md`). API routes:
`services/layer6-benchmarks/src/layer6_benchmarks/api/routes/`.

## Layer rules

- Preserve benchmark dataset lineage.
- Keep peer comparison and statistical validation explicit.
- Dataset, compare, validate, and industry-list operations are tenant-scoped
  where required.
- Do not mix benchmark definitions with tenant-specific benchmark usage unless
  the model explicitly supports it.
- Compatibility wrappers under `src/` are wrapper-only (no local domain logic);
  CI enforces this via `scripts/ci/check_layer6_wrapper_drift.py`.

## Validation

```bash
make test-layer6
make lint-layer6
make typecheck-layer6
```
