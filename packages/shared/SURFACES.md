# Shared Hub Surfaces & Consumer Policy

> Governance note for `packages/shared/src/value_fabric/shared/` (the `value_fabric.shared` kernel).
> Part of the brooks-shared-hub-remediation plan (Steps 1 & 4). This file is the boundary → version
> map and the consumer-policy source of truth; `tests/contract/test_shared_module_consumer_policy.py`
> enforces it in CI.

## Consumer policy (Step 1, R4)

A module may live in `value_fabric.shared` **only** if it has at least one external consumer
(runtime or test) **or** an explicit, justified entry on the allowlist in
`tests/contract/test_shared_module_consumer_policy.py`. Speculative modules (zero consumers)
must be archived.

**Archived in Step 1** (R4 — speculative modules removed; git history preserves them):

| Module | Reason |
|---|---|
| `billing_schemas` | Zero consumers; never reached at runtime. |
| `tracing` | Zero consumers; only a YAML config + README. |
| `tests` | Zero consumers; one orphaned `test_redis_ha.py`. |

**Kept with consumers:**

| Module | Consumers (representative) |
|---|---|
| `testing` | Test-only infra; imported unconditionally by L1/L2/L2-5/L5 conftests and `tests/conftest.py` (test-tree). |
| `projections` | `tests/integration/test_cross_store_consistency.py` (test-tree). |
| `llm_safety` | L1 `source_routes.py`, L2 `llm_client.py`, L4 `thesys_provider.py` + `governed_llm_client.py`, `tests/security`. |

**Allowlisted (zero external consumers, kept out of scope; tracked for future cleanup):**

| Module | Reason |
|---|---|
| `mcp_gateway` | Zero external consumers; outside Step-1 deletion list. |
| `storage` | Zero external consumers; outside Step-1 deletion list. |
| `http_client` | Zero external consumers; outside Step-1 deletion list. |
| `tenant_context_metrics` | Only internal (shared-internal) consumers; outside Step-1 deletion list. |
| `security_middleware` | Test-only consumer `tests/security/test_security_headers.py`; outside Step-1 deletion list. |

## Boundary → version map (Step 4, R2)

The shared hub is partitioned into narrow, independently versioned sub-packages so a change to one
boundary does not force a coordinated release across all nine services. Each boundary below exposes
an explicit public API through its `__init__.py`, carries a `SURFACE_VERSION` marker, and is pinned
in `config/ci/shared_surface_contract.json` by `scripts/ci/check_shared_boundary_surfaces.py` and
`tests/contract/test_shared_boundary_contracts.py`.

A boundary is *versioned* (blue rows) when its exported surface (`__all__`) is pinned. The
`versioned?` column shows the current `SURFACE_VERSION` of governed boundaries; ungoverned rows are
listed for scale awareness and are planned for promotion to a versioned surface when they gain a
contract test.

| Boundary | Role | External consumer scale | Versioned? |
|---|---|---|---|
| `identity` | Tenant/identity context, providers, dependencies | Large (590 refs across services) | `1.0.0` |
| `error_handling` | Structured error types and codes | Large (283 refs) | `1.0.0` |
| `models` | Shared base/Pydantic models | Large (191 refs) | no |
| `audit` | Audit event model | Large (103 refs) | no |
| `security` | Security primitives | Medium (100 refs) | no |
| `observability` | Tracing/metrics hooks | Medium (61 refs) | no |
| `rate_limiting` | Rate-limit policy | Medium (44 refs) | no |
| `fastapi_framework` | FastAPI helpers | Medium (42 refs) | no |
| `crypto` | Cryptographic utilities | Medium (29 refs) | no |
| `secrets` | Secret access | Medium (27 refs) | no |
| `database` | DB/tenant validation helpers | Medium (25 refs) | no |
| `governance` | Governance middleware | Low (18 refs) | no |
| `startup`, `testability`, `boundaries`, `idempotency`, `mcp_gateway`, `resilience`, `storage`, `probes`, `contracts`, `clients`, `infrastructure` | Various | Low (5–16 refs) | no |

Promoting a new boundary to a versioned surface is: add `SURFACE_VERSION = "MAJOR.MINOR.PATCH"`
(outside `__all__`) to its `__init__.py`, add its name to `BOUNDARIES` in
`scripts/ci/check_shared_boundary_surfaces.py`, regenerate the baseline
(`python scripts/ci/check_shared_boundary_surfaces.py --update`), and update this table.

## Change protocol

1. **Adding a module**: it must ship with a consumer (or allowlist entry) and a contract test.
2. **Changing a versioned boundary**: update the boundary's `__init__.py` `__all__` **and** bump its
   `SURFACE_VERSION` marker (a surface change at an unchanged version is refused by
   `scripts/ci/check_shared_boundary_surfaces.py --update` and fails the contract test and the CI
   structural-preflight drift check), then regenerate the baseline
   (`python scripts/ci/check_shared_boundary_surfaces.py --update`) and commit all three together.
   A cross-service change must be coordinated with the version bump (enforced by
   `tests/contract/test_shared_boundary_contracts.py` and the structural-preflight step).
3. **Archiving**: delete + record here; git history preserves the code. If re-added, it needs a real
   consumer and a contract test.
