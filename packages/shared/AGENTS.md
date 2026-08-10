# AGENTS — packages/shared (value_fabric.shared)

Scoped instructions; universal rules live in the root `AGENTS.md`.

## Responsibility

The shared Python library consumed by every layer: tenant context, identity,
base models, database helpers, rate limiting, audit, crypto, contracts, and
boundary utilities. Canonical path: `packages/shared/src/value_fabric/shared/`
(the root `shared/` directory was removed — see `src/value_fabric/shared/DEPRECATED.md`).

## Single-writer surface

Shared contracts and tenant-context primitives are **single-writer surfaces**
(`release/v1/launch-contract.yaml`): two agents may not modify this package
concurrently unless the Release Director explicitly sequences the work.

## Rules

- Changes here fan out to all six layers plus the gateway: check every
  consumer (`grep -r "value_fabric.shared" services/`) before altering a
  public symbol; prefer additive changes.
- Tenant-context helpers must fail closed on missing/conflicting context;
  never add a default-tenant fallback.
- Do not import from any `services/*` package (dependency direction is
  shared -> nothing; layers depend on shared, never the reverse).
- Keep provider-specific logic out of this package.

## Validation

```bash
pytest packages/shared/tests
pytest tests/tenancy -q
make check-behavior-contract
make verify   # before PR, since changes fan out widely
```
