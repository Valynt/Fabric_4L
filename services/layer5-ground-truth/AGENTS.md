# AGENTS — services/layer5-ground-truth (L5, port 8005)

Scoped instructions; universal rules live in the root `AGENTS.md`.

## Responsibility

TruthObject validation, maturity ladder, evidence-backed claims.

## Canonical runtime path

`services/layer5-ground-truth/src/layer5_ground_truth/` — all net-new logic
lands here (see `docs/reference/layer-runtime-path-governance.md`). API:
`services/layer5-ground-truth/src/layer5_ground_truth/api/`.

## Layer rules

- Preserve TruthObject semantics; claims must remain evidence-backed.
- Maturity ladder logic must be auditable.
- Never weaken validation to make tests pass.
- Tenant context is propagated into every repository call.

## Validation

```bash
make test-layer5
make lint-layer5
make typecheck-layer5
```
